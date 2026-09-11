# ShiftCare Demo 0.21.1 Beta

A demonstration build for exploring scheduling features. Demo restrictions remain enabled.

**Windows signing:** this beta installer and application are unsigned (`NotSigned`). The in-app updater continues to require a trusted publisher signature and will reject this installer. Automatic installation through the updater is therefore unavailable for this build. No signature checks have been disabled.

## Changes

- Synchronization polls incoming portal requests even without outgoing changes, merges independent edits, and preserves both copies on conflicts. Startup normalization no longer queues unchanged preferences.
- Repeated sign-in and delayed server responses preserve pending preferences, deletions, department access restrictions, and stable record identifiers.
- Organization settings and scheduling constraints are isolated by organization; database migrations upgrade the schema to version 26.
- SQLite backup includes committed WAL data. Restore coordinates open connections and recovers the previous database if migration fails. Portable backups remove sessions and tokens and require sign-in again.
- Multi-position generation handles shared employees before assigning days off. Portal settings handle loading, retry, save, and network errors.
- Updated RU/EN/HE interface, mobile RTL, and PWA caching. The application is organized into a modular `shiftcare` package.

## Before updating

Keep a full recovery backup of the existing database. This version requires the matching 0.21.1 cloud service for synchronization. Matching local/cloud data establish a shared baseline. A legacy installation without a baseline can also accept proven new weekly preferences or requests created after its last successful push when all shared records still match; ambiguous differences require reconciliation. Old synchronization import protocol requests are rejected.

Schema 26 changes organization settings keys. Rolling back requires a matched application and database backup from before migration; switching only the application version is insufficient.

## Verification

- Local Python suite: 223 tests passed with no skips, including real PostgreSQL 16.15 and temporary SQLite databases.
- Twelve Node interface/PWA checks, metadata consistency, and browser RU/EN/HE and narrow RTL checks passed.
- Windows payload inspected: 847 files; all 63 `shiftcare` modules and 48 static/template resources match the final source. No working databases, `.env`, private directories, or backup files are included.
- Installation on a clean Windows machine and a signed updater installation have not been validated.

## Windows installer

`ShiftCare_Demo_Setup_0.21.1-beta.exe` — 31,580,381 bytes.

SHA256: `7f2d856f4df4855413b29fb708c2492e9f3ff715197b4e3e66876d48836fd21b`

Download `SHA256SUMS.txt` alongside the installer to check the downloaded file. The app executable relies on its accompanying runtime directory; the installer is the distributable package.

## Publication status

Published on 2026-09-11 as an explicitly approved unsigned Windows beta for manual distribution. The updater's trusted-signature requirement remains enabled; this release does not enable automatic installation of unsigned files. The Android asset in the standard release is explicitly labeled as a debug tablet build.

The live employee portal at [portal.shiftcare.co.il](https://portal.shiftcare.co.il/login) and [schedule-app-beta.web.app](https://schedule-app-beta.web.app/login) was upgraded to `0.21.1_beta` before the installers were published. Liveness, readiness, and PostgreSQL connectivity checks passed.

[Original tagged source CI](https://github.com/LittleDespairs/ShiftCare-Demo-Beta/actions/runs/34632678203) passed for commit `ac95bf63bd397a9035fa5884b2320b53697e1af1`: Linux Python 3.12 and 3.13, plus Windows. The existing release tag retains the original snapshot; the current `main` branch contains the synchronization correction used by the refreshed Windows installer. The version and asset URLs are unchanged, and the Android debug APK retains its original checksum.
