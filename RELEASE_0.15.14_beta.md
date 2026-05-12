# ShiftCare 0.15.14 beta

## Weekly preferences

- Fixed the desktop background sync worker so pending local weekly preferences are pushed before any cloud pull can replace local preference tables.
- Prevented local preferences from being deleted by a destructive cloud preference pull while the desktop outbox still has pending changes.
- Added regression coverage for preserving weekly preferences during background sync.

## Verification

- Full Python unittest suite passed: 102 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Python compile check passed for `main.py`.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.14-beta.exe`
