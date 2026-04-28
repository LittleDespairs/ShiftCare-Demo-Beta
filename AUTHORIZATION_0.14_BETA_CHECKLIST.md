# Authorization 0.14.x Beta Checklist

Planning checklist for the `0.14.x_beta` line. Main focus: introduce user authorization, organization accounts, and the first cloud-ready data model while keeping the desktop app as the primary user interface.

## English

### 1. Product Scope

- [x] Start the new beta line: `0.14.x_beta`.
- [x] Define the first target build, for example `0.14.0_beta`.
- [x] Confirm the main goal: add user authorization without moving the scheduling UI out of the desktop app.
- [x] Keep the current local scheduling workflow usable during the transition.
- [x] Separate `must-have` authorization work from later cloud sync and CRM work.
- [x] Document which parts remain local-only in `0.14.x_beta`.

### 2. Target User Flow

- [x] Define the organization creation flow.
- [x] Replace "send organization account database by email" with invitation or activation flow.
- [x] Define first administrator onboarding:
  - [x] User installs the desktop app.
  - [x] User creates or joins an organization.
  - [x] User verifies email.
  - [x] User creates their own password.
  - [x] Desktop app receives organization context after login.
- [x] Define employee onboarding:
  - [x] Admin creates or imports employees.
  - [x] Admin sends invitation links.
  - [x] Employees set their own passwords or use one-time login links.
  - [x] Employees can submit weekly preferences.
- [x] Keep manual employee preference management available inside the desktop app.

### 3. Roles and Permissions

- [x] Add a role model before adding cloud sync.
- [x] Define `Owner` permissions.
- [x] Define `Admin` / `Scheduler` permissions.
- [x] Define `Employee` permissions.
- [x] Define optional `Read-only` / `Manager` permissions.
- [x] Ensure employees can access only their own profile, schedule, and preference submissions.
- [x] Ensure admins can manage schedules, employees, positions, requirements, and preferences.
- [x] Ensure only owners can delete or transfer the organization.
- [x] Add permission checks at the API/backend layer, not only in the UI.

### 4. Data Model Preparation

- [x] Add `organizations` table or equivalent model.
- [x] Add `users` table or equivalent model.
- [x] Add `organization_memberships` table or equivalent model.
- [x] Add role and permission fields.
- [x] Add `organization_id` to organization-owned entities:
  - [x] Employees.
  - [x] Positions.
  - [x] Shift templates.
  - [x] Weekly requirements.
  - [x] Weekly preferences.
  - [x] Generated schedule assignments.
  - [x] Settings.
- [x] Add stable IDs for records that will be synchronized later.
- [x] Add `created_at`, `updated_at`, and `updated_by` where needed.
- [x] Add schema migration path from existing local databases.

### 5. Authentication

- [x] Choose the first auth implementation for beta:
  - Not selected: Local auth for prototype.
  - Not selected: Cloud auth service.
  - [x] Custom backend auth.
- [x] Store passwords only as strong password hashes if handled by the app backend.
- [x] Do not email passwords to users.
- [x] Add password reset flow.
- [x] Add email verification flow.
- [x] Add session/token storage for the desktop app.
- [x] Add logout and session expiration behavior.
- [x] Plan MFA support for owners/admins, even if not shipped in the first `0.14.x_beta` build.

### 6. Desktop App Changes

- [x] Add login screen before opening organization data.
- [x] Add organization selection if the user belongs to multiple organizations.
- [x] Add account/profile screen.
- [x] Add organization members management screen.
- [x] Add invitation management UI for admins.
- [x] Add clear offline/online state indicator.
- [x] Keep existing scheduling pages functional after login.
- [x] Hide or disable actions that the current role cannot perform.
- [x] Add Russian, English, and Hebrew UI strings for new auth screens.

### 7. Employee Preferences Page

- [x] Decide whether employee preference submission is available through:
  - Not selected: Desktop app only.
  - [x] Browser page served by the local app.
  - Not selected: Cloud-hosted web page.
  - Not selected: Temporary invitation link.
- [x] Keep admin-side manual control inside the desktop app.
- [x] Add employee login or one-time link support.
- [x] Add permission checks so one employee cannot view or edit another employee's preferences.
- [x] Add audit trail for preference submissions and admin edits.

### 8. Cloud Database Preparation

- [x] Do not connect the desktop app directly to the cloud SQL database.
- [x] Introduce an API boundary: `Desktop App -> Backend API -> Database`.
- [x] Define which data is cloud-owned in the first phase:
  - [x] Organizations.
  - [x] Users.
  - [x] Roles and memberships.
  - [x] Employees.
  - [x] Weekly preferences.
  - [x] Scheduling data.
- [x] Define which data remains local cache.
- [x] Add API versioning plan.
- [x] Add environment separation: development, staging, production.
- [x] Prefer Israel cloud region for production data residency.

### 9. Local Cache and Backup

- [x] Treat the local database as cache once cloud sync is introduced.
- Deferred before production: Encrypt local database or sensitive local backup files.
- [x] Create a custom backup format, for example `.schedulebackup`.
- [x] Ensure backups do not contain passwords, access tokens, or server secrets.
- [x] Add backup metadata:
  - [x] App version.
  - [x] Schema version.
  - [x] Organization ID.
  - [x] Created date.
  - [x] Created by.
- [x] Restrict restore to authorized owners/admins.
- [x] Add restore conflict warning before overwriting cloud data.

### 10. Security and Compliance Baseline

- [x] Classify stored data by sensitivity.
- [x] Avoid medical/resident CRM data in the `0.14.x_beta` authorization milestone.
- [x] Add audit logs for login, logout, invitation, role change, export, backup, and restore.
- [x] Add rate limits for login and password reset.
- [x] Add account lockout or abuse protection.
- [x] Add privacy notice draft for cloud account usage.
- [x] Add data retention policy draft.
- [x] Add incident response checklist draft.
- [x] Document third-party cloud providers and subprocessors before production use.

### 11. Migration Strategy

- [x] Detect old local-only database on first launch after update.
- [x] Offer to create or connect an organization.
- [x] Map existing local data into the selected organization.
- [x] Create a backup before migration.
- [x] Validate migration result before deleting or replacing local data.
- [x] Keep rollback path for failed migration.
- [x] Add tests for migration from the latest `0.13.x_beta` database.

### 12. Testing and Release Criteria

- [x] Add tests for organization creation.
- [x] Add tests for login/logout.
- [x] Add tests for role-based access.
- [x] Add tests for employee invitation flow.
- [x] Add tests for weekly preference permissions.
- [x] Add tests for migration from local database to organization-scoped database.
- Deferred to packaging pass: Smoke-test the packaged Windows app with a new organization.
- Deferred to packaging pass: Smoke-test the packaged Windows app with an existing local database.
- [x] Update `BETA_CHANGELOG.md`.
- [x] Update version references to `0.14.x_beta`.
- [x] Release only when existing scheduling workflow still works after authorization is enabled.

---

## Русский

### 1. Объём продукта

- [x] Начать новую beta-линейку: `0.14.x_beta`.
- [x] Определить первую целевую сборку, например `0.14.0_beta`.
- [x] Зафиксировать главную цель: внедрить пользовательскую авторизацию, не вынося интерфейс составления расписания из desktop-приложения.
- [x] Сохранить текущий локальный workflow составления расписания на время перехода.
- [x] Отделить обязательную работу по авторизации от будущей синхронизации с облаком и CRM.
- [x] Документировать, какие части в `0.14.x_beta` остаются только локальными.

### 2. Целевой пользовательский сценарий

- [x] Описать сценарий создания организации.
- [x] Заменить идею "отправить базу учётной записи организации по email" на invitation или activation flow.
- [x] Описать первое подключение администратора:
  - [x] Пользователь устанавливает desktop-приложение.
  - [x] Пользователь создаёт организацию или присоединяется к ней.
  - [x] Пользователь подтверждает email.
  - [x] Пользователь сам создаёт пароль.
  - [x] Desktop-приложение получает контекст организации после входа.
- [x] Описать подключение сотрудников:
  - [x] Администратор создаёт или импортирует сотрудников.
  - [x] Администратор отправляет invitation-ссылки.
  - [x] Сотрудники сами задают пароль или используют одноразовые ссылки входа.
  - [x] Сотрудники могут отправлять пожелания по неделе.
- [x] Оставить ручное управление пожеланиями сотрудников внутри desktop-приложения.

### 3. Роли и права

- [x] Добавить модель ролей до внедрения облачной синхронизации.
- [x] Описать права роли `Owner`.
- [x] Описать права роли `Admin` / `Scheduler`.
- [x] Описать права роли `Employee`.
- [x] Описать необязательную роль `Read-only` / `Manager`.
- [x] Убедиться, что сотрудник видит только свой профиль, своё расписание и свои пожелания.
- [x] Убедиться, что администратор управляет расписанием, сотрудниками, должностями, требованиями покрытия и пожеланиями.
- [x] Убедиться, что только владелец может удалить или передать организацию.
- [x] Проверять права на уровне API/backend, а не только в интерфейсе.

### 4. Подготовка модели данных

- [x] Добавить таблицу или модель `organizations`.
- [x] Добавить таблицу или модель `users`.
- [x] Добавить таблицу или модель `organization_memberships`.
- [x] Добавить поля ролей и прав.
- [x] Добавить `organization_id` к данным, принадлежащим организации:
  - [x] Сотрудники.
  - [x] Должности.
  - [x] Шаблоны смен.
  - [x] Недельные требования.
  - [x] Недельные пожелания.
  - [x] Сгенерированные назначения в расписании.
  - [x] Настройки.
- [x] Добавить стабильные ID для записей, которые позже будут синхронизироваться.
- [x] Добавить `created_at`, `updated_at` и `updated_by` там, где это нужно.
- [x] Подготовить путь миграции из существующих локальных баз.

### 5. Авторизация

- [x] Выбрать первую реализацию авторизации для beta:
  - Не выбрано: Локальная авторизация для прототипа.
  - Не выбрано: Облачный auth-сервис.
  - [x] Собственный backend auth.
- [x] Если пароли обрабатывает backend приложения, хранить их только как сильные password hashes.
- [x] Не отправлять пароли пользователям по email.
- [x] Добавить сброс пароля.
- [x] Добавить подтверждение email.
- [x] Добавить хранение session/token для desktop-приложения.
- [x] Добавить logout и истечение сессии.
- [x] Запланировать MFA для владельцев и администраторов, даже если это не войдёт в первую сборку `0.14.x_beta`.

### 6. Изменения в desktop-приложении

- [x] Добавить экран входа перед открытием данных организации.
- [x] Добавить выбор организации, если пользователь состоит в нескольких организациях.
- [x] Добавить экран аккаунта/профиля.
- [x] Добавить экран управления участниками организации.
- [x] Добавить интерфейс управления invitation-ссылками для администраторов.
- [x] Добавить понятный индикатор offline/online состояния.
- [x] Сохранить работоспособность текущих страниц расписания после входа.
- [x] Скрывать или отключать действия, которые недоступны текущей роли.
- [x] Добавить русские, английские и ивритские строки интерфейса для новых auth-экранов.

### 7. Страница пожеланий сотрудников

- [x] Решить, как сотрудники будут отправлять пожелания:
  - Не выбрано: Только через desktop-приложение.
  - [x] Через browser-страницу, которую отдаёт локальное приложение.
  - Не выбрано: Через cloud-hosted web page.
  - Не выбрано: Через временную invitation-ссылку.
- [x] Оставить ручное управление пожеланиями для администратора внутри desktop-приложения.
- [x] Добавить вход сотрудника или поддержку одноразовой ссылки.
- [x] Добавить проверку прав, чтобы один сотрудник не мог видеть или менять пожелания другого сотрудника.
- [x] Добавить audit trail для отправки пожеланий и ручных правок администратором.

### 8. Подготовка облачной базы

- [x] Не подключать desktop-приложение напрямую к cloud SQL базе.
- [x] Ввести API-границу: `Desktop App -> Backend API -> Database`.
- [x] Определить, какие данные на первом этапе принадлежат облаку:
  - [x] Организации.
  - [x] Пользователи.
  - [x] Роли и членство.
  - [x] Сотрудники.
  - [x] Недельные пожелания.
  - [x] Данные расписания.
- [x] Определить, какие данные остаются локальным cache.
- [x] Добавить план версионирования API.
- [x] Разделить окружения: development, staging, production.
- [x] Для production предпочесть cloud region в Израиле ради data residency.

### 9. Локальный cache и backup

- [x] После внедрения cloud sync считать локальную базу cache-слоем.
- Отложено до production: Шифровать локальную базу или чувствительные локальные backup-файлы.
- [x] Создать собственный формат backup, например `.schedulebackup`.
- [x] Убедиться, что backup не содержит пароли, access tokens или серверные секреты.
- [x] Добавить metadata backup:
  - [x] Версия приложения.
  - [x] Версия схемы.
  - [x] ID организации.
  - [x] Дата создания.
  - [x] Кем создан.
- [x] Разрешать restore только авторизованным владельцам/администраторам.
- [x] Добавить предупреждение о конфликтах перед перезаписью cloud-данных.

### 10. Базовая безопасность и compliance

- [x] Классифицировать хранимые данные по чувствительности.
- [x] Не добавлять медицинские данные и CRM домов престарелых в milestone авторизации `0.14.x_beta`.
- [x] Добавить audit logs для login, logout, invitation, смены роли, export, backup и restore.
- [x] Добавить rate limits для входа и сброса пароля.
- [x] Добавить защиту от перебора пароля или блокировку аккаунта.
- [x] Подготовить черновик privacy notice для использования cloud account.
- [x] Подготовить черновик data retention policy.
- [x] Подготовить черновик incident response checklist.
- [x] До production задокументировать cloud providers и subprocessors.

### 11. Стратегия миграции

- [x] На первом запуске после обновления обнаруживать старую локальную базу.
- [x] Предлагать создать организацию или подключиться к существующей.
- [x] Привязать существующие локальные данные к выбранной организации.
- [x] Создавать backup перед миграцией.
- [x] Проверять результат миграции перед удалением или заменой локальных данных.
- [x] Оставить путь отката при неудачной миграции.
- [x] Добавить тесты миграции из последней базы `0.13.x_beta`.

### 12. Тестирование и критерии релиза

- [x] Добавить тесты создания организации.
- [x] Добавить тесты login/logout.
- [x] Добавить тесты role-based access.
- [x] Добавить тесты invitation flow для сотрудников.
- [x] Добавить тесты прав доступа к недельным пожеланиям.
- [x] Добавить тесты миграции из локальной базы в organization-scoped базу.
- Отложено до packaging pass: Smoke-test packaged Windows app с новой организацией.
- Отложено до packaging pass: Smoke-test packaged Windows app с существующей локальной базой.
- [x] Обновить `BETA_CHANGELOG.md`.
- [x] Обновить ссылки на версию до `0.14.x_beta`.
- [x] Выпускать релиз только если текущий workflow составления расписания продолжает работать после включения авторизации.
