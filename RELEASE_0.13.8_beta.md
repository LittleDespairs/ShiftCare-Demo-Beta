# Schedule App 0.13.8_beta

## Release Focus

Publish a test update build through the public release channel.

## What Changed

- Bumped runtime and packaging metadata to `0.13.8_beta`.
- Prepared `ScheduleApp_Setup_0.13.8-beta.exe` as a public release asset for validating in-app updates from `0.13.7_beta`.

## User Impact

- Installed `0.13.7_beta` builds can detect this release as a newer version through Settings > About > Updates.

## Technical Impact

- This release validates the public release-only update feed hosted in `LittleDespairs/Schedule_app_releases`.
