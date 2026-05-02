# ShiftCare 0.15.9_beta

Release date: 2026-05-02

## Fixed

- Sidebar navigation is clickable again after the 0.15.8 UI polish.
- Access control no longer repeatedly rebuilds sidebar links through the mutation observer.
- Navigation ordering and icons stay stable without replacing link DOM nodes on every observer pass.

## Changed

- Runtime, service worker, PyInstaller, installer metadata, and build docs now point to `0.15.9_beta`.

## Verified

- `node --check static/js/access_control.js`
- Playwright click-through check from the sidebar to `/organization`.
- `.venv\Scripts\python.exe -m unittest discover -s tests`
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.9-beta.exe`
