# Schedule App 0.13.7_beta

## Release Focus

Move desktop update delivery to a public release-only GitHub repository.

## What Changed

- Pointed in-app update checks at `LittleDespairs/Schedule_app_releases` so the main source repository can stay private.
- Updated runtime, service worker, Android metadata, PyInstaller, installer, and version-info references to `0.13.7_beta`.
- Prepared the Windows installer asset name for public release distribution as `ScheduleApp_Setup_0.13.7-beta.exe`.

## User Impact

- Installed apps can check the public release repository for updates without needing GitHub authentication.
- The main source repository can remain private.

## Technical Impact

- Release installers are published from the public `Schedule_app_releases` repository.
- The installer asset for this release is `ScheduleApp_Setup_0.13.7-beta.exe`.
