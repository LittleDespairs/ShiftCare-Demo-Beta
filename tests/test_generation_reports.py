import unittest
from tests.test_support import database, main
from tests.fixtures.fixed_week import WEEK_DATES, WEEK_START_DATE  # noqa: E402


class GenerationReportTests(unittest.TestCase):
    def setUp(self):
        self.connection = database.get_connection()
        cursor = self.connection.cursor()
        for table in (
            "schedule_entries",
            "employee_day_statuses",
            "employee_recurring_preferences",
            "employee_week_preferences",
            "employee_preferences",
            "coverage_requirements",
            "shift_requirements",
            "employee_positions",
            "shift_templates",
            "positions",
            "employees",
            "app_settings",
        ):
            cursor.execute(f"DELETE FROM {table}")
        self.connection.commit()

    def tearDown(self):
        self.connection.close()

    def test_day_off_sync_creates_status_for_unworked_days_only(self):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM schedule_entries")
        cursor.execute("DELETE FROM employee_day_statuses")
        cursor.execute("DELETE FROM shift_templates")
        cursor.execute("DELETE FROM positions")
        cursor.execute("DELETE FROM employees")
        cursor.execute(
            """
            INSERT INTO employees (
                id,
                full_name,
                sex,
                min_shifts_per_week,
                target_shifts_per_week,
                max_shifts_per_week,
                can_work_night,
                can_work_weekends,
                can_work_evenings_after_night,
                can_work_mornings_and_evenings
            )
            VALUES (1, 'Employee A', 'female', 0, 3, 5, 1, 1, 1, 1)
            """
        )
        cursor.execute("INSERT INTO positions (id, name) VALUES (1, 'Nurse')")
        cursor.execute(
            """
            INSERT INTO shift_templates (id, position_id, name, category, start_time, end_time, is_overnight, is_active, is_split_only)
            VALUES (1, 1, 'Morning', 'morning', '06:00', '14:00', 0, 1, 0)
            """
        )
        cursor.execute(
            """
            INSERT INTO schedule_entries (employee_id, position_id, date, shift_template_id)
            VALUES (1, 1, ?, 1)
            """,
            (WEEK_DATES[0],),
        )
        cursor.execute(
            """
            INSERT INTO employee_day_statuses (employee_id, date, status_type)
            VALUES (1, ?, 'sick')
            """,
            (WEEK_DATES[1],),
        )

        inserted = main.sync_generated_day_off_statuses(
            self.connection,
            cursor,
            [{"id": 1}],
            1,
            WEEK_DATES[:3],
        )

        cursor.execute(
            """
            SELECT date, status_type
            FROM employee_day_statuses
            WHERE employee_id = 1
            ORDER BY date
            """
        )
        statuses = [(row["date"], row["status_type"]) for row in cursor.fetchall()]

        self.assertEqual(inserted, 1)
        self.assertEqual(statuses, [(WEEK_DATES[1], "sick"), (WEEK_DATES[2], "day_off")])

    def test_day_off_sync_does_not_create_day_off_for_no_show_shift(self):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM schedule_entries")
        cursor.execute("DELETE FROM employee_day_statuses")
        cursor.execute("DELETE FROM shift_templates")
        cursor.execute("DELETE FROM positions")
        cursor.execute("DELETE FROM employees")
        cursor.execute(
            """
            INSERT INTO employees (
                id,
                full_name,
                sex,
                min_shifts_per_week,
                target_shifts_per_week,
                max_shifts_per_week,
                can_work_night,
                can_work_weekends,
                can_work_evenings_after_night,
                can_work_mornings_and_evenings
            )
            VALUES (1, 'Employee A', 'female', 0, 3, 5, 1, 1, 1, 1)
            """
        )
        cursor.execute("INSERT INTO positions (id, name) VALUES (1, 'Nurse')")
        cursor.execute(
            """
            INSERT INTO shift_templates (id, position_id, name, category, start_time, end_time, is_overnight, is_active, is_split_only)
            VALUES (1, 1, 'Morning', 'morning', '06:00', '14:00', 0, 1, 0)
            """
        )
        cursor.execute(
            """
            INSERT INTO schedule_entries (employee_id, position_id, date, shift_template_id, no_show)
            VALUES (1, 1, ?, 1, 1)
            """,
            (WEEK_DATES[0],),
        )

        inserted = main.sync_generated_day_off_statuses(
            self.connection,
            cursor,
            [{"id": 1}],
            1,
            WEEK_DATES[:1],
        )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM employee_day_statuses
            WHERE employee_id = 1 AND date = ?
            """,
            (WEEK_DATES[0],),
        )
        count = cursor.fetchone()[0]

        self.assertEqual(inserted, 0)
        self.assertEqual(count, 0)

    def test_feasibility_reports_blocking_male_staff_shortage(self):
        employees = [
            {
                "id": 1,
                "full_name": "Employee A",
                "sex": "female",
                "min_shifts_per_week": 0,
                "target_shifts_per_week": 3,
                "max_shifts_per_week": 5,
                "can_work_night": True,
                "can_work_weekends": True,
                "can_work_evenings_after_night": True,
                "can_work_mornings_and_evenings": True,
                "is_primary": True,
                "priority_score": 50,
                "is_fallback_only": False,
            }
        ]
        templates = [
            {
                "id": 1,
                "name": "Morning",
                "category": "morning",
                "start_time": "06:00",
                "end_time": "14:00",
                "is_overnight": False,
                "is_active": True,
                "is_split_only": False,
            }
        ]
        coverage_requirements = [
            {
                "id": 1,
                "position_id": 1,
                "start_time": "06:00",
                "end_time": "14:00",
                "required_total": 1,
                "required_female_min": 0,
                "required_male_min": 1,
                "is_overnight": False,
            }
        ]

        report = main.build_generation_feasibility_report(
            self.connection,
            employees,
            templates,
            coverage_requirements,
            [],
            1,
            WEEK_START_DATE,
            WEEK_DATES,
        )

        self.assertEqual(report["status"], "blocking")
        self.assertTrue(any(issue["kind"] == "male_staff" for issue in report["issues"]))
        self.assertTrue(all(issue["constraint_type"] == "hard" for issue in report["hard_constraints"]))
        self.assertEqual(report["soft_constraints"], [])

    def test_feasibility_report_blocks_when_required_staff_exceeds_available_staff(self):
        employees = [
            {
                "id": 1,
                "full_name": "Employee A",
                "sex": "female",
                "min_shifts_per_week": 0,
                "target_shifts_per_week": 3,
                "max_shifts_per_week": 5,
                "can_work_night": True,
                "can_work_weekends": True,
                "can_work_evenings_after_night": True,
                "can_work_mornings_and_evenings": True,
                "is_primary": True,
                "priority_score": 50,
                "is_fallback_only": False,
            }
        ]
        templates = [
            {
                "id": 1,
                "name": "Morning",
                "category": "morning",
                "start_time": "06:00",
                "end_time": "14:00",
                "is_overnight": False,
                "is_active": True,
                "is_split_only": False,
            }
        ]
        coverage_requirements = [
            {
                "id": 1,
                "position_id": 1,
                "start_time": "06:00",
                "end_time": "14:00",
                "required_total": 2,
                "required_female_min": 0,
                "required_male_min": 0,
                "is_overnight": False,
            }
        ]

        report = main.build_generation_feasibility_report(
            self.connection,
            employees,
            templates,
            coverage_requirements,
            [],
            1,
            WEEK_START_DATE,
            WEEK_DATES,
        )

        self.assertEqual(report["status"], "blocking")
        self.assertTrue(any(issue["kind"] == "staff" for issue in report["issues"]))

    def test_interval_underfilled_report_has_structured_missing_counts(self):
        slot = {
            "start": 6 * 60,
            "end": 14 * 60,
            "required_total": 2,
            "required_female_min": 1,
            "required_male_min": 1,
        }

        report = main.build_interval_underfilled_report(
            self.connection,
            [],
            [],
            1,
            WEEK_START_DATE,
            WEEK_DATES[0],
            slot,
            total=1,
            female=1,
            male=0,
        )

        self.assertEqual(report["kind"], "interval")
        self.assertEqual(report["missing"], {"total": 1, "female": 0, "male": 1})
        self.assertEqual(report["slot"]["start"], "06:00")
        self.assertEqual(report["slot"]["end"], "14:00")

    def test_week_shortage_queue_prioritizes_total_shortage_over_gender_shortage(self):
        employees = [
            {
                "id": 1,
                "full_name": "Employee A",
                "sex": "male",
                "min_shifts_per_week": 0,
                "target_shifts_per_week": 3,
                "max_shifts_per_week": 5,
                "can_work_night": True,
                "can_work_weekends": True,
                "can_work_evenings_after_night": True,
                "can_work_mornings_and_evenings": True,
                "is_primary": True,
                "priority_score": 50,
                "is_fallback_only": False,
            }
        ]
        templates = [
            {
                "id": 1,
                "name": "Morning",
                "category": "morning",
                "start_time": "06:00",
                "end_time": "10:00",
                "is_overnight": False,
                "is_active": True,
                "is_split_only": False,
            },
            {
                "id": 2,
                "name": "Evening",
                "category": "evening",
                "start_time": "10:00",
                "end_time": "14:00",
                "is_overnight": False,
                "is_active": True,
                "is_split_only": False,
            },
        ]
        slots = [
            {
                "start": 6 * 60,
                "end": 10 * 60,
                "required_total": 2,
                "required_female_min": 0,
                "required_male_min": 0,
            },
            {
                "start": 10 * 60,
                "end": 14 * 60,
                "required_total": 1,
                "required_female_min": 1,
                "required_male_min": 0,
            },
        ]

        queue = main.build_week_shortage_queue(
            self.connection,
            employees,
            templates,
            1,
            WEEK_START_DATE,
            [WEEK_DATES[0]],
            slots,
        )

        self.assertEqual(queue[0]["slot"]["start"], 6 * 60)
        self.assertEqual(queue[0]["missing_total"], 2)

    def test_auto_generation_allows_morning_evening_combo_without_split_flag(self):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM schedule_entries")
        cursor.execute("DELETE FROM employee_day_statuses")
        cursor.execute("DELETE FROM shift_templates")
        cursor.execute("DELETE FROM employee_positions")
        cursor.execute("DELETE FROM positions")
        cursor.execute("DELETE FROM employees")
        cursor.execute(
            """
            INSERT INTO employees (
                id,
                full_name,
                sex,
                min_shifts_per_week,
                target_shifts_per_week,
                max_shifts_per_week,
                can_work_night,
                can_work_weekends,
                can_work_evenings_after_night,
                can_work_mornings_and_evenings
            )
            VALUES (1, 'Employee A', 'female', 0, 4, 6, 1, 1, 1, 1)
            """
        )
        cursor.execute("INSERT INTO positions (id, name) VALUES (1, 'Nurse')")
        cursor.execute(
            """
            INSERT INTO employee_positions (employee_id, position_id, is_primary, priority_score, is_fallback_only)
            VALUES (1, 1, 1, 100, 0)
            """
        )
        cursor.execute(
            """
            INSERT INTO shift_templates (id, position_id, name, category, start_time, end_time, is_overnight, is_active, is_split_only)
            VALUES
                (1, 1, 'Morning', 'morning', '06:30', '13:30', 0, 1, 0),
                (2, 1, 'Evening', 'evening', '15:00', '20:00', 0, 1, 0)
            """
        )
        cursor.execute(
            """
            INSERT INTO schedule_entries (employee_id, position_id, date, shift_template_id)
            VALUES (1, 1, ?, 1)
            """,
            (WEEK_DATES[0],),
        )

        template = {
            "id": 2,
            "name": "Evening",
            "category": "evening",
            "start_time": "15:00",
            "end_time": "20:00",
            "is_overnight": False,
            "is_active": True,
            "is_split_only": False,
        }
        employee = {
            "id": 1,
            "full_name": "Employee A",
            "sex": "female",
            "min_shifts_per_week": 0,
            "target_shifts_per_week": 4,
            "max_shifts_per_week": 6,
            "can_work_night": True,
            "can_work_weekends": True,
            "can_work_evenings_after_night": True,
            "can_work_mornings_and_evenings": True,
        }

        self.assertTrue(
            main.can_employee_take_template(
                self.connection,
                employee,
                1,
                WEEK_DATES[0],
                template,
                WEEK_START_DATE,
            )
        )
        self.assertIsNone(
            main.explain_employee_template_rejection(
                self.connection,
                employee,
                1,
                WEEK_DATES[0],
                template,
                WEEK_START_DATE,
            )
        )

    def test_consecutive_split_day_limit_blocks_third_split_day(self):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM schedule_entries")
        cursor.execute("DELETE FROM employee_day_statuses")
        cursor.execute("DELETE FROM shift_templates")
        cursor.execute("DELETE FROM employee_positions")
        cursor.execute("DELETE FROM positions")
        cursor.execute("DELETE FROM employees")
        cursor.execute(
            """
            INSERT INTO employees (
                id,
                full_name,
                sex,
                min_shifts_per_week,
                target_shifts_per_week,
                max_shifts_per_week,
                can_work_night,
                can_work_weekends,
                can_work_evenings_after_night,
                can_work_mornings_and_evenings
            )
            VALUES (1, 'Employee A', 'female', 0, 5, 7, 1, 1, 1, 1)
            """
        )
        cursor.execute("INSERT INTO positions (id, name) VALUES (1, 'Nurse')")
        cursor.execute(
            """
            INSERT INTO app_settings (key, value)
            VALUES ('max_daily_work_minutes', '780')
            """
        )
        cursor.execute(
            """
            INSERT INTO employee_positions (employee_id, position_id, is_primary, priority_score, is_fallback_only)
            VALUES (1, 1, 1, 100, 0)
            """
        )
        cursor.execute(
            """
            INSERT INTO shift_templates (id, position_id, name, category, start_time, end_time, is_overnight, is_active, is_split_only)
            VALUES
                (1, 1, 'Morning', 'morning', '06:00', '14:00', 0, 1, 0),
                (2, 1, 'Evening', 'evening', '15:00', '20:00', 0, 1, 0)
            """
        )
        cursor.executemany(
            """
            INSERT INTO schedule_entries (employee_id, position_id, date, shift_template_id)
            VALUES (1, 1, ?, ?)
            """,
            [
                (WEEK_DATES[0], 1),
                (WEEK_DATES[0], 2),
                (WEEK_DATES[1], 1),
                (WEEK_DATES[1], 2),
                (WEEK_DATES[2], 1),
            ],
        )
        self.connection.commit()

        employee = {
            "id": 1,
            "full_name": "Employee A",
            "sex": "female",
            "min_shifts_per_week": 0,
            "target_shifts_per_week": 5,
            "max_shifts_per_week": 7,
            "can_work_night": True,
            "can_work_weekends": True,
            "can_work_evenings_after_night": True,
            "can_work_mornings_and_evenings": True,
        }
        evening_template = {
            "id": 2,
            "name": "Evening",
            "category": "evening",
            "start_time": "15:00",
            "end_time": "20:00",
            "is_overnight": False,
            "is_active": True,
            "is_split_only": False,
        }

        self.assertFalse(
            main.can_employee_take_template(
                self.connection,
                employee,
                1,
                WEEK_DATES[2],
                evening_template,
                WEEK_START_DATE,
            )
        )
        self.assertEqual(
            main.explain_employee_template_rejection(
                self.connection,
                employee,
                1,
                WEEK_DATES[2],
                evening_template,
                WEEK_START_DATE,
            ),
            "too many consecutive split shifts",
        )

    def test_allows_morning_and_night_on_same_day_as_separate_combo(self):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM schedule_entries")
        cursor.execute("DELETE FROM employee_day_statuses")
        cursor.execute("DELETE FROM shift_templates")
        cursor.execute("DELETE FROM employee_positions")
        cursor.execute("DELETE FROM positions")
        cursor.execute("DELETE FROM employees")
        cursor.execute(
            """
            INSERT INTO employees (
                id,
                full_name,
                sex,
                min_shifts_per_week,
                target_shifts_per_week,
                max_shifts_per_week,
                can_work_night,
                can_work_weekends,
                can_work_evenings_after_night,
                can_work_mornings_and_evenings
            )
            VALUES (1, 'Employee A', 'female', 0, 4, 6, 1, 1, 1, 0)
            """
        )
        cursor.execute("INSERT INTO positions (id, name) VALUES (1, 'Nurse')")
        cursor.execute(
            """
            INSERT INTO employee_positions (employee_id, position_id, is_primary, priority_score, is_fallback_only)
            VALUES (1, 1, 1, 100, 0)
            """
        )
        cursor.execute(
            """
            INSERT INTO shift_templates (id, position_id, name, category, start_time, end_time, is_overnight, is_active, is_split_only)
            VALUES
                (1, 1, 'Morning', 'morning', '06:00', '14:00', 0, 1, 0),
                (2, 1, 'Night', 'night', '23:00', '07:00', 1, 1, 0)
            """
        )
        cursor.execute(
            """
            INSERT INTO schedule_entries (employee_id, position_id, date, shift_template_id)
            VALUES (1, 1, ?, 1)
            """,
            (WEEK_DATES[0],),
        )

        template = {
            "id": 2,
            "name": "Night",
            "category": "night",
            "start_time": "23:00",
            "end_time": "07:00",
            "is_overnight": True,
            "is_active": True,
            "is_split_only": False,
        }
        employee = {
            "id": 1,
            "full_name": "Employee A",
            "sex": "female",
            "min_shifts_per_week": 0,
            "target_shifts_per_week": 4,
            "max_shifts_per_week": 6,
            "can_work_night": True,
            "can_work_weekends": True,
            "can_work_evenings_after_night": True,
            "can_work_mornings_and_evenings": False,
        }

        self.assertTrue(
            main.can_employee_take_template(
                self.connection,
                employee,
                1,
                WEEK_DATES[0],
                template,
                WEEK_START_DATE,
            )
        )
        self.assertIsNone(
            main.explain_employee_template_rejection(
                self.connection,
                employee,
                1,
                WEEK_DATES[0],
                template,
                WEEK_START_DATE,
            )
        )

    def test_daily_work_limit_blocks_long_morning_evening_pair(self):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM schedule_entries")
        cursor.execute("DELETE FROM employee_day_statuses")
        cursor.execute("DELETE FROM shift_templates")
        cursor.execute("DELETE FROM employee_positions")
        cursor.execute("DELETE FROM positions")
        cursor.execute("DELETE FROM employees")
        cursor.execute(
            """
            INSERT INTO app_settings (key, value)
            VALUES ('max_daily_work_minutes', '720')
            """
        )
        cursor.execute(
            """
            INSERT INTO employees (
                id,
                full_name,
                sex,
                min_shifts_per_week,
                target_shifts_per_week,
                max_shifts_per_week,
                can_work_night,
                can_work_weekends,
                can_work_evenings_after_night,
                can_work_mornings_and_evenings
            )
            VALUES (1, 'Employee A', 'female', 0, 4, 6, 1, 1, 1, 1)
            """
        )
        cursor.execute("INSERT INTO positions (id, name) VALUES (1, 'Nurse')")
        cursor.execute(
            """
            INSERT INTO employee_positions (employee_id, position_id, is_primary, priority_score, is_fallback_only)
            VALUES (1, 1, 1, 100, 0)
            """
        )
        cursor.execute(
            """
            INSERT INTO shift_templates (id, position_id, name, category, start_time, end_time, is_overnight, is_active, is_split_only)
            VALUES
                (1, 1, 'Morning', 'morning', '06:30', '13:30', 0, 1, 0),
                (2, 1, 'Long Evening', 'evening', '15:00', '23:00', 0, 1, 0)
            """
        )
        cursor.execute(
            """
            INSERT INTO schedule_entries (employee_id, position_id, date, shift_template_id)
            VALUES (1, 1, ?, 1)
            """,
            (WEEK_DATES[0],),
        )
        self.connection.commit()

        employee = {
            "id": 1,
            "full_name": "Employee A",
            "sex": "female",
            "min_shifts_per_week": 0,
            "target_shifts_per_week": 4,
            "max_shifts_per_week": 6,
            "can_work_night": True,
            "can_work_weekends": True,
            "can_work_evenings_after_night": True,
            "can_work_mornings_and_evenings": True,
        }
        long_evening_template = {
            "id": 2,
            "name": "Long Evening",
            "category": "evening",
            "start_time": "15:00",
            "end_time": "23:00",
            "is_overnight": False,
            "is_active": True,
            "is_split_only": False,
        }

        self.assertFalse(
            main.can_employee_take_template(
                self.connection,
                employee,
                1,
                WEEK_DATES[0],
                long_evening_template,
                WEEK_START_DATE,
            )
        )
        self.assertEqual(
            main.explain_employee_template_rejection(
                self.connection,
                employee,
                1,
                WEEK_DATES[0],
                long_evening_template,
                WEEK_START_DATE,
            ),
            "daily work limit exceeded",
        )

        cursor.execute(
            """
            UPDATE app_settings
            SET value = '900'
            WHERE key = 'max_daily_work_minutes'
            """
        )
        self.connection.commit()

        self.assertTrue(
            main.can_employee_take_template(
                self.connection,
                employee,
                1,
                WEEK_DATES[0],
                long_evening_template,
                WEEK_START_DATE,
            )
        )
        self.assertIsNone(
            main.explain_employee_template_rejection(
                self.connection,
                employee,
                1,
                WEEK_DATES[0],
                long_evening_template,
                WEEK_START_DATE,
            )
        )

    def test_staged_previous_night_blocks_next_morning(self):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM schedule_entries")
        cursor.execute("DELETE FROM employee_day_statuses")
        cursor.execute("DELETE FROM shift_templates")
        cursor.execute("DELETE FROM employee_positions")
        cursor.execute("DELETE FROM positions")
        cursor.execute("DELETE FROM employees")
        cursor.execute(
            """
            INSERT INTO employees (
                id,
                full_name,
                sex,
                min_shifts_per_week,
                target_shifts_per_week,
                max_shifts_per_week,
                can_work_night,
                can_work_weekends,
                can_work_evenings_after_night,
                can_work_mornings_and_evenings
            )
            VALUES (1, 'Employee A', 'female', 0, 4, 6, 1, 1, 1, 1)
            """
        )
        cursor.execute("INSERT INTO positions (id, name) VALUES (1, 'Nurse')")
        cursor.execute(
            """
            INSERT INTO employee_positions (employee_id, position_id, is_primary, priority_score, is_fallback_only)
            VALUES (1, 1, 1, 100, 0)
            """
        )

        employee = {
            "id": 1,
            "full_name": "Employee A",
            "sex": "female",
            "min_shifts_per_week": 0,
            "target_shifts_per_week": 4,
            "max_shifts_per_week": 6,
            "can_work_night": True,
            "can_work_weekends": True,
            "can_work_evenings_after_night": True,
            "can_work_mornings_and_evenings": True,
        }
        morning_template = {
            "id": 1,
            "name": "Morning",
            "category": "morning",
            "start_time": "06:00",
            "end_time": "14:00",
            "is_overnight": False,
            "is_active": True,
            "is_split_only": False,
        }
        night_template = {
            "id": 2,
            "name": "Night",
            "category": "night",
            "start_time": "22:00",
            "end_time": "06:00",
            "is_overnight": True,
            "is_active": True,
            "is_split_only": False,
        }
        staged_entries = [
            main.create_entry_preview(employee, 1, WEEK_DATES[0], night_template)
        ]

        self.assertFalse(
            main.can_employee_take_template(
                self.connection,
                employee,
                1,
                WEEK_DATES[1],
                morning_template,
                WEEK_START_DATE,
                staged_entries=staged_entries,
            )
        )
        self.assertEqual(
            main.explain_employee_template_rejection(
                self.connection,
                employee,
                1,
                WEEK_DATES[1],
                morning_template,
                WEEK_START_DATE,
                staged_entries=staged_entries,
            ),
            "morning after previous night is forbidden",
        )

    def test_next_morning_blocks_previous_night_assignment(self):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM schedule_entries")
        cursor.execute("DELETE FROM employee_day_statuses")
        cursor.execute("DELETE FROM shift_templates")
        cursor.execute("DELETE FROM employee_positions")
        cursor.execute("DELETE FROM positions")
        cursor.execute("DELETE FROM employees")
        cursor.execute(
            """
            INSERT INTO employees (
                id,
                full_name,
                sex,
                min_shifts_per_week,
                target_shifts_per_week,
                max_shifts_per_week,
                can_work_night,
                can_work_weekends,
                can_work_evenings_after_night,
                can_work_mornings_and_evenings
            )
            VALUES (1, 'Employee A', 'female', 0, 4, 6, 1, 1, 1, 1)
            """
        )
        cursor.execute("INSERT INTO positions (id, name) VALUES (1, 'Nurse')")
        cursor.execute(
            """
            INSERT INTO employee_positions (employee_id, position_id, is_primary, priority_score, is_fallback_only)
            VALUES (1, 1, 1, 100, 0)
            """
        )
        cursor.execute(
            """
            INSERT INTO shift_templates (id, position_id, name, category, start_time, end_time, is_overnight, is_active, is_split_only)
            VALUES
                (1, 1, 'Morning', 'morning', '06:00', '14:00', 0, 1, 0),
                (2, 1, 'Night', 'night', '22:00', '06:00', 1, 1, 0)
            """
        )
        cursor.execute(
            """
            INSERT INTO schedule_entries (employee_id, position_id, date, shift_template_id)
            VALUES (1, 1, ?, 1)
            """,
            (WEEK_DATES[1],),
        )

        employee = {
            "id": 1,
            "full_name": "Employee A",
            "sex": "female",
            "min_shifts_per_week": 0,
            "target_shifts_per_week": 4,
            "max_shifts_per_week": 6,
            "can_work_night": True,
            "can_work_weekends": True,
            "can_work_evenings_after_night": True,
            "can_work_mornings_and_evenings": True,
        }
        night_template = {
            "id": 2,
            "name": "Night",
            "category": "night",
            "start_time": "22:00",
            "end_time": "06:00",
            "is_overnight": True,
            "is_active": True,
            "is_split_only": False,
        }

        self.assertFalse(
            main.can_employee_take_template(
                self.connection,
                employee,
                1,
                WEEK_DATES[0],
                night_template,
                WEEK_START_DATE,
            )
        )
        self.assertEqual(
            main.explain_employee_template_rejection(
                self.connection,
                employee,
                1,
                WEEK_DATES[0],
                night_template,
                WEEK_START_DATE,
            ),
            "night before next morning is forbidden",
        )

    def test_weekend_restriction_blocks_weekend_assignment(self):
        employee = {
            "id": 1,
            "full_name": "Employee A",
            "sex": "female",
            "min_shifts_per_week": 0,
            "target_shifts_per_week": 4,
            "max_shifts_per_week": 6,
            "can_work_night": True,
            "can_work_weekends": False,
            "can_work_evenings_after_night": True,
            "can_work_mornings_and_evenings": True,
        }
        template = {
            "id": 1,
            "name": "Morning",
            "category": "morning",
            "start_time": "06:00",
            "end_time": "14:00",
            "is_overnight": False,
            "is_active": True,
            "is_split_only": False,
        }

        can_take = main.can_employee_take_template(
            self.connection,
            employee,
            1,
            "2026-04-24",
            template,
            WEEK_START_DATE,
        )
        reason = main.explain_employee_template_rejection(
            self.connection,
            employee,
            1,
            "2026-04-24",
            template,
            WEEK_START_DATE,
        )

        self.assertFalse(can_take)
        self.assertEqual(reason, "employee preferences or permissions block this shift")

    def test_only_night_preference_blocks_day_shift(self):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM employees")
        cursor.execute("DELETE FROM employee_preferences")
        cursor.execute(
            """
            INSERT INTO employees (
                id,
                full_name,
                sex,
                min_shifts_per_week,
                target_shifts_per_week,
                max_shifts_per_week,
                can_work_night,
                can_work_weekends,
                can_work_evenings_after_night,
                can_work_mornings_and_evenings
            )
            VALUES (1, 'Employee A', 'female', 0, 4, 6, 1, 1, 1, 0)
            """
        )
        cursor.execute(
            """
            INSERT INTO employee_preferences (employee_id, allow_morning, allow_evening, allow_night, allow_morning_evening_combo)
            VALUES (1, 0, 0, 1, 0)
            """
        )
        employee = {
            "id": 1,
            "full_name": "Employee A",
            "sex": "female",
            "min_shifts_per_week": 0,
            "target_shifts_per_week": 4,
            "max_shifts_per_week": 6,
            "can_work_night": True,
            "can_work_weekends": True,
            "can_work_evenings_after_night": True,
            "can_work_mornings_and_evenings": False,
        }
        template = {
            "id": 1,
            "name": "Morning",
            "category": "morning",
            "start_time": "06:00",
            "end_time": "14:00",
            "is_overnight": False,
            "is_active": True,
            "is_split_only": False,
        }

        self.assertFalse(
            main.can_employee_take_template(
                self.connection,
                employee,
                1,
                WEEK_DATES[0],
                template,
                WEEK_START_DATE,
            )
        )
        self.assertEqual(
            main.explain_employee_template_rejection(
                self.connection,
                employee,
                1,
                WEEK_DATES[0],
                template,
                WEEK_START_DATE,
            ),
            "employee preferences or permissions block this shift",
        )

    def test_permanent_strict_preference_blocks_day_shift(self):
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO employees (
                id,
                full_name,
                sex,
                min_shifts_per_week,
                target_shifts_per_week,
                max_shifts_per_week,
                can_work_night,
                can_work_weekends,
                can_work_evenings_after_night,
                can_work_mornings_and_evenings
            )
            VALUES (1, 'Employee A', 'female', 0, 4, 6, 1, 1, 1, 1)
            """
        )
        cursor.execute("INSERT INTO positions (id, name) VALUES (1, 'Nurse')")
        cursor.execute(
            """
            INSERT INTO employee_positions (employee_id, position_id, is_primary, priority_score, is_fallback_only)
            VALUES (1, 1, 1, 100, 0)
            """
        )
        cursor.execute(
            """
            INSERT INTO employee_recurring_preferences (
                employee_id, preference_kind, day_of_week, preference_type
            )
            VALUES (1, 'strict', 0, 'only_night')
            """
        )
        employee = {
            "id": 1,
            "full_name": "Employee A",
            "sex": "female",
            "min_shifts_per_week": 0,
            "target_shifts_per_week": 4,
            "max_shifts_per_week": 6,
            "can_work_night": True,
            "can_work_weekends": True,
            "can_work_evenings_after_night": True,
            "can_work_mornings_and_evenings": True,
        }
        template = {
            "id": 1,
            "name": "Morning",
            "category": "morning",
            "start_time": "06:00",
            "end_time": "14:00",
            "is_overnight": False,
            "is_active": True,
            "is_split_only": False,
        }

        self.assertFalse(
            main.can_employee_take_template(
                self.connection,
                employee,
                1,
                WEEK_DATES[0],
                template,
                WEEK_START_DATE,
            )
        )
        self.assertEqual(
            main.explain_employee_template_rejection(
                self.connection,
                employee,
                1,
                WEEK_DATES[0],
                template,
                WEEK_START_DATE,
            ),
            "employee preferences or permissions block this shift",
        )

    def test_permanent_soft_preference_avoids_employee_when_alternative_exists(self):
        cursor = self.connection.cursor()
        cursor.executemany(
            """
            INSERT INTO employees (
                id,
                full_name,
                sex,
                min_shifts_per_week,
                target_shifts_per_week,
                max_shifts_per_week,
                can_work_night,
                can_work_weekends,
                can_work_evenings_after_night,
                can_work_mornings_and_evenings
            )
            VALUES (?, ?, 'female', 0, 4, 6, 1, 1, 1, 1)
            """,
            [(1, "Employee A"), (2, "Employee B")],
        )
        cursor.execute("INSERT INTO positions (id, name) VALUES (1, 'Nurse')")
        cursor.executemany(
            """
            INSERT INTO employee_positions (employee_id, position_id, is_primary, priority_score, is_fallback_only)
            VALUES (?, 1, 1, 100, 0)
            """,
            [(1,), (2,)],
        )
        cursor.execute(
            """
            INSERT INTO shift_templates (
                id, position_id, name, category, start_time, end_time, is_overnight, is_active, is_split_only
            )
            VALUES (1, 1, 'Morning', 'morning', '06:00', '14:00', 0, 1, 0)
            """
        )
        cursor.execute(
            """
            INSERT INTO employee_recurring_preferences (
                employee_id, preference_kind, day_of_week, preference_type
            )
            VALUES (1, 'soft', 0, 'off_day')
            """
        )
        employees = [
            {
                "id": 1,
                "full_name": "Employee A",
                "sex": "female",
                "min_shifts_per_week": 0,
                "target_shifts_per_week": 4,
                "max_shifts_per_week": 6,
                "can_work_night": True,
                "can_work_weekends": True,
                "can_work_evenings_after_night": True,
                "can_work_mornings_and_evenings": True,
                "is_primary": True,
                "priority_score": 100,
                "is_fallback_only": False,
            },
            {
                "id": 2,
                "full_name": "Employee B",
                "sex": "female",
                "min_shifts_per_week": 0,
                "target_shifts_per_week": 4,
                "max_shifts_per_week": 6,
                "can_work_night": True,
                "can_work_weekends": True,
                "can_work_evenings_after_night": True,
                "can_work_mornings_and_evenings": True,
                "is_primary": True,
                "priority_score": 100,
                "is_fallback_only": False,
            },
        ]
        templates = [
            {
                "id": 1,
                "name": "Morning",
                "category": "morning",
                "start_time": "06:00",
                "end_time": "14:00",
                "is_overnight": False,
                "is_active": True,
                "is_split_only": False,
            }
        ]
        requirements = [
            {
                "shift_category": "morning",
                "required_total": 1,
                "required_female_min": 0,
                "required_male_min": 0,
            }
        ]
        created_entries = []
        errors = []
        reports = []

        main.fill_day_by_legacy_categories(
            self.connection,
            cursor,
            employees,
            templates,
            requirements,
            1,
            WEEK_START_DATE,
            WEEK_DATES[0],
            created_entries,
            errors,
            reports,
        )

        cursor.execute("SELECT employee_id FROM schedule_entries")
        self.assertEqual(cursor.fetchone()["employee_id"], 2)
        self.assertEqual(errors, [])
        self.assertEqual(reports, [])


if __name__ == "__main__":
    unittest.main()
