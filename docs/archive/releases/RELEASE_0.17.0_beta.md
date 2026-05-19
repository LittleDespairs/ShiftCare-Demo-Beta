# ShiftCare 0.17.0 Beta

## Changed

- Reworked employee weekly requests into multiple per-day requests with request, exclude, day off, and vacation types.
- Added vacation as a schedule day status and generator blocker.
- Improved Cloud Run stability defaults and cloud request retry behavior.
- Kept the mobile schedule layout fixes and Cloud SQL migrations in the release.

## Verified

- Full Python unittest suite passed: 112 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Python root module compile check passed.
- JavaScript syntax checks passed for `static/js/schedule.js` and `static/js/i18n.js`.
- Cloud Build and Cloud Run deploy passed for `schedule-app-beta-api`.
- Deployed health checks passed for `/api/health/live` and `/api/health/ready` on `portal.shiftcare.co.il`.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.17.0-beta.exe`
- Installer SHA256: `DF98D4AE30ED70A1A98EB5B717F87C638D9E724436F7268D591CA0F51CFB4E1E`
