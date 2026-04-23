import tempfile
import unittest
from pathlib import Path

import database

_TEMP_DIR = tempfile.TemporaryDirectory()
database.DATABASE_PATH = Path(_TEMP_DIR.name) / "schedule_app_test.db"

import main  # noqa: E402
from tests.fixtures.fixed_week import WEEK_DATES, WEEK_START_DATE  # noqa: E402


class GenerationReportTests(unittest.TestCase):
    def setUp(self):
        self.connection = database.get_connection()

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
            INSERT INTO shift_templates (id, name, category, start_time, end_time, is_overnight, is_active, is_split_only)
            VALUES (1, 'Morning', 'morning', '06:00', '14:00', 0, 1, 0)
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

    def test_auto_generation_rejects_non_split_morning_evening_combo(self):
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
            INSERT INTO shift_templates (id, name, category, start_time, end_time, is_overnight, is_active, is_split_only)
            VALUES
                (1, 'Morning', 'morning', '06:00', '14:00', 0, 1, 0),
                (2, 'Evening', 'evening', '15:00', '20:00', 0, 1, 0)
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
            "morning-evening combo requires split-only templates",
        )


if __name__ == "__main__":
    unittest.main()
