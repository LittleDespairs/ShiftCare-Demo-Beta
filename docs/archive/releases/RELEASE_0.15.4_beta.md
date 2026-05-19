# ShiftCare 0.15.4_beta

## Changed

- Restyled the hosted employee portal login page to match the current ShiftCare interface.
- Employee web schedule view now shows coworkers in the same selected/primary position instead of only the logged-in employee's own shifts.
- Kept employee schedule access restricted to positions assigned to that employee.
- Synchronized the active desktop/cloud sync and desktop-first product checklists with the current implementation state.
- Moved remaining licensing, conflict, and production-hardening questions into deferred owner-decision sections.
- Updated runtime, service worker, PyInstaller, and installer metadata to `0.15.4_beta`.

## Verified

- `node --check static/js/auth.js`
- `node --check static/js/auth_i18n.js`
- `node --check static/js/schedule.js`
- `.venv\Scripts\python.exe -m unittest discover -s tests`
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.4-beta.exe`
- Cloud deployment smoke checks for `/api/auth/status` and updated static assets.

## Deferred Owner Decisions

- Final license payload and signature format.
- Offline activation file format and support workflow.
- Whether production sync should support simultaneous multi-admin editing.
- Final SSL/custom-domain rollout for `portal.shiftcare.co.il`.
