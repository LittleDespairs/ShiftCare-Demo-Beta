# Next Beta Update Checklist

Planning checklist for the active `0.13.x_beta` line. Current build: `0.13.2_beta`.

## English

### 1. Scope and Version

- [x] Decide the target version for the next build: `0.13.2_beta`.
- [x] Define the main update goal: start the `0.13.x_beta` beta line with a clean documentation baseline and current runtime version references.
- [x] Separate required fixes from optional polish.
- [x] Start a new line `0.13.x_beta`.

### 2. Clean Previous Beta Files

- [x] Review old beta planning files before deleting anything:
  - `docs/archive/beta-0.12/BETA_CHECKLIST.md`
  - `docs/archive/beta-0.12/BETA_CHECKLIST_RU.txt`
  - `docs/archive/beta-0.12/BETA_FINAL_SUMMARY_RU.md`
  - `docs/archive/beta-0.12/BETA_ISSUE_TRACKER.md`
  - `docs/archive/beta-0.12/WINDOWS_BETA_RELEASE_CHECKLIST.md`
- [x] Keep `BETA_CHANGELOG.md` as the historical source for previous builds.
- [x] Move completed previous-stage documents into an archive folder if they are still useful for history.
- [x] Delete only files that are clearly obsolete and not referenced by runtime, tests, packaging, or current docs.
- [x] Remove placeholder issue-tracker rows if beta issues are now tracked elsewhere.
- [x] Check for stale version references such as old `0.12.1_beta` through `0.12.6_beta` strings that should not appear in current runtime files.
- [x] Remove stale local artifacts such as build outputs, temporary exports, cache folders, and generated files if they are not tracked intentionally.
- [x] Run `git status --short` before and after cleanup to verify the cleanup is scoped.

### 3. Product and UX Review

- [ ] Walk through the core user flow: employees, positions, assignments, templates, weekly preferences, requirements, schedule, settings.
- [ ] Record friction points found during real schedule creation.
- [ ] Prioritize issues by `critical`, `important`, and `nice-to-have`.
- [ ] Confirm that empty states still guide the user to the next required setup step.
- [ ] Verify Hebrew, Russian, and English UI text on screens changed in this update.

### 4. UI Modification

- [ ] Review the current layout of each main screen and identify areas that need structural changes, not just visual polish.
- [ ] Improve navigation between related setup screens, especially employees, positions, assignments, requirements, and schedule.
- [ ] Rework crowded forms or tables where users need too many steps to complete a common action.
- [ ] Add or adjust controls that make frequent actions easier to find and perform.
- [x] Rework the schedule coverage row: fix inaccurate category-mode coverage data and reduce the sticky coverage row height on small screens without losing information or functionality.
- [ ] Confirm that UI changes work in desktop, narrow browser, and RTL layouts.

### 5. UI Polish

- [ ] Align button styles, spacing, table density, form labels, empty states, alerts, and modal behavior across screens.
- [ ] Reduce visual noise on the schedule screen while keeping important warnings visible.
- [ ] Check that success, warning, and error messages use consistent tone and terminology.
- [ ] Polish hover, focus, disabled, loading, and selected states for interactive controls.
- [ ] Verify that long Russian, Hebrew, and English strings fit without overlap or layout jumps.

### 6. Data Safety

- [ ] Verify backup creation before destructive actions.
- [ ] Verify restore still works on a real local database copy.
- [ ] Check delete-impact previews for employees, positions, shift templates, and clear-week actions.
- [ ] Confirm migrations or schema changes are backward-compatible with existing beta databases.

### 7. Schedule Generation

- [ ] Test generation with enough staff and realistic weekly requirements.
- [ ] Test generation with staff shortages.
- [ ] Test night shifts, split shifts, weekend restrictions, and manual edits after generation.
- [ ] Confirm generation summary explains hard blockers, soft compromises, and remaining shortages.
- [ ] Add or update regression tests for every generation bug fixed in this update.

### 8. Export and Reporting

- [ ] Verify Excel export for an empty week.
- [ ] Verify Excel export for a partially filled week.
- [ ] Verify Excel export with real shifts, `no_show`, and `day_off` statuses.
- [ ] Confirm the coordinator summary sheet is still readable and accurate.
- [ ] Add Word export by analogy with Excel export for users who do not have Excel installed.

### 9. Tests and Verification

- [ ] Run the full unit/regression suite.
- [ ] Run a smoke test for the FastAPI app startup.
- [ ] Smoke-test all main HTML pages return successfully.
- [ ] Verify changed API endpoints with both valid and invalid payloads.
- [ ] Document any test gaps before shipping the beta build.

### 10. Packaging and Release

- [x] Update `APP_VERSION` in `main.py`.
- [x] Update asset cache-busting strings in templates and static references.
- [x] Update the PyInstaller spec filename and executable name if the version changes.
- [ ] Build the Windows package.
- [ ] Start the packaged `.exe` and verify at least `/`, `/schedule`, and `/settings`.
- [x] Update `BETA_CHANGELOG.md` with date, version, changes, verification, and known issues.
- [ ] Tag or clearly mark the shipped beta build.

### 11. Exit Criteria

- [ ] No critical runtime errors in the core workflow.
- [ ] No known data-loss issue without backup or recovery path.
- [ ] Regression tests pass.
- [ ] Packaged app starts correctly.
- [ ] Changelog and issue list are current.

---

## Русский

### 1. Объём обновления и версия

- [x] Определить целевую версию следующей сборки: `0.13.2_beta`.
- [x] Сформулировать главную цель обновления: начать beta-линейку `0.13.x_beta` с чистой документационной базы и актуальных runtime-ссылок версии.
- [x] Разделить обязательные исправления и необязательную полировку.
- [x] Зафиксировать переход на новую линейку `0.13.x_beta`.

### 2. Очистка файлов прошлого beta-этапа

- [x] Перед удалением просмотреть старые beta-файлы:
  - `docs/archive/beta-0.12/BETA_CHECKLIST.md`
  - `docs/archive/beta-0.12/BETA_CHECKLIST_RU.txt`
  - `docs/archive/beta-0.12/BETA_FINAL_SUMMARY_RU.md`
  - `docs/archive/beta-0.12/BETA_ISSUE_TRACKER.md`
  - `docs/archive/beta-0.12/WINDOWS_BETA_RELEASE_CHECKLIST.md`
- [x] Оставить `BETA_CHANGELOG.md` как исторический журнал предыдущих сборок.
- [x] Перенести завершённые документы прошлого этапа в архивную папку, если они ещё нужны для истории.
- [x] Удалять только те файлы, которые точно устарели и не используются приложением, тестами, упаковкой или текущей документацией.
- [x] Удалить placeholder-строки из issue tracker, если beta-задачи теперь ведутся в другом месте.
- [x] Проверить старые ссылки на версии `0.12.1_beta` - `0.12.6_beta`, которые не должны оставаться в runtime-файлах текущей версии.
- [x] Удалить устаревшие локальные артефакты: build-вывод, временные экспорты, cache-папки и сгенерированные файлы, если они не должны храниться в репозитории.
- [x] Выполнить `git status --short` до и после очистки, чтобы убедиться, что изменения не вышли за рамки задачи.

### 3. Продуктовая и UX-проверка

- [ ] Пройти основной пользовательский путь: сотрудники, должности, назначения, шаблоны смен, недельные предпочтения, требования покрытия, расписание, настройки.
- [ ] Записать места, где реальное создание расписания всё ещё неудобно.
- [ ] Разложить задачи по приоритетам: `critical`, `important`, `nice-to-have`.
- [ ] Проверить, что пустые состояния по-прежнему ведут пользователя к следующему нужному шагу настройки.
- [ ] Проверить тексты интерфейса на иврите, русском и английском для экранов, затронутых этим обновлением.

### 4. Модификация пользовательского интерфейса

- [ ] Просмотреть текущую структуру каждого основного экрана и определить места, где нужны именно структурные изменения, а не только визуальная полировка.
- [ ] Улучшить навигацию между связанными экранами настройки: сотрудники, должности, назначения, требования покрытия и расписание.
- [ ] Переработать перегруженные формы или таблицы, где для частого действия пользователю нужно слишком много шагов.
- [ ] Добавить или скорректировать элементы управления, чтобы частые действия было проще найти и выполнить.
- [x] Переделать строку покрытия на экране расписания: исправить недостоверный режим отображения по категориям смен и уменьшить высоту sticky-строки покрытия на маленьких экранах без потери информативности.
- [ ] Проверить, что изменения интерфейса работают на desktop, в узком окне браузера и в RTL-режиме.

### 5. Полировка пользовательского интерфейса

- [ ] Выровнять стили кнопок, отступы, плотность таблиц, подписи форм, пустые состояния, уведомления и поведение modal-окон на разных экранах.
- [ ] Уменьшить визуальный шум на экране расписания, сохранив заметность важных предупреждений.
- [ ] Проверить, что success, warning и error-сообщения используют единый тон и терминологию.
- [ ] Отполировать hover, focus, disabled, loading и selected-состояния интерактивных элементов.
- [ ] Проверить, что длинные строки на русском, иврите и английском помещаются без наложений и скачков layout.

### 6. Безопасность данных

- [ ] Проверить создание backup перед опасными действиями.
- [ ] Проверить restore на реальной копии локальной базы данных.
- [ ] Проверить impact preview для удаления сотрудников, должностей, шаблонов смен и очистки недели.
- [ ] Убедиться, что миграции или изменения схемы совместимы с существующими beta-базами.

### 7. Генерация расписания

- [ ] Проверить генерацию при достаточном количестве сотрудников и реалистичных требованиях недели.
- [ ] Проверить генерацию при нехватке сотрудников.
- [ ] Проверить ночные смены, split-смены, ограничения выходных и ручные правки после генерации.
- [ ] Убедиться, что summary генерации объясняет жёсткие блокеры, мягкие компромиссы и оставшиеся нехватки.
- [ ] Добавить или обновить regression-тесты для каждого исправленного бага генерации.

### 8. Экспорт и отчёты

- [ ] Проверить Excel-экспорт для пустой недели.
- [ ] Проверить Excel-экспорт для частично заполненной недели.
- [ ] Проверить Excel-экспорт со сменами, статусами `no_show` и `day_off`.
- [ ] Убедиться, что summary-лист для координатора остаётся читаемым и точным.
- [ ] Добавить экспорт в формате Word по аналогии с Excel для пользователей, у которых не установлен Excel.

### 9. Тесты и проверка

- [ ] Запустить полный набор unit/regression-тестов.
- [ ] Выполнить smoke-test запуска FastAPI-приложения.
- [ ] Проверить, что все основные HTML-страницы успешно открываются.
- [ ] Проверить изменённые API endpoints с валидными и невалидными payload.
- [ ] Перед выпуском beta-сборки зафиксировать известные пробелы в тестах, если они есть.

### 10. Упаковка и выпуск

- [x] Обновить `APP_VERSION` в `main.py`.
- [x] Обновить cache-busting версии в templates и static-ссылках.
- [x] Обновить имя PyInstaller spec-файла и имя `.exe`, если меняется версия.
- [ ] Собрать Windows-пакет.
- [ ] Запустить собранный `.exe` и проверить минимум `/`, `/schedule`, `/settings`.
- [x] Обновить `BETA_CHANGELOG.md`: дата, версия, изменения, проверки, известные проблемы.
- [ ] Поставить tag или явно отметить выпущенную beta-сборку.

### 11. Критерии готовности

- [ ] Нет критических runtime-ошибок в основном workflow.
- [ ] Нет известных рисков потери данных без backup или recovery-пути.
- [ ] Regression-тесты проходят.
- [ ] Упакованное приложение успешно запускается.
- [ ] Changelog и список задач актуальны.
