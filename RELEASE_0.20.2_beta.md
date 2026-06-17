# ShiftCare 0.20.2 Beta

## Release Focus

Employee portal styling and mobile reliability refresh.

## Changed

- Applied the new operations visual style to the employee portal surfaces.
- Reworked mobile weekly preferences into a simpler employee-facing card layout.
- Fixed local/staging employee portal mode so login uses the portal backend login flow, not desktop cloud import.
- Updated service worker cache keys and static asset cache-busters so phones receive the new CSS and JavaScript.
- Hid stale disabled employee accounts from organization member flows and reinvites.
- Updated runtime, service worker cache keys, Android metadata, PyInstaller specs, installer metadata, build docs, and release notes to `0.20.2_beta`.

## Verification

- Automated regression tests passed locally.
- Browser smoke checks passed locally for employee portal login, weekly preferences save, and read-only schedule on mobile viewport.
