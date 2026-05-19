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
- Made `/docs` usable as an authenticated API console: OpenAPI now exposes `BearerAuth`, and Swagger UI applies the active ShiftCare browser session token to `/api/*` requests.
- Kept employee weekly request colors, mobile request cards, vacation blockers, and Cloud Run stability work from the `0.17.x` line.

## Verification

- Full Python unittest suite passed: 114 tests OK, 1 PostgreSQL integration test skipped locally because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Python root module compile check passed.
- OpenAPI/docs regression tests passed for the `BearerAuth` schema and `/docs` browser-session token interceptor.
- JavaScript syntax checks passed for `static/js/home.js`, `static/js/i18n.js`, `static/js/employees.js`, `static/js/schedule.js`, `static/js/auth.js`, `static/js/auth_client.js`, `static/js/access_control.js`, and `static/js/organization.js`.
- Browser UI verification passed for the new Home page on desktop width and a 390px mobile viewport, including no horizontal overflow and wrapped action text on mobile.
- Browser UI verification passed for `/docs`, including the `Authorize` control, `BearerAuth`, generated operations, and no Swagger error panel.
- Main page and health endpoint smoke checks passed for `/`, `/login`, `/schedule`, `/weekly-preferences`, `/employees`, `/settings`, `/organization`, `/support`, `/guide`, `/download`, `/api/health/live`, and `/api/health/ready`.
- Android backend sync tasks passed: `gradlew.bat syncScheduleBackend syncScheduleBackendAssets --no-daemon`.
- Android shim import smoke passed with synced backend reporting `0.18.0_beta`.
- Packaged app smoke passed for `dist\ShiftCare_0.18.0_beta\ShiftCare_0.18.0_beta.exe` on port `8018`, including `/api/health/live`, `/api/health/ready`, and `/docs`.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.18.0-beta.exe`
- Installer SHA256: `79E75CC8D42AF3938F9836407FFC6417CA1B95FD01E66F249C81AD45DD9FB39F`
- Cloud Build passed for image tag `0.18.0-beta` with build ID `3fc1bdf1-5028-4443-875a-384827883f60` and image digest `sha256:e49ce9a5a3c7a5a8e8df9da413ab5d44fe3d4e5a5a9772c0a8c033e375ff402c`.
- Cloud Run deployed revision `schedule-app-beta-api-docs-auth-20260519`; traffic was explicitly moved to that revision after deploy preserved traffic on the previous revision.
- Deployed health checks passed for `/api/health/ready`, `/docs`, and `/openapi.json` on `portal.shiftcare.co.il`, all reporting `0.18.0_beta` where applicable.

## Release notes

- Android checked-in backend copies are refreshed by Gradle sync tasks during build; the source of truth remains the root backend.
- The local PostgreSQL integration test still requires `SCHEDULE_APP_POSTGRES_TEST_DSN`; CI now provides that variable through its PostgreSQL service.
