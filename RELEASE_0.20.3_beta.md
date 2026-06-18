# ShiftCare 0.20.3 Beta

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
