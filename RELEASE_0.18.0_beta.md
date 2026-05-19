# ShiftCare 0.18.0 Beta

## Release focus

Prepare the beta line for release-hardening instead of adding a large new workflow.

## Changed

- Updated runtime, service worker, Windows packaging metadata, build docs, and installer script to `0.18.0_beta`.
- Added the missing `0.17.x` entries back into the active beta changelog.
- Added a GitHub Actions regression workflow with a disposable PostgreSQL service so the PostgreSQL integration test can run outside a manually configured machine.
- Updated the Android wrapper version and backend sync file list so Gradle prebuild copies the current backend modules instead of an incomplete older module set.
- Reworked the Home page into an operational start page with a live next-step recommendation, workspace readiness checklist, current-week counts, license status, and compact shortcuts.
- Shifted the shared interface palette away from the generic blue SaaS baseline toward a quieter graphite/green operations console, with tighter radii and lighter shadows.
- Kept employee weekly request colors, mobile request cards, vacation blockers, and Cloud Run stability work from the `0.17.x` line.

## Verification

- Full Python unittest suite passed: 112 tests OK, 1 PostgreSQL integration test skipped locally because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Python root module compile check passed.
- JavaScript syntax checks passed for `static/js/home.js`, `static/js/i18n.js`, `static/js/employees.js`, `static/js/schedule.js`, `static/js/auth.js`, `static/js/auth_client.js`, `static/js/access_control.js`, and `static/js/organization.js`.
- Browser UI verification passed for the new Home page on desktop width and a 390px mobile viewport, including no horizontal overflow and wrapped action text on mobile.
- Main page and health endpoint smoke checks passed for `/`, `/login`, `/schedule`, `/weekly-preferences`, `/employees`, `/settings`, `/organization`, `/support`, `/guide`, `/download`, `/api/health/live`, and `/api/health/ready`.
- Android backend sync tasks passed: `gradlew.bat syncScheduleBackend syncScheduleBackendAssets --no-daemon`.
- Android shim import smoke passed with synced backend reporting `0.18.0_beta`.
- Packaged app smoke passed for `dist\ShiftCare_0.18.0_beta\ShiftCare_0.18.0_beta.exe` on port `8018`, including `/api/health/live` and `/api/health/ready`.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.18.0-beta.exe`
- Installer SHA256: `D32F501A0799B7D3F2A14637F2AC028D746E396756DB38300FA93E07364B3A2A`
- Cloud Build passed for image tag `0.18.0-beta` with build ID `a2a482db-c998-487f-954d-7ba28318cb54`.
- Cloud Run deployed revision `schedule-app-beta-api-00084-xg6`; traffic was explicitly moved to that revision after deploy preserved traffic on the previous revision.
- Deployed health checks passed for `/api/health/live`, `/api/health/ready`, and `/api/client-config` on `portal.shiftcare.co.il`, all reporting `0.18.0_beta`.

## Release notes

- Android checked-in backend copies are refreshed by Gradle sync tasks during build; the source of truth remains the root backend.
- The local PostgreSQL integration test still requires `SCHEDULE_APP_POSTGRES_TEST_DSN`; CI now provides that variable through its PostgreSQL service.
