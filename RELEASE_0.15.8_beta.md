# ShiftCare 0.15.8_beta

Release date: 2026-05-02

## Fixed

- Sidebar navigation now keeps stable item height, icon alignment, and active-state positioning.
- Role-based navigation now uses a consistent order and icon set for desktop and employee portal views.
- Organization page now has the standard sidebar collapse control and translated labels.
- Missing translation keys are now covered so technical IDs do not appear in the UI.
- Mobile layouts no longer create page-level horizontal overflow on Organization, support, and directory pages.

## Changed

- Runtime, service worker, PyInstaller, installer metadata, and build docs now point to `0.15.8_beta`.

## Verified

- `node --check static/js/access_control.js`
- `node --check static/js/organization.js`
- `node --check static/js/i18n.js`
- `node --check static/js/auth_i18n.js`
- `.venv\Scripts\python.exe -m unittest discover -s tests`
- Playwright desktop/mobile layout checks against local pages.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.8-beta.exe`
