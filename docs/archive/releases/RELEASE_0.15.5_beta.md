# ShiftCare 0.15.5_beta

## Added

- Local license runtime for trial, paid license, grace, expiry, and employee-limit enforcement.
- `Settings -> License & Support` with status, last online check, activation code entry, offline license import, and copyable diagnostics.
- Support tooling at `tools\issue_license.py` for generating signed `.shiftcare-license` files and activation codes.
- Regression tests for license import, activation code import, license blocking, developer bypass, and SQLite/PostgreSQL schema parity.

## Changed

- SQLite and PostgreSQL schemas now include license tables and share schema version `17`.
- Schedule generation, manual shift creation, and employee creation now respect local license enforcement.
- Runtime, service worker, PyInstaller, installer metadata, and build docs now point to `0.15.5_beta`.

## Verified

- `node --check static/js/i18n.js`
- `node --check static/js/auth.js`
- `node --check static/js/auth_i18n.js`
- `node --check static/js/schedule.js`
- `.venv\Scripts\python.exe -m unittest discover -s tests`
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.5-beta.exe`

## Deferred Owner Decisions

- Final production signature format: Ed25519 or ECDSA.
- Final prices for 15 / 35 / 75 / custom employee-limit plans.
- First Israeli payment/invoice provider and accounting workflow.
- Full cloud payment backend, webhooks, and automatic recurring billing.
