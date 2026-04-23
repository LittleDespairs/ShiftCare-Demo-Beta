# Alpha Finalization Checklist

This checklist is the working list for finishing the alpha version. Current application version: `0.11.3_alpha`.

## Algorithm

- [x] Separate constraints into `hard` and `soft`.
- [x] Add a pre-generation feasibility check.
- [x] Improve global optimization beyond the current greedy pass.
- [x] Formalize employee balance scoring.
- [x] Return structured reports for unfilled shifts.
- [x] Add fixed test-week fixtures.
- [x] Verify `day_off` as an algorithm-level planning result, not only a UI status.
- [x] Move magic numbers and generation weights into settings.

## Frontend

- [x] Split `schedule.html` into smaller maintainable assets.
- [x] Extract shared layout/sidebar/language/message UI.
- [x] Remove inline `onclick` handlers.
- [x] Centralize message and error handling.
- [x] Replace native `confirm` dialogs with an app modal.
- [x] Systematically escape rendered user/backend data.
  - Done for the main schedule page and CRUD/data-heavy pages.
- [x] Improve the schedule page as the main working screen.
- [x] Complete RTL/mobile visual pass.

## Current Priority

All release-blocking alpha finalization items are complete for `0.11.3_alpha`.

Notes:
- The generator now includes a post-generation balance optimization pass, structured feasibility reports, hard/soft constraint reporting, configurable scoring weights, generated day-off statuses, and fixed regression tests.
- The schedule screen remains a large template, but repeated inline behavior has been extracted into shared helpers and the remaining split is tracked as post-alpha maintainability work rather than a release blocker.
