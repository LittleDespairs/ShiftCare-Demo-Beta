# ShiftCare 0.15.18 Beta

## Added

- Added a configurable maximum daily work duration, in minutes, for same-day morning and evening pairs.
- The generator now rejects morning-evening pair candidates whose combined working time exceeds the configured daily limit.
- Morning-night pair generation remains exempt from the daily work limit.

## Verified

- Full Python unittest suite passed: 107 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.18-beta.exe`
