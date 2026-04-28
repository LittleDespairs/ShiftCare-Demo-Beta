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

As of `0.14.2_beta`, the deployable Cloud Run container is suitable for backend smoke tests only.
The application data layer is still SQLite-based (`sqlite3`, SQLite DDL, SQLite backup/restore).
Do not connect production organization data to Cloud Run until the PostgreSQL adapter and migrations are implemented.

Current working beta path:

```text
Cloud Run API smoke test -> ephemeral SQLite in /tmp
```

Production target path:

```text
Cloud Run API -> Cloud SQL PostgreSQL
```

Readiness endpoint:

```text
/api/health/ready
```

It returns HTTP `503` when the configured runtime is blocked, for example when `DATABASE_ENGINE=postgresql`
is set before PostgreSQL support exists.

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
```

Smoke deployment command from the repository root:

```bash
gcloud builds submit --config cloudbuild.yaml --project schedule-app-beta
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

The smoke deployment uses:

```text
APP_ENV=staging
DATABASE_ENGINE=sqlite
SCHEDULE_APP_DATABASE_PATH=/tmp/schedule_app.db
```

This is intentionally non-production because Cloud Run container storage is ephemeral.

## PostgreSQL Migration Blockers

Before using Cloud SQL for real beta organizations, complete these items:

- Replace direct `sqlite3` calls with a database abstraction that supports PostgreSQL placeholders and row access.
- Add PostgreSQL DDL migrations for every table currently created in `database.py`.
- Replace SQLite-specific `PRAGMA`, `AUTOINCREMENT`, `randomblob`, and trigger syntax.
- Replace SQLite file backup/restore for deployed mode with logical exports or Cloud SQL backups.
- Add integration tests that run against a disposable PostgreSQL database.
- Add Cloud SQL connection configuration to Cloud Run only after the PostgreSQL integration tests pass.
