# Release 0.20.9 Beta

## Focus

Add user-submitted bug reports and feature requests, then deploy the cloud API that receives desktop-forwarded reports.

## Changes

- Added the `/feedback` Support page for authenticated users.
- Added `POST /api/feedback/reports` with local `feedback_reports` persistence.
- Added support notification email delivery to `SUPPORT_REPORTS_EMAIL`, defaulting to `reports@shiftcare.co.il`.
- Added frontend error capture so bug reports can include recent browser-side errors.
- Added desktop-to-cloud feedback forwarding when the desktop install is linked to cloud sync.
- Bumped runtime, service worker cache keys, Android metadata, PyInstaller specs, Windows installer metadata, build docs, and release notes to `0.20.9_beta`.

## Verification

- `.venv\Scripts\python.exe -m py_compile app_config.py email_service.py database.py schemas.py main.py`
- `.venv\Scripts\python.exe -m unittest discover -s tests -v`
- `.\tools\build_windows_installer.ps1 -Release`
- `.\tools\build_windows_installer.ps1 -Target Demo -Release`
- Cloud Run revision `schedule-app-beta-api-00101-x5d` serves 100% traffic.
- Cloud deployment smoke checks passed for `/api/health/live`, `/api/health/ready`, `/feedback`, and `/api/feedback/reports`.
- Verified packaged app executable version metadata reports `0.20.9.0` / `0.20.9-beta`.

## Windows Installers

- `ShiftCare_Setup_0.20.9-beta.exe`
  - SHA256: `04ACC36AC98C7BB132ABAF9E297B35DE61A2B6D09CD6D490BA4328BA0DC3BDFA`
  - Size: `31,042,327` bytes
- `ShiftCare_Demo_Setup_0.20.9-beta.exe`
  - SHA256: `C44EF31BC878DF00F7698AD5AFBCF37091BB9509DDACCD2E0F4732B0B61C6623`
  - Size: `31,043,598` bytes

## Signing

- Local build status: unsigned (`Get-AuthenticodeSignature` returned `NotSigned`), matching the current unsigned beta release feed behavior.
