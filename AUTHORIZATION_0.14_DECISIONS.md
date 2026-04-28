# Authorization 0.14.x Beta Decisions / Решения по авторизации 0.14.x Beta

## English

### Scope

The `0.14.x_beta` line starts with `0.14.1_beta`. The goal is user authorization, organization accounts, and a cloud-ready data model while keeping the scheduling UI inside the desktop-installed app. CRM, resident medical records, billing, and nursing-home resident care data are explicitly out of scope for this milestone.

Must-have for `0.14.x_beta`: custom backend auth, organization ownership, invitations, roles, local scheduling continuity, backup/restore safety, audit logs, schema versioning, stable public IDs, and organization-scoped local data.

Later cloud sync and CRM work must not be mixed into this milestone except for schema preparation.

### User Flows

Organization creation: the first installed desktop app opens `/login`, the first owner creates the organization, then the app stores a local bearer session and organization context.

Administrator onboarding: install app, create or join organization, create password, verify email through the beta verification token flow, then manage members and invitations from `/organization`.

Employee onboarding: admin creates or imports employees, sends invitation links, employee accepts the invitation, sets their own password, signs in, and later submits weekly preferences through the desktop-served browser page. Passwords are never emailed.

The earlier idea of emailing an organization account database is rejected. Activation/invitation flow is the standard path.

### Roles

Owner: full organization control, backup/restore, members, invitations, future transfer/delete organization, schedule administration.

Admin: manage members except ownership transfer/delete, invitations, schedules, employees, positions, requirements, preferences, backup/restore.

Scheduler: manage schedules and operational planning data. No organization deletion, ownership transfer, or invitation management.

Manager: read operational organization data and member lists where permitted. No invitation or destructive organization control.

Employee: own profile and own future preference submissions only. No member management.

Read-only: future audit/reporting role with no mutating permissions.

### Employee Preferences

First beta decision: preference submission remains a browser page served by the desktop app, not a separate cloud-hosted public site. Admin-side manual preference management stays inside the desktop app. Employee self-service must be restricted to the membership-linked employee record before production use.

### Cloud Ownership

First cloud-owned phase: organizations, users, roles, memberships, employees, weekly preferences, schedule data, and audit events.

Local cache: desktop SQLite database, generated schedule workspace, UI preferences, recovery backups, and temporary offline work. Once cloud sync exists, local SQLite must be treated as cache, not source of truth.

API boundary: desktop app -> backend API -> database. The desktop app must not connect directly to Cloud SQL.

API versioning: first cloud API should use `/api/v1/...`; existing local endpoints remain compatibility endpoints until migration is complete.

Environments: development uses local SQLite, staging uses isolated cloud resources, production uses Israel region where available. Production secrets must live outside git.

### Backup And Cache

The custom backup format is `.schedulebackup`: a ZIP package with `schedule_app.db` and `metadata.json`. Metadata includes app version, schema version, organization ID, created date, creator ID, and security flags. Backups do not contain access tokens or server secrets. Current beta backups may contain password hashes because the local database contains user accounts; therefore backup encryption remains required before production.

Restore is restricted to owner/admin once auth is initialized, and the UI warns before overwriting current data. A pre-restore backup is created automatically.

### Security And Compliance

Sensitivity classification:

- High: password hashes, auth tokens, invitation tokens, reset tokens, email verification tokens, audit events.
- Personal data: employee names, emails, roles, schedule assignments, weekly preferences, day statuses.
- Operational data: positions, shift templates, requirements, app settings.
- Excluded from this milestone: medical/resident CRM data.

Privacy notice draft: the app stores organization account data, member identity, employee scheduling data, weekly preferences, audit logs, and backups for scheduling operations. Data may be processed by the selected cloud provider once cloud sync is enabled.

Retention draft: auth audit logs and schedule history should be retained according to customer policy; reset and verification tokens expire and are single-use; deleted organizations should enter a retention window before hard deletion.

Incident response draft: detect, contain, revoke sessions/tokens, preserve audit logs, notify affected organization owners, rotate secrets, restore from known-good backup if needed, and document root cause.

Subprocessors before production: Google Cloud Platform, GitHub Releases for update distribution, and any future email provider used for reset/verification delivery.

MFA plan: owners/admins should get TOTP/WebAuthn support before production cloud rollout.

### Migration

On first launch after update, `init_db()` detects an older database by missing schema metadata, creates a safety-compatible schema, adds organization scope, stable public IDs, audit tables, and records schema migration version. Existing local data maps to organization `1` (`local-default`). Backups must be created before destructive migration steps. Rollback path is the pre-migration or pre-restore backup.

## Русский

### Объём

Линейка `0.14.x_beta` начинается с `0.14.1_beta`. Цель: пользовательская авторизация, организации и подготовка модели данных к облаку, при этом интерфейс составления расписания остаётся внутри desktop-приложения. CRM, медицинские данные постояльцев, биллинг и данные ухода не входят в этот milestone.

Обязательное для `0.14.x_beta`: собственный backend auth, организация, владелец, приглашения, роли, сохранение локального workflow расписания, безопасный backup/restore, audit logs, версия схемы, стабильные public IDs и organization-scoped локальные данные.

### Пользовательские сценарии

Создание организации: пользователь открывает `/login`, первый владелец создаёт организацию, приложение сохраняет локальную bearer-сессию и контекст организации.

Подключение администратора: установка приложения, создание или присоединение к организации, создание пароля, подтверждение email через beta verification token flow, управление участниками и приглашениями на `/organization`.

Подключение сотрудника: администратор создаёт или импортирует сотрудников, отправляет invitation link, сотрудник принимает приглашение, задаёт пароль, входит в систему и позднее отправляет недельные пожелания через browser-страницу, которую отдаёт desktop-приложение.

Идея отправлять базу учётной записи организации по email отклонена. Стандартный путь: activation/invitation flow.

### Роли

Owner: полный контроль организации, backup/restore, участники, приглашения, будущая передача/удаление организации, администрирование расписания.

Admin: участники без передачи/удаления организации, приглашения, расписания, сотрудники, должности, требования, пожелания, backup/restore.

Scheduler: расписание и операционные данные планирования. Без удаления организации и управления приглашениями.

Manager: чтение операционных данных и списков участников там, где это разрешено.

Employee: только свой профиль и будущие собственные пожелания.

Read-only: будущая роль для аудита/просмотра без изменений.

### Пожелания сотрудников

Решение первой beta: отправка пожеланий остаётся browser-страницей, которую отдаёт desktop-приложение. Отдельный cloud-hosted публичный сайт откладывается. Ручное управление пожеланиями администратора остаётся внутри desktop-приложения.

### Облако

На первом облачном этапе cloud-owned: организации, пользователи, роли, членство, сотрудники, недельные пожелания, данные расписания и audit events.

Локальный cache: SQLite desktop database, рабочее пространство генерации, UI-настройки, recovery backups и временная offline-работа. После cloud sync локальная база не должна считаться источником истины.

Граница API: desktop app -> backend API -> database. Прямое подключение desktop app к Cloud SQL запрещено.

API versioning: для cloud API использовать `/api/v1/...`; текущие local endpoints оставить как compatibility layer.

Окружения: development - local SQLite, staging - изолированное облако, production - регион Израиля, где доступно. Production secrets не хранятся в git.

### Backup И Cache

Формат `.schedulebackup`: ZIP с `schedule_app.db` и `metadata.json`. Metadata содержит версию приложения, версию схемы, ID организации, дату создания, ID создателя и security flags. Backup не содержит access tokens или server secrets. В текущей beta backup может содержать password hashes, поэтому шифрование backup остаётся обязательным до production.

Restore разрешён только owner/admin после инициализации auth. UI предупреждает о перезаписи. Перед restore создаётся pre-restore backup.

### Security И Compliance

Классификация:

- High: password hashes, auth tokens, invitation tokens, reset tokens, verification tokens, audit events.
- Personal data: имена сотрудников, email, роли, назначения расписания, недельные пожелания, статусы дней.
- Operational data: должности, шаблоны смен, требования, настройки.
- Исключено: medical/resident CRM data.

Privacy notice draft: приложение хранит данные организации, участников, сотрудников, расписания, пожелания, audit logs и backups для задач планирования. После включения cloud sync данные могут обрабатываться выбранным cloud provider.

Retention draft: audit logs и история расписания хранятся по политике клиента; reset/verification tokens истекают и одноразовые; удалённые организации должны иметь retention window перед hard delete.

Incident response draft: обнаружить, локализовать, отозвать sessions/tokens, сохранить audit logs, уведомить владельцев организации, повернуть secrets, восстановить known-good backup, описать root cause.

Subprocessors до production: Google Cloud Platform, GitHub Releases для обновлений, будущий email provider для reset/verification.

MFA plan: для owner/admin добавить TOTP/WebAuthn до production cloud rollout.

### Миграция

При первом запуске после обновления `init_db()` обнаруживает старую базу по отсутствию schema metadata, добавляет organization scope, stable public IDs, audit tables и записывает schema migration version. Существующие локальные данные привязываются к организации `1` (`local-default`). Перед destructive migration steps нужен backup. Rollback path: pre-migration или pre-restore backup.
