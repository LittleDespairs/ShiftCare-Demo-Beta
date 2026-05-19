# ShiftCare 0.15.16 Beta

## Fixed

- Desktop weekly preferences now pull the latest employee portal wishes from cloud before rendering the weekly preferences list, while still skipping the pull when local pending preference changes must be pushed first.
- Deployed the employee portal backend from the current release line instead of the stale `0.15.11_beta` cloud image.
- Raised Cloud Run capacity and kept three warm instances for the employee portal to avoid `429 Too Many Requests` / no available instance responses.

## Verified

- Full Python unittest suite passed: 103 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Employee portal health endpoint returned `0.15.16_beta` and `/login` returned `200 OK` after the cloud redeploy.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.16-beta.exe`
