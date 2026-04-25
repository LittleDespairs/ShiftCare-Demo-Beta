# Schedule App 0.13.6_beta

## Release Focus

Add in-app update checks and installation through GitHub Releases.

## What Changed

- Added GitHub Releases update discovery for Windows installer assets named `ScheduleApp_Setup_<version>.exe`.
- Added Settings > About controls to check for updates and start installation from inside the app.
- Added an update install endpoint that downloads the selected release asset, launches the installer, and closes the desktop app after the installer starts.
- Added version comparison and release asset validation so only newer Schedule App installers from GitHub Releases can be installed.
- Updated runtime, service worker, Android metadata, PyInstaller, installer, and version-info references to `0.13.6_beta`.

## User Impact

- Users can check for a new build from inside the desktop app.
- A newer GitHub release can be installed without manually browsing to GitHub.

## Technical Impact

- GitHub Releases are now the update source for desktop builds.
- The installer asset for this release is `ScheduleApp_Setup_0.13.6-beta.exe`.
- Regression coverage verifies newer installer detection and ignores non-installer release assets.
