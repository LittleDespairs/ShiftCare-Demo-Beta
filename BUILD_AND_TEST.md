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

Run for an Android tablet on the same Wi-Fi network:

```powershell
.\.venv\Scripts\python.exe run_tablet_server.py
```

If port `8000` is busy:

```powershell
$env:SCHEDULE_APP_PORT = "8001"
.\.venv\Scripts\python.exe run_tablet_server.py
```

Desktop launcher path:

```powershell
.\.venv\Scripts\python.exe launcher.py
```

This starts the FastAPI backend on localhost and opens the app in a native desktop window.
If port `8000` is busy, the launcher automatically uses the next free local port. You can also request a port:

```powershell
$env:SCHEDULE_APP_PORT = "8010"
.\.venv\Scripts\python.exe launcher.py
```

## Backend Health Checks

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health/live
Invoke-RestMethod http://127.0.0.1:8000/api/health/ready
```

`/api/health/ready` checks runtime configuration and database connectivity.

## Cloud Run Smoke Container

The Cloud Run container uses backend-only dependencies:

```text
requirements-cloud.txt
```

Local Docker smoke test:

```powershell
docker build -t schedule-app-api:local .
docker run --rm -p 8080:8080 schedule-app-api:local
```

Then check:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/api/health/live
Invoke-RestMethod http://127.0.0.1:8080/api/health/ready
```

Cloud Run beta deployments use PostgreSQL through Cloud SQL. For release confidence,
run the PostgreSQL integration test with `SCHEDULE_APP_POSTGRES_TEST_DSN` set, or use
the GitHub Actions workflow that starts a disposable PostgreSQL service.

## Android Standalone APK

The standalone Android wrapper is in `android/`.

It requires Android Studio, Android SDK, and JDK 17+. The current local Java is Java 8, so install/configure JDK 17 before building.

```powershell
cd android
.\gradlew.bat assembleDebug
```

On this machine, the working build command is:

```powershell
$env:JAVA_HOME = "C:\Program Files\JetBrains\IntelliJ IDEA 2025.2.5\jbr"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
cd android
.\gradlew.bat assembleDebug
```

See `ANDROID_STANDALONE_APK.md` and `android/README.md`.

## PyInstaller Build

Current spec:

```text
ShiftCare_0.20.10_beta.spec
```

Build command:

```powershell
.\.venv\Scripts\pyinstaller.exe ShiftCare_0.20.10_beta.spec
```

## Windows Installer

The installer is built with Inno Setup 6 and creates a normal Windows installation:
Program Files app folder, Start Menu shortcut, Desktop shortcut, uninstall entry, and post-install launch option.

One-command build:

```powershell
.\tools\build_windows_installer.ps1
.\tools\build_windows_installer.ps1 -Target Demo
```

If Inno Setup is not installed locally:

```powershell
.\tools\build_windows_installer.ps1 -InstallInnoSetup
```

Expected installer output:

```text
dist\installer\ShiftCare_Setup_0.20.10-beta.exe
dist\installer\ShiftCare_Demo_Setup_0.20.10-beta.exe
```

Customer release build with code signing:

```powershell
$env:SHIFTCARE_SIGN_CERT_THUMBPRINT = "YOUR_CERT_THUMBPRINT_WITHOUT_SPACES"
.\tools\build_windows_installer.ps1 -Target ShiftCare -Release -Sign
```

`-Release` rebuilds with a clean PyInstaller work directory and disables UPX. `-Sign` signs the
PyInstaller app executable, lets Inno Setup sign the installer and uninstaller, and verifies the
final app executable and setup signature. If the certificate is selected by subject instead of
thumbprint, set `SHIFTCARE_SIGN_CERT_SUBJECT`. The release script also checks that the signed
publisher matches `release_config.py`.

Before the first stable build, set the expected updater publisher in `release_config.py`. It should
match the legal subject in the code-signing certificate.

Before uploading the installer to GitHub Releases, verify it on a clean Windows machine:

```powershell
signtool verify /pa /tw /v .\dist\installer\ShiftCare_Setup_0.20.10-beta.exe
```

## Before Committing

- Run the full unittest suite in `.venv`.
- Check the schedule page route loads.
- Check there are no accidental leftover alpha version strings in runtime files.
- Keep `BETA_CHANGELOG.md` updated when a beta iteration materially changes the app.
