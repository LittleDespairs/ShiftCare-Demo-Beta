# Windows Release Signing

This checklist prepares customer-facing Windows builds so users see a verified publisher and the
updater only launches trusted installers.

## One-time setup

1. Obtain a real code-signing identity:
   - Microsoft Store publication if store distribution is acceptable.
   - Microsoft Artifact Signing for CI/CD signing.
   - OV/EV Code Signing Certificate from a trusted CA for standalone installers.
2. Install Windows SDK Signing Tools or set `SHIFTCARE_SIGNTOOL_PATH` to `signtool.exe`.
3. Put the signing certificate in the Windows certificate store available to the release machine.
4. Decide the exact publisher subject to trust for updates. It must match the signer certificate
   subject, for example `ShiftCare` or the legal company name in the certificate.

EV certificates do not guarantee immediate SmartScreen trust. Reputation still builds over time
from signed downloads and clean installs.

## Release environment

Set one certificate selector:

```powershell
$env:SHIFTCARE_SIGN_CERT_THUMBPRINT = "YOUR_CERT_THUMBPRINT_WITHOUT_SPACES"
```

Or:

```powershell
$env:SHIFTCARE_SIGN_CERT_SUBJECT = "Your Legal Publisher Name"
```

Set the updater signer pin in `release_config.py` before building the customer installer:

```python
WINDOWS_SIGNER_SUBJECT = "Your Legal Publisher Name"
```

`SHIFTCARE_WINDOWS_SIGNER_SUBJECT` is only a runtime override for local tests or diagnostics. It is
not automatically baked into the customer executable.

Optional overrides:

```powershell
$env:SHIFTCARE_SIGNTOOL_PATH = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.xxxxx.x\x64\signtool.exe"
$env:SHIFTCARE_TIMESTAMP_URL = "http://timestamp.digicert.com"
```

## Build

```powershell
.\tools\build_windows_installer.ps1 -Target ShiftCare -Release -Sign
```

For demo builds:

```powershell
.\tools\build_windows_installer.ps1 -Target Demo -Release -Sign
```

The script signs:

- `dist\ShiftCare_...\ShiftCare_....exe`
- the Inno Setup installer
- the Inno Setup uninstaller embedded in the installer

It also verifies the final app executable and setup executable.
The signed publisher is compared with `release_config.py`; the build fails if they do not match.

## Before publishing

1. Install on a clean Windows VM.
2. Confirm the installer properties show a valid Digital Signatures tab.
3. Confirm Windows shows the expected verified publisher.
4. Run the app and check `/api/updates/check`.
5. Upload only the signed installer to GitHub Releases.

## Update safety

The desktop updater downloads installers only from GitHub release asset hosts, checks the installer
filename pattern, and verifies the Windows Authenticode signature before launching it. If the signer
subject does not contain `SHIFTCARE_WINDOWS_SIGNER_SUBJECT`, the update is blocked.

When the certificate is renewed, keep the same publisher identity where possible. Timestamped old
builds remain valid after the certificate expires.
