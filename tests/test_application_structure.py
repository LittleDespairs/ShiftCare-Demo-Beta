"""HTTP contract and lifecycle checks for the modular application."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.test_support import main
from shiftcare.application import create_app
from shiftcare import config
from shiftcare.services import runtime, sync_worker


class ApplicationCompositionTests(unittest.TestCase):
    def test_existing_http_routes_survive_router_extraction(self):
        expected = json.loads((Path(__file__).parent / 'fixtures' / 'api_routes_02013.json').read_text(encoding='utf-8'))
        actual = [(method, route.path) for route in main.app.routes for method in getattr(route, 'methods', [])]
        for method, path in expected:
            self.assertEqual(actual.count((method, path)), 1, f'{method} {path}')

    def test_factories_have_independent_openapi_and_no_duplicate_routes(self):
        first, second = create_app(initialize_database=False), create_app(initialize_database=False)
        self.assertIsNot(first, second)
        self.assertEqual(len(first.routes), len(second.routes))
        schema = first.openapi()
        self.assertEqual(schema['info']['version'], '0.21.1_beta')
        self.assertIn('BearerAuth', schema['components']['securitySchemes'])
        self.assertIsNone(second.openapi_schema)
        with TestClient(second) as client:
            self.assertEqual(client.get('/api/health/live').json()['app_version'], '0.21.1_beta')
            self.assertEqual(client.get('/api/health/ready').status_code, 200)

    def test_manifest_distinguishes_normal_and_demo_applications(self):
        with TestClient(create_app(initialize_database=False)) as client:
            for name in ('ShiftCare', 'ShiftCare Demo'):
                with patch.object(config, 'APP_NAME', name):
                    response = client.get('/manifest.webmanifest')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['name'], name)
                self.assertEqual(response.json()['short_name'], name)
                self.assertEqual(response.headers['cache-control'], 'no-cache')

    def test_worker_can_stop_and_restart_without_duplicate_threads(self):
        with patch.object(sync_worker, 'should_start_desktop_sync_worker', return_value=True), patch.object(runtime, 'is_demo_mode_enabled', return_value=False):
            worker = sync_worker.start_desktop_sync_worker()
            self.assertIsNotNone(worker)
            self.addCleanup(sync_worker.stop_desktop_sync_worker, worker)
            self.assertIsNone(sync_worker.start_desktop_sync_worker())
            sync_worker.stop_desktop_sync_worker(None)
            self.assertTrue(worker.is_alive())
            sync_worker.stop_desktop_sync_worker(worker)
            self.assertFalse(worker.is_alive())
            restarted = sync_worker.start_desktop_sync_worker()
            self.addCleanup(sync_worker.stop_desktop_sync_worker, restarted)
            self.assertIsNotNone(restarted)
            self.assertIsNot(restarted, worker)
            sync_worker.stop_desktop_sync_worker(restarted)
            self.assertFalse(restarted.is_alive())


if __name__ == '__main__':
    unittest.main()
