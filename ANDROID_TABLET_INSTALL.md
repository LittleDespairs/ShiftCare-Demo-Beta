# Android Tablet Install

This project is a Python/FastAPI web app with a SQLite database. Android cannot run the Windows `.exe` build directly. This guide covers using the app over a local network:

1. Run the app server on your PC.
2. Open it from the Android tablet over the same Wi-Fi network.
3. Add it to the tablet home screen from Chrome/Samsung Internet.

This does not publish anything to Google Play.

## Run for a tablet

On the PC:

```powershell
.\.venv\Scripts\python.exe run_tablet_server.py
```

If port `8000` is busy, use another port:

```powershell
$env:SCHEDULE_APP_PORT = "8001"
.\.venv\Scripts\python.exe run_tablet_server.py
```

The terminal prints one or more tablet URLs, for example:

```text
Open on tablet: http://192.168.1.25:8000
```

Keep this terminal window open while using the app on the tablet.

## Open on Android

1. Make sure the PC and tablet are on the same Wi-Fi network.
2. Open Chrome or Samsung Internet on the tablet.
3. Go to the printed URL, for example `http://192.168.1.25:8000`.
4. Open the browser menu.
5. Choose `Add to Home screen` or `Install app`, depending on the browser.

The app includes a web app manifest, an icon, theme color, and a service worker registration. On local/LAN HTTP, Android browsers may create a home-screen shortcut instead of a full installable PWA because service workers require a secure context except for `localhost`.

## If the tablet cannot connect

- Allow Python or the app through Windows Firewall for private networks.
- Check that both devices are on the same Wi-Fi network.
- Use the exact IP address printed by `run_tablet_server.py`.
- If port `8000` is busy, stop the other server first.

## Standalone tablet APK

The project also includes a standalone Android WebView wrapper with an embedded Python backend and its own local SQLite database. The **0.21.1 beta** debug APK has been built and checked locally; a physical-tablet launch has not been verified.

See [standalone APK build and installation](ANDROID_STANDALONE_APK.md) for that option. The LAN setup above remains useful when the tablet should use the database running on the PC.
