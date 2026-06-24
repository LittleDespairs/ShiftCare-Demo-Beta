# Release 0.20.7 Beta

## Focus

Add department-aware scheduling and administrator department access controls.

## Changes

- Added departments as an internal Settings directory for separating care, cleaning, kitchen, and other local teams.
- Removed Departments from the global sidebar while keeping department management inside Settings > Directories.
- Added per-department access controls for organization administrators, schedulers, managers, and read-only users on the Organization members screen.
- Enforced department access on schedule reads/writes, schedule generation, directories, employee assignments, shift templates, coverage requirements, exports, and bulk clear actions.
- Bumped runtime, service worker cache keys, Android metadata, PyInstaller specs, Windows installer metadata, build docs, and release notes to `0.20.7_beta`.

## Verification

- `.venv\Scripts\python.exe -m py_compile main.py update_service.py database.py schemas.py`
- `.venv\Scripts\python.exe -m unittest discover -s tests -v`
  - `Ran 142 tests`
  - `OK (skipped=1)`; PostgreSQL integration was skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- `.\tools\build_windows_installer.ps1 -Release`
- `.\tools\build_windows_installer.ps1 -Target Demo -Release`
- Verified packaged app executable version metadata reports `0.20.7.0` / `0.20.7-beta`.

## Windows Installers

- `ShiftCare_Setup_0.20.7-beta.exe`
  - SHA256: `612D46E86DA627EBD1564541AF3ED0F9FBD9871B613030DAEF81B0BE9AA3B3E4`
  - Size: `31,034,807` bytes
- `ShiftCare_Demo_Setup_0.20.7-beta.exe`
  - SHA256: `90C913CE1D10D85901FBAD199B1364FF3B22861B46D6F55F83BDE055BCCB0739`
  - Size: `31,035,051` bytes

## Signing

- Local build status: unsigned (`Get-AuthenticodeSignature` returned `NotSigned`).
- No `SHIFTCARE_SIGN_CERT_THUMBPRINT` or `SHIFTCARE_SIGN_CERT_SUBJECT` value was configured in this shell, so the `-Sign` release path was not run.

## Publishing

- Published to the public main update feed repository: `LittleDespairs/Schedule_app_releases`.
- Published the demo installer to the public demo update feed repository: `LittleDespairs/ShiftCare-Demo-Beta`.
