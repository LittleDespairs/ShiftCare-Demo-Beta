# Windows Beta Release Checklist

Use this checklist before shipping any `0.12.x_beta` desktop build.

## Build

- [ ] Confirm `APP_VERSION` in `main.py` matches the intended beta build.
- [ ] Confirm the PyInstaller spec filename and app artifact name match the same beta build.
- [ ] Run the full unittest suite in `.venv`.
- [ ] Build with `pyinstaller` using the current spec.

## Smoke Test

- [ ] Start the packaged application.
- [ ] Confirm the browser opens and the app responds on the local URL.
- [ ] Open the pages: dashboard, schedule, employees, weekly preferences, settings.
- [ ] Confirm templates and static assets load correctly in packaged mode.
- [ ] Confirm the bundled database is copied to the runtime directory on first start.

## Schedule Checks

- [ ] Load a real position and week.
- [ ] Run auto-generation once.
- [ ] Confirm the summary panel appears and is localized in the selected language.
- [ ] Confirm problem days are highlighted in the table if generation leaves warnings or gaps.
- [ ] Add one shift manually and remove it again.
- [ ] Change one day status and one no-show status.
- [ ] Export Excel for a generated week.

## Release Notes

- [ ] Add the build entry to `BETA_CHANGELOG.md`.
- [ ] Record known issues and must-fix blockers before sharing the build.
