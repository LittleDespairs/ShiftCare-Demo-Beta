"""Regression checks for restoring old identities and organization-specific rules."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from app_settings_service import save_app_settings
from schemas import AppSettingsUpdate
from schedule_time import build_week_dates
from tests.test_support import database, main
from shiftcare.scheduling.optimization import append_fatigue_summary_warnings


class RestoreActorAndFatigueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiftcare-restore-review-")
        self.addCleanup(self.temp.cleanup)
        path_patch = patch.object(database, "DATABASE_PATH", Path(self.temp.name) / "review.db")
        path_patch.start()
        self.addCleanup(path_patch.stop)
        database.init_db()
        self.client = TestClient(main.app)

    def test_restore_backup_older_than_actor_and_organization_succeeds_and_audits_safely(self):
        old_backup = database.create_database_backup("before_new_account")
        response = self.client.post("/api/auth/create-organization", json={
            "organization_name": "Created Later", "full_name": "New Owner",
            "email": "later@example.com", "password": "LaterPassword123",
        })
        self.assertEqual(response.status_code, 200, response.text)
        session = response.json()
        actor_id = session["user"]["id"]
        organization_id = session["user"]["memberships"][0]["organization_id"]
        self.assertNotEqual(organization_id, 1)
        response = self.client.post("/api/database/restore", json={"backup_name": old_backup.name},
                                    headers={"Authorization": "Bearer " + session["access_token"]})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["requires_login"])
        self.assertTrue((database.get_backup_dir() / response.json()["pre_restore_backup"]).exists())
        with database.get_connection() as connection:
            self.assertIsNone(connection.execute("SELECT id FROM users WHERE id = ?", (actor_id,)).fetchone())
            self.assertIsNone(connection.execute("SELECT id FROM organizations WHERE id = ?", (organization_id,)).fetchone())
            event = connection.execute("SELECT user_id, organization_id FROM auth_audit_events WHERE event_type = 'database_backup_restored' ORDER BY id DESC LIMIT 1").fetchone()
            self.assertIsNotNone(event)
            self.assertIsNone(event["user_id"])
            self.assertIsNone(event["organization_id"])
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_fatigue_report_uses_the_second_organizations_limits(self):
        dates = build_week_dates("2026-09-13")
        with database.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO organizations (id, public_id, name) VALUES (2, 'second-org', 'Second Clinic')")
            cursor.execute("INSERT INTO departments (organization_id, name) VALUES (2, 'Second Ward')")
            department_id = cursor.lastrowid
            cursor.execute("INSERT INTO positions (organization_id, department_id, name) VALUES (2, ?, 'Night Nurse')", (department_id,))
            position_id = cursor.lastrowid
            cursor.execute("INSERT INTO employees (organization_id, full_name, sex, min_shifts_per_week, target_shifts_per_week, max_shifts_per_week, can_work_night, can_work_weekends, can_work_evenings_after_night, can_work_mornings_and_evenings) VALUES (2, 'Second Nurse', 'female', 0, 3, 7, 1, 1, 1, 1)")
            employee_id = cursor.lastrowid
            cursor.execute("INSERT INTO shift_templates (organization_id, position_id, category, name, start_time, end_time, is_overnight) VALUES (2, ?, 'night', 'Night', '23:00', '07:00', 1)", (position_id,))
            template_id = cursor.lastrowid
            for date in dates[:3]:
                cursor.execute("INSERT INTO schedule_entries (organization_id, employee_id, position_id, date, shift_template_id) VALUES (2, ?, ?, ?, ?)", (employee_id, position_id, date, template_id))
            save_app_settings(connection, AppSettingsUpdate(max_work_days_per_week=6, max_consecutive_nights=5, emergency_max_consecutive_nights=5), 1)
            save_app_settings(connection, AppSettingsUpdate(max_work_days_per_week=1, max_consecutive_nights=1), 2)
            connection.commit()
            warnings = []
            append_fatigue_summary_warnings(connection, [{"id": employee_id, "full_name": "Second Nurse"}], position_id, dates, dates[0], warnings)
            self.assertTrue(any("mandatory weekly day off is violated" in warning for warning in warnings), warnings)
            self.assertTrue(any("3 consecutive night days; normal limit is 1" in warning for warning in warnings), warnings)


if __name__ == "__main__":
    unittest.main()
