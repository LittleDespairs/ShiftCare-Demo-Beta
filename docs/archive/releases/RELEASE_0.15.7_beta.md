# ShiftCare 0.15.7_beta

## Fixed

- Hosted employee portal login now uses a single clean stacked entry block, so the login button no longer overlaps the copy on large screens.
- `portal.shiftcare.co.il` and other `*.shiftcare.co.il` hosts are now treated as hosted cloud origins by the auth client.
- Cloud Build now defaults `PUBLIC_APP_BASE_URL` to `https://portal.shiftcare.co.il`.

## Changed

- Runtime, service worker, PyInstaller, installer metadata, and build docs now point to `0.15.7_beta`.

## Verified

- `node --check static/js/auth_client.js`
- `node --check static/js/auth.js`
- `node --check static/js/auth_i18n.js`
- `.venv\Scripts\python.exe -m unittest discover -s tests`
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.7-beta.exe`
