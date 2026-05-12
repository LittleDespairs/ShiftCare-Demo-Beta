# Schedule App 0.13.4_beta

## Description

This beta release focuses on stable Excel export formatting and a cleaner Settings experience. The export no longer uses rich text fragments, which removes the Excel repair warning while preserving useful visual highlighting for shifts assigned in other positions.

## Changelog

- Rebuilt Excel export layout for employees with multiple same-day shifts.
- Added separate worksheet rows inside one employee block for multi-shift days.
- Merged single-shift cells vertically inside multi-row employee blocks.
- Added clear outer borders around each employee block in exported workbooks.
- Highlighted other-position shift rows with the position color while keeping text black.
- Added Settings support to reset schedule card colors and position/export colors to defaults.
- Merged Settings `General` and `Schedule` into one `Appearance` section.
- Updated app version references to `0.13.4_beta`.

## Verification

- `python -m py_compile excel_export.py main.py database.py`
- `python -m unittest discover -s tests -v`
- Excel COM smoke check confirmed generated workbooks open without repair.
