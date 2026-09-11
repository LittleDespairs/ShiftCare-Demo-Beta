"""Release checks that do not import the application or use its database."""

import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseAssetTests(unittest.TestCase):
    def test_generated_release_metadata_is_current(self):
        result = subprocess.run([sys.executable, "tools/sync_release_metadata.py", "--check"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_all_template_scripts_and_styles_are_precached(self):
        from release_config import APP_VERSION

        worker = (ROOT / "static/service-worker.js").read_text(encoding="utf-8")
        assets = set(json.loads(re.search(r"const SHELL_ASSETS = (\[[\s\S]*?\]);", worker)[1]))
        for template in (ROOT / "templates").glob("*.html"):
            text = template.read_text(encoding="utf-8")
            for url in re.findall(r'(?:src|href)="(/static/(?:js|css)/[^"<>]+)"', text):
                self.assertIn(url.replace("{{ app_version }}", APP_VERSION), assets, f"{template.name}: {url}")

    def test_required_service_worker_assets_are_available_on_desktop_and_cloud(self):
        from fastapi.testclient import TestClient
        from unittest.mock import patch
        from shiftcare.application import create_app
        from shiftcare.services import runtime

        worker = (ROOT / "static/service-worker.js").read_text(encoding="utf-8")
        assets = json.loads(re.search(r"const SHELL_ASSETS = (\[[\s\S]*?\]);", worker)[1])
        client = TestClient(create_app(initialize_database=False))
        self.addCleanup(client.close)
        for cloud in (False, True):
            with patch.object(runtime, "is_cloud_employee_portal_mode", return_value=cloud), patch.object(runtime, "is_developer_mode_enabled", return_value=False):
                for asset in assets:
                    with self.subTest(cloud=cloud, asset=asset):
                        self.assertEqual(client.get(asset).status_code, 200)
                self.assertEqual(client.get("/support").status_code, 404)
                self.assertEqual(client.get("/settings").status_code, 404 if cloud else 200)

    def test_current_desktop_specs_exclude_workspace_database(self):
        from release_config import APP_VERSION

        for prefix in ("ShiftCare", "ShiftCare_Demo"):
            source = (ROOT / f"{prefix}_{APP_VERSION}.spec").read_text(encoding="utf-8")
            self.assertNotIn("schedule_app.db", source)
            self.assertIn("collect_submodules('shiftcare')", source)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for frontend behavior checks")
    def test_frontend_behavior(self):
        result = subprocess.run([shutil.which("node"), "--test", "tests/frontend_regressions.cjs"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_android_router_and_lifespan(self):
        from contextlib import asynccontextmanager
        from starlette.testclient import TestClient

        path = ROOT / "android/app/src/main/python/fastapi/__init__.py"
        spec = importlib.util.spec_from_file_location("shiftcare_android_fastapi", path)
        shim = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(shim)
        events = []

        @asynccontextmanager
        async def lifespan(app):
            events.append("started")
            yield
            events.append("stopped")

        router = shim.APIRouter()

        @router.get("/ready")
        def ready():
            return {"ready": True}

        app = shim.FastAPI(lifespan=lifespan)
        app.include_router(router, prefix="/api")
        with TestClient(app) as client:
            self.assertEqual(client.get("/api/ready").json(), {"ready": True})
            self.assertEqual(events, ["started"])
        self.assertEqual(events, ["started", "stopped"])

    def test_android_shim_imports_and_serves_the_modular_application(self):
        script = """
import os, sys, tempfile
from pathlib import Path
os.environ.update(PYTHON_DOTENV_DISABLED='1', DATABASE_ENGINE='sqlite', APP_ENV='development', SCHEDULE_APP_DISABLE_BACKGROUND_SYNC='1', SHIFTCARE_DEMO='0', SCHEDULE_APP_DEMO_MODE='0')
with tempfile.TemporaryDirectory(prefix='shiftcare-android-smoke-') as temporary:
    os.environ['SCHEDULE_APP_DATABASE_PATH'] = str(Path(temporary) / 'smoke.db')
    sys.path.insert(0, str(Path('android/app/src/main/python').resolve()))
    import main
    from starlette.testclient import TestClient
    with TestClient(main.app) as client:
        for path in ['/api/health/live', '/api/health/ready', '/login', '/manifest.webmanifest', '/service-worker.js']:
            response = client.get(path)
            assert response.status_code == 200, (path, response.status_code)
"""
        result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("powershell"), "PowerShell is required for installer checks")
    def test_windows_builder_stops_on_native_failure_and_private_payload(self):
        def quote(value):
            return "'" + str(value).replace("'", "''") + "'"

        with tempfile.TemporaryDirectory(prefix="shiftcare-payload-check-") as temporary:
            (Path(temporary) / "schedule_app.db").write_bytes(b"test fixture, no user data")
            script = f"""
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile({quote(ROOT / 'tools/build_windows_installer.ps1')}, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) {{ throw ($parseErrors | Out-String) }}
foreach ($name in @('Invoke-CheckedNativeCommand', 'Test-InstallerPayload')) {{
    $definition = $ast.Find({{ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name }}, $true)
    Invoke-Expression $definition.Extent.Text
}}
$nativeFailed = $false
try {{ Invoke-CheckedNativeCommand -FilePath {quote(sys.executable)} -Arguments @('-c', 'raise SystemExit(13)') }}
catch {{ if ($_.Exception.Message -notmatch 'exit code 13') {{ throw }}; $nativeFailed = $true }}
if (-not $nativeFailed) {{ throw 'Native nonzero exit was ignored' }}
$payloadFailed = $false
try {{ Test-InstallerPayload -Path {quote(temporary)} }}
catch {{ if ($_.Exception.Message -notmatch 'private runtime data') {{ throw }}; $payloadFailed = $true }}
if (-not $payloadFailed) {{ throw 'Private payload was accepted' }}
"""
            result = subprocess.run([shutil.which("powershell"), "-NoProfile", "-Command", script], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
