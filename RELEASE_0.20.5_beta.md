# Release 0.20.5 Beta

## Focus

Validate the startup update notification flow before the next installer release.

## Changes

- Added automatic update checks on app startup for the installed desktop runtime.
- Added a startup modal when a newer Windows installer is available.
- Added a post-update changelog modal that shows the main release changes once the updated app starts.
- Stored pending changelog data locally before launching the installer so it survives the app restart.
- Updated runtime, service worker cache keys, Android metadata, PyInstaller specs, installer metadata, and build scripts to `0.20.5_beta`.

## Verification

- `.venv\Scripts\python.exe -m py_compile main.py update_service.py database.py`
- `.venv\Scripts\python.exe -m unittest tests.test_api_regressions.ApiRegressionTests.test_service_worker_caches_current_employee_portal_assets tests.test_api_regressions.ApiRegressionTests.test_update_notifier_script_is_loaded_on_startup_pages tests.test_api_regressions.ApiRegressionTests.test_update_check_reports_newer_github_release_asset tests.test_api_regressions.ApiRegressionTests.test_update_install_records_changelog_for_next_startup`
- `.venv\Scripts\python.exe -m unittest tests.test_generation_reports tests.test_api_regressions`

## Windows Installers

- `ShiftCare_Setup_0.20.5-beta.exe`
  - SHA256: `BE685CC6F956BA07B2D7FD3B1031853AD9BD4954C3BA2F551E9675A0C1369CCE`
- `ShiftCare_Demo_Setup_0.20.5-beta.exe`
  - SHA256: `F0FAD6862EB696592AC72E09FFFF608EA46D263DD3545E3AD57FD4F0350397A7`
