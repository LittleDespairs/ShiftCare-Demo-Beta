# Standalone Android APK

The project includes an Android wrapper in `android/` for a standalone tablet build. The current debug build is **0.21.1 beta** (`versionCode 17`, `versionName 0.21.1-beta-tablet-current`).

It is designed to run without a PC server:

1. Android launches the app.
2. Chaquopy starts embedded Python inside the APK.
3. Python starts the existing FastAPI app on `127.0.0.1:8766`.
4. Android WebView opens that local URL.
5. A new SQLite database is initialized in Android internal app storage and retained across app restarts and upgrades. Working databases and private configuration are excluded from the APK.

## Build Prerequisites

- Android Studio with Android SDK.
- JDK 17 or newer.
- Internet access for the first Gradle/Chaquopy dependency download.

The 0.21.1 beta debug APK was built locally with the JetBrains JBR below and the Android SDK configured in `android/local.properties`. Set `JAVA_HOME` explicitly if the system Java on PATH is older than JDK 17.

## Build Command

With Android SDK and JDK 17 or newer configured:

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

The Gradle wrapper produces the APK at:

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

This is a debug artifact for local testing, not a Google Play release. Build and package-content checks passed; a physical-tablet launch has not been verified. See [the 0.21.1 release report](docs/RELEASE_0.21.1_beta_RU.md) for the artifact checksum and validation details.
