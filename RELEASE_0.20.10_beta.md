# Release 0.20.10 Beta

## Focus

Ship the employee weekly-preference approval workflow as a proper update release for desktop, public release feed, and demo distribution.

## Changes

- Added a two-day direct weekly preference limit for employees.
- Queued additional weekly preference days for department administrator approval instead of saving them directly.
- Added administrator approve, reject, and delete actions for queued weekly preference requests.
- Added employee-side deletion for pending and rejected weekly preference requests.
- Fixed PostgreSQL weekly preference saves after pending-request cleanup.
- Bumped runtime, service worker cache keys, Android metadata, PyInstaller specs, Windows installer metadata, build docs, and release notes to `0.20.10_beta`.

## Verification

- `.venv\Scripts\python.exe -m unittest tests.test_schema_parity tests.test_api_regressions`
- `.venv\Scripts\python.exe -m py_compile main.py database.py schemas.py tests\test_api_regressions.py`
- `.\tools\build_windows_installer.ps1 -Release`
- `.\tools\build_windows_installer.ps1 -Target Demo -Release`
- Cloud deployment smoke checks passed for `/api/health/live`, `/api/health/ready`, `/weekly-preferences`, and `/openapi.json` on `portal.shiftcare.co.il`.
- Verified packaged app executable version metadata reports `0.20.10.0` / `0.20.10-beta`.

## Windows Installers

- `ShiftCare_Setup_0.20.10-beta.exe`
  - SHA256: `913171C68F40226DDC2605D6CFA1D20334825DFC209450D0C0FD4203B02C9DB4`
  - Size: `31,047,576` bytes
- `ShiftCare_Demo_Setup_0.20.10-beta.exe`
  - SHA256: `9B8887B51A35468116576E3FA92BD703A1FB0C37F710FA88AA20268723E3CD64`
  - Size: `31,052,586` bytes

## Signing

- Local build status: unsigned (`Get-AuthenticodeSignature` returned `NotSigned`), matching the current unsigned beta release feed behavior.
