# Release 0.20.8 Beta

## Focus

Hotfix desktop startup after the `0.20.7_beta` department migration.

## Changes

- Made SQLite rebuild migrations recover from stale `*_old` tables left by a failed previous launch.
- Fixed startup failure caused by `sqlite3.OperationalError: there is already another table or index with this name: shift_templates_old`.
- Preserved existing shift templates and schedule entries while completing the department migration.
- Added regression coverage for stale `shift_templates_old` recovery.
- Bumped runtime, service worker cache keys, Android metadata, PyInstaller specs, Windows installer metadata, build docs, and release notes to `0.20.8_beta`.

## Verification

- `.venv\Scripts\python.exe -m py_compile database.py main.py schemas.py`
- `.venv\Scripts\python.exe -m unittest tests.test_api_regressions.ApiRegressionTests.test_shift_template_rebuild_recovers_from_stale_old_table`
- `.venv\Scripts\python.exe -m unittest discover -s tests -v`
- Migrated a copy of the broken installed database from `%LOCALAPPDATA%\Schedule App\schedule_app.db`; schema version reached `22`, stale `_old` tables were removed, `16` shift templates and `272` schedule entries were preserved.
- `.\tools\build_windows_installer.ps1 -Release`
- `.\tools\build_windows_installer.ps1 -Target Demo -Release`
- Verified packaged app executable version metadata reports `0.20.8.0` / `0.20.8-beta`.

## Windows Installers

- `ShiftCare_Setup_0.20.8-beta.exe`
  - SHA256: `8B5816305679A06CEA2D97C40B679B7BE494AC98E56AB85ED0AC478F8E6F754D`
  - Size: `31,035,986` bytes
- `ShiftCare_Demo_Setup_0.20.8-beta.exe`
  - SHA256: `4EA8DCE7002AB13981C90073BC96299F947FB41451FBD82D47DC0779D0EB8F85`
  - Size: `31,032,445` bytes

## Signing

- Local build status: unsigned (`Get-AuthenticodeSignature` returned `NotSigned`), matching the current unsigned beta release feed behavior.

## Recovery Note

If `0.20.7_beta` was already installed and the app no longer opens, install `0.20.8_beta` over the existing installation. The repaired migration runs before the desktop window opens.
