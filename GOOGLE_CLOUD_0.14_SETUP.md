# Google Cloud 0.14.x Beta Setup

Infrastructure notes for the `0.14.x_beta` authorization milestone.

## Current Decision

The desktop application remains the primary user interface. Cloud SQL stores organization and user data, but the desktop app must not connect directly to the production database. The intended production path is:

```text
Desktop App -> HTTPS Backend API -> Cloud SQL PostgreSQL
```

For Google Cloud deployment, the intended backend path is:

```text
Cloud Run API -> Cloud SQL PostgreSQL
```

## Current Implementation Status

As of `0.14.17_beta`, Cloud Run is connected to Cloud SQL PostgreSQL through the application database adapter.
The desktop/local runtime still defaults to SQLite, while the deployed beta backend uses PostgreSQL.

Current working beta path:

```text
Cloud Run API -> Cloud SQL PostgreSQL
```

Readiness endpoint:

```text
/api/health/ready
```

It returns HTTP `503` when the configured runtime is blocked, for example when PostgreSQL is selected but required database settings or connectivity are missing.

## Google Cloud Resources

```text
Project ID: schedule-app-beta
Region: me-west1
Zone: me-west1-b
Cloud SQL instance: schedule-beta-db
Cloud SQL connection name: schedule-app-beta:me-west1:schedule-beta-db
Database engine: PostgreSQL 18
Database name: schedule_beta
Database user: schedule_app
```

Do not store the database password in this repository. Use a local `.env` file for development and Google Secret Manager for deployed services.

## Cloud SQL Configuration

```text
Edition: Enterprise
Machine type: db-custom-1-3840
vCPUs: 1
RAM: 3.75 GB
Storage: 10 GB SSD
Availability: Single zone
Region: me-west1 / Tel Aviv
Private IP: enabled
Public IP: enabled for now
Authorized networks: empty
SSL only: enabled
Automated backups: enabled
Point-in-time recovery: enabled
```

`Public IP` can remain enabled during early setup, but `Authorized networks` must stay empty unless a temporary, specific IP is needed for diagnostics. Never add `0.0.0.0/0`.

## Billing Guardrail

Before adding more paid resources, confirm that Google Cloud billing alerts are configured:

```text
Budget: 20-30 USD or another explicit beta limit
Alerts: 50%, 90%, 100%
Scope: schedule-app-beta project
```

## 0.14.x Beta Scope

The first implementation phase should focus on authorization and organization ownership:

- `organizations`
- `users`
- `organization_memberships`
- roles and permissions
- password hashing
- login/logout
- `/auth/me`
- invitation flow
- audit events for auth and role changes

Cloud synchronization of the full scheduling database is a later step. Medical or resident CRM data must stay out of the `0.14.x_beta` authorization milestone.

## Backend Rules

- The desktop app must call a backend API instead of opening direct Cloud SQL access.
- Backend permission checks are required even when UI controls are hidden.
- Every organization-owned record must be designed to receive an `organization_id`.
- Local database files are treated as current runtime storage now and future cache storage after sync is introduced.
- Backups must not include passwords, access tokens, or server secrets.

## Local Environment

Use `.env.example` as the template for local development:

```text
.env.example -> .env
```

Required local secrets:

```text
DATABASE_PASSWORD
AUTH_TOKEN_SECRET
```

Keep `.env` private. It is ignored by git.

## Cloud Run Smoke Deployment

The repository includes:

```text
Dockerfile
requirements-cloud.txt
cloudbuild.yaml
docs/postgresql/001_initial_schema.sql
```

Smoke deployment command from the repository root:

```bash
gcloud builds submit --config cloudbuild.yaml --project schedule-app-beta --substitutions=_TAG=0.14.17-beta
```

The Cloud Run build now uses the approved public app domain by default:

```text
PUBLIC_APP_BASE_URL=https://portal.shiftcare.co.il
SCHEDULE_APP_DEFAULT_API_BASE_URL=https://portal.shiftcare.co.il
```

After deployment:

```bash
gcloud run services describe schedule-app-beta-api --region me-west1 --project schedule-app-beta --format="value(status.url)"
```

Open:

```text
<service-url>/api/health/live
<service-url>/api/health/ready
```

The Cloud Run deployment uses:

```text
APP_ENV=staging
DATABASE_ENGINE=postgresql
DATABASE_NAME=schedule_beta
DATABASE_USER=schedule_app
CLOUD_SQL_CONNECTION_NAME=schedule-app-beta:me-west1:schedule-beta-db
DATABASE_PASSWORD=<Secret Manager: schedule-app-db-password>
AUTH_TOKEN_SECRET=<Secret Manager: schedule-app-auth-token-secret>
```

SQLite remains only the desktop/local default. Do not use container-local SQLite for Cloud Run beta data.

## Firebase Hosting Custom Domain

Cloud Run direct custom domain mapping is not available in `me-west1`. The beta uses Firebase Hosting as the public HTTPS entry point and rewrites all traffic to the Tel Aviv Cloud Run service.

Firebase files:

```text
.firebaserc
firebase.json
static/firebase-placeholder/index.html
```

Firebase Hosting target:

```text
Project: schedule-app-beta
Primary custom domain: portal.shiftcare.co.il
Legacy alias: app.shiftcare.co.il
Rewrite target: Cloud Run service schedule-app-beta-api in me-west1
```

Google Cloud DNS zone:

```text
Managed zone: shiftcare-co-il
DNS name: shiftcare.co.il.
```

Set these nameservers at the domain registrar for `shiftcare.co.il`:

```text
ns-cloud-b1.googledomains.com
ns-cloud-b2.googledomains.com
ns-cloud-b3.googledomains.com
ns-cloud-b4.googledomains.com
```

The Cloud DNS zone already contains this Firebase Hosting record:

```text
Type: CNAME
Host/name: portal
Target/value: schedule-app-beta.web.app
```

Firebase has not requested a separate `portal` ACME TXT record yet. If Firebase later asks for one, add it to the same Cloud DNS zone:

```text
Type: TXT
Host/name: _acme-challenge.portal
Target/value: use the current value shown by Firebase custom domain status
```

After Firebase confirms the custom domain, deploy Hosting from the repository root:

```bash
firebase deploy --only hosting --project schedule-app-beta
```

Then verify:

```text
https://portal.shiftcare.co.il/login
https://portal.shiftcare.co.il/api/client-config
```

DNS status on 2026-04-29: Google Public DNS resolves `portal.shiftcare.co.il` to `schedule-app-beta.web.app`.
Some local ISP/OS resolvers may still temporarily show the old Box nameservers while delegation cache expires.

## Cloud SQL PostgreSQL Preparation

The PostgreSQL baseline schema lives at:

```text
docs/postgresql/001_initial_schema.sql
```

The deployed runtime applies this baseline through `database.init_db()` when `DATABASE_ENGINE=postgresql`.
Apply it manually only to an empty Cloud SQL PostgreSQL database.

Required PostgreSQL environment variables:

```text
DATABASE_ENGINE=postgresql
DATABASE_NAME=schedule_beta
DATABASE_USER=schedule_app
DATABASE_PASSWORD=<secret>
CLOUD_SQL_CONNECTION_NAME=schedule-app-beta:me-west1:schedule-beta-db
DATABASE_SSL_MODE=require
```

For Cloud Run with Cloud SQL Unix socket connectivity, keep `DATABASE_HOST` empty and configure the Cloud SQL connection on the Cloud Run service.

## PostgreSQL Migration Checklist

Completed in `0.14.17_beta`:

- Replaced direct Cloud Run `sqlite3` runtime with a database adapter that supports PostgreSQL placeholders, row-style access, `lastrowid`, and SQLite-compatible integrity errors.
- Hardened the PostgreSQL DDL baseline for the current application schema and default seed rows.
- Replaced SQLite-only runtime readiness blockers and kept SQLite-specific migrations on the local SQLite path.
- Disabled SQLite file backup/restore actions for PostgreSQL runtime; use Cloud SQL automated backups and point-in-time recovery.
- Added adapter regression coverage and verified deployed Cloud SQL runtime through public API smoke tests.
- Added Cloud SQL connection, Secret Manager credentials, and Cloud Run Cloud SQL instance binding to `cloudbuild.yaml`.

Verified on 2026-04-29:

```text
Cloud Run revision: schedule-app-beta-api-00023-59z
App version: 0.14.17_beta
Ready endpoint: /api/health/ready -> ok
Database engine: postgresql
Bootstrap state: 1 active organization, 0 active users
API smoke: create/list/delete employee, position, and shift template -> ok
```

Remaining production hardening:

- Add a disposable PostgreSQL CI service for full integration tests instead of relying only on deployed Cloud SQL smoke checks.
- Add logical export tooling if customer-level export/import is needed beyond Cloud SQL managed backups.
