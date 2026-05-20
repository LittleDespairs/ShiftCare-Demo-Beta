# ShiftCare 0.18.1 Beta

## Release focus

Restore the `0.17.x` blue interface baseline and force clients to load the corrected CSS through a patch-version cache refresh.

## Changed

- Restored the shared blue `0.17.2_beta` palette, radii, shadows, and schedule table colors in `static/css/style.css` and `static/css/schedule.css`.
- Kept the functional `0.18.0_beta` Home page improvements while making them inherit the restored blue visual system.
- Updated runtime, service worker cache name, static asset query params, Android version metadata, Windows packaging metadata, build docs, and installer script to `0.18.1_beta`.
- Archived the `0.18.0_beta` release notes and PyInstaller spec, then added the active `ShiftCare_0.18.1_beta.spec`.

## Refresh - 2026-05-20

- Restored organization role management in the Organization page, including visible role selection for invitations and inline role changes for accepted members.
- Added owner/admin safeguards for member role updates, including last-owner protection and admin restrictions around owner/admin assignments.
- Added employee-link handling for members whose role is changed to `employee`.
- Added a disabled owner role field to first-organization setup so the creator role is explicit without allowing an unsafe non-owner bootstrap.
- Refreshed script cache-busting and the service worker cache name without changing the `0.18.1_beta` app version.

## Verification

- `static/css/schedule.css` matches `v0.17.2-beta`; `static/css/style.css` differs from `v0.17.2-beta` only by the new Home page classes kept from `0.18.0_beta`.
- Android backend sync tasks passed with JDK 17: `gradlew.bat syncScheduleBackend syncScheduleBackendAssets --no-daemon`.
- Full Python unittest suite passed: 114 tests OK, 1 PostgreSQL integration test skipped locally because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Python root module compile check passed.
- Service worker JavaScript syntax check passed.
- `git diff --check` passed.
- Browser verification passed on `http://127.0.0.1:8026/login`: computed CSS reported `--primary: #2357d6`, `--bg: #f6f8fb`, `--radius-xl: 14px`, `--radius-lg: 12px`, and the service worker contained the new `0.18.1_beta` cache-bust.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.18.1-beta.exe`
- Initial installer SHA256: `A3F33C5A97264AB9757F0E6C3F792718C86892809DC91718E3AAA9004B20BBB8`
- Refresh verification passed on 2026-05-20: `node --check` for `auth_i18n.js`, `organization.js`, and `service-worker.js`; Python root module compile check; full Python unittest suite with 116 tests OK and 1 PostgreSQL integration test skipped locally because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Browser role-management verification passed on 2026-05-20: owner can switch a `read_only` member to `employee`, link that account to an employee record, and the invitation role selector hides/shows employee selection correctly.
- Refreshed Windows installer build: `dist\installer\ShiftCare_Setup_0.18.1-beta.exe`
- Refreshed installer SHA256: `245CB3A9C1DE8F489CDB40A4EB56D6A3EBA90A4F8D7C0DED6F602C48CB3332D7`

## Release notes

- Installer and GitHub release artifacts were rebuilt for `0.18.1_beta`.
- The existing `0.18.1_beta` release was refreshed without a version bump to restore organization role management and ship the updated installer.
