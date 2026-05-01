# ShiftCare 0.15.6_beta

Release date: 2026-05-01

## Fixed

- Organization page now has a top language switcher and complete RU/EN/HE translations for headings, tables, statuses, roles, messages, and empty states.
- Employee portal and invitation links now display as normal full URLs with `Open link` and `Copy link` actions.
- Invitation form labels no longer drift after the hidden role field; the expiry field is labelled correctly.
- Desktop installs now fall back to `https://portal.shiftcare.co.il` for employee portal and invitation URLs.

## Changed

- Added the payment provider and selling-site concept to the private payment/license checklist.
- Runtime, service worker, PyInstaller, installer metadata, and build docs now point to `0.15.6_beta`.

## Verified

- `node --check static/js/organization.js`
- `node --check static/js/auth_i18n.js`
- `node --check static/js/i18n.js`
- `node --check static/js/auth.js`
- `.venv\Scripts\python.exe -m unittest discover -s tests`
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.6-beta.exe`
