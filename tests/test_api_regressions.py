import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from tests.test_support import database, main


class ApiRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(main.app)

    def setUp(self):
        self.connection = database.get_connection()
        self._reset_database()

    def tearDown(self):
        self.connection.close()

    def _reset_database(self):
        cursor = self.connection.cursor()
        for table in (
            "schedule_entries",
            "employee_day_statuses",
            "employee_week_preferences",
            "employee_preferences",
            "coverage_requirements",
            "shift_requirements",
            "employee_positions",
            "shift_templates",
            "positions",
            "employees",
        ):
            cursor.execute(f"DELETE FROM {table}")
        self.connection.commit()
        backup_dir = database.get_backup_dir()
        for backup_path in backup_dir.glob("*.db"):
            backup_path.unlink()

    def _employee_payload(self, **overrides):
        payload = {
            "full_name": "Employee A",
            "sex": "female",
            "min_shifts_per_week": 1,
            "target_shifts_per_week": 3,
            "max_shifts_per_week": 5,
            "can_work_night": True,
            "can_work_weekends": True,
            "can_work_evenings_after_night": True,
            "can_work_mornings_and_evenings": True,
        }
        payload.update(overrides)
        return payload

    def _position_payload(self, **overrides):
        payload = {
            "name": "Nurse",
            "requires_continuous_coverage": False,
            "minimum_staff_presence": 0,
        }
        payload.update(overrides)
        return payload

    def _template_payload(self, **overrides):
        payload = {
            "name": "Morning",
            "category": "morning",
            "start_time": "06:00",
            "end_time": "14:00",
            "is_overnight": False,
            "is_active": True,
            "is_split_only": False,
        }
        payload.update(overrides)
        return payload

    def _create_employee(self, **overrides):
        response = self.client.post("/api/employees", json=self._employee_payload(**overrides))
        self.assertEqual(response.status_code, 200)
        return response.json()["employee"]["id"]

    def _create_position(self, **overrides):
        response = self.client.post("/api/positions", json=self._position_payload(**overrides))
        self.assertEqual(response.status_code, 200)
        return response.json()["position"]["id"]

    def _create_shift_template(self, **overrides):
        response = self.client.post("/api/shift-templates", json=self._template_payload(**overrides))
        self.assertEqual(response.status_code, 200)
        return response.json()["shift_template"]["id"]

    def _save_shift_requirement(self, **overrides):
        payload = {
            "position_id": overrides.pop("position_id"),
            "shift_category": "morning",
            "required_total": 1,
            "required_female_min": 0,
            "required_male_min": 0,
        }
        payload.update(overrides)
        response = self.client.post("/api/shift-requirements", json=payload)
        self.assertEqual(response.status_code, 200)
        return response.json()["requirement"]

    def test_employee_crud_flow_round_trips_flags_and_values(self):
        create_response = self.client.post("/api/employees", json=self._employee_payload())
        self.assertEqual(create_response.status_code, 200)
        employee = create_response.json()["employee"]
        employee_id = employee["id"]
        self.assertEqual(employee["full_name"], "Employee A")

        list_response = self.client.get("/api/employees")
        self.assertEqual(list_response.status_code, 200)
        employees = list_response.json()
        self.assertEqual(len(employees), 1)
        self.assertTrue(employees[0]["can_work_night"])

        update_response = self.client.put(
            f"/api/employees/{employee_id}",
            json=self._employee_payload(
                full_name="Employee A Updated",
                target_shifts_per_week=4,
                can_work_night=False,
            ),
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["employee"]["full_name"], "Employee A Updated")

        list_response = self.client.get("/api/employees")
        updated_employee = list_response.json()[0]
        self.assertEqual(updated_employee["target_shifts_per_week"], 4)
        self.assertFalse(updated_employee["can_work_night"])

        delete_response = self.client.delete(f"/api/employees/{employee_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(self.client.get("/api/employees").json(), [])

    def test_position_crud_blocks_duplicate_names(self):
        position_id = self._create_position()
        duplicate_response = self.client.post("/api/positions", json=self._position_payload())
        self.assertEqual(duplicate_response.status_code, 400)
        self.assertEqual(duplicate_response.json()["detail"], "Position already exists")

        update_response = self.client.put(
            f"/api/positions/{position_id}",
            json=self._position_payload(
                name="Charge Nurse",
                requires_continuous_coverage=True,
                minimum_staff_presence=2,
            ),
        )
        self.assertEqual(update_response.status_code, 200)

        positions = self.client.get("/api/positions").json()
        self.assertEqual(positions[0]["name"], "Charge Nurse")
        self.assertTrue(positions[0]["requires_continuous_coverage"])
        self.assertEqual(positions[0]["minimum_staff_presence"], 2)

    def test_validation_rejects_conflicting_assignment_flags_and_invalid_time_windows(self):
        employee_id = self._create_employee()
        position_id = self._create_position()

        assignment_response = self.client.post(
            "/api/employee-positions",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "is_primary": True,
                "priority_score": 100,
                "is_fallback_only": True,
            },
        )
        self.assertEqual(assignment_response.status_code, 422)

        template_response = self.client.post(
            "/api/shift-templates",
            json=self._template_payload(start_time="14:00", end_time="06:00", is_overnight=False),
        )
        self.assertEqual(template_response.status_code, 422)

        coverage_response = self.client.post(
            "/api/coverage-requirements",
            json={
                "position_id": position_id,
                "start_time": "14:00",
                "end_time": "06:00",
                "required_total": 1,
                "required_female_min": 0,
                "required_male_min": 0,
                "is_overnight": False,
            },
        )
        self.assertEqual(coverage_response.status_code, 422)

    def test_shift_template_crud_and_active_filter(self):
        template_id = self._create_shift_template()

        update_response = self.client.put(
            f"/api/shift-templates/{template_id}",
            json=self._template_payload(
                name="Morning Inactive",
                is_active=False,
            ),
        )
        self.assertEqual(update_response.status_code, 200)

        all_templates = self.client.get("/api/shift-templates").json()
        self.assertEqual(len(all_templates), 1)
        self.assertFalse(all_templates[0]["is_active"])

        active_templates = self.client.get("/api/shift-templates", params={"active_only": True}).json()
        self.assertEqual(active_templates, [])

        delete_response = self.client.delete(f"/api/shift-templates/{template_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(self.client.get("/api/shift-templates").json(), [])

    def test_weekly_preference_upsert_and_delete(self):
        employee_id = self._create_employee()

        create_response = self.client.post(
            "/api/employee-week-preferences",
            json={
                "employee_id": employee_id,
                "week_start_date": "2026-04-20",
                "preference_date": "2026-04-21",
                "preference_type": "off_day",
            },
        )
        self.assertEqual(create_response.status_code, 200)

        update_response = self.client.post(
            "/api/employee-week-preferences",
            json={
                "employee_id": employee_id,
                "week_start_date": "2026-04-20",
                "preference_date": "2026-04-21",
                "preference_type": "vacation",
            },
        )
        self.assertEqual(update_response.status_code, 200)

        list_response = self.client.get(
            "/api/employee-week-preferences",
            params={"week_start_date": "2026-04-20"},
        )
        self.assertEqual(list_response.status_code, 200)
        preferences = list_response.json()
        self.assertEqual(len(preferences), 1)
        self.assertEqual(preferences[0]["preference_type"], "vacation")

        delete_response = self.client.delete(
            "/api/employee-week-preferences",
            params={"employee_id": employee_id, "preference_date": "2026-04-21"},
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["deleted_count"], 1)

    def test_schedule_entry_status_and_clear_week_flow(self):
        employee_id = self._create_employee()
        position_id = self._create_position()
        template_id = self._create_shift_template()

        assignment_response = self.client.post(
            "/api/employee-positions",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "is_primary": True,
                "priority_score": 100,
                "is_fallback_only": False,
            },
        )
        self.assertEqual(assignment_response.status_code, 200)

        day_status_response = self.client.post(
            "/api/employee-day-statuses",
            json={
                "employee_id": employee_id,
                "date": "2026-04-20",
                "status_type": "day_off",
            },
        )
        self.assertEqual(day_status_response.status_code, 200)

        create_response = self.client.post(
            "/api/schedule",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "date": "2026-04-20",
                "shift_template_id": template_id,
            },
        )
        self.assertEqual(create_response.status_code, 200)
        schedule_entry_id = create_response.json()["schedule_entry"]["id"]

        status_response = self.client.patch(
            f"/api/schedule/{schedule_entry_id}/status",
            json={"no_show": True},
        )
        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(status_response.json()["no_show"])

        schedule_entries = self.client.get("/api/schedule").json()
        self.assertEqual(len(schedule_entries), 1)
        self.assertTrue(schedule_entries[0]["no_show"])

        clear_response = self.client.post(
            "/api/schedule/clear-week",
            json={
                "position_id": position_id,
                "week_start_date": "2026-04-20",
            },
        )
        self.assertEqual(clear_response.status_code, 200)
        self.assertEqual(clear_response.json()["deleted_count"], 1)
        self.assertEqual(self.client.get("/api/schedule").json(), [])
        self.assertEqual(self.client.get("/api/employee-day-statuses").json(), [])

    def test_manual_schedule_edits_keep_day_off_status_in_sync(self):
        employee_id = self._create_employee()
        position_id = self._create_position()
        template_id = self._create_shift_template()

        response = self.client.post(
            "/api/employee-positions",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "is_primary": True,
                "priority_score": 100,
                "is_fallback_only": False,
            },
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/employee-day-statuses",
            json={
                "employee_id": employee_id,
                "date": "2026-04-20",
                "status_type": "day_off",
            },
        )
        self.assertEqual(response.status_code, 200)

        create_response = self.client.post(
            "/api/schedule",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "date": "2026-04-20",
                "shift_template_id": template_id,
            },
        )
        self.assertEqual(create_response.status_code, 200)
        schedule_entry_id = create_response.json()["schedule_entry"]["id"]

        day_statuses = self.client.get("/api/employee-day-statuses").json()
        self.assertEqual(day_statuses, [])

        delete_response = self.client.delete(f"/api/schedule/{schedule_entry_id}")
        self.assertEqual(delete_response.status_code, 200)

        day_statuses = self.client.get("/api/employee-day-statuses").json()
        self.assertEqual(len(day_statuses), 1)
        self.assertEqual(day_statuses[0]["employee_id"], employee_id)
        self.assertEqual(day_statuses[0]["date"], "2026-04-20")
        self.assertEqual(day_statuses[0]["status_type"], "day_off")

    def test_manual_edits_after_auto_generation_restore_day_off_for_removed_shift(self):
        employee_id = self._create_employee(full_name="Employee A")
        position_id = self._create_position()
        template_id = self._create_shift_template()

        response = self.client.post(
            "/api/employee-positions",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "is_primary": True,
                "priority_score": 100,
                "is_fallback_only": False,
            },
        )
        self.assertEqual(response.status_code, 200)

        self._save_shift_requirement(position_id=position_id)

        generate_response = self.client.post(
            "/api/schedule/auto-generate",
            json={"position_id": position_id, "week_start_date": "2026-04-20"},
        )
        self.assertEqual(generate_response.status_code, 200)
        self.assertEqual(generate_response.json()["created_count"], 5)

        generated_entries = self.client.get("/api/schedule").json()
        monday_entry = next(entry for entry in generated_entries if entry["date"] == "2026-04-20")

        delete_response = self.client.delete(f"/api/schedule/{monday_entry['id']}")
        self.assertEqual(delete_response.status_code, 200)

        day_statuses = self.client.get("/api/employee-day-statuses").json()
        monday_status = next(
            status
            for status in day_statuses
            if status["employee_id"] == employee_id and status["date"] == "2026-04-20"
        )
        self.assertEqual(monday_status["status_type"], "day_off")

    def test_app_settings_persist_generation_weights_and_display_mode(self):
        initial_response = self.client.get("/api/app-settings")
        self.assertEqual(initial_response.status_code, 200)
        initial_settings = initial_response.json()
        self.assertEqual(initial_settings["schedule_coverage_display_mode"], "interval")
        self.assertEqual(initial_settings["coverage_shortage_gain_weight"], 100)
        self.assertEqual(initial_settings["balance_target_distance_weight"], 70)

        update_response = self.client.put(
            "/api/app-settings",
            json={
                "schedule_coverage_display_mode": "category",
                "coverage_shortage_gain_weight": 180,
                "balance_target_distance_weight": 95,
                "after_night_evening_penalty": 1600,
            },
        )
        self.assertEqual(update_response.status_code, 200)

        stored_settings = update_response.json()["settings"]
        self.assertEqual(stored_settings["schedule_coverage_display_mode"], "category")
        self.assertEqual(stored_settings["coverage_shortage_gain_weight"], 180)
        self.assertEqual(stored_settings["balance_target_distance_weight"], 95)
        self.assertEqual(stored_settings["after_night_evening_penalty"], 1600)

        direct_read = main.get_app_settings(self.connection)
        self.assertEqual(direct_read["schedule_coverage_display_mode"], "category")
        self.assertEqual(direct_read["coverage_shortage_gain_weight"], 180)
        self.assertEqual(direct_read["balance_target_distance_weight"], 95)
        self.assertEqual(direct_read["after_night_evening_penalty"], 1600)

    def test_auto_generate_end_to_end_for_two_positions_fills_full_week(self):
        template_id = self._create_shift_template()
        self.assertIsInstance(template_id, int)

        ward_a_id = self._create_position(name="Ward A")
        ward_b_id = self._create_position(name="Ward B")

        employee_ids = [
            self._create_employee(full_name="Employee A"),
            self._create_employee(full_name="Employee B"),
            self._create_employee(full_name="Employee C"),
            self._create_employee(full_name="Employee D"),
        ]

        for employee_id in employee_ids[:2]:
            response = self.client.post(
                "/api/employee-positions",
                json={
                    "employee_id": employee_id,
                    "position_id": ward_a_id,
                    "is_primary": True,
                    "priority_score": 100,
                    "is_fallback_only": False,
                },
            )
            self.assertEqual(response.status_code, 200)

        for employee_id in employee_ids[2:]:
            response = self.client.post(
                "/api/employee-positions",
                json={
                    "employee_id": employee_id,
                    "position_id": ward_b_id,
                    "is_primary": True,
                    "priority_score": 100,
                    "is_fallback_only": False,
                },
            )
            self.assertEqual(response.status_code, 200)

        self._save_shift_requirement(position_id=ward_a_id)
        self._save_shift_requirement(position_id=ward_b_id)

        generate_a = self.client.post(
            "/api/schedule/auto-generate",
            json={"position_id": ward_a_id, "week_start_date": "2026-04-20"},
        )
        self.assertEqual(generate_a.status_code, 200)

        generate_b = self.client.post(
            "/api/schedule/auto-generate",
            json={"position_id": ward_b_id, "week_start_date": "2026-04-20"},
        )
        self.assertEqual(generate_b.status_code, 200)

        for response in (generate_a, generate_b):
            payload = response.json()
            self.assertEqual(payload["created_count"], 7)
            self.assertEqual(payload["feasibility_report"]["status"], "ok")
            self.assertEqual(payload["unfilled_reports"], [])

        schedule_entries = self.client.get("/api/schedule").json()
        self.assertEqual(len(schedule_entries), 14)
        self.assertEqual({entry["position_id"] for entry in schedule_entries}, {ward_a_id, ward_b_id})
        self.assertEqual({entry["date"] for entry in schedule_entries}, {
            "2026-04-20",
            "2026-04-21",
            "2026-04-22",
            "2026-04-23",
            "2026-04-24",
            "2026-04-25",
            "2026-04-26",
        })

    def test_auto_generate_spreads_night_shifts_evenly_between_night_staff(self):
        night_template_id = self._create_shift_template(
            name="Night",
            category="night",
            start_time="23:00",
            end_time="07:00",
            is_overnight=True,
        )
        self.assertIsInstance(night_template_id, int)

        position_id = self._create_position(name="Night Ward")
        employee_ids = [
            self._create_employee(full_name="Vaheed", sex="male", target_shifts_per_week=3, max_shifts_per_week=7),
            self._create_employee(full_name="Employee B", sex="female", target_shifts_per_week=3, max_shifts_per_week=7),
            self._create_employee(full_name="Employee C", sex="male", target_shifts_per_week=3, max_shifts_per_week=7),
        ]

        for employee_id in employee_ids:
            response = self.client.post(
                "/api/employee-positions",
                json={
                    "employee_id": employee_id,
                    "position_id": position_id,
                    "is_primary": True,
                    "priority_score": 100,
                    "is_fallback_only": False,
                },
            )
            self.assertEqual(response.status_code, 200)

        self._save_shift_requirement(
            position_id=position_id,
            shift_category="night",
            required_total=1,
            required_female_min=0,
            required_male_min=0,
        )

        generate_response = self.client.post(
            "/api/schedule/auto-generate",
            json={"position_id": position_id, "week_start_date": "2026-04-20"},
        )
        self.assertEqual(generate_response.status_code, 200)
        self.assertEqual(generate_response.json()["unfilled_reports"], [])

        schedule_entries = self.client.get(
            "/api/schedule",
            params={"position_id": position_id, "week_start_date": "2026-04-20"},
        ).json()

        self.assertEqual(len(schedule_entries), 7)
        self.assertTrue(all(entry["shift_category"] == "night" for entry in schedule_entries))

        counts: dict[str, int] = {}
        for entry in schedule_entries:
            counts[entry["employee_name"]] = counts.get(entry["employee_name"], 0) + 1

        self.assertEqual(set(counts.keys()), {"Vaheed", "Employee B", "Employee C"})
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)

    def test_auto_generate_avoids_locking_same_shift_type_to_one_employee(self):
        self._create_shift_template(name="Morning", category="morning", start_time="06:00", end_time="14:00")
        self._create_shift_template(name="Evening", category="evening", start_time="14:00", end_time="20:00")

        position_id = self._create_position(name="Mixed Ward")
        employee_ids = [
            self._create_employee(full_name="Employee A", target_shifts_per_week=4, max_shifts_per_week=7),
            self._create_employee(full_name="Employee B", target_shifts_per_week=4, max_shifts_per_week=7),
        ]

        for employee_id in employee_ids:
            response = self.client.post(
                "/api/employee-positions",
                json={
                    "employee_id": employee_id,
                    "position_id": position_id,
                    "is_primary": True,
                    "priority_score": 100,
                    "is_fallback_only": False,
                },
            )
            self.assertEqual(response.status_code, 200)

        self._save_shift_requirement(
            position_id=position_id,
            shift_category="morning",
            required_total=1,
            required_female_min=0,
            required_male_min=0,
        )
        self._save_shift_requirement(
            position_id=position_id,
            shift_category="evening",
            required_total=1,
            required_female_min=0,
            required_male_min=0,
        )

        generate_response = self.client.post(
            "/api/schedule/auto-generate",
            json={"position_id": position_id, "week_start_date": "2026-04-20"},
        )
        self.assertEqual(generate_response.status_code, 200)
        self.assertEqual(len(generate_response.json()["unfilled_reports"]), 2)

        schedule_entries = self.client.get(
            "/api/schedule",
            params={"position_id": position_id, "week_start_date": "2026-04-20"},
        ).json()

        self.assertEqual(len(schedule_entries), 12)

        counts: dict[str, dict[str, int]] = {}
        for entry in schedule_entries:
            counts.setdefault(entry["employee_name"], {"morning": 0, "evening": 0, "night": 0})
            counts[entry["employee_name"]][entry["shift_category"]] += 1

        for employee_name in ("Employee A", "Employee B"):
            self.assertGreater(counts[employee_name]["morning"], 0)
            self.assertGreater(counts[employee_name]["evening"], 0)

    def test_export_excel_for_empty_week_has_headers_and_zero_total(self):
        employee_id = self._create_employee(full_name="Employee A")
        position_id = self._create_position()
        response = self.client.post(
            "/api/employee-positions",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "is_primary": True,
                "priority_score": 100,
                "is_fallback_only": False,
            },
        )
        self.assertEqual(response.status_code, 200)

        export_response = self.client.get(
            "/api/schedule/export-excel",
            params={"week_start_date": "2026-04-20", "position_id": position_id, "lang": "en"},
        )
        self.assertEqual(export_response.status_code, 200)

        workbook = load_workbook(filename=main.BytesIO(export_response.content))
        worksheet = workbook.active
        self.assertEqual(worksheet["A1"].value, "Schedule export - Nurse - week starting 2026-04-20")
        self.assertEqual(worksheet["A3"].value, "Employee")
        self.assertEqual(worksheet["I5"].value, 0)

    def test_export_excel_includes_shift_no_show_and_day_off_labels(self):
        employee_id = self._create_employee(full_name="Employee A")
        position_id = self._create_position()
        morning_id = self._create_shift_template(name="Morning")
        evening_id = self._create_shift_template(
            name="Evening",
            category="evening",
            start_time="14:00",
            end_time="20:00",
        )

        response = self.client.post(
            "/api/employee-positions",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "is_primary": True,
                "priority_score": 100,
                "is_fallback_only": False,
            },
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/schedule",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "date": "2026-04-20",
                "shift_template_id": morning_id,
            },
        )
        self.assertEqual(response.status_code, 200)
        entry_id = response.json()["schedule_entry"]["id"]

        response = self.client.post(
            "/api/schedule",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "date": "2026-04-21",
                "shift_template_id": evening_id,
            },
        )
        self.assertEqual(response.status_code, 200)
        no_show_entry_id = response.json()["schedule_entry"]["id"]

        response = self.client.patch(f"/api/schedule/{no_show_entry_id}/status", json={"no_show": True})
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/employee-day-statuses",
            json={
                "employee_id": employee_id,
                "date": "2026-04-22",
                "status_type": "day_off",
            },
        )
        self.assertEqual(response.status_code, 200)

        export_response = self.client.get(
            "/api/schedule/export-excel",
            params={"week_start_date": "2026-04-20", "position_id": position_id, "lang": "ru"},
        )
        self.assertEqual(export_response.status_code, 200)

        workbook = load_workbook(filename=main.BytesIO(export_response.content))
        worksheet = workbook.active
        self.assertEqual(worksheet["B5"].value, "Morning")
        self.assertEqual(worksheet["C5"].value, "Неявка")
        self.assertEqual(worksheet["D5"].value, "Выходной")
        self.assertEqual(worksheet["I5"].value, 1)
        summary_sheet = workbook["Summary"]
        self.assertEqual(summary_sheet["A1"].value, "Coordinator summary")
        self.assertEqual(summary_sheet["B3"].value, "Nurse")
        self.assertEqual(summary_sheet["B6"].value, 2)
        self.assertEqual(summary_sheet["B8"].value, 1)
        self.assertEqual(summary_sheet["B10"].value, 1)

    def test_delete_impact_endpoints_report_related_records(self):
        employee_id = self._create_employee(full_name="Employee A")
        position_id = self._create_position()
        template_id = self._create_shift_template(name="Morning")

        response = self.client.post(
            "/api/employee-positions",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "is_primary": True,
                "priority_score": 100,
                "is_fallback_only": False,
            },
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/employee-preferences",
            json={
                "employee_id": employee_id,
                "allow_morning": True,
                "allow_evening": True,
                "allow_night": True,
                "allow_morning_evening_combo": True,
            },
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/employee-week-preferences",
            json={
                "employee_id": employee_id,
                "week_start_date": "2026-04-20",
                "preference_date": "2026-04-21",
                "preference_type": "vacation",
            },
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/employee-day-statuses",
            json={
                "employee_id": employee_id,
                "date": "2026-04-22",
                "status_type": "day_off",
            },
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/shift-requirements",
            json={
                "position_id": position_id,
                "shift_category": "morning",
                "required_total": 1,
                "required_female_min": 0,
                "required_male_min": 0,
            },
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/coverage-requirements",
            json={
                "position_id": position_id,
                "start_time": "06:00",
                "end_time": "14:00",
                "required_total": 1,
                "required_female_min": 0,
                "required_male_min": 0,
                "is_overnight": False,
            },
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/schedule",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "date": "2026-04-20",
                "shift_template_id": template_id,
            },
        )
        self.assertEqual(response.status_code, 200)

        employee_impact = self.client.get(f"/api/employees/{employee_id}/delete-impact")
        self.assertEqual(employee_impact.status_code, 200)
        self.assertEqual(
            employee_impact.json(),
            {
                "employee_id": employee_id,
                "employee_name": "Employee A",
                "assignments": 1,
                "schedule_entries": 1,
                "general_preferences": 1,
                "weekly_preferences": 1,
                "day_statuses": 1,
            },
        )

        position_impact = self.client.get(f"/api/positions/{position_id}/delete-impact")
        self.assertEqual(position_impact.status_code, 200)
        self.assertEqual(position_impact.json()["position_name"], "Nurse")
        self.assertEqual(position_impact.json()["assignments"], 1)
        self.assertEqual(position_impact.json()["schedule_entries"], 1)
        self.assertEqual(position_impact.json()["shift_requirements"], 1)
        self.assertEqual(position_impact.json()["coverage_requirements"], 1)

        assignment_impact = self.client.get(
            "/api/employee-positions/delete-impact",
            params={"employee_id": employee_id, "position_id": position_id},
        )
        self.assertEqual(assignment_impact.status_code, 200)
        self.assertEqual(assignment_impact.json()["employee_name"], "Employee A")
        self.assertEqual(assignment_impact.json()["position_name"], "Nurse")
        self.assertEqual(assignment_impact.json()["schedule_entries"], 1)

        template_impact = self.client.get(f"/api/shift-templates/{template_id}/delete-impact")
        self.assertEqual(template_impact.status_code, 200)
        self.assertEqual(template_impact.json()["template_name"], "Morning")
        self.assertEqual(template_impact.json()["schedule_entries"], 1)

    def test_clear_week_preview_reports_entries_and_day_off_statuses(self):
        employee_id = self._create_employee(full_name="Employee A")
        position_id = self._create_position(name="Ward A")
        template_id = self._create_shift_template()

        response = self.client.post(
            "/api/employee-positions",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "is_primary": True,
                "priority_score": 100,
                "is_fallback_only": False,
            },
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/schedule",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "date": "2026-04-20",
                "shift_template_id": template_id,
            },
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/employee-day-statuses",
            json={
                "employee_id": employee_id,
                "date": "2026-04-21",
                "status_type": "day_off",
            },
        )
        self.assertEqual(response.status_code, 200)

        preview_response = self.client.get(
            "/api/schedule/clear-week-preview",
            params={"position_id": position_id, "week_start_date": "2026-04-20"},
        )
        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(
            preview_response.json(),
            {
                "position_id": position_id,
                "position_name": "Ward A",
                "week_start_date": "2026-04-20",
                "assigned_employees": 1,
                "schedule_entries": 1,
                "day_off_statuses": 1,
            },
        )

    def test_get_base_path_uses_meipass_in_frozen_mode(self):
        with patch.object(main.sys, "frozen", True, create=True), patch.object(
            main.sys,
            "_MEIPASS",
            str(Path("D:/fake_bundle")),
            create=True,
        ):
            self.assertEqual(main.get_base_path(), Path("D:/fake_bundle"))

    def test_database_backup_create_list_restore_round_trip(self):
        employee_id = self._create_employee(full_name="Employee A")
        self.assertIsInstance(employee_id, int)

        create_backup = self.client.post("/api/database/backups", json={"label": "manual"})
        self.assertEqual(create_backup.status_code, 200)
        backup_name = create_backup.json()["backup_name"]

        backup_list = self.client.get("/api/database/backups")
        self.assertEqual(backup_list.status_code, 200)
        self.assertTrue(any(item["name"] == backup_name for item in backup_list.json()["backups"]))

        delete_response = self.client.delete(f"/api/employees/{employee_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(self.client.get("/api/employees").json(), [])

        restore_response = self.client.post("/api/database/restore", json={"backup_name": backup_name})
        self.assertEqual(restore_response.status_code, 200)

        employees = self.client.get("/api/employees").json()
        self.assertEqual(len(employees), 1)
        self.assertEqual(employees[0]["full_name"], "Employee A")

    def test_delete_employee_cascades_related_records_and_returns_backup_name(self):
        employee_id = self._create_employee(full_name="Employee A")
        position_id = self._create_position()
        template_id = self._create_shift_template()

        response = self.client.post(
            "/api/employee-positions",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "is_primary": True,
                "priority_score": 100,
                "is_fallback_only": False,
            },
        )
        self.assertEqual(response.status_code, 200)

        self.client.post(
            "/api/employee-preferences",
            json={
                "employee_id": employee_id,
                "allow_morning": True,
                "allow_evening": True,
                "allow_night": True,
                "allow_morning_evening_combo": True,
            },
        )
        self.client.post(
            "/api/employee-week-preferences",
            json={
                "employee_id": employee_id,
                "week_start_date": "2026-04-20",
                "preference_date": "2026-04-21",
                "preference_type": "vacation",
            },
        )
        self.client.post(
            "/api/employee-day-statuses",
            json={"employee_id": employee_id, "date": "2026-04-22", "status_type": "day_off"},
        )
        self.client.post(
            "/api/schedule",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "date": "2026-04-20",
                "shift_template_id": template_id,
            },
        )

        delete_response = self.client.delete(f"/api/employees/{employee_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertTrue(delete_response.json()["backup_name"])
        self.assertEqual(self.client.get("/api/employees").json(), [])
        self.assertEqual(self.client.get("/api/employee-positions").json(), [])
        self.assertEqual(self.client.get("/api/schedule").json(), [])
        self.assertEqual(self.client.get("/api/employee-day-statuses").json(), [])
        preferences = self.client.get("/api/employee-week-preferences", params={"week_start_date": "2026-04-20"}).json()
        self.assertEqual(preferences, [])

    def test_delete_position_cascades_related_records_and_returns_backup_name(self):
        employee_id = self._create_employee(full_name="Employee A")
        position_id = self._create_position(name="Ward A")
        template_id = self._create_shift_template()

        self.client.post(
            "/api/employee-positions",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "is_primary": True,
                "priority_score": 100,
                "is_fallback_only": False,
            },
        )
        self.client.post(
            "/api/shift-requirements",
            json={
                "position_id": position_id,
                "shift_category": "morning",
                "required_total": 1,
                "required_female_min": 0,
                "required_male_min": 0,
            },
        )
        self.client.post(
            "/api/coverage-requirements",
            json={
                "position_id": position_id,
                "start_time": "06:00",
                "end_time": "14:00",
                "required_total": 1,
                "required_female_min": 0,
                "required_male_min": 0,
                "is_overnight": False,
            },
        )
        self.client.post(
            "/api/schedule",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "date": "2026-04-20",
                "shift_template_id": template_id,
            },
        )

        delete_response = self.client.delete(f"/api/positions/{position_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertTrue(delete_response.json()["backup_name"])
        self.assertEqual(self.client.get("/api/positions").json(), [])
        self.assertEqual(self.client.get("/api/employee-positions").json(), [])
        self.assertEqual(self.client.get("/api/shift-requirements").json(), [])
        self.assertEqual(self.client.get("/api/coverage-requirements").json(), [])
        self.assertEqual(self.client.get("/api/schedule").json(), [])

    def test_delete_shift_template_in_use_is_blocked_and_plain_delete_returns_backup_name(self):
        template_id = self._create_shift_template(name="Morning")
        employee_id = self._create_employee()
        position_id = self._create_position()
        self.client.post(
            "/api/employee-positions",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "is_primary": True,
                "priority_score": 100,
                "is_fallback_only": False,
            },
        )
        self.client.post(
            "/api/schedule",
            json={
                "employee_id": employee_id,
                "position_id": position_id,
                "date": "2026-04-20",
                "shift_template_id": template_id,
            },
        )

        in_use_delete = self.client.delete(f"/api/shift-templates/{template_id}")
        self.assertEqual(in_use_delete.status_code, 400)

        self.client.post(
            "/api/schedule/clear-week",
            json={"position_id": position_id, "week_start_date": "2026-04-20"},
        )
        delete_response = self.client.delete(f"/api/shift-templates/{template_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertTrue(delete_response.json()["backup_name"])


if __name__ == "__main__":
    unittest.main()
