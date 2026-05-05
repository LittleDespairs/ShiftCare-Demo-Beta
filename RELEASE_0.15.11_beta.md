# ShiftCare 0.15.11 beta

Release date: 2026-05-06

## Permanent preferences

- Added permanent employee preferences for every weekday, split into strict rules and soft preferences.
- Owners and admins can manage permanent preferences from the employee modal.
- Schedule generation now blocks shifts that violate strict permanent rules and applies penalties for soft permanent preferences.

## Data and sync

- Added the `employee_recurring_preferences` table to SQLite and the PostgreSQL baseline.
- Included permanent preferences in organization export/import, backup/restore cleanup, and employee deletion impact reporting.

## Verification

- JavaScript syntax checks passed for changed employee/i18n frontend files.
- Focused Python regression tests passed for API and generation behavior.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.11-beta.exe`
