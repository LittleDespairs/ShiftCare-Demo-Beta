# ShiftCare 0.14.5 Beta

This beta makes employee-facing access usable from a deployed Cloud Run address instead of local desktop URLs.

## Highlights

- Added `PUBLIC_APP_BASE_URL` for the public ShiftCare employee portal address.
- Added `employee_portal_url` and invitation URL metadata to `/api/client-config`.
- Invitation creation and token regeneration now return a ready-to-copy public `invitation_url`.
- The organization page now shows the employee portal address with a copy button.
- Local development still falls back to the current local origin when no public URL is configured.

## Cloud API Status

The current Cloud Run service is still a beta smoke API on SQLite. It is useful for account, invitation, and UI validation, but final production use still requires the Cloud SQL/PostgreSQL data-layer migration.

## Installer

- `ShiftCare_Setup_0.14.5-beta.exe`
