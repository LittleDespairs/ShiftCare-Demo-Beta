# Beta Changelog

This file tracks beta builds across the `0.12.x_beta`, `0.13.x_beta`, and `0.14.x_beta` lines.

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
