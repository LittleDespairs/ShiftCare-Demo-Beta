# ShiftCare 0.15.19 Beta

## Changed

- Replaced the global same-day multi-position generation setting with a per-position setting.
- Manual schedule edits can now add same-day shifts across different positions without being blocked by the generation rule.
- Automatic generation allows same-day work across positions only when all involved positions allow it.

## Verified

- Full Python unittest suite passed: 108 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.19-beta.exe`
