# ShiftCare 0.14.8 Beta

This beta improves the cloud-linking flow after the first local-to-cloud upload.

## Highlights

- Added a cloud-link status API for organization owners, admins, schedulers, and managers.
- Added a visible cloud-link summary on the Organization page.
- The Organization page now shows the linked Cloud API, cloud organization ID, and linked timestamp.
- Added localization for the cloud-link status block in English, Russian, and Hebrew.
- Added regression coverage for saving and reading cloud-link metadata.

## Verification

- `python -m unittest` - 62 tests passed.
- Browser check confirmed the Organization page shows the cloud-link summary without console errors.

