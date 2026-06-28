# Release 0.20.9 Beta

## Focus

Add user-submitted bug reports and feature requests, then deploy the cloud API that receives desktop-forwarded reports.
This refresh also ships the employee portal weekly-preference approval flow.

## Changes

- Added the `/feedback` Support page for authenticated users.
- Added `POST /api/feedback/reports` with local `feedback_reports` persistence.
- Added support notification email delivery to `SUPPORT_REPORTS_EMAIL`, defaulting to `reports@shiftcare.co.il`.
- Added frontend error capture so bug reports can include recent browser-side errors.
- Added desktop-to-cloud feedback forwarding when the desktop install is linked to cloud sync.
- Bumped runtime, service worker cache keys, Android metadata, PyInstaller specs, Windows installer metadata, build docs, and release notes to `0.20.9_beta`.
- Added a two-day direct weekly preference limit for employees; extra days are queued for department administrator approval.
- Added approve, reject, and delete actions for queued weekly preference requests.
- Fixed PostgreSQL preference saves after pending-request cleanup.

## Verification

- `.venv\Scripts\python.exe -m py_compile app_config.py email_service.py database.py schemas.py main.py`
- `.venv\Scripts\python.exe -m unittest discover -s tests -v`
- `.venv\Scripts\python.exe -m unittest tests.test_schema_parity tests.test_api_regressions`
- `.venv\Scripts\python.exe -m py_compile main.py database.py schemas.py tests\test_api_regressions.py`
- `.\tools\build_windows_installer.ps1 -Release`
- `.\tools\build_windows_installer.ps1 -Target Demo -Release`
- Cloud Run revision `schedule-app-beta-api-00101-x5d` serves 100% traffic.
- Cloud deployment smoke checks passed for `/api/health/live`, `/api/health/ready`, `/feedback`, and `/api/feedback/reports`.
- Cloud Run revisions `schedule-app-beta-api-00103-tv7` and `schedule-app-beta-api-00104-zrd` deployed the weekly preference fixes and request deletion; deployed health checks passed on `portal.shiftcare.co.il`.
- Verified packaged app executable version metadata reports `0.20.9.0` / `0.20.9-beta`.

## Windows Installers

- `ShiftCare_Setup_0.20.9-beta.exe`
  - SHA256: `41BD76427CFF96D01202C81C13B3478C76975854DD29AC34AD97DA8090359EC2`
  - Size: `31,051,092` bytes
- `ShiftCare_Demo_Setup_0.20.9-beta.exe`
  - SHA256: `DB48D746BE913C1BABBC069EC840DB7AB66A20FCB2FF5C27F940346979CEA785`
  - Size: `31,050,139` bytes

## Signing

- Local build status: unsigned (`Get-AuthenticodeSignature` returned `NotSigned`), matching the current unsigned beta release feed behavior.
