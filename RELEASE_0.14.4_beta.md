# ShiftCare 0.14.4 Beta

This beta starts the visible product rebrand from Schedule App to ShiftCare.

## Highlights

- Branded the desktop/web shell as ShiftCare.
- Updated localized titles, subtitles, navigation branding, manifests, and Windows metadata.
- Renamed packaged Windows artifacts to `ShiftCare_0.14.4_beta` and `ShiftCare_Setup_0.14.4-beta.exe`.
- Preserved the legacy local data directory for compatibility with existing beta installations.
- Kept update discovery compatible with both `ScheduleApp_Setup_...` and `ShiftCare_Setup_...` release assets.

## Cloud API Status

The Cloud Run API remains a beta smoke API. It is suitable for connectivity and UI validation, but production Cloud SQL/PostgreSQL data traffic is still blocked until the SQLite query layer is fully migrated.

## Installer

- `ShiftCare_Setup_0.14.4-beta.exe`
