# ShiftCare 0.15.10 beta

## Demo polish
- Fixed the organization invite employee selector placeholder translation in Russian and Hebrew.
- Renamed the employee ID-card column in Russian so it no longer looks like a duplicate internal ID column.
- Render empty employee ID-card values as a dash instead of a blank table cell.

## Verification
- JavaScript syntax checks passed for changed frontend files.
- Full Python unittest suite passed: 95 tests, 1 skipped.
- Local UI smoke test covered login state, sidebar navigation, schedule loading, weekly preferences loading/saving, organization, settings, employees, support, and guide pages.
