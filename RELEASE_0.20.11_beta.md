# ShiftCare 0.20.11 Beta

Desktop/cloud synchronization hotfix for employee portal weekly preference requests.

## Fixed

- Desktop cloud pull now imports pending employee weekly preference requests, not only confirmed weekly preferences.
- The administrator request queue now triggers the same cloud pull before reading local SQLite data.
- Cloud SQL startup migration now removes the legacy recurring-preference uniqueness constraint that could keep desktop sync stuck in `failed`.

## Verification

- Confirmed portal cloud export contains the reported test data: two confirmed Raja preferences for week `2026-06-28` and one pending request for `2026-06-30`.
- Added regression coverage for desktop pulling cloud pending requests and keeping imported rows out of the local sync outbox.
- Targeted sync regression tests passed locally.
