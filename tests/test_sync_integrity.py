import copy
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from tests.test_support import database, main

import shiftcare.services.authentication as services_authentication
import shiftcare.services.bundles as services_bundles
import shiftcare.services.cloud_client as services_cloud_client
import shiftcare.services.common as services_common
import shiftcare.services.desktop_session as services_desktop_session
import shiftcare.services.memberships as services_memberships
import shiftcare.services.sync_pull as services_sync_pull
import shiftcare.services.sync_worker as services_sync_worker
from sync_policy import SyncConflict, canonical_snapshot, merge_snapshots


class SyncIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiftcare-sync-test-")
        self.addCleanup(self.temp.cleanup)
        self.local_path = Path(self.temp.name) / "local.db"
        self.cloud_path = Path(self.temp.name) / "cloud.db"
        self.path_patch = patch.object(database, "DATABASE_PATH", self.local_path)
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        database.init_db()
        self.client = TestClient(main.app)
        response = self.client.post("/api/auth/bootstrap", json={
            "organization_name": "Sync Clinic", "full_name": "Owner", "email": "owner@example.com",
            "password": "SyncTestPassword123",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.owner_id = response.json()["user"]["id"]
        self.owner_session = response.json()
        self.headers = {"Authorization": "Bearer " + response.json()["access_token"]}
        response = self.client.post("/api/employees", headers=self.headers, json={
            "full_name": "Nurse", "sex": "female", "min_shifts_per_week": 0,
            "target_shifts_per_week": 3, "max_shifts_per_week": 7,
            "can_work_night": True, "can_work_weekends": True,
            "can_work_evenings_after_night": True, "can_work_mornings_and_evenings": True,
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.employee_id = response.json()["employee"]["id"]

    def export(self):
        response = self.client.get("/api/organizations/1/cloud-export", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def preference(self, date, kind="off_day"):
        response = self.client.post("/api/employee-week-preferences", headers=self.headers, json={
            "employee_id": self.employee_id, "week_start_date": "2026-09-13",
            "preference_date": date, "preference_type": kind,
        })
        self.assertEqual(response.status_code, 200, response.text)

    def connect_cloud_copy(self):
        baseline = self.export()
        with database.get_connection() as connection:
            with closing(sqlite3.connect(self.cloud_path)) as destination:
                connection.backup(destination)
            cursor = connection.cursor()
            services_bundles.save_desktop_sync_baseline(cursor, baseline)
            for key, value in {
                "cloud_api_base_url": "https://cloud.invalid", "cloud_organization_id": "1",
                "desktop_cloud_access_token": self.headers["Authorization"].split(" ", 1)[1],
            }.items():
                cursor.execute(
                    "INSERT INTO app_settings (organization_id, key, value) VALUES (1, ?, ?) "
                    "ON CONFLICT(organization_id, key) DO UPDATE SET value = excluded.value", (key, value),
                )
            cursor.execute("DELETE FROM desktop_sync_outbox")
            connection.commit()
        return baseline

    def cloud_request(self, base_url, path, **kwargs):
        with patch.object(database, "DATABASE_PATH", self.cloud_path):
            response = self.client.request(
                kwargs.get("method", "GET"), path, headers=self.headers, json=kwargs.get("payload"),
            )
        if response.status_code >= 400:
            raise HTTPException(response.status_code, response.json().get("detail"))
        return response.json()

    def test_stale_and_legacy_import_cannot_erase_cloud_preference(self):
        stale = self.export()
        self.preference("2026-09-14")
        response = self.client.post("/api/organizations/1/cloud-import", headers=self.headers,
                                    json={"bundle": stale, "replace_existing": True})
        self.assertEqual(response.status_code, 409, response.text)
        stale.pop("sync_revision")
        response = self.client.post("/api/organizations/1/cloud-import", headers=self.headers,
                                    json={"bundle": stale, "replace_existing": True})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(len(self.export()["records"]["employee_week_preferences"]), 1)

    def test_import_preserves_allowlist_and_last_department_removal_denies_all(self):
        with database.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO users (email, full_name, status) VALUES ('reader@example.com', 'Reader', 'active')")
            user_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO organization_memberships (organization_id, user_id, role, status, department_access_mode) "
                "VALUES (1, ?, 'read_only', 'active', 'restricted')", (user_id,),
            )
            cursor.execute("INSERT INTO departments (organization_id, name) VALUES (1, 'Restricted ward')")
            department_id = cursor.lastrowid
            cursor.execute("INSERT INTO user_department_access (organization_id, user_id, department_id) VALUES (1, ?, ?)",
                           (user_id, department_id))
            connection.commit()
        context = {"user": {"id": user_id}, "membership": {"organization_id": 1, "role": "read_only"}}
        bundle = self.export()
        public_id = next(row["public_id"] for row in bundle["records"]["departments"] if row["id"] == department_id)
        response = self.client.post("/api/organizations/1/cloud-import", headers=self.headers,
                                    json={"bundle": bundle, "replace_existing": True})
        self.assertEqual(response.status_code, 200, response.text)
        with database.get_connection() as connection:
            allowed = services_memberships.get_allowed_department_ids(connection.cursor(), context)
            self.assertEqual(len(allowed), 1)
            self.assertEqual(connection.execute("SELECT public_id FROM departments WHERE id = ?", (next(iter(allowed)),)).fetchone()[0], public_id)
        bundle = self.export()
        bundle["records"]["departments"] = [row for row in bundle["records"]["departments"] if row["public_id"] != public_id]
        response = self.client.post("/api/organizations/1/cloud-import", headers=self.headers,
                                    json={"bundle": bundle, "replace_existing": True})
        self.assertEqual(response.status_code, 200, response.text)
        with database.get_connection() as connection:
            self.assertEqual(services_memberships.get_allowed_department_ids(connection.cursor(), context), set())

    def test_worker_merges_local_and_cloud_requests_and_does_not_echo_imports(self):
        self.connect_cloud_copy()
        self.preference("2026-09-14")
        with patch.object(database, "DATABASE_PATH", self.cloud_path):
            self.preference("2026-09-15")
        with patch.object(services_cloud_client, 'request_cloud_json', side_effect=self.cloud_request):
            self.assertTrue(services_sync_worker.run_desktop_sync_once())
        local = canonical_snapshot(self.export())
        with patch.object(database, "DATABASE_PATH", self.cloud_path):
            cloud = canonical_snapshot(self.export())
        self.assertEqual(local, cloud)
        self.assertEqual(len(local["records"]["employee_week_preferences"]), 2)
        with database.get_connection() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM desktop_sync_outbox WHERE status != 'synced'").fetchone()[0], 0)

    def test_worker_keeps_cloud_deletion_and_new_local_preference(self):
        self.preference("2026-09-14")
        self.connect_cloud_copy()
        self.preference("2026-09-16")
        with patch.object(database, "DATABASE_PATH", self.cloud_path):
            with database.get_connection() as connection:
                connection.execute("DELETE FROM employee_week_preferences WHERE preference_date = '2026-09-14'")
                connection.commit()
        with patch.object(services_cloud_client, 'request_cloud_json', side_effect=self.cloud_request):
            self.assertTrue(services_sync_worker.run_desktop_sync_once())
        dates = {row["preference_date"] for row in self.export()["records"]["employee_week_preferences"]}
        self.assertEqual(dates, {"2026-09-16"})

    def test_conflicting_approval_is_preserved_and_retry_reports_conflict(self):
        # A reviewed request is a business change even if another copy still
        # contains its original pending state; conflicting decisions must stop.
        base = canonical_snapshot(self.export())
        base["records"]["employee_week_preference_requests"] = {"request-1": {
            "public_id": "request-1", "employee_public_id": next(iter(base["records"]["employees"])), "status": "pending",
        }}
        local, remote = copy.deepcopy(base), copy.deepcopy(base)
        local["records"]["employee_week_preference_requests"]["request-1"]["status"] = "approved"
        remote["records"]["employee_week_preference_requests"]["request-1"]["status"] = "rejected"
        with self.assertRaises(SyncConflict):
            merge_snapshots(base, local, remote)
        merged = merge_snapshots(base, base, local)
        self.assertEqual(merged["records"]["employee_week_preference_requests"]["request-1"]["status"], "approved")

    def test_stale_syncing_recovers_and_fresh_syncing_is_not_stolen(self):
        self.connect_cloud_copy()
        self.preference("2026-09-14")
        with database.get_connection() as connection:
            connection.execute("UPDATE desktop_sync_outbox SET status = 'syncing', updated_at = '2000-01-01T00:00:00'")
            connection.commit()
        with patch.object(services_cloud_client, 'request_cloud_json', side_effect=self.cloud_request):
            self.assertTrue(services_sync_worker.run_desktop_sync_once())
        self.preference("2026-09-15")
        with database.get_connection() as connection:
            connection.execute("UPDATE desktop_sync_outbox SET status = 'syncing', updated_at = ? WHERE status = 'pending'", (services_common.current_utc_timestamp(),))
            connection.commit()
        with patch.object(services_cloud_client, 'request_cloud_json') as request:
            self.assertFalse(services_sync_worker.run_desktop_sync_once())
            request.assert_not_called()

    def test_edit_during_push_stays_pending_and_reentrant_worker_does_not_claim_it(self):
        self.connect_cloud_copy()
        self.preference("2026-09-14")
        added = False

        def request(base_url, path, **kwargs):
            nonlocal added
            if path.endswith("cloud-import") and not added:
                self.preference("2026-09-16")
                added = True
                self.assertFalse(services_sync_worker.run_desktop_sync_once())
            return self.cloud_request(base_url, path, **kwargs)

        with patch.object(services_cloud_client, 'request_cloud_json', side_effect=request):
            self.assertTrue(services_sync_worker.run_desktop_sync_once())
        self.assertEqual(len(self.export()["records"]["employee_week_preferences"]), 2)
        with database.get_connection() as connection:
            self.assertGreater(connection.execute("SELECT COUNT(*) FROM desktop_sync_outbox WHERE status = 'pending'").fetchone()[0], 0)
        with patch.object(services_cloud_client, 'request_cloud_json', side_effect=self.cloud_request):
            self.assertTrue(services_sync_worker.run_desktop_sync_once())

    def test_settings_without_outbox_trigger_are_detected(self):
        self.connect_cloud_copy()
        with database.get_connection() as connection:
            connection.execute("UPDATE app_settings SET value = '4' WHERE organization_id = 1 AND key = 'max_work_days_per_week'")
            connection.commit()
        with patch.object(services_cloud_client, 'request_cloud_json', side_effect=self.cloud_request):
            self.assertTrue(services_sync_worker.run_desktop_sync_once())
        with patch.object(database, "DATABASE_PATH", self.cloud_path):
            with database.get_connection() as connection:
                self.assertEqual(connection.execute("SELECT value FROM app_settings WHERE organization_id = 1 AND key = 'max_work_days_per_week'").fetchone()[0], '4')

    def test_cloud_edit_between_export_and_import_retries_without_losing_either_copy(self):
        self.connect_cloud_copy()
        self.preference("2026-09-14")
        changed = False

        def request(base_url, path, **kwargs):
            nonlocal changed
            if path.endswith("cloud-import") and not changed:
                with patch.object(database, "DATABASE_PATH", self.cloud_path):
                    self.preference("2026-09-15")
                changed = True
            return self.cloud_request(base_url, path, **kwargs)

        with patch.object(services_cloud_client, 'request_cloud_json', side_effect=request):
            self.assertFalse(services_sync_worker.run_desktop_sync_once())
        self.assertEqual(len(self.export()["records"]["employee_week_preferences"]), 1)
        with patch.object(database, "DATABASE_PATH", self.cloud_path):
            self.assertEqual(len(self.export()["records"]["employee_week_preferences"]), 1)
        with database.get_connection() as connection:
            connection.execute("UPDATE desktop_sync_outbox SET next_attempt_at = NULL WHERE status = 'failed'")
            connection.commit()
        with patch.object(services_cloud_client, 'request_cloud_json', side_effect=self.cloud_request):
            self.assertTrue(services_sync_worker.run_desktop_sync_once())
        self.assertEqual(len(self.export()["records"]["employee_week_preferences"]), 2)

    def test_pull_keeps_unqueued_local_setting_and_imports_cloud_preference(self):
        self.connect_cloud_copy()
        with database.get_connection() as connection:
            connection.execute("UPDATE app_settings SET value = '4' WHERE organization_id = 1 AND key = 'max_work_days_per_week'")
            connection.commit()
        with patch.object(database, "DATABASE_PATH", self.cloud_path):
            self.preference("2026-09-15")
        with patch.object(services_cloud_client, 'request_cloud_json', side_effect=self.cloud_request):
            with database.get_connection() as connection:
                services_sync_pull.pull_cloud_preferences_for_desktop_generation(connection)
                connection.commit()
                self.assertEqual(connection.execute("SELECT value FROM app_settings WHERE organization_id = 1 AND key = 'max_work_days_per_week'").fetchone()[0], '4')
        self.assertEqual(len(self.export()["records"]["employee_week_preferences"]), 1)

    def test_missing_baseline_never_resurrects_remote_deletion(self):
        self.preference("2026-09-14")
        local = canonical_snapshot(self.export())
        remote = copy.deepcopy(local)
        remote["records"]["employee_week_preferences"] = {}
        with self.assertRaises(SyncConflict):
            merge_snapshots(None, local, remote)

    def test_restricted_admin_cannot_bypass_department_scope_with_full_sync(self):
        bundle = self.export()
        with database.get_connection() as connection:
            connection.execute("INSERT INTO users (email, full_name, status) VALUES ('limited@example.com', 'Limited', 'active')")
            user_id = connection.execute("SELECT id FROM users WHERE email = 'limited@example.com'").fetchone()[0]
            connection.execute(
                "INSERT INTO organization_memberships (organization_id, user_id, role, status, department_access_mode) VALUES (1, ?, 'admin', 'active', 'restricted')",
                (user_id,),
            )
            auth = services_authentication.build_auth_response(connection, user_id)
            connection.commit()
        headers = {"Authorization": "Bearer " + auth["access_token"]}
        self.assertEqual(self.client.get("/api/organizations/1/cloud-export", headers=headers).status_code, 403)
        self.assertEqual(self.client.post("/api/organizations/1/cloud-import", headers=headers, json={"bundle": bundle}).status_code, 403)

    def test_relogin_merges_pending_local_changes_instead_of_erasing_them(self):
        self.connect_cloud_copy()
        self.preference("2026-09-14")
        with patch.object(database, "DATABASE_PATH", self.cloud_path):
            self.preference("2026-09-15")
        with patch.object(services_cloud_client, "request_cloud_json", side_effect=self.cloud_request):
            response = services_desktop_session.import_cloud_session_to_desktop("https://cloud.invalid", self.owner_session)
        self.assertTrue(response["desktop_sync"]["sync_pending"])
        self.assertEqual(len(self.export()["records"]["employee_week_preferences"]), 2)
        with database.get_connection() as connection:
            self.assertGreater(connection.execute("SELECT COUNT(*) FROM desktop_sync_outbox WHERE status = 'pending'").fetchone()[0], 0)

    def test_relogin_to_another_cloud_cannot_replace_populated_local_workspace(self):
        self.preference("2026-09-14")
        bundle = self.export()
        with patch.object(services_cloud_client, "request_cloud_json", return_value=bundle):
            with self.assertRaises(HTTPException) as error:
                services_desktop_session.import_cloud_session_to_desktop("https://different.invalid", self.owner_session)
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(len(self.export()["records"]["employee_week_preferences"]), 1)

    def test_initial_link_refuses_populated_cloud_even_with_current_cas_revision(self):
        bundle = self.export()
        changed = copy.deepcopy(bundle)
        changed["records"]["employees"][0]["full_name"] = "Stale desktop name"
        changed["sync"] = {"protocol": 2, "base_revision": bundle["sync_revision"], "initial_link": True}
        response = self.client.post("/api/organizations/1/cloud-import", headers=self.headers, json={"bundle": changed})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.export()["records"]["employees"][0]["full_name"], "Nurse")

    def test_initial_link_and_finalize_keep_edits_made_on_both_sides_after_upload(self):
        self.connect_cloud_copy()
        local_bundle = self.export()
        with patch.object(database, "DATABASE_PATH", self.cloud_path):
            with database.get_connection() as connection:
                connection.execute("DELETE FROM employees")
                connection.commit()
            remote = self.export()
            local_bundle["sync"] = {"protocol": 2, "base_revision": remote["sync_revision"], "initial_link": True}
            response = self.client.post("/api/organizations/1/cloud-import", headers=self.headers, json={"bundle": local_bundle})
            self.assertEqual(response.status_code, 200, response.text)
            accepted = response.json()["sync_bundle"]
            remote_employee_id = accepted["records"]["employees"][0]["id"]
            old_employee_id = self.employee_id
            self.employee_id = remote_employee_id
            self.preference("2026-09-15")
            self.employee_id = old_employee_id
        self.preference("2026-09-14")
        with patch.object(services_cloud_client, "request_cloud_json", side_effect=self.cloud_request):
            response = self.client.post("/api/organizations/1/cloud-link", headers=self.headers, json={
                "cloud_api_base_url": "https://cloud.invalid", "cloud_organization_id": 1,
                "cloud_organization_public_id": accepted["organization"]["public_id"],
                "cloud_access_token": self.owner_session["access_token"], "sync_bundle": accepted,
            })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["sync_pending"])
        self.assertEqual(len(self.export()["records"]["employee_week_preferences"]), 2)

    def test_scheduler_desktop_login_is_rejected_before_reading_or_changing_local_data(self):
        session = copy.deepcopy(self.owner_session)
        session["user"]["memberships"][0]["role"] = "scheduler"
        with patch.object(database, "get_connection") as connection, patch.object(services_cloud_client, "request_cloud_json") as request:
            with self.assertRaises(HTTPException) as error:
                services_desktop_session.import_cloud_session_to_desktop("https://cloud.invalid", session)
            self.assertEqual(error.exception.status_code, 403)
            connection.assert_not_called()
            request.assert_not_called()

    def test_unlink_during_http_prevents_old_response_from_being_applied_locally(self):
        self.connect_cloud_copy()
        self.preference("2026-09-14")
        with patch.object(database, "DATABASE_PATH", self.cloud_path):
            self.preference("2026-09-15")

        def request(base_url, path, **kwargs):
            response = self.cloud_request(base_url, path, **kwargs)
            if path.endswith("cloud-import"):
                with database.get_connection() as connection:
                    connection.execute("DELETE FROM app_settings WHERE organization_id = 1 AND key = 'cloud_organization_id'")
                    connection.commit()
            return response

        with patch.object(services_cloud_client, "request_cloud_json", side_effect=request):
            self.assertFalse(services_sync_worker.run_desktop_sync_once())
        self.assertEqual(len(self.export()["records"]["employee_week_preferences"]), 1)

    def test_pull_cannot_apply_old_response_after_another_sync_advanced_baseline(self):
        self.connect_cloud_copy()
        stale_remote = self.export()

        def complete_another_sync(*args, **kwargs):
            self.preference("2026-09-14")
            with database.get_connection() as connection:
                newer = services_bundles.build_organization_export_bundle(connection, 1)
                services_bundles.save_desktop_sync_baseline(connection.cursor(), newer)
                connection.commit()
            return stale_remote

        with patch.object(services_cloud_client, "request_cloud_json", side_effect=complete_another_sync):
            with database.get_connection() as connection:
                with self.assertRaises(HTTPException) as error:
                    services_sync_pull.pull_cloud_preferences_for_desktop_generation(connection)
                self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(len(self.export()["records"]["employee_week_preferences"]), 1)

    def test_relogin_cannot_apply_old_response_after_worker_advanced_baseline(self):
        self.connect_cloud_copy()
        stale_remote = self.export()

        def complete_another_sync(*args, **kwargs):
            self.preference("2026-09-14")
            with database.get_connection() as connection:
                newer = services_bundles.build_organization_export_bundle(connection, 1)
                services_bundles.save_desktop_sync_baseline(connection.cursor(), newer)
                connection.commit()
            return stale_remote

        with patch.object(services_cloud_client, "request_cloud_json", side_effect=complete_another_sync):
            with self.assertRaises(HTTPException) as error:
                services_desktop_session.import_cloud_session_to_desktop("https://cloud.invalid", self.owner_session)
            self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(len(self.export()["records"]["employee_week_preferences"]), 1)

    def test_relogin_does_not_resurrect_last_employee_deleted_locally(self):
        self.connect_cloud_copy()
        with database.get_connection() as connection:
            connection.execute("DELETE FROM employees WHERE id = ?", (self.employee_id,))
            connection.commit()
        with patch.object(services_cloud_client, "request_cloud_json", side_effect=self.cloud_request):
            result = services_desktop_session.import_cloud_session_to_desktop("https://cloud.invalid", self.owner_session)
        self.assertTrue(result["desktop_sync"]["sync_pending"])
        self.assertEqual(self.export()["records"]["employees"], [])


if __name__ == "__main__":
    unittest.main()
