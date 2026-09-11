import os
import sqlite3
import unittest
import uuid
from pathlib import Path

import database
from app_settings_service import get_app_settings, get_position_app_settings, reset_visual_color_settings, save_app_settings
from db_adapter import PostgresConnectionAdapter, apply_postgres_schema, migrate_postgres_runtime_constraints
from schemas import AppSettingsUpdate


POSTGRES_TEST_DSN = os.getenv("SCHEDULE_APP_POSTGRES_TEST_DSN", "").strip()


@unittest.skipUnless(POSTGRES_TEST_DSN, "SCHEDULE_APP_POSTGRES_TEST_DSN is not set")
class PostgresIntegrationTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql

        self.schema_name = f"schedule_app_test_{uuid.uuid4().hex}"
        self.raw_connection = psycopg.connect(POSTGRES_TEST_DSN)
        self.addCleanup(self.dispose_schema)
        self.raw_connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema_name)))
        self.raw_connection.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(self.schema_name)))
        self.raw_connection.commit()
        self.connection = PostgresConnectionAdapter(self.raw_connection)
        self.schema_path = Path(__file__).resolve().parents[1] / "docs" / "postgresql" / "001_initial_schema.sql"
        apply_postgres_schema(self.connection, self.schema_path)

    def dispose_schema(self):
        from psycopg import sql
        try:
            self.raw_connection.rollback()
            self.raw_connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.schema_name)))
            self.raw_connection.commit()
        finally:
            self.raw_connection.close()

    def test_postgres_schema_applies_to_disposable_schema(self):
        self.assertEqual(self.connection.execute("SELECT COUNT(*) AS count FROM organizations").fetchone()["count"], 1)
        self.assertGreater(self.connection.execute("SELECT COUNT(*) AS count FROM app_settings").fetchone()["count"], 0)
        apply_postgres_schema(self.connection, self.schema_path)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) AS count FROM organizations").fetchone()["count"], 1)

    def test_runtime_preference_normalization_does_not_rewrite_current_rows(self):
        self.connection.execute("""
            INSERT INTO employees (
                id, full_name, sex, min_shifts_per_week, max_shifts_per_week,
                can_work_night, can_work_weekends, can_work_evenings_after_night,
                can_work_mornings_and_evenings
            ) VALUES (1, 'Preference migration', 'female', 0, 7, 1, 1, 1, 1)
        """)
        for table, columns, values in (
            ("employee_recurring_preferences", "preference_kind, day_of_week", "'strict', 0"),
            ("employee_week_preferences", "week_start_date, preference_date", "'2026-09-13', '2026-09-13'"),
        ):
            self.connection.execute(f"""
                INSERT INTO {table} (employee_id, {columns}, preference_type, request_type, target_category)
                VALUES (1, {values}, 'off_day', 'day_off', NULL),
                       (1, {values}, 'not_evening', 'request_shift', NULL)
            """)
        self.connection.commit()

        def snapshot():
            return {
                table: [tuple(row[column] for column in ("preference_type", "request_type", "target_category", "row_version")) for row in self.connection.execute(
                    f"SELECT preference_type, request_type, target_category, xmin::text AS row_version FROM {table} ORDER BY preference_type"
                ).fetchall()]
                for table in ("employee_recurring_preferences", "employee_week_preferences")
            }

        original = snapshot()
        database._ensure_postgres_runtime_schema(self.connection)
        migrated = snapshot()
        for table, rows in migrated.items():
            self.assertEqual(rows[0][:3], ("not_evening", "exclude_shift", "evening"))
            self.assertNotEqual(rows[0][3], original[table][0][3])
            self.assertEqual(rows[1], original[table][1])
        for _ in range(2):
            database._ensure_postgres_runtime_schema(self.connection)
            self.assertEqual(snapshot(), migrated)

    def test_settings_writes_and_visual_reset_do_not_cross_organization_boundaries(self):
        self.connection.execute("INSERT INTO organizations (id, public_id, name) VALUES (2, 'org-two', 'Two')")
        save_app_settings(self.connection, AppSettingsUpdate(max_work_days_per_week=4, schedule_morning_color="#123456"), 1)
        save_app_settings(self.connection, AppSettingsUpdate(max_work_days_per_week=5, schedule_morning_color="#654321"), 2)
        self.connection.commit()
        reset_visual_color_settings(self.connection, 2)
        self.connection.commit()
        self.assertEqual(get_app_settings(self.connection, 1)["max_work_days_per_week"], 4)
        self.assertEqual(get_app_settings(self.connection, 2)["max_work_days_per_week"], 5)
        self.assertEqual(get_app_settings(self.connection, 1)["schedule_morning_color"], "#123456")
        self.assertEqual(get_app_settings(self.connection, 2)["schedule_morning_color"], "#ecfeff")
        self.connection.execute("INSERT INTO departments (id, organization_id, public_id, name) VALUES (22, 2, 'department-22', 'Two')")
        self.connection.execute("INSERT INTO positions (id, organization_id, department_id, name, max_consecutive_nights) VALUES (22, 2, 22, 'Two nurse', 1)")
        position_settings = get_position_app_settings(self.connection, 22)
        self.assertEqual(position_settings["max_work_days_per_week"], 5)
        self.assertEqual(position_settings["max_consecutive_nights"], 1)

    def test_old_global_settings_key_migrates_and_keeps_existing_values(self):
        self.connection.execute("INSERT INTO organizations (id, public_id, name) VALUES (2, 'org-two', 'Two')")
        self.connection.execute("DROP TABLE app_settings")
        self.connection.execute("CREATE TABLE app_settings (organization_id BIGINT NOT NULL DEFAULT 1 REFERENCES organizations(id), key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.connection.execute("INSERT INTO app_settings VALUES (2, 'max_work_days_per_week', '3')")
        self.connection.execute("INSERT INTO app_settings VALUES (1, 'retained', 'keep')")
        self.connection.commit()
        apply_postgres_schema(self.connection, self.schema_path)
        apply_postgres_schema(self.connection, self.schema_path)
        self.assertEqual(get_app_settings(self.connection, 1)["max_work_days_per_week"], 6)
        self.assertEqual(get_app_settings(self.connection, 2)["max_work_days_per_week"], 3)
        self.assertEqual(self.connection.execute("SELECT value FROM app_settings WHERE organization_id = 1 AND key = 'retained'").fetchone()[0], "keep")
        save_app_settings(self.connection, AppSettingsUpdate(max_work_days_per_week=4), 1)
        self.connection.commit()
        self.assertEqual(get_app_settings(self.connection, 2)["max_work_days_per_week"], 3)

    def test_department_acl_migration_keeps_restricted_mode_after_last_grant_deleted(self):
        self.connection.execute("INSERT INTO users (id, email, full_name) VALUES (1, 'scheduler@example.test', 'Scheduler')")
        self.connection.execute("INSERT INTO organization_memberships (organization_id, user_id, role) VALUES (1, 1, 'scheduler')")
        self.connection.execute("INSERT INTO departments (id, organization_id, public_id, name) VALUES (77, 1, 'department-77', 'Restricted')")
        self.connection.execute("INSERT INTO user_department_access (organization_id, user_id, department_id) VALUES (1, 1, 77)")
        self.connection.execute("ALTER TABLE organization_memberships DROP COLUMN department_access_mode")
        self.connection.commit()
        migrate_postgres_runtime_constraints(self.connection)
        self.connection.commit()
        self.connection.execute("DELETE FROM departments WHERE id = 77")
        self.connection.commit()
        migrate_postgres_runtime_constraints(self.connection)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM user_department_access").fetchone()[0], 0)
        self.assertEqual(self.connection.execute("SELECT department_access_mode FROM organization_memberships").fetchone()[0], "restricted")

    def test_settings_without_serial_id_do_not_abort_new_connection_transaction(self):
        import psycopg
        from psycopg import sql
        raw = psycopg.connect(POSTGRES_TEST_DSN)
        try:
            raw.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(self.schema_name)))
            raw.commit()
            fresh = PostgresConnectionAdapter(raw)
            save_app_settings(fresh, AppSettingsUpdate(max_work_days_per_week=4), 1)
            self.assertEqual(get_app_settings(fresh, 1)["max_work_days_per_week"], 4)
            fresh.rollback()
            self.assertEqual(get_app_settings(fresh, 1)["max_work_days_per_week"], 6)
        finally:
            raw.close()

    def test_settings_foreign_key_error_can_be_rolled_back_without_losing_committed_data(self):
        save_app_settings(self.connection, AppSettingsUpdate(max_work_days_per_week=4), 1)
        self.connection.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            save_app_settings(self.connection, AppSettingsUpdate(max_work_days_per_week=5), 999)
        self.connection.rollback()
        self.assertEqual(get_app_settings(self.connection, 1)["max_work_days_per_week"], 4)
