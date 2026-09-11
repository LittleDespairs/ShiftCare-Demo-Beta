# ShiftCare Demo — 0.21.1 beta

Public demonstration build and source snapshot of ShiftCare, a desktop application for employee schedules, shifts, positions, and weekly preferences. Demo restrictions remain enabled; this edition is intended for exploring features.

- [Download the Windows Demo installer](https://github.com/LittleDespairs/ShiftCare-Demo-Beta/releases/download/v0.21.1-beta/ShiftCare_Demo_Setup_0.21.1-beta.exe)
- [Release notes and checksums](https://github.com/LittleDespairs/ShiftCare-Demo-Beta/releases/tag/v0.21.1-beta)
- [Standard Windows release](https://github.com/LittleDespairs/Schedule_app_releases/releases/tag/v0.21.1-beta)
- [Download page](https://download.shiftcare.co.il/)

The Windows application and installer are unsigned. The in-app updater requires a trusted publisher signature and will reject this installer. Read the release notes before installing and keep a recovery backup of an existing database.

The 0.21.1 beta update improves concurrent desktop/cloud synchronization, organization isolation, SQLite backup and restore, multi-position generation, and RU/EN/HE portal/PWA behavior. Database schema 26 requires the matching 0.21.1 cloud service for synchronization.

## Source and development

This snapshot was synchronized from source commit `20f91cd63a09bf257e6cc8bf132d005f84a270d6`, preserving this repository's existing history. Working databases, secrets, private documents, build outputs, and internal project/release audit reports are excluded.

- [Build and test guide](BUILD_AND_TEST.md)
- [Application architecture](docs/ARCHITECTURE.md)
- [Windows signing](docs/WINDOWS_RELEASE_SIGNING.md)
- [Android tablet build](android/README.md)
- [Changes](BETA_CHANGELOG.md)

Run the desktop demonstration from an isolated Python environment with `python demo_launcher.py`; follow the build guide for dependencies and configuration. Android remains a debug tablet test build and requires device validation.
