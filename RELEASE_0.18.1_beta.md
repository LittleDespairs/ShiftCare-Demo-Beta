# ShiftCare 0.18.1 Beta

## Release focus

Restore the `0.17.x` blue interface baseline and force clients to load the corrected CSS through a patch-version cache refresh.

## Changed

- Restored the shared blue `0.17.2_beta` palette, radii, shadows, and schedule table colors in `static/css/style.css` and `static/css/schedule.css`.
- Kept the functional `0.18.0_beta` Home page improvements while making them inherit the restored blue visual system.
- Updated runtime, service worker cache name, static asset query params, Android version metadata, Windows packaging metadata, build docs, and installer script to `0.18.1_beta`.
- Archived the `0.18.0_beta` release notes and PyInstaller spec, then added the active `ShiftCare_0.18.1_beta.spec`.

## Verification

- `static/css/schedule.css` matches `v0.17.2-beta`; `static/css/style.css` differs from `v0.17.2-beta` only by the new Home page classes kept from `0.18.0_beta`.
- Android backend sync tasks passed with JDK 17: `gradlew.bat syncScheduleBackend syncScheduleBackendAssets --no-daemon`.
- Full Python unittest suite passed: 114 tests OK, 1 PostgreSQL integration test skipped locally because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Python root module compile check passed.
- Service worker JavaScript syntax check passed.
- `git diff --check` passed.
- Browser verification passed on `http://127.0.0.1:8026/login`: computed CSS reported `--primary: #2357d6`, `--bg: #f6f8fb`, `--radius-xl: 14px`, `--radius-lg: 12px`, and the service worker contained the new `0.18.1_beta` cache-bust.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.18.1-beta.exe`
- Installer SHA256: `A3F33C5A97264AB9757F0E6C3F792718C86892809DC91718E3AAA9004B20BBB8`

## Release notes

- Installer and GitHub release artifacts were rebuilt for `0.18.1_beta`.
