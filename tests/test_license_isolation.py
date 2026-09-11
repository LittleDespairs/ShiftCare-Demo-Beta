import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import database
from shiftcare.application import create_app
from shiftcare.services import authentication, bundle_rows


class LicenseImportIsolationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="shiftcare-license-isolation-")
        self.addCleanup(temporary.cleanup)
        for replacement in (
            patch.object(database, "DATABASE_PATH", Path(temporary.name) / "isolated.db"),
            patch.object(database, "get_app_config", return_value=SimpleNamespace(database_engine="sqlite")),
            patch.object(database, "is_demo_mode_enabled", return_value=False),
            patch.object(database, "get_bundled_database_path", return_value=None),
        ):
            replacement.start()
            self.addCleanup(replacement.stop)
        database.init_db()
        self.license = {"license_id": "known-license-other-organization", "certificate_json": '{"fixture":true}', "signature": "test-signature", "plan_code": "fixture", "employee_limit": 25}
        with database.get_connection() as connection:
            connection.execute("INSERT INTO organizations (id, public_id, name) VALUES (2, 'org-license-other', 'Other organization')")
            connection.execute("INSERT INTO users (id, email, full_name) VALUES (91, 'license-owner@example.test', 'Owner')")
            connection.execute("INSERT INTO organization_memberships (organization_id, user_id, role, status) VALUES (1, 91, 'owner', 'active')")
            bundle_rows._insert_license_bundle_rows(connection.cursor(), [self.license], 2, "2026-09-11")
        self.app = create_app(initialize_database=False)
        self.app.dependency_overrides[authentication.get_current_user] = lambda: {
            "id": 91, "status": "active", "memberships": [{"organization_id": 1, "role": "owner", "status": "active"}]
        }
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def test_cloud_import_cannot_move_or_overwrite_another_organizations_license(self):
        exported = self.client.get("/api/organizations/1/cloud-export")
        self.assertEqual(exported.status_code, 200, exported.text)
        bundle = exported.json()
        original_name = bundle["organization"]["name"]
        bundle["sync"] = {"protocol": 2, "base_revision": bundle["sync_revision"]}
        bundle["organization"]["name"] = "Must roll back"
        bundle["records"]["licenses"] = [{**copy.deepcopy(self.license), "employee_limit": 999, "certificate_json": '{"changed":true}'}]
        response = self.client.post("/api/organizations/1/cloud-import", json={"bundle": bundle, "replace_existing": True})
        self.assertEqual(response.status_code, 409, response.text)
        with database.get_connection() as connection:
            row = connection.execute("SELECT organization_id, employee_limit, certificate_json FROM licenses WHERE license_id = ?", (self.license["license_id"],)).fetchone()
            self.assertEqual(tuple(row), (2, 25, self.license["certificate_json"]))
            self.assertEqual(connection.execute("SELECT name FROM organizations WHERE id = 1").fetchone()[0], original_name)

    def test_same_organization_license_update_preserves_identity(self):
        with database.get_connection() as connection:
            old_id = connection.execute("SELECT id FROM licenses WHERE license_id = ?", (self.license["license_id"],)).fetchone()[0]
            count = bundle_rows._insert_license_bundle_rows(connection.cursor(), [{**self.license, "employee_limit": 30}], 2, "2026-09-12")
            self.assertEqual(count, 1)
            row = connection.execute("SELECT id, organization_id, employee_limit FROM licenses WHERE license_id = ?", (self.license["license_id"],)).fetchone()
            self.assertEqual(tuple(row), (old_id, 2, 30))
