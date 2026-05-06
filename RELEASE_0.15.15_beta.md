# ShiftCare 0.15.15 beta

Release date: 2026-05-06

## Release

- Rebuilt the Windows installer from the latest `main` after the weekly-preference sync fix.
- Kept the bundled database in the desktop package so first installs include the packaged full-access license.
- Updated runtime version, service worker cache keys, Windows packaging metadata, and installer spec to `0.15.15_beta`.

## Verification

- Full Python unittest suite passed: 102 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.15-beta.exe`
