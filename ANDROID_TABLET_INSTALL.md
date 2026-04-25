# Android Tablet Install

This project is a Python/FastAPI web app with a SQLite database. Android cannot run the existing Windows `.exe` build directly. The current tablet-friendly path is:

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

## Fully standalone tablet app later

A real APK that runs everything on the tablet would need a different packaging path, such as:

- a native Android wrapper with an embedded Python backend,
- a rewrite of the backend to an Android-native stack,
- or a hosted server plus a simple Android WebView shell.

The PWA/LAN route is the lowest-risk way to use the current app on a private tablet before deciding whether a full APK is worth building.
