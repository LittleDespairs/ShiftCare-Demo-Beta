import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

import database
from app_settings_service import get_app_settings, get_position_app_settings, reset_visual_color_settings, save_app_settings
from schemas import AppSettingsUpdate


class DataIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "test.db"
        for replacement in (
            patch.object(database, "DATABASE_PATH", self.path),
            patch.object(database, "get_app_config", return_value=SimpleNamespace(database_engine="sqlite")),
            patch.object(database, "is_demo_mode_enabled", return_value=False),
            patch.object(database, "get_bundled_database_path", return_value=None),
        ):
            replacement.start()
            self.addCleanup(replacement.stop)
        database.init_db()

    def add_second_organization(self, connection):
        connection.execute("INSERT INTO organizations (id, public_id, name) VALUES (2, 'org-two', 'Two')")

    def create_probe(self, value):
        with database.get_connection() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS integrity_probe (value TEXT NOT NULL)")
            connection.execute("DELETE FROM integrity_probe")
            connection.execute("INSERT INTO integrity_probe VALUES (?)", (value,))

    def read_probe(self, path=None):
        connection = sqlite3.connect(path or self.path)
        try:
            return connection.execute("SELECT value FROM integrity_probe").fetchone()[0]
        finally:
            connection.close()

    def test_settings_and_visual_reset_are_isolated_between_organizations(self):
        with database.get_connection() as connection:
            self.add_second_organization(connection)
            save_app_settings(connection, AppSettingsUpdate(max_work_days_per_week=4, schedule_morning_color="#123456"), 1)
            save_app_settings(connection, AppSettingsUpdate(max_work_days_per_week=5, schedule_morning_color="#654321"), 2)
            self.assertEqual(get_app_settings(connection, 1)["max_work_days_per_week"], 4)
            self.assertEqual(get_app_settings(connection, 2)["max_work_days_per_week"], 5)
            reset_visual_color_settings(connection, 2)
            self.assertEqual(get_app_settings(connection, 1)["schedule_morning_color"], "#123456")
            self.assertEqual(get_app_settings(connection, 2)["schedule_morning_color"], "#ecfeff")
        database.init_db()
        with database.get_connection() as connection:
            self.assertEqual(get_app_settings(connection, 1)["max_work_days_per_week"], 4)
            self.assertEqual(get_app_settings(connection, 2)["max_work_days_per_week"], 5)

    def test_legacy_key_primary_key_migrates_without_overwriting_any_organization(self):
        with database.get_connection() as connection:
            self.add_second_organization(connection)
            connection.execute("DROP TABLE app_settings")
            connection.execute("CREATE TABLE app_settings (organization_id INTEGER NOT NULL DEFAULT 1, key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute("INSERT INTO app_settings VALUES (1, 'custom-local', 'keep-local')")
            connection.execute("INSERT INTO app_settings VALUES (2, 'max_work_days_per_week', '3')")
            connection.execute("UPDATE schema_metadata SET value = '25' WHERE key = 'schema_version'")
        database.init_db()
        database.init_db()
        with database.get_connection() as connection:
            self.assertEqual(connection.execute("SELECT value FROM app_settings WHERE organization_id = 1 AND key = 'custom-local'").fetchone()[0], "keep-local")
            self.assertEqual(get_app_settings(connection, 1)["max_work_days_per_week"], 6)
            self.assertEqual(get_app_settings(connection, 2)["max_work_days_per_week"], 3)
            save_app_settings(connection, AppSettingsUpdate(max_work_days_per_week=4), 1)
            self.assertEqual(get_app_settings(connection, 2)["max_work_days_per_week"], 3)

    def test_position_generation_settings_infer_the_owning_organization(self):
        with database.get_connection() as connection:
            self.add_second_organization(connection)
            connection.execute("INSERT INTO departments (id, organization_id, name) VALUES (22, 2, 'Two')")
            connection.execute("INSERT INTO positions (id, organization_id, department_id, name, max_consecutive_nights) VALUES (22, 2, 22, 'Two nurse', 1)")
            save_app_settings(connection, AppSettingsUpdate(max_work_days_per_week=4), 1)
            save_app_settings(connection, AppSettingsUpdate(max_work_days_per_week=5), 2)
            actual = get_position_app_settings(connection, 22)
            self.assertEqual(actual["max_work_days_per_week"], 5)
            self.assertEqual(actual["max_consecutive_nights"], 1)
            foreign = get_position_app_settings(connection, 22, organization_id=1)
            self.assertEqual(foreign["max_work_days_per_week"], 4)
            self.assertEqual(foreign["max_consecutive_nights"], 2)

    def test_sync_suspension_only_suppresses_its_own_organization(self):
        with database.get_connection() as connection:
            self.add_second_organization(connection)
            database._upsert_app_setting(connection.cursor(), "desktop_sync_suspended", "1", 1)
            database._upsert_app_setting(connection.cursor(), "desktop_sync_suspended", "0", 2)
            connection.execute("DELETE FROM desktop_sync_outbox")
            connection.execute("INSERT INTO departments (organization_id, name) VALUES (1, 'Hidden change')")
            connection.execute("INSERT INTO departments (organization_id, name) VALUES (2, 'Visible change')")
            rows = connection.execute("SELECT DISTINCT organization_id FROM desktop_sync_outbox").fetchall()
            self.assertEqual([row[0] for row in rows], [2])

    def test_legacy_department_restriction_survives_last_department_deletion(self):
        with database.get_connection() as connection:
            connection.execute("INSERT INTO users (id, email, full_name) VALUES (1, 'scheduler@example.test', 'Scheduler')")
            connection.execute("INSERT INTO organization_memberships (organization_id, user_id, role) VALUES (1, 1, 'scheduler')")
            connection.execute("INSERT INTO departments (id, organization_id, name) VALUES (77, 1, 'Restricted')")
            connection.execute("INSERT INTO user_department_access (organization_id, user_id, department_id) VALUES (1, 1, 77)")
            connection.execute("ALTER TABLE organization_memberships DROP COLUMN department_access_mode")
        database.init_db()
        with database.get_connection() as connection:
            self.assertEqual(connection.execute("SELECT department_access_mode FROM organization_memberships").fetchone()[0], "restricted")
            connection.execute("DELETE FROM departments WHERE id = 77")
        database.init_db()
        with database.get_connection() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM user_department_access").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT department_access_mode FROM organization_memberships").fetchone()[0], "restricted")

    def test_plain_and_archive_backups_include_committed_wal_pages(self):
        writer = sqlite3.connect(self.path)
        try:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute("CREATE TABLE integrity_probe (value TEXT NOT NULL)")
            writer.execute("INSERT INTO integrity_probe VALUES ('committed in WAL')")
            writer.commit()
            self.assertTrue(Path(str(self.path) + "-wal").is_file())
            backup = database.create_database_backup()
            archive_path = database.create_schedule_backup()
            self.assertEqual(self.read_probe(backup), "committed in WAL")
            with ZipFile(archive_path) as archive:
                snapshot = Path(self.directory.name) / "from-archive.db"
                snapshot.write_bytes(archive.read("schedule_app.db"))
                self.assertEqual(self.read_probe(snapshot), "committed in WAL")
        finally:
            writer.close()

    def test_integrity_validation_rejects_corrupt_database_with_valid_header(self):
        corrupted = Path(self.directory.name) / "corrupted.db"
        database._copy_sqlite_snapshot(self.path, corrupted)
        with corrupted.open("r+b") as handle:
            handle.seek(100)
            handle.write(b"\x00")
        with self.assertRaisesRegex(ValueError, "integrity check failed"):
            database.validate_sqlite_file(corrupted)

    def test_integrity_validation_checks_reported_errors_not_just_sql_execution(self):
        corrupted = Path(self.directory.name) / "reported-error.db"
        connection = sqlite3.connect(corrupted)
        try:
            connection.execute("CREATE TABLE invalid_data (value TEXT)")
            connection.execute("INSERT INTO invalid_data VALUES (NULL)")
            connection.execute("PRAGMA writable_schema=ON")
            connection.execute("UPDATE sqlite_master SET sql = 'CREATE TABLE invalid_data (value TEXT NOT NULL)' WHERE name = 'invalid_data'")
            connection.commit()
        finally:
            connection.close()
        with self.assertRaisesRegex(ValueError, "NULL value"):
            database.validate_sqlite_file(corrupted)

    def test_portable_archive_removes_credentials_but_recovery_backup_is_complete(self):
        cloud_token = "portable-backup-must-not-contain-this-bearer-token"
        session_hash = "portable-backup-must-not-contain-this-session-hash"
        baseline = '{"revision":"keep-sync-baseline"}'
        with database.get_connection() as connection:
            connection.execute("INSERT INTO users (id, email, full_name, password_hash) VALUES (1, 'owner@example.test', 'Owner', 'retained-password-hash')")
            connection.execute("INSERT INTO auth_sessions (user_id, token_hash, expires_at) VALUES (1, ?, '2099-01-01')", (session_hash,))
            database._upsert_app_setting(connection.cursor(), "desktop_cloud_access_token", cloud_token)
            database._upsert_app_setting(connection.cursor(), "desktop_cloud_sync_baseline", baseline)
        recovery = database.create_database_backup()
        archive_path = database.create_schedule_backup()
        with ZipFile(archive_path) as archive:
            payload = archive.read("schedule_app.db")
            self.assertNotIn(cloud_token.encode(), payload)
            self.assertNotIn(session_hash.encode(), payload)
            metadata = json.loads(archive.read("metadata.json"))
            self.assertFalse(metadata["contains_access_tokens"])
            self.assertTrue(metadata["requires_login"])
            snapshot = Path(self.directory.name) / "sanitized.db"
            snapshot.write_bytes(payload)
        connection = sqlite3.connect(snapshot)
        try:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM auth_sessions").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT value FROM app_settings WHERE key = 'desktop_cloud_sync_baseline'").fetchone()[0], baseline)
            self.assertEqual(connection.execute("SELECT password_hash FROM users").fetchone()[0], "retained-password-hash")
        finally:
            connection.close()
        for original in (self.path, recovery):
            connection = sqlite3.connect(original)
            try:
                self.assertEqual(connection.execute("SELECT value FROM app_settings WHERE key = 'desktop_cloud_access_token'").fetchone()[0], cloud_token)
                self.assertEqual(connection.execute("SELECT token_hash FROM auth_sessions").fetchone()[0], session_hash)
            finally:
                connection.close()

    def test_restore_preserves_pre_restore_data_and_reopens_connections(self):
        self.create_probe("before")
        backup = database.create_schedule_backup()
        self.create_probe("after")
        with database.get_connection() as open_connection:
            with self.assertRaisesRegex(ValueError, "Close active"):
                database.restore_database_backup(backup.name)
            self.assertEqual(open_connection.execute("SELECT value FROM integrity_probe").fetchone()[0], "after")
        result = database.restore_database_backup(backup.name)
        self.assertEqual(self.read_probe(), "before")
        self.assertEqual(self.read_probe(database.get_backup_dir() / result["pre_restore_backup"]), "after")
        with database.get_connection() as connection:
            connection.execute("UPDATE integrity_probe SET value = 'usable after restore'")
        self.assertEqual(self.read_probe(), "usable after restore")

    def test_restore_waits_for_another_threads_connection(self):
        self.create_probe("before")
        backup = database.create_database_backup()
        self.create_probe("after")
        opened, release, done = threading.Event(), threading.Event(), threading.Event()
        errors = []

        def hold_connection():
            with database.get_connection() as connection:
                connection.execute("SELECT value FROM integrity_probe").fetchone()
                opened.set()
                release.wait(5)

        def restore():
            try:
                database.restore_database_backup(backup.name)
            except BaseException as exc:
                errors.append(exc)
            finally:
                done.set()

        reader = threading.Thread(target=hold_connection)
        reader.start()
        self.assertTrue(opened.wait(2))
        restorer = threading.Thread(target=restore)
        restorer.start()
        try:
            self.assertFalse(done.wait(0.05))
        finally:
            release.set()
            reader.join(5)
            restorer.join(5)
        self.assertTrue(done.is_set())
        self.assertEqual(errors, [])
        self.assertEqual(self.read_probe(), "before")

    def test_restore_migration_failure_rolls_back_to_current_database(self):
        self.create_probe("before")
        backup = database.create_database_backup()
        self.create_probe("latest")
        with patch.object(database, "_initialize_sqlite_schema", side_effect=ValueError("migration failed")):
            with self.assertRaisesRegex(ValueError, "migration failed"):
                database.restore_database_backup(backup.name)
        self.assertEqual(self.read_probe(), "latest")
        with database.get_connection() as connection:
            self.assertEqual(connection.execute("PRAGMA quick_check").fetchone()[0], "ok")

    def test_new_writes_wait_until_restore_finishes(self):
        self.create_probe("backup")
        backup = database.create_database_backup()
        self.create_probe("before restore")
        restoring, release, connected = threading.Event(), threading.Event(), threading.Event()
        failures = []
        original_copy = database._copy_sqlite_snapshot

        def paused_copy(source, destination, **kwargs):
            if destination == self.path:
                restoring.set()
                if not release.wait(5):
                    raise RuntimeError("Test restore timeout")
            return original_copy(source, destination, **kwargs)

        def restore():
            try:
                database.restore_database_backup(backup.name)
            except BaseException as exc:
                failures.append(exc)

        def write():
            try:
                with database.get_connection() as connection:
                    connected.set()
                    connection.execute("UPDATE integrity_probe SET value = 'new committed write'")
            except BaseException as exc:
                failures.append(exc)

        with patch.object(database, "_copy_sqlite_snapshot", side_effect=paused_copy):
            restorer = threading.Thread(target=restore)
            restorer.start()
            self.assertTrue(restoring.wait(2))
            writer = threading.Thread(target=write)
            writer.start()
            try:
                self.assertFalse(connected.wait(0.05))
            finally:
                release.set()
                restorer.join(5)
                writer.join(5)
        self.assertFalse(restorer.is_alive())
        self.assertFalse(writer.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual(self.read_probe(), "new committed write")


if __name__ == "__main__":
    unittest.main()
