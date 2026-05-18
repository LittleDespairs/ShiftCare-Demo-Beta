# ShiftCare 0.17.2 Beta

## Changed

- Weekly request chips now use the same shift colors as the schedule cards.
- Weekly request and employee permanent-preference cards now read shift colors from app settings instead of fixed local values.
- Employee permanent strict wishes and preferences now use the same card-based request editor pattern as weekly wishes.

## Verified

- Python root module compile check passed.
- JavaScript syntax checks passed for `static/js/i18n.js` and `static/js/employees.js`.
- Weekly request regression tests passed.
- Full Python unittest suite passed: 112 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Cloud Build and Cloud Run deploy passed for `schedule-app-beta-api`.
- Deployed health checks passed for `/api/health/live` and `/api/health/ready` on `portal.shiftcare.co.il`.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.17.2-beta.exe`
- Installer SHA256: A981731C1ACC891E54B8FDA12F221A7B8E87F7581E76AF970A67CFF2D73EE7C2
