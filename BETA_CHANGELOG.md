# Beta Changelog

This file tracks beta builds across the active beta lines from `0.12.x_beta` onward.

# 0.20.9_beta - 2026-06-24

## Release Focus

Add user-submitted bug reports and feature requests, and deploy the feedback endpoint to cloud.

## Changed

- Added a user-facing Support page at `/feedback` for bug reports and feature requests.
- Added `POST /api/feedback/reports`, `feedback_reports` storage, frontend error context capture, and support report email notifications to `reports@shiftcare.co.il`.
- Added desktop-to-cloud forwarding for feedback reports when a desktop install is linked to the cloud API.
- Updated runtime version, service worker cache keys, Android metadata, PyInstaller specs, installer metadata, build docs, and release notes to `0.20.9_beta`.

## Verification

- Automated regression tests passed locally.
- Cloud deployment smoke checks passed for the feedback endpoint and health checks.

# 0.20.8_beta - 2026-06-24

## Release Focus

Hotfix desktop startup after the `0.20.7_beta` department migration.

## Changed

- Made SQLite table rebuild migrations recover from stale `*_old` tables left by a failed previous launch.
- Fixed startup failure caused by `sqlite3.OperationalError: there is already another table or index with this name: shift_templates_old`.
- Added regression coverage for stale `shift_templates_old` recovery during shift template rebuilds.
- Updated runtime version, service worker cache keys, Android metadata, PyInstaller specs, installer metadata, build docs, and release notes to `0.20.8_beta`.

## Verification

- Verified the hotfix migrates a copy of the broken installed database and preserves shift templates and schedule entries.
- Automated regression tests passed locally.

# 0.20.7_beta - 2026-06-23

## Release Focus

Add department-aware scheduling controls and restrict administrator access by department.

## Changed

- Added departments as an internal Settings directory so roles, employees, templates, coverage requirements, and schedules can be separated by care team, cleaning, kitchen, or other local units.
- Removed the standalone Departments item from the global sidebar; departments remain managed from Settings > Directories.
- Added per-department access for organization administrators, schedulers, managers, and read-only users from the Organization members screen.
- Enforced department restrictions on schedule reads/writes, generation, directory management, employee assignment, coverage requirements, shift templates, exports, and bulk clear actions.
- Updated runtime version, service worker cache keys, Android metadata, PyInstaller specs, installer metadata, build docs, and release notes to `0.20.7_beta`.

## Verification

- Automated regression tests passed locally.
- Added regression coverage for department-scoped administrator access across schedule and directory APIs.

# 0.20.4_beta - 2026-06-19

## Release Focus

Improve schedule generation fidelity and make manual schedule corrections safer for production use.

## Changed

- Improved position assignment priority handling so primary and higher-priority employees are favored more consistently during generation.
- Added multi-request permanent strict and soft preferences in employee cards, matching the weekly preferences workflow.
- Added manual shift time overrides on the schedule page and included those overrides in coverage calculations.
- Preserved manually pre-filled shifts during generation and counted them toward coverage instead of replacing them.
- Stopped single-position generation from filling unrelated empty days with day-off statuses.
- Prevented hidden cloud preference pulls from replacing local preferences immediately before generation, and kept pulled cloud preference rows out of the local sync outbox.
- Updated runtime, service worker cache keys, Android metadata, PyInstaller specs, installer metadata, build docs, and release notes to `0.20.4_beta`.

## Verification

- Automated regression tests passed locally.
- Added regression coverage for manual time overrides, preserved manual shifts, multi-request recurring preferences, strict preference generation, and cloud preference sync safety.

# 0.20.3_beta - 2026-06-18

## Release Focus

Employee portal schedule synchronization hotfix.

## Changed

- Fixed cloud sync so schedules created in the desktop/admin flow keep the correct organization ownership.
- Preserved employee portal account links during full cloud imports by restoring links through stable employee public IDs.
- Kept portal schedule reads scoped to the authenticated organization.
- Updated runtime, service worker cache keys, Android metadata, PyInstaller specs, installer metadata, build docs, and release notes to `0.20.3_beta`.

## Verification

- Automated regression tests passed locally.
- Added regression coverage for employee portal schedule visibility after cloud import.

# 0.20.2_beta - 2026-06-17

## Release Focus

Employee portal styling and mobile reliability refresh.

## Changed

- Applied the new operations visual style to the employee portal surfaces.
- Reworked mobile weekly preferences into a simpler employee-facing card layout.
- Fixed local/staging employee portal mode so login uses the portal backend login flow, not desktop cloud import.
- Updated service worker cache keys and static asset cache-busters so phones receive the new CSS and JavaScript.
- Hid stale disabled employee accounts from organization member flows and reinvites.
- Updated runtime, service worker cache keys, Android metadata, PyInstaller specs, installer metadata, build docs, and release notes to `0.20.2_beta`.

## Verification

- Automated regression tests passed locally.
- Browser smoke checks passed locally for employee portal login, weekly preferences save, and read-only schedule on mobile viewport.

# 0.20.1_beta - 2026-06-15

## Release Focus

Small bug fixes were completed.

## Changed

- Small bug fixes were completed.
- Updated runtime, service worker cache keys, Android metadata, PyInstaller specs, installer metadata, build docs, and release notes to `0.20.1_beta`.

## Verification

- Automated regression tests passed locally.
- Browser smoke checks passed locally for the schedule page and RTL layout.

# 0.20.0_beta - 2026-06-15

## Release Focus

Make large employee rosters easier to work with by adding search and filters, then refresh the scheduling workspace around a denser weekly board and a clearer week picker.

## Changed

- Added employee search and filtering controls to staff-heavy pages, including position filtering on Employees and Weekly Preferences.
- Reworked the main-app Weekly Preferences tab into an all-employee table so employees no longer need to be selected one by one before entering requests.
- Kept the employee portal wish flow separate while applying the shared filtering/search behavior to the main and demo applications.
- Redesigned the Schedule page around a broad weekly table, always-visible coverage status, retained shift/status creation actions, and a right-side operational panel.
- Replaced plain date-field week selection with a more deliberate week picker on pages that choose a week.
- Updated runtime, service worker cache keys, Android metadata, PyInstaller specs, installer metadata, build docs, and release notes to `0.20.0_beta`.
- Archived the previous root release note and `0.19.2_beta` PyInstaller specs, then added the active `0.20.0_beta` specs.

## Verification

- Browser smoke checks passed locally for the redesigned schedule page and demo workflow.
- JavaScript syntax checks passed for the changed frontend scripts.
- Windows installer outputs for this build are `dist\installer\ShiftCare_Setup_0.20.0-beta.exe` and `dist\installer\ShiftCare_Demo_Setup_0.20.0-beta.exe`.
- Installer SHA256: `190E7BAE538A292A4132AD726214530B38CE3F67544937F7EAA35BD7102C7B55` for main and `874ABA80BA0E1ADF8D4E202C3B4FCC947E89E4FE6AD3DC927E05259CAC983F35` for demo.

# 0.19.0_beta - 2026-06-05

## Release Focus

Ship transactional email delivery for invitations and auth links, then align cloud and desktop version metadata on the `0.19.0_beta` beta line.

## Changed

- Added SMTP-backed email delivery for organization invitations, password reset, and email verification.
- Added `/reset-password` and `/verify-email` pages for emailed auth links.
- Added Cloud Run email configuration with Secret Manager-backed SMTP password handling.
- Added Box SMTP support for `invite@shiftcare.co.il` and DNS authentication records for `shiftcare.co.il` including MX, SPF, DMARC, and DKIM.
- Updated Organization invite feedback for sent, disabled, and failed email states while preserving copyable invitation links.
- Updated runtime, service worker cache keys, Android metadata, PyInstaller spec, installer metadata, build docs, and release notes to `0.19.0_beta`.

## Verification

- SMTP login and test send passed through `cp57.box.co.il:465`.
- Google Cloud DNS resolves the new email authentication records.
- API regression tests and deployed `/api/client-config` version verification are part of the release pass.

# 0.18.1_beta - 2026-05-19

## Release Focus

Restore the visual baseline from the `0.17.x` beta line and force a patch-version cache refresh.

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

## Verified

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

# 0.18.0_beta - 2026-05-19

## Release Focus

Prepare the beta line for release-hardening instead of adding a large new workflow.

## Changed

- Updated runtime, service worker, Windows packaging metadata, build docs, and installer script to `0.18.0_beta`.
- Added the missing `0.17.x` entries back into this changelog.
- Added a GitHub Actions regression workflow with a disposable PostgreSQL service so the PostgreSQL integration test can run outside a manually configured machine.
- Updated the Android wrapper version and backend sync file list so Gradle prebuild copies the current backend modules instead of an incomplete older module set.
- Reworked the Home page into an operational start page with a live next-step recommendation, workspace readiness checklist, current-week counts, license status, and compact shortcuts.
- Shifted the shared interface palette away from the generic blue SaaS baseline toward a quieter graphite/green operations console, with tighter radii and lighter shadows.
- Made `/docs` usable as an authenticated API console: OpenAPI now exposes `BearerAuth`, and Swagger UI applies the active ShiftCare browser session token to `/api/*` requests.
- Kept employee weekly request colors, mobile request cards, vacation blockers, and Cloud Run stability work from the `0.17.x` line.

## Verified

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

# 0.17.2_beta - 2026-05-18

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
- Installer SHA256: `A981731C1ACC891E54B8FDA12F221A7B8E87F7581E76AF970A67CFF2D73EE7C2`

# 0.17.1_beta - 2026-05-17

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

# 0.17.0_beta - 2026-05-15

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

# 0.16.1_beta - 2026-05-14

## Changed

- Split request schemas, date/time helpers, update logic, app settings, and row serializers out of `main.py`.
- Preserved public helper names used by tests and local scripts while reducing `main.py` coupling.
- Fixed SQLite context-manager cleanup for `database.get_connection()`.

## Verified

- Full Python unittest suite passed: 108 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Python root module compile check passed.
- Cloud dependency smoke passed with `requirements-cloud.txt`.
- Cloud Run-like local health smoke passed for `/api/health/live` and `/api/health/ready`.
- Deployed Cloud Run health smoke passed for the existing `schedule-app-beta-api` service.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.16.1-beta.exe`
- Installer SHA256: `66D87A789CE65F7AA5F59454907D509DE88D69EFED8C0B6611C2662F059DD30E`

# 0.15.19_beta

## Changed

- Replaced the global same-day multi-position generation setting with a per-position setting.
- Manual schedule edits can now add same-day shifts across different positions without being blocked by the generation rule.
- Automatic generation allows same-day work across positions only when all involved positions allow it.

## Verified

- Full Python unittest suite passed: 108 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.19-beta.exe`

# 0.15.18_beta - 2026-05-12

## Added

- Added a configurable maximum daily work duration, in minutes, for same-day morning and evening pairs.
- The generator now rejects morning-evening pair candidates whose combined working time exceeds the configured daily limit.
- Morning-night pair generation remains exempt from the daily work limit.

## Verified

- Full Python unittest suite passed: 107 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.18-beta.exe`

# 0.15.17_beta - 2026-05-12

## Fixed

- Desktop weekly preferences now pull the latest employee portal wishes from cloud before rendering the weekly preferences list, while still skipping the pull when local pending preference changes must be pushed first.
- Deployed the employee portal backend from the current release line instead of the stale `0.15.11_beta` cloud image.
- Raised Cloud Run capacity and kept three warm instances for the employee portal to avoid `429 Too Many Requests` / no available instance responses.

## Verified

- Full Python unittest suite passed: 106 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Employee portal health endpoint returned `0.15.17_beta` and `/login` returned `200 OK` after the cloud redeploy.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.17-beta.exe`

# 0.15.15_beta - 2026-05-06

## Release

- Rebuilt the Windows installer from the latest `main` after the weekly-preference sync fix.
- Kept the bundled database in the desktop package so first installs include the packaged full-access license.
- Updated runtime version, service worker cache keys, Windows packaging metadata, and installer spec to `0.15.15_beta`.

## Verified

- Full Python unittest suite passed: 102 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.15-beta.exe`

# 0.15.14_beta - 2026-05-06

## Fixed

- Fixed the desktop background sync worker so pending local weekly preferences are pushed before any cloud pull can replace local preference tables.
- Prevented local preferences from being deleted by a destructive cloud preference pull while the desktop outbox still has pending changes.
- Added regression coverage for preserving weekly preferences during background sync.

## Changed

- Updated runtime version, service worker cache keys, Windows packaging metadata, and installer spec to `0.15.14_beta`.

## Verified

- Full Python unittest suite passed: 102 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Python compile check passed for `main.py`.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.14-beta.exe`

# 0.15.13_beta - 2026-05-06

## Fixed

- Fixed the Windows desktop package so `schedule_app.db` is bundled with the PyInstaller build.
- Fresh installs can now copy the bundled database during first launch, including the packaged full-access license.
- Existing installs that already created a trial runtime database now seed the bundled license without overwriting user data, when the organization public ID matches.

## Changed

- Updated runtime version, service worker cache keys, Windows packaging metadata, and installer spec to `0.15.13_beta`.

## Verified

- Full Python unittest suite passed: 101 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.13-beta.exe`

# 0.15.12_beta - 2026-05-06

## Release Focus

Fix weekly employee preferences so local changes are reliably preserved and respected during schedule generation.

## Changes

- Fixed desktop generation so pending local weekly preference changes are not overwritten by a cloud pull before the generator reads them.
- Added API validation that rejects weekly preference dates outside the selected week.
- Updated the weekly preferences page so changing the week or employee clears stale loaded rows before saving.
- Saving `no_preference` now clears the stored weekly preference instead of leaving redundant records.
- Preserved the current cloud organization license import/export updates in this release line.
- Updated runtime version, service worker cache keys, Windows packaging metadata, and installer spec to `0.15.12_beta`.

## Verification

- Full Python unittest suite passed: 100 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Python compile check passed for `main.py`.

## Release Artifact

- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.12-beta.exe`

# 0.15.11_beta - 2026-05-06

## Added

- Added permanent employee preferences with separate strict and soft rules for each weekday.
- Added employee-screen controls for editing permanent preferences in the employee modal.
- Added generation support for strict permanent rules and soft scoring penalties during automatic schedule generation.

## Changed

- Added `employee_recurring_preferences` to SQLite, PostgreSQL baseline, organization export/import, cleanup, backup/restore, and employee delete impact reporting.
- Restricted permanent preference management to owners and admins after authorization is initialized.
- Updated runtime version, service worker cache keys, Windows packaging metadata, and installer spec to `0.15.11_beta`.

## Verified

- `node --check static/js/employees.js static/js/i18n.js`
- `.venv\Scripts\python.exe -m unittest tests.test_api_regressions tests.test_generation_reports`
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.11-beta.exe`

# 0.15.10_beta - 2026-05-03

## Fixed

- Fixed the organization invitation employee selector placeholder so it is translated instead of showing `Select employee` in the Russian interface.
- Renamed the Russian employee ID-card table column to `Номер ID`, avoiding the duplicate `ID / ID` header during demos.
- Render empty employee ID-card values as `—` so the employee table does not look broken when ID numbers are not filled yet.

## Changed

- Updated runtime version, service worker cache keys, Windows packaging metadata, and installer spec to `0.15.10_beta`.

## Verified

- `node --check static/js/auth_i18n.js static/js/i18n.js static/js/employees.js`
- Local UI smoke test for sidebar navigation, schedule loading, weekly preferences, organization, settings, employees, support, and guide pages.
- `.venv\Scripts\python.exe -m unittest discover -s tests`

# 0.15.9_beta - 2026-05-02

## Fixed

- Fixed sidebar navigation becoming effectively unclickable after the 0.15.8 navigation normalization.
- Prevented access-control navigation normalization from repeatedly replacing sidebar links through the page mutation observer.
- Kept role-based navigation ordering stable without recreating link DOM nodes on every observer pass.

## Changed

- Updated runtime version, service worker cache keys, Windows packaging metadata, and installer spec to `0.15.9_beta`.

## Verified

- `node --check static/js/access_control.js`
- Playwright click-through check from the sidebar to `/organization`.
- `.venv\Scripts\python.exe -m unittest discover -s tests`

# 0.15.8_beta - 2026-05-02

## Fixed

- Stabilized sidebar navigation so active items keep the same height and alignment as inactive items.
- Normalized role-based navigation ordering and icons, including the Organization tab in desktop and employee portal views.
- Added the missing Organization sidebar collapse control and translated Organization page labels.
- Fixed missing translation keys that could surface as raw technical IDs in the interface.
- Removed mobile horizontal overflow from Organization, support, and directory pages.

## Changed

- Updated runtime version, service worker cache keys, Windows packaging metadata, and installer spec to `0.15.8_beta`.

## Verified

- `node --check static/js/access_control.js`
- `node --check static/js/organization.js`
- `node --check static/js/i18n.js`
- `node --check static/js/auth_i18n.js`
- `.venv\Scripts\python.exe -m unittest discover -s tests`
- Playwright desktop/mobile layout checks against local pages.

# 0.15.7_beta - 2026-05-01

## Fixed

- Rebuilt the hosted employee portal login entry so the call-to-action no longer overlaps the text panel on wide desktop screens.
- Treated `shiftcare.co.il` and `*.shiftcare.co.il` as hosted cloud origins in the auth client.
- Updated Cloud Build defaults to use `https://portal.shiftcare.co.il` as the public app base URL.

## Changed

- Updated runtime version, service worker cache keys, Windows packaging metadata, and installer spec to `0.15.7_beta`.

## Verified

- `node --check static/js/auth_client.js`
- `node --check static/js/auth.js`
- `node --check static/js/auth_i18n.js`
- `.venv\Scripts\python.exe -m unittest discover -s tests`

# 0.15.6_beta - 2026-05-01

## Fixed

- Polished the Organization page with a language switcher, translated labels/messages/statuses, and corrected field labels in the invitation form.
- Employee portal and invitation links now render as full URLs with open/copy actions instead of raw tokens or unconfigured text.
- Desktop client config now falls back to `https://portal.shiftcare.co.il` for employee portal and invitation URLs.

## Changed

- Added the payment provider and selling-site concept to the private payment/license checklist.
- Updated runtime version, service worker cache keys, Windows packaging metadata, and installer spec to `0.15.6_beta`.

## Verified

- `node --check static/js/organization.js`
- `node --check static/js/auth_i18n.js`
- `node --check static/js/i18n.js`
- `node --check static/js/auth.js`
- `.venv\Scripts\python.exe -m unittest discover -s tests`

# 0.15.5_beta - 2026-05-01

## Added

- Added the local licensing runtime for paid/trial status, employee limits, grace periods, and desktop enforcement.
- Added the `Settings -> License & Support` panel with license status, last online check, activation code entry, offline license import, and support diagnostics copy.
- Added `tools/issue_license.py` for support-issued `.shiftcare-license` files and activation codes.
- Added regression coverage for SQLite/PostgreSQL schema parity and license enforcement.

## Changed

- Updated SQLite and PostgreSQL baseline schemas to version `17` with license tables.
- Updated runtime version, service worker cache keys, Windows packaging metadata, and installer spec to `0.15.5_beta`.

## Verified

- `node --check static/js/i18n.js`
- `node --check static/js/auth.js`
- `node --check static/js/auth_i18n.js`
- `node --check static/js/schedule.js`
- `.venv\Scripts\python.exe -m unittest discover -s tests`

# 0.15.4_beta - 2026-05-01

## Changed

- Updated the cloud employee portal login shell with a cleaner ShiftCare-styled entry panel and cache-busted auth assets.
- Changed employee web schedule scoping so employees see the full schedule for their selected/primary assigned position, including coworkers in the same role, while still blocking unassigned positions.
- Updated desktop/cloud sync and desktop-first product checklists to match the current `0.15.x_beta` implementation state and moved owner-dependent decisions into deferred discussion sections.
- Updated runtime version, service worker cache keys, Windows packaging metadata, and installer spec to `0.15.4_beta`.

## Verified

- `node --check static/js/auth.js`
- `node --check static/js/auth_i18n.js`
- `node --check static/js/schedule.js`
- `.venv\Scripts\python.exe -m unittest discover -s tests`
- Cloud Run smoke checks after deployment.

# 0.15.3_beta - 2026-04-30

## Fixed

- Added RU/HE translations and a top language switcher to the authorization page without exposing raw `auth_*` keys.
- Hidden schedule coverage rows and coverage display controls in the hosted employee web interface while preserving desktop coverage tools.
- Repaired employee portal account linking so accepted employee members are automatically linked back to employee records.
- Added ID-card login fallback for legacy unlinked employee members when the employee record can be identified safely.
- Updated service worker cache keys and Windows packaging metadata to `0.15.3_beta`.

# 0.15.2_beta - 2026-04-30

## Changed

- Added explicit Email / ID card login mode buttons on the authorization dialog while preserving the existing login API shape for compatibility.
- Allowed employee login by matching the entered ID card number to the linked employee record.
- Scoped employee schedule access so employee accounts receive only their own schedule entries, assignments, and assigned positions.
- Made the employee schedule page preselect the primary assigned position and auto-load it on open.
- Updated Windows packaging metadata, service worker cache keys, and installer output to `0.15.2_beta`.

# 0.15.1_beta - 2026-04-29

## Changed

- Started the desktop-cloud-sync line: the installed app no longer exposes a user-facing Local/Cloud workspace switch.
- Desktop login now authenticates against the cloud, imports the selected organization into local SQLite, and opens a local desktop session.
- Added local desktop sync metadata and a `desktop_sync_outbox` table as the foundation for non-blocking background uploads.
- Kept employee portal pages cloud-hosted and separate from the installed scheduling workspace.

# 0.14.17_beta - 2026-04-29

## Added

- Added PostgreSQL connection adapter for Cloud SQL runtime while keeping SQLite as the desktop runtime.
- Switched Cloud Run deployment config from ephemeral SQLite to Cloud SQL PostgreSQL with Secret Manager-backed credentials.
- Updated PostgreSQL baseline schema to match the current application compatibility layer.
- Disabled SQLite file backup/restore endpoints for PostgreSQL runtime in favor of Cloud SQL managed backups.
- Deployed and verified Cloud Run `0.14.17_beta` against Cloud SQL PostgreSQL with create/list/delete API smoke coverage.
- Fixed organization cloud-import SQL so the full legacy SQLite scheduling bundle can import into PostgreSQL.
- Fixed Settings directory embeds so owner/admin/scheduler access can load Positions, Shift templates, Assignments, and Coverage requirements inside the Settings page.
- Mapped PostgreSQL restrict/foreign-key violations to the existing validation path so deleting an in-use shift template returns a clear 400 error instead of a server error.
- Localized the in-use shift template deletion message in the Directories UI.
- Forced desktop/WebView pages on localhost to use the local SQLite API even if a previous Cloud beta API selection was saved.

# 0.14.16_beta - 2026-04-29

## Fixed

- Support dashboard now reads the local desktop API directly, so Cloud beta portal mode cannot redirect `/support` diagnostics to cloud where developer mode is disabled.

# 0.14.15_beta - 2026-04-29

## Added

- Added private monetization/licensing decisions to ignored local notes.
- Added developer/support mode feature flag with a read-only `/support` dashboard.
- Added `/api/support/accounts` for owner/admin diagnostics when `SCHEDULE_APP_DEVELOPER_MODE=1`.

# 0.14.14_beta - 2026-04-29

## Fixed

- Added a temporary cloud API fallback from `https://portal.shiftcare.co.il` to `https://schedule-app-beta.web.app` while DNS delegation is still propagating.
- Improved the login page error shown when Cloud beta portal is unreachable from the desktop app.
- Bumped frontend cache markers and Windows packaging metadata to `0.14.14_beta`.

# 0.14.13_beta - 2026-04-29

## Fixed

- Employee invitation URLs now require an explicit organization cloud-link before using the public portal domain.
- Added owner/admin cloud unlink support for beta testing.
- Completed the desktop-first checklist items before the Licensing section.
- Updated Windows packaging metadata to `0.14.13_beta`.
- Removed the bundled development SQLite database from the Windows package so fresh installs can create the first local owner offline.

## Verified

- `python -m unittest` - 64 tests passed.
- `tools/build_windows_installer.ps1` built `dist\installer\ShiftCare_Setup_0.14.13-beta.exe`.
- Packaged exe smoke confirmed a clean local data directory reports `bootstrap_available=true` and can create the first owner.

# 0.14.12_beta - 2026-04-29

## Fixed

- Reworded the Organization page so employee portal and Cloud connection are explicitly optional beta add-ons.
- Local workspaces no longer display a fake employee portal URL when no public portal URL is configured.
- Invitation UI fallback no longer fabricates a same-origin public invitation link without a configured portal base URL.

## Verified

- `python -m unittest` - 62 tests passed.

# 0.14.11_beta - 2026-04-29

## Fixed

- Restored desktop-first login behavior: local/same-origin workspace is the default and Cloud beta portal is explicit opt-in.
- Reworded login connection UI around offline desktop scheduling and optional cloud portal/migration.
- Added `DESKTOP_FIRST_PRODUCT_PLAN.md` to track the product direction, licensing, offline use, and optional cloud portal work.

## Verified

- `python -m unittest` - 62 tests passed.

# 0.14.10_beta - 2026-04-29

## Fixed

- Kept the Firebase Hosting beta URL usable while `portal.shiftcare.co.il` DNS is still propagating.
- Hosted Cloud origins now use same-origin API calls instead of forcing the not-yet-live portal domain.

## Verified

- `python -m unittest` - 62 tests passed.
- `https://schedule-app-beta.web.app/api/client-config` returns portal-facing employee links.

# 0.14.9_beta - 2026-04-29

## Changed

- Shifted login toward a cloud-first product model.
- Cloud workspace is selected by default when no explicit API mode was chosen.
- Local mode is now grouped under "Local recovery and migration" instead of being shown as a primary equal mode.
- Added a persistent API mode preference for local recovery use.

## Verified

- `python -m unittest` - 62 tests passed.
- Browser check confirmed Cloud is default, Local is hidden until the recovery section is expanded, and no console errors were reported.

# 0.14.8_beta - 2026-04-29

## Added

- Added a cloud-link status API for organization owners, admins, schedulers, and managers.
- Added a cloud-link summary on the Organization page.
- Added localized labels for linked Cloud API, cloud organization, and linked timestamp.
- Added regression coverage for saving and reading cloud-link metadata.

## Verified

- `python -m unittest` - 62 tests passed.
- Browser check confirmed the Organization page shows the cloud-link summary without console errors.

# 0.14.7_beta - 2026-04-29

## Added

- Added owner/admin organization export bundles for uploading local setup data to the Cloud beta API.
- Added cloud organization import with replace-existing behavior and an automatic safety backup before import.
- Added local cloud-link persistence for the selected cloud API URL and cloud organization identity.
- Added a Cloud connection panel on the Organization page.
- Added regression coverage for local organization export/import round trips.

## Notes

- This is the first migration/linking step, not full two-way synchronization yet.

## 0.14.6_beta - 2026-04-29

### What Changed

- Added `/api/auth/status` so the login screen can detect whether the selected backend allows first-owner creation.
- Added a login-screen warning when Cloud beta API is selected and already has an owner, which was easy to confuse with the local installed database.
- Added regression coverage for auth bootstrap availability reporting.

### Release Artifact

- `dist\installer\ShiftCare_Setup_0.14.6-beta.exe`

## 0.14.5_beta - 2026-04-29

### What Changed

- Added `PUBLIC_APP_BASE_URL` so deployed builds can expose a stable employee-facing web address.
- Added employee portal URL metadata to `/api/client-config`.
- Returned ready-to-copy public invitation links from invitation creation and regeneration APIs.
- Updated the organization page to show the employee portal address and copy it from the UI.
- Kept local development fallback behavior so local-only invitation links still use the current local origin when no public URL is configured.

### Release Artifact

- `dist\installer\ShiftCare_Setup_0.14.5-beta.exe`

## 0.14.4_beta - 2026-04-29

### What Changed

- Rebranded the visible desktop and web shell from Schedule App to ShiftCare.
- Updated the application title, login screen, side navigation headers, manifests, localized UI strings, and Windows version metadata.
- Renamed the Windows build output to `ShiftCare_0.14.4_beta` and the installer asset to `ShiftCare_Setup_0.14.4-beta.exe`.
- Kept the legacy local data directory for existing beta users so local databases and logs are not lost during the brand transition.
- Updated the in-app update checker to accept both old `ScheduleApp_Setup_...` and new `ShiftCare_Setup_...` installer assets.

### Release Artifact

- `dist\installer\ShiftCare_Setup_0.14.4-beta.exe`

## 0.14.3_beta - 2026-04-29

### What Changed

- Added a login-screen API mode switch for Local API and Cloud beta API.
- Added a global frontend API resolver so existing `/api/...` calls can route to the selected backend.
- Added CORS support for local desktop/browser shells calling the Cloud Run API.
- Added a richer status indicator showing online/offline state plus Local API or Cloud API readiness.
- Extracted core authorization database helpers into `auth_repository.py` as a first step toward a database adapter layer.
- Kept Cloud Run explicitly in smoke mode; Cloud SQL/PostgreSQL production traffic is still blocked until the SQLite query layer is migrated.

### Release Artifact

- `dist\installer\ScheduleApp_Setup_0.14.3-beta.exe`

## 0.14.2_beta - 2026-04-29

### What Changed

- Bumped runtime, service worker, Windows packaging, installer, and Android beta metadata to `0.14.2_beta`.
- Allowed `employee` users to view the schedule while keeping schedule editing blocked for non-scheduler roles.
- Added local per-user schedule card display mode and local read-only coverage display preferences.
- Added backend permission checks for employee day status writes so non-scheduler roles cannot edit schedule status data through direct API calls.
- Added backend health endpoints: `/api/health/live` and `/api/health/ready`.
- Added runtime configuration validation for deployed environments and unsupported database engines.
- Added `Dockerfile`, `.dockerignore`, `requirements-cloud.txt`, and `cloudbuild.yaml` for a Cloud Run smoke backend deployment.
- Updated Google Cloud setup documentation to explicitly separate current Cloud Run smoke readiness from the future Cloud SQL/PostgreSQL production target.

### Verification

- `.\.venv\Scripts\python.exe -m py_compile app_config.py database.py main.py`
- `.\.venv\Scripts\python.exe -m unittest discover -s tests`
- Local health checks:
  - `GET /api/health/live`
  - `GET /api/health/ready`
- Browser verification for `employee` schedule access, read-only schedule controls, and compact card display mode.
- Built Windows installer asset:
  - `dist\installer\ScheduleApp_Setup_0.14.2-beta.exe`

### Current Cloud Limitation

- Cloud Run smoke deployment can start the backend with ephemeral SQLite.
- Production Cloud SQL/PostgreSQL is not enabled yet because the current data layer is still SQLite-specific.

## 0.14.1_beta - 2026-04-28

### Release Focus

Start the `0.14.x_beta` line with the first organization-based authorization foundation while carrying forward the latest beta UI, export, and packaging work.

### What Changed

- Added the initial authorization schema: organizations, users, organization memberships, invitations, auth sessions, and auth audit events.
- Added password reset and email verification beta token flows.
- Added role-aware weekly preference access so employees can manage only their linked employee record after authorization is initialized.
- Added `.schedulebackup` backup packages with metadata for app version, schema version, organization ID, created date, and creator ID.
- Added local schema metadata and migration history for `0.13.x` to `0.14.x` upgrades.
- Added stable public IDs for organization-owned data to prepare future cloud synchronization.
- Added account/profile editing, password change, organization selection, and owner/admin backup/restore controls.
- Added online/offline status indicator across app pages.
- Added `AUTHORIZATION_0.14_DECISIONS.md` with product scope, onboarding flows, roles, cloud ownership, cache/backup policy, compliance drafts, and migration strategy.
- Added organization scoping fields to the main scheduling tables as preparation for future cloud sync.
- Added backend auth endpoints for first-owner bootstrap, login, logout, current user lookup, invitation creation, invitation acceptance, organization members, and organization invitations.
- Added `/login`, `/organization`, and `/accept-invitation` screens for the desktop-hosted web UI.
- Added local session token storage in the UI and a shared frontend auth client for authenticated API calls.
- Added organization member and invitation management UI for owner/admin workflows.
- Added owner/admin organization actions to remove member access and revoke pending invitation links.
- Added employee selection to organization invitations so employee accounts are linked to existing employee records.
- Added Google Cloud `0.14.x_beta` setup notes and `.env.example` while keeping real secrets out of git.
- Updated the release metadata, Windows packaging metadata, service worker cache version, and Android beta version name to `0.14.1_beta`.
- Added Word `.docx` export endpoints for the selected schedule and all schedules.
- Added Word export buttons to the schedule output toolbar.
- Reused the existing Excel export labels and schedule cell payload logic for English, Russian, and Hebrew output.
- Reworked Word exports to render as visible fixed-layout tables with borders, column widths, padding, and repeated header rows.
- Reworked mobile sidebar behavior so narrow screens open with a compact app header instead of a full navigation panel, while keeping the toggle available.
- Aligned duplicated sidebar state logic across setup pages so schedule, employees, positions, assignments, shift templates, weekly preferences, and settings behave consistently on mobile.
- Simplified the schedule toolbar into three modal action groups and removed the duplicated empty schedule workspace panel above the table.
- Hardened shared modal sizing so app modals stay within the viewport and scroll internally when content is tall.
- Replaced native select dropdown interactions with a shared modal-select control across pages while keeping the underlying form selects and change events intact.
- Reworked the Employees page so the employee form opens in a modal for add and edit actions, leaving the page focused on the employee table.
- Fixed employee table action labels so Edit/Delete render through the shared translation keys.
- Expanded the user guide with a detailed end-to-end workflow covering setup order, employees, positions, shift templates, assignments, coverage requirements, weekly preferences, generation, manual edits, Excel/Word exports, backups, and troubleshooting.
- Added regression coverage for recovery backups on schedule clear actions.
- Added regression coverage for the consecutive split-day generation limit and isolated generation report tests from shared database state.

### Verification

- `.\.venv\Scripts\python.exe -m unittest discover -s tests`
- Regression test for removing organization members, revoking their active sessions, and revoking pending invitations.
- FastAPI smoke test for `/login`, `/organization`, and `/accept-invitation`.
- `.\.venv\Scripts\python.exe -m py_compile main.py excel_export.py word_export.py`
- `.\.venv\Scripts\python.exe -m unittest discover tests`
- FastAPI smoke test for `/`, `/schedule`, `/employees`, `/positions`, `/employee-positions`, `/shift-templates`, `/weekly-preferences`, `/coverage-requirements`, `/settings`, `/docs`, and `/guide`.
- Word export endpoint checks: valid selected export, valid all-schedules export with fallback language, missing `position_id` validation, and missing position `404`.
- Rendered a generated Word export through the documents renderer and visually confirmed the schedule and coordinator summary appear as bordered tables.
- Verified mobile and desktop UI screenshots for schedule, employees, and settings, including Hebrew RTL mobile rendering.
- Verified updated schedule toolbar screenshots on desktop and narrow mobile layouts.
- Verified native browser dialog calls are absent and checked modal-select trigger rendering on schedule, employees, and settings.
- Verified the Employees page desktop and mobile layouts after moving the form into a modal.
- Verified the expanded guide page on desktop and narrow mobile layouts and checked that all guide translation keys are present.
- Verified backup, restore, delete-impact, clear-week preview, and clear-week recovery backup regression tests.
- Verified generation scenarios for enough staff, shortages, night shifts, split-day limits, weekend restrictions, manual edits after generation, and structured generation reports.
- Verified the PyInstaller package build and generated installer:
  - `dist\ScheduleApp_0.14.1_beta\ScheduleApp_0.14.1_beta.exe`
  - `dist\installer\ScheduleApp_Setup_0.14.1-beta.exe`
- Smoke-tested the packaged `.exe` on port `8014` and confirmed `/`, `/login`, `/organization`, `/accept-invitation`, and `/settings` return `200`.

### UX Review Notes

- `critical`: no open critical runtime or data-loss issue found in the verified core workflow.
- `important`: schedule and employee screens were structurally simplified with modal action flows; remaining setup screens use the shared modal/select behavior and should be candidates for deeper form consolidation in a later UI pass.
- `nice-to-have`: broaden screenshot coverage for every secondary setup page before a public visual release, especially with long Hebrew/Russian labels and dense real data.

### Known Test Gaps Before Shipping

- No blocking test gap remains for the local beta verification build.
- Full public-release validation still needs the external release step: publish/tag the installer in the release channel if this build is shipped outside the local workspace.

## 0.13.8_beta - 2026-04-26

### Release Focus

Publish a test update build through the public release channel.

### What Changed

- Bumped runtime and packaging metadata to `0.13.8_beta`.
- Prepared `ScheduleApp_Setup_0.13.8-beta.exe` as a public release asset for validating in-app updates from `0.13.7_beta`.

### User Impact

- Installed `0.13.7_beta` builds can detect this release as a newer version through Settings > About > Updates.

### Technical Impact

- This release is intended to validate the public release-only update feed.

## 0.13.7_beta - 2026-04-26

### Release Focus

Move desktop update delivery to a public release-only GitHub repository.

### What Changed

- Pointed in-app update checks at `LittleDespairs/Schedule_app_releases` so the main source repository can stay private.
- Updated runtime, service worker, Android metadata, PyInstaller, installer, and version-info references to `0.13.7_beta`.
- Prepared the Windows installer asset name for public release distribution as `ScheduleApp_Setup_0.13.7-beta.exe`.

### User Impact

- Installed apps can check the public release repository for updates without needing GitHub authentication.

### Technical Impact

- Source code remains in the private `Schedule_app` repository.
- Release installers are published from the public `Schedule_app_releases` repository.

## 0.13.6_beta - 2026-04-26

### Release Focus

Add in-app update checks and installation through GitHub Releases.

### What Changed

- Added GitHub Releases update discovery for Windows installer assets named `ScheduleApp_Setup_<version>.exe`.
- Added Settings > About update controls to check for updates and start installation from inside the app.
- Added an update install endpoint that downloads the selected release asset, launches the installer, and closes the desktop app after the installer starts.
- Added version comparison and release asset validation so only newer Schedule App installers from GitHub Releases can be installed.
- Updated runtime, service worker, Android metadata, PyInstaller, installer, and version-info references to `0.13.6_beta`.

### User Impact

- Users can check for a new build from inside the desktop app instead of manually visiting GitHub.
- A newer GitHub release can be installed by starting the installer directly from Settings.

### Technical Impact

- Regression coverage now verifies update detection for newer installer assets and ignores non-installer release assets.
- The generated installer for this build is `ScheduleApp_Setup_0.13.6-beta.exe`.

## 0.13.5_beta - 2026-04-26

### Release Focus

Restore the Windows desktop distribution path and add a product-style installer.

### What Changed

- Reworked the desktop launcher to open the app in a native `pywebview` window instead of a browser tab.
- Added graceful localhost port selection and clean backend shutdown when the desktop window closes.
- Added a generated Windows `.ico` asset for the desktop window, EXE, installer, and shortcuts.
- Updated PyInstaller packaging to build `ScheduleApp_0.13.5_beta` with desktop window dependencies.
- Added an Inno Setup installer that installs to Program Files, creates Start Menu and Desktop shortcuts, registers uninstall, and offers post-install launch.
- Added a one-command installer build script.
- Moved installed runtime data, logs, backups, and WebView profile storage to `%LOCALAPPDATA%\Schedule App` so standard users can run the installed app.

### User Impact

- The app now launches like a normal Windows desktop product.
- Installed users get a desktop icon, Start Menu entry, and normal Windows uninstall flow.

### Technical Impact

- Windows installer output is produced under `dist\installer`.
- Inno Setup 6 is the installer toolchain; the build helper can install it through `winget` when available.
- Regression coverage verifies that frozen Windows builds do not write the database into the installation directory.

## 0.13.4_beta - 2026-04-25

### Release Focus

Stabilize Excel export formatting, improve settings navigation, and finish the visual customization reset flow.

### What Changed

- Reworked Excel export so same-day multi-shift entries render as separate worksheet rows inside one employee block.
- Added vertical merging for single-shift days inside multi-row employee blocks so ordinary cells remain visually centered and readable.
- Added a visible outline around each employee schedule block in exported Excel files.
- Highlighted other-position shifts with row-level fill while keeping text black and avoiding rich text that caused Excel repair prompts.
- Added a reset endpoint and Settings action to restore both schedule card colors and position/export colors to defaults.
- Merged the previous Settings `General` and `Schedule` sections into one `Appearance` section with language, version context, coverage display, and color controls.
- Updated runtime version references, asset cache-busting strings, service worker cache name, Android version name, and PyInstaller build references to `0.13.4_beta`.

### User Impact

- Excel exports open without repair prompts and are easier to scan when employees have shifts in multiple positions.
- Employees with split/multi-shift days are visually separated from neighboring employees in exported workbooks.
- Users can reset visual colors back to the default app palette from Settings.
- Settings navigation is simpler because visual and language options now live in one section.

### Technical Impact

- Excel export no longer relies on rich text fragments for partial formatting.
- Regression coverage now verifies Excel formatting for other-position rows, merged single-shift cells, employee block borders, and color reset behavior.
- Version metadata is aligned across backend, templates, static assets, PWA cache, Android metadata, and packaging files.

## 0.13.3_beta - 2026-04-25

### Release Focus

Ship the first broad frontend modernization pass for the schedule workspace and prepare the app for tablet/PWA testing.

### What Changed

- Reworked the schedule toolbar into clearer action groups: context loading, generation, output, and dangerous actions.
- Added a shift legend and schedule status strip with week, position, staff, shift count, coverage mode, and coverage gaps.
- Refined the shared visual system with calmer colors, tighter radii, clearer focus states, disabled states, and a destructive button style.
- Improved schedule coverage-row rendering and compactness from the previous UI pass.
- Added PWA/tablet assets and references, including manifest, service worker, app icon, and tablet installation documentation.
- Updated runtime version references, asset cache-busting strings, and build references to `0.13.3_beta`.

### User Impact

- The schedule page is easier to scan and its key actions are grouped by intent.
- Dangerous actions are visually separated from routine generation/export actions.
- Tablet/PWA testing has a clearer baseline.

### Technical Impact

- The frontend now has a cleaner shared design-token baseline for the next UI customization work.
- The beta build metadata is aligned again across backend, templates, static assets, PWA cache keys, and packaging files.

## 0.13.2_beta - 2026-04-25

### Release Focus

Fix a rare generator and post-optimization fatigue violation where a morning shift could be placed immediately after a night shift.

### What Changed

- Blocked morning assignments when the previous night shift exists only in staged generation entries.
- Blocked night assignments when the same employee already has a morning shift on the following day.
- Added regression tests for both directions of the night-to-morning rule.
- Updated runtime version references, asset cache-busting strings, and build references to `0.13.2_beta`.

### User Impact

- Auto-generation should no longer create an invalid night-to-next-morning sequence for the same employee.

### Technical Impact

- Eligibility checks now account for both persisted schedule entries and staged generator entries when enforcing the night-to-morning rule.

## 0.13.1_beta - 2026-04-24

### Release Focus

Start the next beta line with a clean planning baseline and remove active references to the previous beta stage from runtime and packaging files.

### What Changed

- Set the active app version line to `0.13.1_beta`.
- Updated runtime version references, asset cache-busting strings, and build references to `0.13.1_beta`.
- Renamed the PyInstaller spec file to `ScheduleApp_0.13.1_beta.spec`.
- Moved completed `0.12.x_beta` planning and release documents into `docs/archive/beta-0.12`.
- Kept `BETA_CHANGELOG.md` at the project root as the historical source for previous beta builds.
- Removed the stale local `__pycache__` artifact from the project root.

### User Impact

- The visible app version now starts the `0.13.x_beta` line.
- Previous beta-stage planning files no longer clutter the active project root.

### Technical Impact

- Backend, templates, static asset cache keys, build docs, and packaging metadata now point to the same active beta version.
- Completed `0.12.x_beta` documentation remains available for reference in the archive folder.

## 0.12.6_beta - 2026-04-24

### Release Focus

Compact the schedule cell layout, make cross-position shifts easier to scan, and cut vertical bloat in the planning grid.

### What Changed

- Moved other-position shifts into the same in-cell card flow instead of rendering them as a separate block below.
- Restyled all shift cards to a shared compact shape with clearer category colors and a narrow accent strip.
- Reduced card typography and spacing so busy schedule rows stay denser and easier to scan.
- Moved the shift delete action out of the card content flow into a side control to save vertical space.
- Updated runtime version references, asset cache-busting strings, and build references to `0.12.6_beta`.

### User Impact

- Employees with multiple same-day position assignments are now visible without stretching the table rows as much.
- Shift types are easier to distinguish at a glance because the card colors no longer look nearly identical.
- Dense weeks should remain more manageable on screen because each schedule cell uses less height.

### Technical Impact

- Schedule cell rendering now merges current-position and foreign-position entries into one card list.
- Shift card styling is aligned across ordinary, muted, and actionable states with less layout overhead.
- Version metadata is aligned again between backend, frontend, templates, and packaging files.

## 0.12.5_beta - 2026-04-23

### Release Focus

Improve generator decisions under staffing pressure, refine schedule coverage behavior, and align the visible app version across the interface.

### What Changed

- Added support for `morning + night` as a separate allowed same-day combination without folding it into split-shift logic.
- Improved projected balancing for night assignments so night-capable employees receive a more even weekly distribution.
- Changed interval candidate selection so missing total headcount is prioritized before gender-specific balancing when a slot is understaffed.
- Added extra anti-repetition balancing so the generator is less likely to keep assigning the same shift category to one employee without a strong reason.
- Fixed coverage counters so `sick` day status removes an employee from displayed coverage totals the same way `no_show` already did.
- Extended the coverage-by-category mode so the men counter is always shown.
- Added the same footer used on the dashboard and guide to the rest of the main application pages.
- Updated runtime version references, asset cache-busting strings, and build references to `0.12.5_beta`.

### User Impact

- Understaffed slots now bias toward getting enough people on shift before fine-tuning gender composition.
- Employees should see fewer repetitive same-type assignments in ordinary weeks.
- Coverage numbers now react correctly when a person is marked sick.
- The app now presents one consistent footer and one consistent visible version across the interface.

### Technical Impact

- Candidate ordering for interval and legacy generation uses stronger projected balancing signals.
- Regression coverage was expanded around shortage prioritization and same-category distribution.
- Version metadata is aligned again between backend, frontend, templates, and packaging files.

## 0.12.1_beta - 2026-04-23

### Release Focus

Establish the beta baseline and remove alpha-specific naming and leftover files.

### What Changed

- Switched the project version from `0.11.3_alpha` to `0.12.1_beta`.
- Renamed the PyInstaller spec file to `ScheduleApp_0.12.1_beta.spec`.
- Updated runtime version references in the app, templates, and static assets.
- Removed obsolete root-level files and stale alpha cleanup artifacts.
- Verified clean database initialization and packaged database copy behavior.

### User Impact

- The app now consistently identifies itself as a beta build.
- Build artifacts and packaged output use the same beta naming as the running app.
- The project root is cleaner and easier to maintain.

### Technical Impact

- Version drift between the app, templates, and packaging config was removed.
- The workspace now has a cleaner baseline for the next beta iterations.

### Notes

- This build establishes the beta baseline.
- Packaging verification was continued in later beta stages.

## 0.12.2_beta - 2026-04-23

### Release Focus

Strengthen regression protection so beta changes can land without breaking core workflows.

### What Changed

- Expanded backend regression coverage beyond generation-report-only tests.
- Added regression tests for:
  - employee CRUD,
  - position CRUD,
  - shift template CRUD,
  - weekly preference upsert/delete,
  - schedule status updates,
  - clear-week operations,
  - app settings persistence,
  - generation-weight persistence.
- Added a two-position end-to-end weekly auto-generation test.
- Added edge-case coverage for weekend restrictions, staff shortage, and `day_off` synchronization.

### User Impact

- Core scheduling operations are less likely to regress between beta builds.
- Manual fixes and generation-related flows now have better safety coverage.

### Technical Impact

- The backend moved from narrow test coverage to practical workflow coverage.
- The project gained a stable test bootstrap for database-backed regression runs.

### Notes

- The regression suite reached `18` passing tests at this stage.

## 0.12.3_beta - 2026-04-23

### Release Focus

Improve the main scheduling surface so generation output is easier to understand and fix manually.

### What Changed

- Added a dedicated generation summary panel on the schedule screen.
- Localized generation summaries and related notifications across supported languages.
- Reduced routine success-message noise for common schedule edits.
- Highlighted dates with generation issues directly in the schedule header and coverage row.
- Improved sync behavior for `day_off` after manual shift add/delete operations.
- Added clearer schedule empty states, next-step hints, and action gating.
- Improved weekly table scrolling and layout behavior for mobile and RTL usage.

### User Impact

- Generation results are no longer buried in a single long message.
- It is easier to see which exact days need manual attention after generation.
- The main weekly workspace behaves more predictably on smaller screens and RTL layouts.
- The screen gives better guidance when setup is incomplete.

### Technical Impact

- The schedule page now has structured summary rendering instead of relying on ad hoc message output.
- UI state handling for generation, reloads, and localized rendering became more explicit.

### Notes

- This build concentrated on the schedule screen as the main work surface.
- Remaining deeper safety and packaging hardening continued in the next stage.

## 0.12.4_beta - 2026-04-23

### Release Focus

Add data-safety features, cleanup guarantees, stronger destructive confirmations, and final beta hardening.

### What Changed

- Added delete-impact preview endpoints for:
  - employees,
  - positions,
  - assignments,
  - shift templates.
- Added a clear-week preview endpoint with affected-record counts.
- Updated destructive confirmations to show related-record impact before deletion.
- Added a settings-level backup/restore flow for the database.
- Added automatic recovery backups before destructive deletes and clear-week actions.
- Added stricter validation for:
  - conflicting assignment flags,
  - invalid non-overnight time windows.
- Added more SQLite indexes for assignment lookup, weekly preferences, and day statuses.
- Added regression coverage for:
  - backup/restore,
  - cascade cleanup,
  - delete-impact previews,
  - export summary content,
  - `only_night` preference edge cases,
  - packaged frozen-path resolution.
- Moved Excel export-building logic out of `main.py` into `excel_export.py`.
- Added a coordinator summary worksheet to Excel export.
- Added shared empty-state panels and prerequisite-aware feedback on management screens.
- Disabled assignment and coverage forms until required setup data exists.
- Standardized `Preferences` and `Assignments` terminology across UI and guide content.
- Added recovery-backup details to destructive-action success feedback.
- Built the packaged Windows app with PyInstaller and smoke-tested the generated `.exe`.

### User Impact

- Destructive actions are safer and easier to understand before confirming them.
- Recovery from accidental deletes or cleanup actions is now practical through backups.
- Exported Excel files provide a clearer high-level summary for coordination work.
- Admin screens now explain what is missing instead of just showing empty tables.
- Terminology across the app is more consistent and easier to follow.

### Technical Impact

- Data integrity and safety guarantees are stronger across entity deletion flows.
- The main application module is less overloaded after export logic extraction.
- Beta coverage now includes both runtime and packaged-mode verification.

### Notes

- The backend regression suite reached `27` passing tests.
- The packaged build stores bundled templates, static assets, and `schedule_app.db` under `_internal`.
- The generated Windows `.exe` served `/schedule` with `200` during smoke verification.
