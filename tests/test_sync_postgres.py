"""Sync invariants against an explicitly configured disposable PostgreSQL schema."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

from fastapi import HTTPException
from db_adapter import PostgresConnectionAdapter, apply_postgres_schema
from schemas import CloudOrganizationImportRequest
from tests.test_support import database
from shiftcare.routes import organizations
from shiftcare.services import backups, bundles, memberships


DSN = os.getenv("SCHEDULE_APP_POSTGRES_TEST_DSN", "").strip()


@unittest.skipUnless(DSN, "SCHEDULE_APP_POSTGRES_TEST_DSN is not set")
class PostgresSyncTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        self.schema = "shiftcare_sync_" + uuid.uuid4().hex
        self.admin = psycopg.connect(DSN)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.admin.commit()
        self.addCleanup(self.cleanup_schema)
        connection = self.connect()
        try:
            apply_postgres_schema(connection, Path(__file__).resolve().parents[1] / "docs/postgresql/001_initial_schema.sql")
            cursor = connection.cursor()
            cursor.execute("INSERT INTO users (email, full_name, status, email_verified) VALUES ('owner@sync.test', 'Owner', 'active', 1)")
            self.owner_id = cursor.lastrowid
            cursor.execute("INSERT INTO organization_memberships (organization_id, user_id, role, status) VALUES (1, ?, 'owner', 'active')", (self.owner_id,))
            cursor.execute("INSERT INTO users (email, full_name, status, email_verified) VALUES ('reader@sync.test', 'Reader', 'active', 1)")
            self.reader_id = cursor.lastrowid
            cursor.execute("INSERT INTO organization_memberships (organization_id, user_id, role, status, department_access_mode) VALUES (1, ?, 'read_only', 'active', 'restricted')", (self.reader_id,))
            cursor.execute("SELECT id FROM departments WHERE organization_id = 1 ORDER BY id")
            self.department_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO user_department_access (organization_id, user_id, department_id) VALUES (1, ?, ?)", (self.reader_id, self.department_id))
            cursor.execute("INSERT INTO employees (full_name, sex, min_shifts_per_week, target_shifts_per_week, max_shifts_per_week, can_work_night, can_work_weekends, can_work_evenings_after_night, can_work_mornings_and_evenings) VALUES ('Nurse', 'female', 0, 3, 7, 1, 1, 1, 1)")
            self.employee_id = cursor.lastrowid
            cursor.execute("INSERT INTO positions (department_id, name) VALUES (?, 'Nurse')", (self.department_id,))
            self.position_id = cursor.lastrowid
            cursor.execute("INSERT INTO employee_positions (employee_id, position_id) VALUES (?, ?)", (self.employee_id, self.position_id))
            cursor.execute("INSERT INTO shift_templates (position_id, category, name, start_time, end_time) VALUES (?, 'morning', 'Morning', '07:00', '15:00')", (self.position_id,))
            self.template_id = cursor.lastrowid
            cursor.execute("INSERT INTO schedule_entries (employee_id, position_id, date, shift_template_id) VALUES (?, ?, '2026-09-14', ?)", (self.employee_id, self.position_id, self.template_id))
            self.entry_id = cursor.lastrowid
            connection.commit()
        finally:
            connection.close()
        self.user = {"id": self.owner_id, "memberships": [{"organization_id": 1, "role": "owner", "status": "active"}]}

    def connect(self):
        import psycopg
        from psycopg import sql
        raw = psycopg.connect(DSN)
        raw.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(self.schema)))
        raw.commit()
        return PostgresConnectionAdapter(raw)

    def cleanup_schema(self):
        from psycopg import sql
        try:
            self.admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.schema)))
            self.admin.commit()
        finally:
            self.admin.close()

    def export(self):
        with patch.object(database, "get_connection", side_effect=self.connect):
            return organizations.export_organization_for_cloud(1, self.user)

    def import_bundle(self, bundle):
        with patch.object(database, "get_connection", side_effect=self.connect), patch.object(backups, "create_recovery_backup", return_value="managed-test-backup"):
            return organizations.import_organization_from_cloud_bundle(1, CloudOrganizationImportRequest(bundle=bundle), self.user)

    def test_real_cas_import_preserves_record_ids_and_department_acl(self):
        exported = self.export()
        result = self.import_bundle(exported)
        self.assertEqual(result["sync_bundle"]["records"]["employees"][0]["id"], self.employee_id)
        self.assertEqual(result["sync_bundle"]["records"]["schedule_entries"][0]["id"], self.entry_id)
        connection = self.connect()
        try:
            scope = memberships.get_allowed_department_ids(connection.cursor(), {
                "user": {"id": self.reader_id}, "membership": {"organization_id": 1, "role": "read_only"},
            })
            self.assertEqual(scope, {self.department_id})
        finally:
            connection.close()

    def test_stale_cas_does_not_erase_a_concurrent_cloud_preference(self):
        stale = self.export()
        connection = self.connect()
        try:
            connection.execute("INSERT INTO employee_week_preferences (employee_id, week_start_date, preference_date, preference_type, request_type) VALUES (?, '2026-09-13', '2026-09-15', 'off_day', 'day_off')", (self.employee_id,))
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(HTTPException) as error:
            self.import_bundle(stale)
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(len(self.export()["records"]["employee_week_preferences"]), 1)

    def test_export_snapshot_does_not_mix_rows_committed_between_reads(self):
        reader, writer = self.connect(), self.connect()
        try:
            bundles.begin_organization_export_snapshot(reader)
            before = bundles.build_organization_export_bundle(reader, 1)
            writer.execute("UPDATE employees SET full_name = 'Changed' WHERE id = ?", (self.employee_id,))
            writer.commit()
            during = bundles.build_organization_export_bundle(reader, 1)
            self.assertEqual(during["sync_revision"], before["sync_revision"])
            reader.rollback()
            after = bundles.build_organization_export_bundle(reader, 1)
            self.assertNotEqual(after["sync_revision"], before["sync_revision"])
        finally:
            reader.close()
            writer.close()

    def test_import_lock_blocks_an_ordinary_writer_during_compare_and_replace(self):
        import psycopg
        importer, writer = self.connect(), self.connect()
        try:
            bundles.lock_organization_sync_snapshot(importer, 1)
            writer.execute("SET LOCAL lock_timeout = '100ms'")
            with self.assertRaises(psycopg.errors.LockNotAvailable):
                writer.execute("UPDATE employees SET full_name = 'Racing writer' WHERE id = ?", (self.employee_id,))
            writer.rollback()
            importer.rollback()
            writer.execute("UPDATE employees SET full_name = 'After import' WHERE id = ?", (self.employee_id,))
            writer.commit()
        finally:
            importer.close()
            writer.close()


if __name__ == "__main__":
    unittest.main()
