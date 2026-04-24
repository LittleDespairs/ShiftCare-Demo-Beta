# Beta Checklist

Working checklist for the beta cycle. Version line is now fixed at `0.12.x_beta`.

## Version Policy

- Base beta line: `0.12`
- First beta build: `0.12.1_beta`
- Next builds: `0.12.2_beta`, `0.12.3_beta`, ...
- Do not introduce `0.13.x` or another minor line until beta goals are complete.

## Beta Goals

- Stabilize the current scheduling workflow for real usage.
- Catch regressions in generation, editing, and weekly planning.
- Make packaged desktop builds predictable and easy to verify.
- Close the highest-friction UI and data-safety issues before release candidate work.

## Release Management

- [x] Rename app version metadata from `0.11.3_alpha` to `0.12.1_beta`.
- [x] Rename packaging artifacts and build names to the `0.12.x_beta` format.
- [x] Define one source of truth for the app version so FastAPI title, OpenAPI version, spec file, and build output cannot drift.
- [x] Add a short beta changelog file for each build.

## Beta Entry Blockers

- [x] Smoke-test all main pages: employees, positions, assignments, templates, preferences, requirements, schedule, settings.
- [x] Verify a fresh database start on a clean environment.
- [x] Verify packaged app startup with bundled database creation/copy behavior.
- [x] Verify no critical traceback is shown for invalid user input or empty-state actions.

## Regression Tests

- [x] Expand backend tests beyond `test_generation_reports.py`.
- [x] Add CRUD tests for employees, positions, shift templates, and weekly preferences.
- [x] Add tests for settings persistence and generation weights.
- [x] Add tests for schedule clearing, manual assignment, and `no_show` status flow.
- [x] Add one end-to-end regression scenario for a realistic week with multiple employees and positions.

## Schedule Generation

- [x] Audit generation behavior on edge cases: too few staff, gender shortage, night-only staff, split-day conflicts, weekend restrictions.
- [x] Review scoring weights and defaults against real beta scenarios.
- [x] Improve explainability of generation failures and soft violations in the UI.
- [x] Add a visible post-generation summary: shortages, overloads, hard blockers, soft compromises.
- [x] Check whether manual edits after auto-generation preserve data consistency and day-off sync.

## Data Integrity and Safety

- [x] Review SQLite schema for missing uniqueness rules, indexes, and migration safety.
- [x] Add a backup/restore flow for the local database before risky bulk actions.
- [x] Add stronger confirmation behavior for destructive actions such as clearing a week or deleting core entities.
- [x] Add recovery behavior for destructive actions such as clearing a week or deleting core entities.
- [x] Verify cross-table cleanup when employees, positions, or templates are removed.

## UX and Workflow

- [x] Run a full usability pass on the schedule screen as the main work surface.
- [x] Reduce friction in the most frequent flows: creating staff, assigning positions, setting requirements, generating a week, fixing exceptions.
- [x] Add clearer empty states and success/error feedback on all management screens.
- [x] Review mobile and RTL behavior again after beta fixes land.
- [x] Standardize terminology across UI, API messages, and documentation.

## Import, Export, and Reporting

- [x] Verify Excel export against real schedules and formatting edge cases.
- [x] Add export validation for empty weeks, partially filled weeks, and no-show days.
- [x] Decide whether beta needs import tools for employees or preferences, or whether that is postponed.
- [x] Improve printable/exported summary for coordinator review.

## Packaging and Delivery

- [x] Create a repeatable beta build checklist for Windows packaging.
- [x] Verify that static assets, templates, and DB behavior work in packaged mode.
- [x] Add a simple pre-release verification pass for every new `0.12.x_beta` build.
- [x] Clean up obsolete build naming and legacy alpha references in project files.

## Code Health

- [x] Clean the project from obsolete files and stale artifacts that no longer participate in runtime, tests, or packaging.
- [x] Review and remove likely cleanup candidates: `main copy.py`, legacy prototype `test.py`, stale `__pycache__` directories, and outdated alpha-only helper artifacts.
- [x] Split high-risk or overloaded sections of `main.py` into clearer modules if that reduces beta bug-fix risk.
- [x] Remove dead code, duplicate helpers, and outdated comments that can mislead during beta support.
- [x] Review validation boundaries in Pydantic models and request handlers.
- [x] Add lightweight developer docs for running tests and building the app.

## Beta Feedback Loop

- [x] Define how beta issues are recorded: markdown log, GitHub issues, or in-repo checklist sections.
- [x] Create labels or sections for `bug`, `ux`, `algorithm`, `packaging`, and `release`.
- [x] Track every beta build with date, version, major changes, and known issues.
- [x] Maintain a short list of must-fix items before leaving beta.

## Proposed First Iteration

- [x] `0.12.1_beta`: switch versioning, clean artifact naming, clean obsolete project files, run core smoke pass, remove alpha references.
- [x] `0.12.2_beta`: expand regression tests for CRUD and schedule operations.
- [x] `0.12.3_beta`: polish schedule UX and generation summary/reporting.
- [x] `0.12.4_beta`: packaging hardening and beta verification pass.

## Notes

- This file is intentionally broader than the final must-fix list.
- As beta feedback appears, items should be reordered into `critical`, `important`, and `nice-to-have`.
- Verified in the current workspace: backend tests pass in `.venv`, app imports with `APP_VERSION = 0.12.1_beta`, and core pages return `200` via `TestClient`.
- Additional verification completed: fresh SQLite initialization works in a temp location, packaged-mode database copy logic copies the bundled DB into the runtime directory, and invalid API payloads return `422`.
- Test coverage was expanded with API regression tests for employee CRUD, position CRUD, shift template CRUD, weekly preference upsert/delete, and schedule status/clear-week flows.
- Regression coverage now also includes app-settings persistence, generation-weight persistence, and a two-position end-to-end weekly auto-generation scenario.
- The schedule screen now includes a dedicated post-generation summary panel with run metrics, hard/soft constraint sections, remaining unfilled requirements, and warning details instead of relying only on a single message box.
- The schedule generation summary and related notifications were localized across supported languages, including summary titles, counters, notes, feasibility status labels, and backend-derived reason strings.
- Routine schedule actions were made quieter on success: load, shift edits, and day/shift status changes no longer spam redundant success messages, while errors and important generation outcomes remain visible.
- Dates with generation issues are now highlighted directly in the schedule table header and coverage row, making it easier to jump from summary diagnostics to the exact days that need manual fixes.
- Excel export validation now covers empty weeks plus mixed real-shift, `no_show`, and `day_off` cases through workbook-level assertions.
- Legacy `0.11.3_alpha` asset-version strings and footer version labels were removed from the remaining templates, so runtime templates now consistently point at the beta version line.
- Regression coverage now includes a post-auto-generation manual-delete scenario that restores `day_off` state correctly; the `night-only staff` edge case is still open because that capability is not modeled separately in the current app.
- Destructive actions now load impact previews before confirmation on employees, positions, assignments, shift templates, and clear-week operations, so the user sees related-record counts before deleting.
- Automated regression now covers delete-impact preview endpoints and verifies that `get_base_path()` resolves `sys._MEIPASS` in frozen mode.
- The app now has a working backup/restore flow in settings plus automatic recovery backups before destructive entity deletes and clear-week operations.
- Schema review resulted in additional SQLite indexes for assignment lookup, weekly preferences, and day statuses, while validation review added stricter request-model checks for invalid time windows and conflicting assignment flags.
- Cross-table cleanup is now regression-covered for employee and position cascades, and shift-template deletion remains intentionally restricted when schedule rows still reference it.
- Excel export now includes a coordinator summary sheet, and packaged-mode verification was completed with a real PyInstaller build whose `.exe` answered `/schedule` with `200` while loading bundled templates, static assets, and DB data from `_internal`.
- Beta decision for `0.12`: import tools are postponed; backup/restore is the supported data-safety path for this line.
- Export-building logic was extracted from `main.py` into [excel_export.py](D:\WebStorm_Projects\PetProjects\Schedule_app\excel_export.py), reducing one of the riskiest overloaded surfaces in the main app module.
