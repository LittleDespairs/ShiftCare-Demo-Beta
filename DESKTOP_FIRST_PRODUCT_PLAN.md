# Desktop-Sync Product Plan

Planning checklist for the target ShiftCare product model: the installed desktop app is the only scheduler workspace, while cloud is the account authority, customer data hub, background sync target, and public employee portal.

## Target Architecture - 2026-04-29

- [x] Remove the user-facing choice between local and cloud workspaces.
- [x] Desktop login calls the cloud account service with email/password.
- [x] After successful cloud login, desktop downloads the organization bundle into local SQLite.
- [x] Desktop creates a local session and all heavy scheduler screens use only the local API.
- [x] Desktop schedule generation, edits, exports, settings, and directory screens use the local API first.
- [x] Local changes are written immediately to SQLite and queued for background cloud sync.
- [x] Background sync is non-blocking, retryable, and visible as status only, not modal workflow.
- [x] Employee public pages stay cloud-hosted and read/write cloud data only.
- [x] Employee public pages are separate portal-scoped flows, not a cloud workspace switch.
- [x] Other users keep their portal flow: invitation link, password setup, preferences, and read-only schedule view.

## Data Authority

- Cloud owns identities, organization membership, licensing, employee portal data, and the latest synced organization snapshot.
- Desktop owns the active scheduling transaction while the user is working.
- Local SQLite is a required working cache, not an optional offline fallback.
- Cloud sync is eventual. A slow network must not slow down desktop navigation or schedule generation.
- Conflict rules must be explicit before multi-admin simultaneous editing is allowed.

## Implementation Phases

- [x] Phase 1: remove Local/Cloud UI choices and make desktop API mode internal only.
- [x] Phase 2: add desktop cloud-login endpoint that authenticates against the cloud portal.
- [x] Phase 3: download/import organization bundle after login and create a local desktop session.
- [x] Phase 4: add local change journal table and wrap mutating endpoints with sync event recording.
- [x] Phase 5: add background sync worker with retry/backoff and sync status UI.
- [x] Phase 6: split public employee portal pages from desktop pages and lock portal to cloud-safe read/write endpoints.
- [x] Phase 7 beta baseline: add conflict/version direction, support tooling, and leave licensing enforcement for the licensing milestone.

## Product Direction

- [x] Treat the desktop app as the core scheduler product.
- [x] Treat cloud as account authority, sync hub, licensing backend, and employee portal.
- [x] Keep local SQLite as the active desktop runtime store.
- [x] Keep Cloud Run/Firebase Hosting for cloud login, sync API, and employee portal.
- [x] Define paid license activation as part of the cloud account/organization entitlement.
- [x] Define offline license/grace-period behavior.
- [x] Decide which features require internet and which must work offline.

### Product Decisions Before Licensing Detail

- License activation is a desktop entitlement decision, not a cloud account login requirement.
- Cloud account login is only for optional portal/sync/migration features.
- Offline license behavior should allow continued desktop work from locally stored entitlement data, with any expiry/grace policy defined in the later Licensing section.
- Must work offline: local owner login, employees, positions, assignments, templates, requirements, weekly preferences, schedule generation, manual edits, Excel/Word exports, local backups, and restore.
- Requires internet: online activation, update checks, cloud portal linking, employee public invitation links, cloud import/export, future sync, and future email delivery.

## Desktop Core

- [x] Startup must default to the local/same-origin API.
- [x] Ensure packaged desktop users can create the first local owner without internet.
- [x] Ensure schedule generation, manual edits, exports, backups, and restore work without internet.
- [x] Add a clear desktop-local setup path for first launch.
- [x] Add an explicit "Connect cloud portal" action after local organization setup.
- [x] Review all frontend API defaults for accidental hard dependency on `portal.shiftcare.co.il`.

## Cloud Portal

- [x] Keep `portal.shiftcare.co.il` as the public employee-facing domain.
- [x] Keep Firebase Hosting rewrite to Cloud Run.
- [x] Keep cloud organization export/import as a migration/linking step.
- [x] Use cloud only after an owner/admin explicitly links an organization.
- [x] Make employee invitation links use the public portal domain only when cloud portal is enabled.
- [x] Add UI copy that cloud beta is optional and not required for offline desktop use.
- [x] Add a cloud disconnect / unlink path for beta testing.

## Licensing

- [x] Choose license model: one-time desktop license plus recurring annual support/cloud plan.
- [x] Define draft license payload fields: license ID, organization/branch, employee limit, support/cloud expiry, grace period, features, signature.
- [x] Define local license storage requirement without requiring cloud login on every launch.
- [x] Choose online activation as the first activation path.
- [x] Define offline activation file path requirement for customers without reliable internet.
- [x] Bundle employee portal/cloud access into the recurring annual support/cloud plan.
- [x] Define unlicensed behavior: block creating/generating new schedules.
- [x] Define expired subscription behavior: 14-day grace period with persistent reminders.
- [x] Attach license primarily to organization/branch.

## Data Ownership and Sync

- [x] Local database remains the current source of truth for desktop-only organizations.
- [x] Cloud sync must be opt-in.
- [x] Define beta conflict rules before two-way sync.
- [x] Define what is cloud-owned after sync is enabled.
- [x] Keep backups local and restorable without internet.
- [x] Do not use Cloud SQL for production organization data until PostgreSQL adapter work is complete.

## Immediate Implementation

- [x] Stop automatic cloud-first API selection on login.
- [x] Rename login-side status from "Local recovery" to desktop-local workspace.
- [x] Keep Cloud beta behind an explicit connection button.
- [x] Verify packaged desktop first-launch flow.
- [x] Add regression coverage for default API mode.
- [x] Revisit Organization page cloud panel copy and placement.

## Deferred Owner Decisions

- Finalize license payload values and signature format before implementing enforcement.
- Decide exact offline activation file format and support workflow.
- Decide whether production sync should support simultaneous admin editing or stay single-admin per organization for the first paid version.
- Confirm whether Cloud SQL is acceptable for production after the PostgreSQL CI and backup/export hardening are complete.

---

# Desktop-First Product Plan - Русская версия

Чеклист для возврата ShiftCare к исходной продуктовой модели: установленное desktop-приложение является основным offline-capable продуктом, а cloud-функции остаются необязательными дополнениями для портала сотрудников, миграции, синхронизации и восстановления.

## Продуктовое направление

- [x] Считать desktop-приложение основным продуктом.
- [x] Считать доступ к cloud portal необязательной инфраструктурой, а не обязательным главным workflow.
- [x] Оставить локальный SQLite активным runtime-хранилищем desktop-приложения до отдельного внедрения sync layer.
- [x] Оставить Cloud Run/Firebase Hosting beta-инфраструктурой для employee portal и будущей синхронизации.
- [x] Определить платную активацию лицензии отдельно от входа в cloud account.
- [x] Определить поведение offline license / grace period.
- [x] Решить, какие функции требуют интернет, а какие обязаны работать offline.

### Продуктовые решения до детальной проработки лицензирования

- Активация лицензии - это entitlement desktop-приложения, а не обязательный cloud account login.
- Cloud account login нужен только для необязательных функций портала, sync и миграции.
- Offline license behavior должен позволять продолжать desktop-работу на основе локально сохранённого entitlement; срок действия и grace policy будут определены в разделе Licensing.
- Обязано работать offline: локальный вход owner, сотрудники, должности, назначения, шаблоны, требования, недельные пожелания, генерация расписания, ручные правки, Excel/Word exports, локальные backups и restore.
- Требует интернет: online activation, update checks, cloud portal linking, публичные invitation links для сотрудников, cloud import/export, будущая синхронизация и будущая email delivery.

## Desktop Core

- [x] При запуске приложение должно по умолчанию использовать local/same-origin API.
- [x] Убедиться, что пользователи packaged desktop могут создать первого локального owner без интернета.
- [x] Убедиться, что генерация расписания, ручные правки, exports, backups и restore работают без интернета.
- [x] Добавить понятный desktop-local setup path для первого запуска.
- [x] Добавить явное действие "Connect cloud portal" после локальной настройки организации.
- [x] Проверить все frontend API defaults на случайную жёсткую зависимость от `portal.shiftcare.co.il`.

## Cloud Portal

- [x] Оставить `portal.shiftcare.co.il` публичным employee-facing доменом.
- [x] Оставить Firebase Hosting rewrite на Cloud Run.
- [x] Оставить cloud organization export/import как шаг миграции/привязки.
- [x] Использовать cloud только после того, как owner/admin явно привяжет организацию.
- [x] Делать invitation links для сотрудников через публичный portal domain только когда cloud portal включён.
- [x] Добавить UI-тексты, что cloud beta необязателен и не нужен для offline desktop use.
- [x] Добавить cloud disconnect / unlink path для beta-тестирования.

## Лицензирование

- [x] Выбрать модель лицензии: one-time desktop license плюс ежегодный support/cloud plan.
- [x] Определить черновой payload лицензии: license ID, организация/филиал, лимит сотрудников, срок support/cloud, grace period, features, signature.
- [x] Зафиксировать требование хранить лицензию локально без необходимости cloud login при каждом запуске.
- [x] Выбрать online activation как первый путь активации.
- [x] Зафиксировать offline activation file path для клиентов без стабильного интернета.
- [x] Включить employee portal/cloud access в ежегодный support/cloud plan.
- [x] Определить поведение без лицензии: блокировать создание/генерацию новых расписаний.
- [x] Определить поведение после истечения подписки: 14 дней grace period с постоянными напоминаниями.
- [x] Привязывать лицензию в первую очередь к организации/филиалу.

## Владение данными и синхронизация

- [x] Локальная база остаётся текущим source of truth для desktop-only организаций.
- [x] Cloud sync должен быть opt-in.
- [x] Определить beta conflict rules до внедрения two-way sync.
- [x] Определить, какие данные становятся cloud-owned после включения sync.
- [x] Оставить backups локальными и восстанавливаемыми без интернета.
- [x] Не использовать Cloud SQL для production organization data, пока PostgreSQL adapter work не завершён.

## Ближайшая реализация

- [x] Остановить автоматический cloud-first API selection на login.
- [x] Переименовать login-side status с "Local recovery" на desktop-local workspace.
- [x] Оставить Cloud beta за явной кнопкой подключения.
- [x] Проверить packaged desktop first-launch flow.
- [x] Добавить regression coverage для default API mode.
- [x] Пересмотреть текст и размещение cloud panel на странице Organization.

## Отложенные решения владельца

- Финализировать значения license payload и формат подписи перед enforcement.
- Решить точный формат offline activation file и support workflow.
- Решить, разрешаем ли одновременное редактирование несколькими админами в первой платной версии.
- Подтвердить готовность Cloud SQL для production после PostgreSQL CI и backup/export hardening.
