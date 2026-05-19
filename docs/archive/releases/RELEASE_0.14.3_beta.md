# Schedule App 0.14.3 Beta

## Highlights

- Added a Local API / Cloud beta API switch on the login screen.
- Added a global frontend API resolver so existing `/api/...` calls can use the selected backend.
- Added Cloud Run CORS support for local desktop/browser shells.
- Added an online/API status indicator showing Local API or Cloud API readiness.
- Extracted core authorization database helpers into `auth_repository.py`.

## Verification

- `.\.venv\Scripts\python.exe -m py_compile app_config.py auth_repository.py cloud_sql.py database.py main.py excel_export.py word_export.py launcher.py`
- `.\.venv\Scripts\python.exe -m unittest discover -s tests`
- Cloud Run health checks:
  - `/api/health/live`
  - `/api/health/ready`
- Browser smoke check:
  - Login screen API selector
  - Cloud API status: ready

## Artifact

- `ScheduleApp_Setup_0.14.3-beta.exe`
- SHA256: `892A33D8393950CB442700C2EE002468066413214FA887431A7E12A8F2A71E6E`

## Known Limitation

Cloud Run is still a smoke backend using ephemeral SQLite. Do not use it for real organization data until the PostgreSQL/Cloud SQL data layer migration is complete.
