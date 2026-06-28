# ShiftCare 0.20.12 Beta

Hotfix for approving employee weekly preference requests in the administrator client.

## Fixed

- Desktop cloud pull now preserves local SQLite IDs for imported weekly preferences and pending approval requests.
- The weekly preferences page now performs one cloud pull per load instead of two, avoiding stale approval button IDs and reducing delay.
- Approve/reject/delete actions for extra weekly preference requests no longer fail with `Preference request not found` after a refresh or background pull.

## Verification

- Added regression coverage for repeated cloud pulls keeping the same pending request ID.
- Full API and schema regression suite passed locally.
