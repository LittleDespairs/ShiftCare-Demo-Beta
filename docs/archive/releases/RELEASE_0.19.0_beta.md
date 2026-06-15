# ShiftCare 0.19.0 Beta

## Release focus

Ship transactional email delivery for organization invitations and align the cloud, desktop, and release metadata on the `0.19.0_beta` version line.

## Changed

- Added SMTP-backed email delivery for organization invitation links, password reset messages, and email verification messages.
- Added `/reset-password` and `/verify-email` pages so emailed auth links resolve to working user flows.
- Added email delivery configuration to runtime settings, Cloud Run deployment settings, and `.env.example`.
- Updated Organization invite feedback so users see whether the email was sent, disabled, or failed while still receiving a copyable invitation link.
- Added Box SMTP configuration support for `invite@shiftcare.co.il`, with Cloud Run secrets wired through Secret Manager.
- Added DNS email-authentication records for `shiftcare.co.il`: MX, SPF, DMARC, and DKIM.
- Updated runtime, service worker cache name, Windows packaging metadata, Android version metadata, build docs, and installer script to `0.19.0_beta`.
- Archived the `0.18.1_beta` release notes and PyInstaller spec, then added the active `ShiftCare_0.19.0_beta.spec`.

## Verification

- SMTP login and test send passed for `invite@shiftcare.co.il` through `cp57.box.co.il:465`.
- Google Cloud DNS resolves MX, SPF, DMARC, and DKIM for `shiftcare.co.il`.
- Cloud Run reports `EMAIL_ENABLED=1` and uses `schedule-app-smtp-password` from Secret Manager.
- Public `/api/client-config` will be checked after deployment to confirm `app_version` is `0.19.0_beta`.
- API regression tests will be run before release publication.

## Known notes

- WhatsApp invitation delivery is intentionally deferred until a WhatsApp Business organization and sender number are available.
