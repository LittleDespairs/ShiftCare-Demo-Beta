# Standalone Android APK

The project now includes an Android wrapper in `android/` for a standalone tablet build.

It is designed to run without a PC server:

1. Android launches the app.
2. Chaquopy starts embedded Python inside the APK.
3. Python starts the existing FastAPI app on `127.0.0.1:8765`.
4. Android WebView opens that local URL.
5. SQLite is copied once into Android internal app storage and then used from there.

## Build Prerequisites

- Android Studio with Android SDK.
- JDK 17 or newer.
- Internet access for the first Gradle/Chaquopy dependency download.

This machine currently has Java 8 and no Android SDK/Gradle on PATH, so I could scaffold and verify the Python side, but I cannot produce the final `.apk` here until the Android build tools are installed.

## Build Command

After installing Android Studio/JDK 17:

```powershell
cd android
.\gradlew.bat assembleDebug
```

If the terminal still uses Java 8, run the build with Android Studio or JetBrains JBR:

```powershell
$env:JAVA_HOME = "C:\Program Files\JetBrains\IntelliJ IDEA 2025.2.5\jbr"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
cd android
.\gradlew.bat assembleDebug
```

If Android Studio creates/updates the Gradle wrapper, the APK path will be:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

## Install Only On Your Tablet

With USB debugging:

```powershell
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

Without USB debugging, copy the APK to the tablet and open it there after enabling install from unknown sources.

## Android Compatibility Note

Chaquopy cannot package `pydantic_core` for this Android target. To avoid that blocker, the Android build uses lightweight local shim modules for `fastapi` and `pydantic`, backed by Starlette where needed. The regular desktop app still uses the real FastAPI/Pydantic dependencies.

The debug APK was successfully built locally at:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```
