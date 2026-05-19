# ShiftCare 0.15.13 beta

## Licensing

- Fixed the Windows desktop package so `schedule_app.db` is bundled with the PyInstaller build.
- Fresh installs can now copy the bundled database during first launch, including the packaged full-access license.
- Existing installs that already created a trial runtime database now seed the bundled license without overwriting user data, when the organization public ID matches.

## Verification

- Full Python unittest suite passed: 101 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.13-beta.exe`
