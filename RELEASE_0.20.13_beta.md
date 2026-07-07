# ShiftCare 0.20.13 Beta

Employee portal release for controlled shift swap requests.

## Added

- Employees can request shift swaps from the schedule.
- Target employees can accept or reject swap requests.
- Administrators review accepted requests before the schedule is changed.
- Administrators can enable or disable new employee shift swap requests from the organization portal and desktop settings.

## Fixed

- Swap validation blocks cross-position swaps.
- Swap validation blocks duplicate same-day shift categories after an exchange.
- Mobile schedule tables keep the logged-in employee at the top.
- Employee portal navigation no longer shows unavailable sections.

## Verification

- Full local regression suite passed: 150 tests, 1 skipped PostgreSQL integration test.
- Portal deployment verified on Cloud Run revision `schedule-app-beta-api-00114-dwt`.
