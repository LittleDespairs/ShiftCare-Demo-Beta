# ShiftCare 0.14.6 Beta

This beta makes the login screen clearer when the installed desktop app is pointed at Cloud beta API instead of the local database.

## Highlights

- Added `/api/auth/status` so the login screen can detect if first-owner setup is available on the selected backend.
- Added a clear warning when Cloud beta API is selected and already has an owner.
- Clarified the difference between local installed data and the Cloud beta API on the auth screen.
- Added regression coverage for auth bootstrap availability reporting.

## Cloud API Status

The current Cloud Run service is still a beta smoke API on SQLite. It is useful for account, invitation, and UI validation, but final production use still requires the Cloud SQL/PostgreSQL data-layer migration.

## Installer

- `ShiftCare_Setup_0.14.6-beta.exe`
