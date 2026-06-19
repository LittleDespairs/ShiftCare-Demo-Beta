# Release 0.20.4 Beta

## Focus

Improve schedule generation fidelity and make manual schedule corrections safer for production use.

## Changes

- Improved position assignment priority handling so primary and higher-priority employees are favored more consistently during generation.
- Added multi-request permanent strict and soft preferences in employee cards, matching the weekly preferences workflow.
- Added manual shift time overrides on the schedule page and included those overrides in coverage calculations.
- Preserved manually pre-filled shifts during generation and counted them toward coverage instead of replacing them.
- Stopped single-position generation from filling unrelated empty days with day-off statuses.
- Prevented hidden cloud preference pulls from replacing local preferences immediately before generation, and kept pulled cloud preference rows out of the local sync outbox.
- Updated runtime, service worker cache keys, Android metadata, PyInstaller specs, installer metadata, build docs, and release notes to `0.20.4_beta`.

## Verification

- `.venv\Scripts\python.exe -m unittest tests.test_generation_reports tests.test_api_regressions`

## Windows Installers

- `ShiftCare_Setup_0.20.4-beta.exe`
  - SHA256: `FA82201161DE0B39CCA0DB88CC03BAA97DBC49F88485D8AAFD3D151916C72910`
- `ShiftCare_Demo_Setup_0.20.4-beta.exe`
  - SHA256: `74CC3086AD672C65CBC3E4108AF4BF1C4F6EF5FA7CBD5A162A00F9405E5018E7`
