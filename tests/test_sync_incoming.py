"""Incoming portal changes must not depend on local outgoing activity."""
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException
from tests import test_sync_integrity as fixtures
from tests.test_support import database
from shiftcare.services import cloud_client, sync_pull, sync_worker
from shiftcare.services.bundles import DESKTOP_SYNC_IDENTITY_KEYS


class IncomingSyncTests(TestCase):
    def setUp(self):
        self.fixture = fixtures.SyncIntegrityTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.connect_cloud_copy()

    def add_cloud_requests(self):
        with patch.object(database, "DATABASE_PATH", self.fixture.cloud_path):
            with database.get_connection() as connection:
                for week, day in (("2026-09-13", "2026-09-14"), ("2026-09-20", "2026-09-21")):
                    connection.execute(
                        """INSERT INTO employee_week_preference_requests
                           (organization_id, public_id, employee_id, week_start_date,
                            preference_date, preference_type, request_type, target_category, status)
                           VALUES (1, ?, ?, ?, ?, 'only_morning', 'request_shift', 'morning', 'pending')""",
                        ("portal-request-" + week, self.fixture.employee_id, week, day),
                    )
                connection.commit()

    def legacy_without_baseline(self):
        with database.get_connection() as connection:
            connection.execute("DELETE FROM app_settings WHERE key='desktop_cloud_sync_baseline' AND organization_id=1")
            connection.execute(
                "INSERT INTO app_settings (organization_id, key, value) VALUES (1, 'desktop_cloud_last_push_at', '2026-01-01T00:00:00')"
            )
            connection.commit()

    def test_legacy_additions_after_successful_push_establish_baseline_and_ack_redundant_upserts(self):
        self.legacy_without_baseline()
        self.add_cloud_requests()
        with database.get_connection() as connection:
            # Repeated migration updates can queue rows without changing them.
            connection.execute("UPDATE employees SET full_name=full_name")
            connection.execute("UPDATE desktop_sync_outbox SET status='failed'")
            captured_ids = {row[0] for row in connection.execute("SELECT id FROM desktop_sync_outbox")}
            connection.commit()
        with patch.object(cloud_client, "request_cloud_json", side_effect=self.fixture.cloud_request) as http:
            self.assertTrue(sync_worker.run_desktop_sync_once())
        self.assertEqual([call.kwargs.get("method", "GET") for call in http.call_args_list], ["GET"])
        with database.get_connection() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM employee_week_preference_requests").fetchone()[0], 2)
            self.assertIsNotNone(connection.execute(
                "SELECT value FROM app_settings WHERE key='desktop_cloud_sync_baseline' AND organization_id=1"
            ).fetchone())
            self.assertEqual({row[0] for row in connection.execute(
                "SELECT id FROM desktop_sync_outbox WHERE status='synced'"
            )}, captured_ids)

    def test_legacy_ambiguous_copies_and_deletion_history_still_require_review(self):
        self.legacy_without_baseline()
        self.add_cloud_requests()
        scenarios = (
            "UPDATE employees SET full_name='Local edit'",
            "INSERT INTO desktop_sync_outbox (organization_id, entity_type, entity_public_id, operation) "
            "VALUES (1, 'employee_week_preference_requests', 'portal-request-2026-09-13', 'delete')",
            "UPDATE app_settings SET value='2099-01-01T00:00:00' WHERE key='desktop_cloud_last_push_at'",
        )
        for statement in scenarios:
            with self.subTest(statement=statement):
                with database.get_connection() as connection:
                    connection.execute("SAVEPOINT evidence")
                    connection.execute(statement)
                    with patch.object(cloud_client, "request_cloud_json", side_effect=self.fixture.cloud_request):
                        with self.assertRaises(HTTPException) as conflict:
                            sync_pull.pull_cloud_preferences_for_desktop_generation(connection)
                    self.assertEqual(conflict.exception.status_code, 409)
                    self.assertEqual(connection.execute("SELECT COUNT(*) FROM employee_week_preference_requests").fetchone()[0], 0)
                    self.assertIsNone(connection.execute(
                        "SELECT value FROM app_settings WHERE key='desktop_cloud_sync_baseline'"
                    ).fetchone())
                    connection.execute("ROLLBACK TO evidence")
                    connection.execute("RELEASE evidence")

    def test_legacy_local_only_preference_never_becomes_an_outgoing_addition(self):
        self.legacy_without_baseline()
        self.fixture.preference("2026-09-16")
        self.add_cloud_requests()
        with patch.object(cloud_client, "request_cloud_json", side_effect=self.fixture.cloud_request) as http:
            self.assertFalse(sync_worker.run_desktop_sync_once())
        self.assertEqual([call.kwargs.get("method", "GET") for call in http.call_args_list], ["GET"])
        with database.get_connection() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM employee_week_preferences").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM employee_week_preference_requests").fetchone()[0], 0)

    def test_pull_acknowledges_only_captured_redundant_upserts(self):
        self.legacy_without_baseline()
        self.add_cloud_requests()
        with database.get_connection() as connection:
            connection.execute("UPDATE employees SET full_name=full_name")
            captured = {row[0] for row in connection.execute("SELECT id FROM desktop_sync_outbox")}
            connection.commit()

        def concurrent_unchanged_update(*args, **kwargs):
            with database.get_connection() as writer:
                writer.execute("UPDATE employees SET full_name=full_name")
                writer.commit()
            return self.fixture.cloud_request(*args, **kwargs)

        with patch.object(cloud_client, "request_cloud_json", side_effect=concurrent_unchanged_update):
            with database.get_connection() as connection:
                sync_pull.pull_cloud_preferences_for_desktop_generation(connection)
                connection.commit()
                synced = {row[0] for row in connection.execute("SELECT id FROM desktop_sync_outbox WHERE status='synced'")}
                pending = {row[0] for row in connection.execute("SELECT id FROM desktop_sync_outbox WHERE status='pending'")}
                self.assertEqual(synced, captured)
                self.assertTrue(pending)
                self.assertFalse(captured & pending)

    def test_idle_linked_worker_fetches_requests_for_both_future_weeks_without_push(self):
        self.add_cloud_requests()
        with patch.object(cloud_client, "request_cloud_json", side_effect=self.fixture.cloud_request) as http:
            self.assertTrue(sync_worker.run_desktop_sync_once())
        self.assertEqual([call.kwargs.get("method", "GET") for call in http.call_args_list], ["GET"])
        with database.get_connection() as connection:
            rows = connection.execute(
                "SELECT week_start_date, status FROM employee_week_preference_requests ORDER BY week_start_date"
            ).fetchall()
            self.assertEqual([(row["week_start_date"], row["status"]) for row in rows],
                             [("2026-09-13", "pending"), ("2026-09-20", "pending")])

    def test_pending_local_preference_does_not_hide_independent_portal_requests(self):
        self.fixture.preference("2026-09-16")
        self.add_cloud_requests()
        with patch.object(cloud_client, "request_cloud_json", side_effect=self.fixture.cloud_request):
            for week in ("2026-09-13", "2026-09-20"):
                response = self.fixture.client.get(
                    "/api/employee-week-preference-requests",
                    headers=self.fixture.headers,
                    params={"week_start_date": week, "status": "pending"},
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(len(response.json()), 1, response.text)
        with database.get_connection() as connection:
            self.assertEqual(connection.execute(
                "SELECT COUNT(*) FROM employee_week_preferences WHERE preference_date='2026-09-16'"
            ).fetchone()[0], 1)
            self.assertGreater(connection.execute(
                "SELECT COUNT(*) FROM desktop_sync_outbox WHERE status='pending'"
            ).fetchone()[0], 0)

    def test_retry_backoff_does_not_block_incoming_requests_or_overwrite_local_edits(self):
        self.fixture.preference("2026-09-16")
        with database.get_connection() as connection:
            connection.execute(
                "UPDATE desktop_sync_outbox SET status='failed', next_attempt_at='2099-01-01T00:00:00'"
            )
            connection.execute(
                "INSERT INTO app_settings (organization_id, key, value) "
                "VALUES (1, 'desktop_cloud_last_push_error', 'The previous upload failed')"
            )
            before_count = connection.execute("SELECT COUNT(*) FROM desktop_sync_outbox").fetchone()[0]
            connection.commit()
        self.add_cloud_requests()
        with patch.object(cloud_client, "request_cloud_json", side_effect=self.fixture.cloud_request) as http:
            self.assertTrue(sync_worker.run_desktop_sync_once())
        self.assertEqual([call.kwargs.get("method", "GET") for call in http.call_args_list], ["GET"])
        with database.get_connection() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM desktop_sync_outbox").fetchone()[0], before_count)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM employee_week_preference_requests").fetchone()[0], 2)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM employee_week_preferences").fetchone()[0], 1)
            self.assertEqual(connection.execute(
                "SELECT value FROM app_settings WHERE organization_id=1 AND key='desktop_cloud_last_push_error'"
            ).fetchone()[0], 'The previous upload failed')

    def test_pull_routes_using_captured_identity_instead_of_stale_caller_settings(self):
        self.add_cloud_requests()
        with patch.object(cloud_client, "request_cloud_json", side_effect=self.fixture.cloud_request) as http:
            with database.get_connection() as connection:
                sync_pull.sync_cloud_preferences_to_desktop(connection, {
                    "cloud_api_base_url": "https://stale.invalid", "cloud_organization_id": "99",
                    "desktop_cloud_access_token": "stale-token",
                })
                connection.commit()
        self.assertEqual(http.call_args.args, ("https://cloud.invalid", "/api/organizations/1/cloud-export"))
        self.assertEqual(http.call_args.kwargs["token"], self.fixture.headers["Authorization"].split(" ", 1)[1])

    def test_unlink_before_identity_capture_prevents_request_using_stale_settings(self):
        with database.get_connection() as connection:
            connection.executemany("DELETE FROM app_settings WHERE organization_id=1 AND key=?",
                                   [(key,) for key in DESKTOP_SYNC_IDENTITY_KEYS])
            connection.commit()
            with patch.object(cloud_client, "request_cloud_json") as http:
                self.assertFalse(sync_pull.sync_cloud_preferences_to_desktop(connection, {
                    "cloud_api_base_url": "https://stale.invalid", "cloud_organization_id": "99",
                    "desktop_cloud_access_token": "stale-token",
                }))
            http.assert_not_called()

    def test_repeated_manual_pull_does_not_bypass_outgoing_retry_backoff(self):
        self.fixture.preference("2026-09-16")
        with database.get_connection() as connection:
            connection.execute(
                "UPDATE desktop_sync_outbox SET status='failed', next_attempt_at='2099-01-01T00:00:00'"
            )
            original_count = connection.execute("SELECT COUNT(*) FROM desktop_sync_outbox").fetchone()[0]
            connection.commit()
        self.add_cloud_requests()
        with patch.object(cloud_client, "request_cloud_json", side_effect=self.fixture.cloud_request):
            for _ in range(3):
                with database.get_connection() as connection:
                    sync_pull.pull_cloud_preferences_for_desktop_generation(connection)
                    connection.commit()
                    self.assertEqual(connection.execute("SELECT COUNT(*) FROM desktop_sync_outbox").fetchone()[0], original_count)
