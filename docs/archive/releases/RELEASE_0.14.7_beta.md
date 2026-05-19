# ShiftCare 0.14.7 Beta

This beta adds the first real bridge between an installed local organization and the Cloud beta API.

## Highlights

- Added organization export bundles for owner/admin users.
- Added cloud organization import with replace-existing behavior and a safety backup before import.
- Added local cloud-link persistence so an installed app can remember which cloud organization it was connected to.
- Added a Cloud connection panel on the Organization page.
- The Cloud connection flow can sign in to an existing cloud owner account or bootstrap the first cloud owner when the cloud API is empty.
- Added regression coverage for local export/import round trips.

## Notes

This is still not full two-way synchronization. It is the migration/linking layer needed before proper cloud-first sync can be implemented.

## Verification

- `python -m unittest` - 62 tests passed.

