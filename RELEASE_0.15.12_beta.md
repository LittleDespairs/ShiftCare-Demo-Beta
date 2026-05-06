# ShiftCare 0.15.12 beta

Release date: 2026-05-06

## Weekly preferences

- Fixed desktop generation so pending local weekly preference changes are not overwritten by a cloud pull before the generator reads them.
- Added API validation that rejects weekly preference dates outside the selected week.
- Updated the weekly preferences page so changing the week or employee clears stale loaded rows before saving.
- Saving `no_preference` now clears the stored weekly preference instead of leaving redundant records.

## Data and sync

- Preserved the current cloud organization license import/export updates in this release line.
- Updated runtime version, service worker cache keys, Windows packaging metadata, and installer spec to `0.15.12_beta`.

## Verification

- Full Python unittest suite passed: 100 tests OK, 1 PostgreSQL integration test skipped because `SCHEDULE_APP_POSTGRES_TEST_DSN` is not set.
- Python compile check passed for `main.py`.
- Windows installer build: `dist\installer\ShiftCare_Setup_0.15.12-beta.exe`
