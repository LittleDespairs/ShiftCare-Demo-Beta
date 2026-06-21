# Release 0.20.6 Beta

## Focus

Verify the end-to-end desktop updater flow from an installed `0.20.5-beta` build.

## Changes

- Bumped the desktop runtime, Windows installer metadata, PyInstaller specs, Android metadata, service worker cache keys, and build scripts to `0.20.6_beta`.
- Published this release as the next GitHub `latest` version so `0.20.5-beta` can show the startup update notification.
- Added a concise release changelog for validating the post-update changelog modal after the upgraded app starts.
- Kept updater behavior unchanged from `0.20.5-beta`; this build is specifically for updater notification validation.

## Verification

- `.venv\Scripts\python.exe -m py_compile main.py update_service.py database.py`
- `.venv\Scripts\python.exe -m unittest tests.test_api_regressions.ApiRegressionTests.test_service_worker_caches_current_employee_portal_assets tests.test_api_regressions.ApiRegressionTests.test_update_notifier_script_is_loaded_on_startup_pages tests.test_api_regressions.ApiRegressionTests.test_update_check_reports_newer_github_release_asset tests.test_api_regressions.ApiRegressionTests.test_update_install_records_changelog_for_next_startup`
- `.venv\Scripts\python.exe -m unittest tests.test_generation_reports tests.test_api_regressions`

## Windows Installers

- `ShiftCare_Setup_0.20.6-beta.exe`
  - SHA256: `0DD5F662B97BEA342B06A18B8B38F6DAB2D30C8B06B589A144BDEB608EC38B66`
- `ShiftCare_Demo_Setup_0.20.6-beta.exe`
  - SHA256: `343EB0F057C58AF8176AD84F682CFBC6FC7449838B2C6A344D04E2DB4BC63A80`
