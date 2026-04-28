# ShiftCare Standalone Android APK

This folder contains a standalone Android wrapper for the existing FastAPI app.

Runtime model:

- Android starts a Java `Activity`.
- Chaquopy starts an embedded Python runtime.
- `app_bridge.py` starts the FastAPI backend on `127.0.0.1:8765` inside the tablet.
- Android WebView opens that local URL.
- SQLite data is stored in the app internal storage directory, so it survives app restarts and upgrades.

## Requirements

- Android Studio with Android SDK installed.
- JDK 17 or newer.
- Internet access during the first Gradle build, because Gradle downloads Android and Chaquopy dependencies.

The current machine has Java 8 and no Android SDK/Gradle on PATH, so the project is scaffolded but cannot be built here until those tools are installed.

## Build

Open the `android` folder in Android Studio and run the `app` configuration, or use:

```powershell
cd android
.\gradlew.bat assembleDebug
```

If PowerShell still reports Java 8, point `JAVA_HOME` at the JBR bundled with a JetBrains IDE before building:

```powershell
$env:JAVA_HOME = "C:\Program Files\JetBrains\IntelliJ IDEA 2025.2.5\jbr"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
cd android
.\gradlew.bat assembleDebug
```

The debug APK will be created under:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

## Install on your tablet

Enable USB debugging on the tablet, then:

```powershell
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

You can also copy the APK to the tablet and open it there if installing from unknown sources is enabled.

## Android FastAPI/Pydantic shim

The desktop backend uses FastAPI/Pydantic, but Chaquopy cannot install `pydantic_core` for this Android target. The Android project therefore includes local shim modules in `app/src/main/python/fastapi` and `app/src/main/python/pydantic.py`. They provide the subset of FastAPI/Pydantic used by `main.py` and avoid native Rust dependencies.
