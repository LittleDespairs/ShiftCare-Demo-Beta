# Build And Test

## Test

Use the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Quick import check:

```powershell
@'
import main
print(main.APP_VERSION)
print(main.app.title)
'@ | .\.venv\Scripts\python.exe -
```

## Local Run

Run the web app in the project environment:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Desktop launcher path:

```powershell
.\.venv\Scripts\python.exe launcher.py
```

## PyInstaller Build

Current spec:

```text
ScheduleApp_0.12.6_beta.spec
```

Build command:

```powershell
.\.venv\Scripts\pyinstaller.exe ScheduleApp_0.12.6_beta.spec
```

## Before Committing

- Run the full unittest suite in `.venv`.
- Check the schedule page route loads.
- Check there are no accidental leftover alpha version strings in runtime files.
- Keep `BETA_CHANGELOG.md` updated when a beta iteration materially changes the app.

