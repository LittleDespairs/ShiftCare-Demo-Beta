# ShiftCare 0.15.3_beta

## Fixed

- Added Russian and Hebrew authorization-page translations with the language selector available on login.
- Fixed raw `auth_*` translation keys appearing in the UI after cache refreshes.
- Removed hosted-web schedule coverage display from employee portal pages while keeping desktop coverage tools intact.
- Automatically repairs active employee members that lost their employee-record link.
- Restored ID-card login for employee accounts after the employee ID card is added to the employee record.

## Verified

- `python -m py_compile main.py`
- `node --check static/js/organization.js`
- `.venv\Scripts\python.exe -m unittest` - 85 tests passed, 1 skipped.
- `tools\build_windows_installer.ps1` built `dist\installer\ShiftCare_Setup_0.15.3-beta.exe`.
