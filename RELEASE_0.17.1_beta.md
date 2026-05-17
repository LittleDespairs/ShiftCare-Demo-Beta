# ShiftCare 0.17.1 Beta

## Changed

- Matched weekly request shift-picking cards to the main schedule card colors for morning, evening, and night shifts.
- Reworked the mobile weekly requests table into stacked day cards so employees do not need horizontal scrolling on phones.
- Kept the 0.17.0 request modal flow and Cloud Run stability profile.

## Verified

- Python root module compile check passed.
- JavaScript syntax checks passed for `static/js/i18n.js`.
- Weekly request regression tests passed.
- Full Python unittest suite passed: 112 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Cloud Build and Cloud Run deploy passed for `schedule-app-beta-api`.
- Deployed health checks passed for `/api/health/live` and `/api/health/ready` on `portal.shiftcare.co.il`.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.17.1-beta.exe`
- Installer SHA256: `137026E1101C97C234D87AC31D093DB5D73EE4E9C62E21761C7B7D2AF89033EA`
