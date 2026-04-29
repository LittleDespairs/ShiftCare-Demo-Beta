# ShiftCare 0.14.9 Beta

This beta moves the login experience toward the cloud-first product model.

## Highlights

- Cloud workspace is now selected by default on the login screen when no explicit mode was chosen.
- Local mode is no longer presented as an equal primary choice.
- Local access is now grouped under "Local recovery and migration".
- Added a persistent API mode preference so choosing local recovery does not immediately reset back to cloud.
- Updated login-side copy to describe local mode as migration, backup, and emergency access.

## Verification

- `python -m unittest` - 62 tests passed.
- Browser check confirmed Cloud is default, Local is hidden until the recovery section is expanded, and no console errors were reported.

