# Authorization 0.14.x Beta Checklist

Planning checklist for the `0.14.x_beta` line. Main focus: introduce user authorization, organization accounts, and the first cloud-ready data model while keeping the desktop app as the primary user interface.

## English

### 1. Product Scope

- [ ] Start the new beta line: `0.14.x_beta`.
- [ ] Define the first target build, for example `0.14.0_beta`.
- [ ] Confirm the main goal: add user authorization without moving the scheduling UI out of the desktop app.
- [ ] Keep the current local scheduling workflow usable during the transition.
- [ ] Separate `must-have` authorization work from later cloud sync and CRM work.
- [ ] Document which parts remain local-only in `0.14.x_beta`.

### 2. Target User Flow

- [ ] Define the organization creation flow.
- [ ] Replace "send organization account database by email" with invitation or activation flow.
- [ ] Define first administrator onboarding:
  - [ ] User installs the desktop app.
  - [ ] User creates or joins an organization.
  - [ ] User verifies email.
  - [ ] User creates their own password.
  - [ ] Desktop app receives organization context after login.
- [ ] Define employee onboarding:
  - [ ] Admin creates or imports employees.
  - [x] Admin sends invitation links.
  - [x] Employees set their own passwords or use one-time login links.
  - [ ] Employees can submit weekly preferences.
- [ ] Keep manual employee preference management available inside the desktop app.

### 3. Roles and Permissions

- [ ] Add a role model before adding cloud sync.
- [ ] Define `Owner` permissions.
- [ ] Define `Admin` / `Scheduler` permissions.
- [ ] Define `Employee` permissions.
- [ ] Define optional `Read-only` / `Manager` permissions.
- [ ] Ensure employees can access only their own profile, schedule, and preference submissions.
- [ ] Ensure admins can manage schedules, employees, positions, requirements, and preferences.
- [ ] Ensure only owners can delete or transfer the organization.
- [x] Add permission checks at the API/backend layer, not only in the UI.

### 4. Data Model Preparation

- [x] Add `organizations` table or equivalent model.
- [x] Add `users` table or equivalent model.
- [x] Add `organization_memberships` table or equivalent model.
- [x] Add role and permission fields.
- [ ] Add `organization_id` to organization-owned entities:
  - [x] Employees.
  - [x] Positions.
  - [x] Shift templates.
  - [x] Weekly requirements.
  - [x] Weekly preferences.
  - [x] Generated schedule assignments.
  - [ ] Settings.
- [ ] Add stable IDs for records that will be synchronized later.
- [x] Add `created_at`, `updated_at`, and `updated_by` where needed.
- [ ] Add schema migration path from existing local databases.

### 5. Authentication

- [ ] Choose the first auth implementation for beta:
  - [ ] Local auth for prototype.
  - [ ] Cloud auth service.
  - [x] Custom backend auth.
- [x] Store passwords only as strong password hashes if handled by the app backend.
- [x] Do not email passwords to users.
- [ ] Add password reset flow.
- [ ] Add email verification flow.
- [x] Add session/token storage for the desktop app.
- [x] Add logout and session expiration behavior.
- [ ] Plan MFA support for owners/admins, even if not shipped in the first `0.14.x_beta` build.

### 6. Desktop App Changes

- [x] Add login screen before opening organization data.
- [x] Add organization selection if the user belongs to multiple organizations.
- [x] Add account/profile screen.
- [x] Add organization members management screen.
- [x] Add invitation management UI for admins.
- [ ] Add clear offline/online state indicator.
- [ ] Keep existing scheduling pages functional after login.
- [x] Hide or disable actions that the current role cannot perform.
- [ ] Add Russian, English, and Hebrew UI strings for new auth screens.

### 7. Employee Preferences Page

- [ ] Decide whether employee preference submission is available through:
  - [ ] Desktop app only.
  - [ ] Browser page served by the local app.
  - [ ] Cloud-hosted web page.
  - [ ] Temporary invitation link.
- [ ] Keep admin-side manual control inside the desktop app.
- [ ] Add employee login or one-time link support.
- [ ] Add permission checks so one employee cannot view or edit another employee's preferences.
- [ ] Add audit trail for preference submissions and admin edits.

### 8. Cloud Database Preparation

- [x] Do not connect the desktop app directly to the cloud SQL database.
- [x] Introduce an API boundary: `Desktop App -> Backend API -> Database`.
- [ ] Define which data is cloud-owned in the first phase:
  - [ ] Organizations.
  - [ ] Users.
  - [ ] Roles and memberships.
  - [ ] Employees.
  - [ ] Weekly preferences.
  - [ ] Scheduling data.
- [ ] Define which data remains local cache.
- [ ] Add API versioning plan.
- [ ] Add environment separation: development, staging, production.
- [x] Prefer Israel cloud region for production data residency.

### 9. Local Cache and Backup

- [ ] Treat the local database as cache once cloud sync is introduced.
- [ ] Encrypt local database or sensitive local backup files.
- [ ] Create a custom backup format, for example `.schedulebackup`.
- [ ] Ensure backups do not contain passwords, access tokens, or server secrets.
- [ ] Add backup metadata:
  - [ ] App version.
  - [ ] Schema version.
  - [ ] Organization ID.
  - [ ] Created date.
  - [ ] Created by.
- [ ] Restrict restore to authorized owners/admins.
- [ ] Add restore conflict warning before overwriting cloud data.

### 10. Security and Compliance Baseline

- [ ] Classify stored data by sensitivity.
- [ ] Avoid medical/resident CRM data in the `0.14.x_beta` authorization milestone.
- [ ] Add audit logs for login, logout, invitation, role change, export, backup, and restore.
- [ ] Add rate limits for login and password reset.
- [ ] Add account lockout or abuse protection.
- [ ] Add privacy notice draft for cloud account usage.
- [ ] Add data retention policy draft.
- [ ] Add incident response checklist draft.
- [ ] Document third-party cloud providers and subprocessors before production use.

### 11. Migration Strategy

- [ ] Detect old local-only database on first launch after update.
- [ ] Offer to create or connect an organization.
- [ ] Map existing local data into the selected organization.
- [ ] Create a backup before migration.
- [ ] Validate migration result before deleting or replacing local data.
- [ ] Keep rollback path for failed migration.
- [ ] Add tests for migration from the latest `0.13.x_beta` database.

### 12. Testing and Release Criteria

- [x] Add tests for organization creation.
- [x] Add tests for login/logout.
- [x] Add tests for role-based access.
- [x] Add tests for employee invitation flow.
- [ ] Add tests for weekly preference permissions.
- [ ] Add tests for migration from local database to organization-scoped database.
- [ ] Smoke-test the packaged Windows app with a new organization.
- [ ] Smoke-test the packaged Windows app with an existing local database.
- [ ] Update `BETA_CHANGELOG.md`.
- [ ] Update version references to `0.14.x_beta`.
- [ ] Release only when existing scheduling workflow still works after authorization is enabled.

---

## Русский

### 1. Объём продукта

- [ ] Начать новую beta-линейку: `0.14.x_beta`.
- [ ] Определить первую целевую сборку, например `0.14.0_beta`.
- [ ] Зафиксировать главную цель: внедрить пользовательскую авторизацию, не вынося интерфейс составления расписания из desktop-приложения.
- [ ] Сохранить текущий локальный workflow составления расписания на время перехода.
- [ ] Отделить обязательную работу по авторизации от будущей синхронизации с облаком и CRM.
- [ ] Документировать, какие части в `0.14.x_beta` остаются только локальными.

### 2. Целевой пользовательский сценарий

- [ ] Описать сценарий создания организации.
- [ ] Заменить идею "отправить базу учётной записи организации по email" на invitation или activation flow.
- [ ] Описать первое подключение администратора:
  - [ ] Пользователь устанавливает desktop-приложение.
  - [ ] Пользователь создаёт организацию или присоединяется к ней.
  - [ ] Пользователь подтверждает email.
  - [ ] Пользователь сам создаёт пароль.
  - [ ] Desktop-приложение получает контекст организации после входа.
- [ ] Описать подключение сотрудников:
  - [ ] Администратор создаёт или импортирует сотрудников.
  - [x] Администратор отправляет invitation-ссылки.
  - [x] Сотрудники сами задают пароль или используют одноразовые ссылки входа.
  - [ ] Сотрудники могут отправлять пожелания по неделе.
- [ ] Оставить ручное управление пожеланиями сотрудников внутри desktop-приложения.

### 3. Роли и права

- [ ] Добавить модель ролей до внедрения облачной синхронизации.
- [ ] Описать права роли `Owner`.
- [ ] Описать права роли `Admin` / `Scheduler`.
- [ ] Описать права роли `Employee`.
- [ ] Описать необязательную роль `Read-only` / `Manager`.
- [ ] Убедиться, что сотрудник видит только свой профиль, своё расписание и свои пожелания.
- [ ] Убедиться, что администратор управляет расписанием, сотрудниками, должностями, требованиями покрытия и пожеланиями.
- [ ] Убедиться, что только владелец может удалить или передать организацию.
- [x] Проверять права на уровне API/backend, а не только в интерфейсе.

### 4. Подготовка модели данных

- [x] Добавить таблицу или модель `organizations`.
- [x] Добавить таблицу или модель `users`.
- [x] Добавить таблицу или модель `organization_memberships`.
- [x] Добавить поля ролей и прав.
- [ ] Добавить `organization_id` к данным, принадлежащим организации:
  - [x] Сотрудники.
  - [x] Должности.
  - [x] Шаблоны смен.
  - [x] Недельные требования.
  - [x] Недельные пожелания.
  - [x] Сгенерированные назначения в расписании.
  - [ ] Настройки.
- [ ] Добавить стабильные ID для записей, которые позже будут синхронизироваться.
- [x] Добавить `created_at`, `updated_at` и `updated_by` там, где это нужно.
- [ ] Подготовить путь миграции из существующих локальных баз.

### 5. Авторизация

- [ ] Выбрать первую реализацию авторизации для beta:
  - [ ] Локальная авторизация для прототипа.
  - [ ] Облачный auth-сервис.
  - [x] Собственный backend auth.
- [x] Если пароли обрабатывает backend приложения, хранить их только как сильные password hashes.
- [x] Не отправлять пароли пользователям по email.
- [ ] Добавить сброс пароля.
- [ ] Добавить подтверждение email.
- [x] Добавить хранение session/token для desktop-приложения.
- [x] Добавить logout и истечение сессии.
- [ ] Запланировать MFA для владельцев и администраторов, даже если это не войдёт в первую сборку `0.14.x_beta`.

### 6. Изменения в desktop-приложении

- [x] Добавить экран входа перед открытием данных организации.
- [x] Добавить выбор организации, если пользователь состоит в нескольких организациях.
- [x] Добавить экран аккаунта/профиля.
- [x] Добавить экран управления участниками организации.
- [x] Добавить интерфейс управления invitation-ссылками для администраторов.
- [ ] Добавить понятный индикатор offline/online состояния.
- [ ] Сохранить работоспособность текущих страниц расписания после входа.
- [x] Скрывать или отключать действия, которые недоступны текущей роли.
- [ ] Добавить русские, английские и ивритские строки интерфейса для новых auth-экранов.

### 7. Страница пожеланий сотрудников

- [ ] Решить, как сотрудники будут отправлять пожелания:
  - [ ] Только через desktop-приложение.
  - [ ] Через browser-страницу, которую отдаёт локальное приложение.
  - [ ] Через cloud-hosted web page.
  - [ ] Через временную invitation-ссылку.
- [ ] Оставить ручное управление пожеланиями для администратора внутри desktop-приложения.
- [ ] Добавить вход сотрудника или поддержку одноразовой ссылки.
- [ ] Добавить проверку прав, чтобы один сотрудник не мог видеть или менять пожелания другого сотрудника.
- [ ] Добавить audit trail для отправки пожеланий и ручных правок администратором.

### 8. Подготовка облачной базы

- [x] Не подключать desktop-приложение напрямую к cloud SQL базе.
- [x] Ввести API-границу: `Desktop App -> Backend API -> Database`.
- [ ] Определить, какие данные на первом этапе принадлежат облаку:
  - [ ] Организации.
  - [ ] Пользователи.
  - [ ] Роли и членство.
  - [ ] Сотрудники.
  - [ ] Недельные пожелания.
  - [ ] Данные расписания.
- [ ] Определить, какие данные остаются локальным cache.
- [ ] Добавить план версионирования API.
- [ ] Разделить окружения: development, staging, production.
- [x] Для production предпочесть cloud region в Израиле ради data residency.

### 9. Локальный cache и backup

- [ ] После внедрения cloud sync считать локальную базу cache-слоем.
- [ ] Шифровать локальную базу или чувствительные локальные backup-файлы.
- [ ] Создать собственный формат backup, например `.schedulebackup`.
- [ ] Убедиться, что backup не содержит пароли, access tokens или серверные секреты.
- [ ] Добавить metadata backup:
  - [ ] Версия приложения.
  - [ ] Версия схемы.
  - [ ] ID организации.
  - [ ] Дата создания.
  - [ ] Кем создан.
- [ ] Разрешать restore только авторизованным владельцам/администраторам.
- [ ] Добавить предупреждение о конфликтах перед перезаписью cloud-данных.

### 10. Базовая безопасность и compliance

- [ ] Классифицировать хранимые данные по чувствительности.
- [ ] Не добавлять медицинские данные и CRM домов престарелых в milestone авторизации `0.14.x_beta`.
- [ ] Добавить audit logs для login, logout, invitation, смены роли, export, backup и restore.
- [ ] Добавить rate limits для входа и сброса пароля.
- [ ] Добавить защиту от перебора пароля или блокировку аккаунта.
- [ ] Подготовить черновик privacy notice для использования cloud account.
- [ ] Подготовить черновик data retention policy.
- [ ] Подготовить черновик incident response checklist.
- [ ] До production задокументировать cloud providers и subprocessors.

### 11. Стратегия миграции

- [ ] На первом запуске после обновления обнаруживать старую локальную базу.
- [ ] Предлагать создать организацию или подключиться к существующей.
- [ ] Привязать существующие локальные данные к выбранной организации.
- [ ] Создавать backup перед миграцией.
- [ ] Проверять результат миграции перед удалением или заменой локальных данных.
- [ ] Оставить путь отката при неудачной миграции.
- [ ] Добавить тесты миграции из последней базы `0.13.x_beta`.

### 12. Тестирование и критерии релиза

- [x] Добавить тесты создания организации.
- [x] Добавить тесты login/logout.
- [x] Добавить тесты role-based access.
- [x] Добавить тесты invitation flow для сотрудников.
- [ ] Добавить тесты прав доступа к недельным пожеланиям.
- [ ] Добавить тесты миграции из локальной базы в organization-scoped базу.
- [ ] Smoke-test packaged Windows app с новой организацией.
- [ ] Smoke-test packaged Windows app с существующей локальной базой.
- [ ] Обновить `BETA_CHANGELOG.md`.
- [ ] Обновить ссылки на версию до `0.14.x_beta`.
- [ ] Выпускать релиз только если текущий workflow составления расписания продолжает работать после включения авторизации.
