# ShiftCare 0.16.1 Beta

## Changed

- Split request schemas, date/time helpers, update logic, app settings, and row serializers out of `main.py`.
- Preserved existing public helper names for tests and local scripts while reducing `main.py` coupling.
- Fixed SQLite context-manager cleanup so `with database.get_connection()` closes connections.

## Verified

- Full Python unittest suite passed: 108 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Python root module compile check passed.
- Cloud dependency smoke passed with `requirements-cloud.txt`.
- Cloud Run-like local health smoke passed for `/api/health/live` and `/api/health/ready`.
- Deployed Cloud Run health smoke passed for the existing `schedule-app-beta-api` service.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.16.1-beta.exe`
- Installer SHA256: `66D87A789CE65F7AA5F59454907D509DE88D69EFED8C0B6611C2662F059DD30E`
