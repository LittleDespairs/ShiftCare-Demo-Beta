/* =========================================================
           PAGE DATA / ДАННЫЕ СТРАНИЦЫ
           ========================================================= */

        // Weekday names / Названия дней недели
        // They are taken from translations when possible.
        // По возможности берём их из переводов.
        const WEEKDAY_KEYS = [
            "weekday_sunday",
            "weekday_monday",
            "weekday_tuesday",
            "weekday_wednesday",
            "weekday_thursday",
            "weekday_friday",
            "weekday_saturday"
        ];

        // Logical categories of shifts / Логические категории смен
        const SHIFT_CATEGORIES = [
            ["morning", "Morning"],
            ["evening", "Evening"],
            ["night", "Night"]
        ];

        // Cached data from backend / Кэшированные данные из backend
        let allEmployees = [];
        let allPositions = [];
        let allAssignments = [];
        let allScheduleEntries = [];
        let allRequirements = [];
        let allCoverageRequirements = [];
        let appSettings = {};
        let allShiftTemplates = [];
        let allDayStatuses = [];
        let weekDates = [];
        let pendingShiftTarget = null;
        let pendingStatusTarget = null;
        let lastGenerationSummary = null;
        let selectedGenerationMode = "balanced";
        let scheduleDataLoaded = false;
        let scheduleEmployeeFilters = {
            search: "",
            mode: "",
        };
        const LOCAL_COVERAGE_DISPLAY_MODE_PREFIX = "schedule_app_coverage_display_mode";
        const LOCAL_CARD_DISPLAY_MODE_PREFIX = "schedule_app_card_display_mode";

        function isDemoMode() {
            return document.body?.dataset?.demoMode === "1";
        }

        function demoRestrictionText() {
            return t("demo_restricted_message", "This feature is disabled in ShiftCare Demo.");
        }

        function showDemoRestriction() {
            showMessage(demoRestrictionText(), "warning");
        }

        /* =========================================================
           PAGE INIT / ИНИЦИАЛИЗАЦИЯ СТРАНИЦЫ
           ========================================================= */
        document.addEventListener("DOMContentLoaded", async () => {
            applyHostedWebScheduleMode();
            setDefaultWeekStart();
            bindPageButtons();
            bindShiftPicker();
            bindStatusPicker();
            bindSidebarToggle();
            bindScheduleActionModals();
            bindScheduleFloatingHeader();
            bindScheduleEmployeeFilters();

            // Apply remembered sidebar state / Применяем сохранённое состояние sidebar
            applySidebarState(getSavedSidebarState());
            if (isDemoMode()) {
                showMessage(
                    t(
                        "demo_schedule_notice",
                        "ShiftCare Demo includes sample data. Generation, export, and schedule cleanup are available; backup, cloud sync, updates, and license activation are disabled."
                    ),
                    "info"
                );
            }

            // Load initial settings and reference data / Загружаем настройки и справочники
            await Promise.all([
                loadPositions(),
                loadScheduleDisplaySetting()
            ]);
            if (isEmployeeUser() && document.getElementById("position_select").value) {
                await loadSchedulePageData({ showLoadedMessage: false });
            }
        });

        // Re-render parts that depend on language / Перерисовка частей, зависящих от языка
        document.addEventListener("app-language-changed", () => {
            const positionId = Number(document.getElementById("position_select").value);
            if (weekDates.length > 0 && positionId) {
                renderScheduleTable(positionId);
            } else {
                renderScheduleInitialState();
            }
            if (lastGenerationSummary) {
                renderGenerationSummary(lastGenerationSummary);
            }
            updateScheduleBoardRange();
            updateScheduleInspector();
            updateScheduleActionAvailability();
            syncScheduleFloatingHeader();
        });

        /* =========================================================
           SIDEBAR STATE / СОСТОЯНИЕ БОКОВОГО МЕНЮ
           ========================================================= */

        function getSavedSidebarState() {
            // Read saved sidebar mode / Читаем сохранённый режим меню
            return localStorage.getItem("scheduleAppSidebar");
        }

        function applySidebarState(state) {
            // Reset old classes first / Сначала сбрасываем старые классы
            document.body.classList.remove("sidebar-collapsed", "mobile-sidebar-hidden");

            // On mobile the sidebar defaults to a compact header / На мобильных меню по умолчанию компактное
            if (window.innerWidth <= 920) {
                if (state !== "expanded") {
                    document.body.classList.add("mobile-sidebar-hidden");
                }
                return;
            }

            // On desktop we only collapse it / На десктопе мы только сворачиваем меню
            if (state === "collapsed") {
                document.body.classList.add("sidebar-collapsed");
            }
        }

        function toggleSidebar() {
            // Different behavior for desktop and mobile / Разное поведение для десктопа и мобильных
            if (window.innerWidth <= 920) {
                const hiddenNow = document.body.classList.contains("mobile-sidebar-hidden");
                const nextState = hiddenNow ? "expanded" : "hidden";
                localStorage.setItem("scheduleAppSidebar", nextState);
                applySidebarState(nextState);
                return;
            }

            const collapsedNow = document.body.classList.contains("sidebar-collapsed");
            const nextState = collapsedNow ? "expanded" : "collapsed";
            localStorage.setItem("scheduleAppSidebar", nextState);
            applySidebarState(nextState);
        }

        function bindSidebarToggle() {
            // Bind sidebar toggle button / Привязываем кнопку сворачивания меню
            const button = document.getElementById("sidebar-toggle");
            if (!button) return;

            button.addEventListener("click", toggleSidebar);

            window.addEventListener("resize", () => {
                applySidebarState(getSavedSidebarState());
            });
        }

        /* =========================================================
           BASIC HELPERS / БАЗОВЫЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
           ========================================================= */

        function t(key, fallback = "") {
            // Safe translation helper / Безопасный помощник перевода
            if (typeof translate === "function") {
                return translate(key);
            }
            return fallback || key;
        }

        function isHostedWebScheduleMode() {
            return Boolean(window.scheduleAuth?.isHostedCloudOrigin?.());
        }

        function shouldShowCoverageInSchedule() {
            return !isHostedWebScheduleMode();
        }

        function applyHostedWebScheduleMode() {
            if (!isHostedWebScheduleMode()) return;
            document.body.classList.add("hosted-employee-schedule");
            document.querySelectorAll("[data-web-hide='coverage']").forEach(element => {
                element.hidden = true;
            });
        }

        function formatDate(dateObject) {
            // Format JS Date to YYYY-MM-DD / Форматируем дату в YYYY-MM-DD
            return dateObject.toISOString().split("T")[0];
        }

        function buildWeekDates(weekStart) {
            // Build 7 dates starting from selected week start
            // Строим 7 дат, начиная с выбранного начала недели
            const base = new Date(weekStart);
            const dates = [];

            for (let i = 0; i < 7; i++) {
                const current = new Date(base);
                current.setDate(base.getDate() + i);
                dates.push(formatDate(current));
            }

            return dates;
        }

        function setDefaultWeekStart() {
            // Default week starts from Sunday in this project
            // В этом проекте неделя начинается с воскресенья
            const input = document.getElementById("week_start");
            const today = new Date();
            const day = today.getDay(); // Sunday = 0
            today.setDate(today.getDate() - day);
            input.value = formatDate(today);
            window.refreshWeekPicker?.(input);
        }

        function capitalizeFirstLetter(text) {
            // Simple helper for display / Простой helper для отображения
            if (!text) return "";
            return text.charAt(0).toUpperCase() + text.slice(1);
        }

        function escapeHtml(value) {
            if (value === null || value === undefined) return "";
            return String(value)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#39;");
        }

        function getActiveMembership() {
            return window.scheduleAuth?.getActiveMembership?.() || null;
        }

        function canEditSchedule() {
            const role = getActiveMembership()?.role;
            if (!role || !window.scheduleAccessControl?.accessForRole) {
                return true;
            }
            return Boolean(window.scheduleAccessControl.accessForRole(role).canEditSchedule);
        }

        function isEmployeeUser() {
            return getActiveMembership()?.role === "employee";
        }

        function getUserScopedStorageKey(prefix) {
            const userId = window.scheduleAuth?.getUser?.()?.id || "local";
            return `${prefix}_${userId}`;
        }

        function formatConfirmImpactList(items) {
            const rows = items
                .filter(item => item && item.label)
                .map(item => `<li><strong>${escapeHtml(item.label)}:</strong> ${escapeHtml(item.value ?? 0)}</li>`)
                .join("");
            return rows ? `<ul>${rows}</ul>` : "";
        }

        function formatApiError(errorValue) {
            // Convert backend error payload to readable HTML text
            // Преобразуем ответ backend с ошибкой в понятный HTML-текст

            if (errorValue === null || errorValue === undefined) {
                return "";
            }

            if (typeof errorValue === "string") {
                return escapeHtml(errorValue);
            }

            if (Array.isArray(errorValue)) {
                return errorValue.map(item => formatApiError(item)).join("<br>");
            }

            if (typeof errorValue === "object") {
                // FastAPI validation error item example:
                // { loc: [...], msg: "...", type: "..." }
                if (errorValue.msg) {
                    if (Array.isArray(errorValue.loc) && errorValue.loc.length > 0) {
                        return `${escapeHtml(errorValue.loc.join(" → "))}: ${escapeHtml(errorValue.msg)}`;
                    }
                    return escapeHtml(errorValue.msg);
                }

                if (errorValue.detail) {
                    return formatApiError(errorValue.detail);
                }

                try {
                    return escapeHtml(JSON.stringify(errorValue, null, 2));
                } catch {
                    return escapeHtml(String(errorValue));
                }
            }

            return escapeHtml(String(errorValue));
        }

        function localizeGenerationWarning(text) {
            if (!text) return "";
            let value = String(text);

            const replacements = [
                [/No active coverage slots for this week/g, t("generation_warning_no_active_slots_week", "No active coverage slots for this week")],
                [/No active coverage slots for ([0-9-]+)/g, (_match, date) => `${date}: ${t("generation_warning_no_active_slots_day", "No active coverage slots for this day")}`],
                [/Pre-check blocking:/g, t("generation_precheck_blocking", "Pre-check blocking:")],
                [/Pre-check warning:/g, t("generation_precheck_warning", "Pre-check warning:")],
                [/No active coverage slots can be built from coverage requirements\./g, t("generation_precheck_no_slots", "No active coverage slots can be built from coverage requirements.")],
                [/No active shift template covers this required interval\./g, t("generation_precheck_no_template", "No active shift template covers this required interval.")],
                [/No active template exists for this legacy shift requirement\./g, t("generation_precheck_no_legacy_template", "No active template exists for this legacy shift requirement.")],
                [/Required staff is greater than employees assigned to the position\./g, t("generation_precheck_staff_shortage", "Required staff is greater than employees assigned to the position.")],
                [/Required female staff is greater than available female employees\./g, t("generation_precheck_female_shortage", "Required female staff is greater than available female employees.")],
                [/Required male staff is greater than available male employees\./g, t("generation_precheck_male_shortage", "Required male staff is greater than available male employees.")],
                [/No eligible employee\/template candidate can cover this interval\./g, t("generation_precheck_no_candidate", "No eligible employee/template candidate can cover this interval.")],
                [/This interval is only coverable with emergency fatigue relaxation\./g, t("generation_precheck_emergency_only", "This interval is only coverable with emergency fatigue relaxation.")],
                [/emergency fatigue relaxation was used to cover a slot/g, t("generation_warning_emergency_fatigue", "emergency fatigue relaxation was used to cover a slot")],
                [/underfilled/g, t("generation_warning_underfilled", "underfilled")],
                [/Reasons:/g, t("generation_warning_reasons", "Reasons:")],
                [/not enough female employees available/g, t("generation_reason_not_enough_female", "not enough female employees available")],
                [/not enough male employees available/g, t("generation_reason_not_enough_male", "not enough male employees available")],
                [/day status blocks employee/g, t("generation_reason_day_status", "day status blocks employee")],
                [/employee is not assigned to this position/g, t("generation_reason_not_assigned", "employee is not assigned to this position")],
                [/employee reached max shifts/g, t("generation_reason_max_shifts", "employee reached max shifts")],
                [/employee reached weekly maximum shifts/g, t("generation_reason_weekly_max_shifts", "employee reached weekly maximum shifts")],
                [/employee preferences or permissions block this shift/g, t("generation_reason_preference_or_permission", "employee preferences or permissions block this shift")],
                [/mandatory weekly day off would be violated/g, t("generation_reason_mandatory_day_off", "mandatory weekly day off would be violated")],
                [/employee already has an overlapping shift/g, t("generation_reason_overlapping_shift", "employee already has an overlapping shift")],
                [/employee cannot work morning and evening on the same day/g, t("generation_reason_cannot_split_day", "employee cannot work morning and evening on the same day")],
                [/employee already has another shift type that cannot be paired/g, t("generation_reason_unpairable_shift_type", "employee already has another shift type that cannot be paired")],
                [/same-day work with other positions is not allowed for one of the positions/g, t("generation_reason_cross_position_day", "same-day work with other positions is not allowed for one of the positions")],
                [/weekly preference blocks morning-evening combo/g, t("generation_reason_weekly_preference_split", "weekly preference blocks morning-evening combo")],
                [/employee already has two shifts that day/g, t("generation_reason_two_shifts_day", "employee already has two shifts that day")],
                [/employee requested off or vacation/g, t("generation_reason_off_or_vacation", "employee requested off or vacation")],
                [/shift conflicts with employee preference/g, t("generation_reason_preference_conflict", "shift conflicts with employee preference")],
                [/morning after night is forbidden/g, t("generation_reason_morning_after_night", "morning after night is forbidden")],
                [/not enough rest after night before evening/g, t("generation_reason_night_evening_rest", "not enough rest after night before evening")],
                [/not enough rest between morning and evening/g, t("generation_reason_morning_evening_rest", "not enough rest between morning and evening")],
                [/daily work limit exceeded/g, t("generation_reason_daily_work_limit", "daily work limit exceeded")],
                [/weekly day off would be violated/g, t("generation_reason_weekly_day_off", "weekly day off would be violated")],
                [/consecutive night limit reached/g, t("generation_reason_consecutive_nights", "consecutive night limit reached")],
                [/consecutive split limit reached/g, t("generation_reason_consecutive_splits", "consecutive split limit reached")],
                [/too many consecutive night shifts/g, t("generation_reason_too_many_consecutive_nights", "too many consecutive night shifts")],
                [/too many consecutive split shifts/g, t("generation_reason_too_many_consecutive_splits", "too many consecutive split shifts")],
                [/candidates existed, but they did not improve coverage without overfilling other intervals/g, t("generation_reason_no_coverage_gain", "candidates existed, but they did not improve coverage without overfilling other intervals")]
            ];

            replacements.forEach(([pattern, replacement]) => {
                value = value.replace(pattern, replacement);
            });

            value = value.replace(
                /([A-Za-zА-Яа-я\u0590-\u05FF .'_-]+) has (\d+) worked days in the week; mandatory weekly day off is violated/g,
                (_match, name, count) => `${name} ${t("generation_warning_worked_days", "has worked days without a mandatory weekly day off")}: ${count}`
            );
            value = value.replace(
                /([A-Za-zА-Яа-я\u0590-\u05FF .'_-]+) has (\d+) consecutive night days; normal limit is (\d+)/g,
                (_match, name, count, limit) => `${name}: ${t("generation_warning_consecutive_nights", "consecutive night days")}: ${count} / ${limit}`
            );
            value = value.replace(
                /([A-Za-zА-Яа-я\u0590-\u05FF .'_-]+) has (\d+) consecutive split days; normal limit is (\d+)/g,
                (_match, name, count, limit) => `${name}: ${t("generation_warning_consecutive_splits", "consecutive split days")}: ${count} / ${limit}`
            );

            return escapeHtml(value);
        }

        function formatGenerationWarnings(errors) {
            if (!Array.isArray(errors)) {
                return formatApiError(errors);
            }

            return errors.map(item => localizeGenerationWarning(item)).join("<br>");
        }

        function getLocalizedFeasibilityStatus(status) {
            const value = String(status || "ok").toLowerCase();
            const mapping = {
                ok: t("generation_feasibility_status_ok", "OK"),
                blocking: t("generation_feasibility_status_blocking", "Blocking")
            };
            return mapping[value] || capitalizeFirstLetter(value);
        }


        function getWeekdayName(index) {
            // Get translated weekday name / Получаем переведённое название дня недели
            const key = WEEKDAY_KEYS[index];
            return t(key, ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][index]);
        }

        function getScheduleLocale() {
            const lang = localStorage.getItem("scheduleAppLanguage") || document.documentElement.lang || "en";
            if (lang === "he") return "he-IL";
            if (lang === "ru") return "ru-RU";
            return "en-US";
        }

        function formatBoardDate(value, options = {}) {
            const date = new Date(`${value}T00:00:00`);
            return new Intl.DateTimeFormat(getScheduleLocale(), {
                day: "2-digit",
                month: "short",
                ...(options.year ? { year: "numeric" } : {})
            }).format(date);
        }

        function getBoardWeekDates() {
            if (weekDates.length > 0) return weekDates;
            const weekStart = document.getElementById("week_start")?.value;
            return weekStart ? buildWeekDates(weekStart) : [];
        }

        function updateScheduleBoardRange() {
            const title = document.getElementById("schedule-board-range");
            if (!title) return;
            const dates = getBoardWeekDates();
            if (dates.length === 0) {
                title.textContent = t("schedule_board_empty_range", "No week selected");
                return;
            }
            const start = dates[0];
            const end = dates[dates.length - 1];
            const sameYear = start.slice(0, 4) === end.slice(0, 4);
            title.textContent = `${formatBoardDate(start, { year: !sameYear })} - ${formatBoardDate(end, { year: true })}`;
        }

        /* =========================================================
           MESSAGE UI / СООБЩЕНИЯ НА СТРАНИЦЕ
           ========================================================= */

        function showMessage(text, type = "info") {
            // Render a styled message / Показываем аккуратное сообщение
            renderPageMessage("message-box", text, type, { html: true });
        }

        function clearMessage() {
            // Clear current message / Очищаем текущее сообщение
            document.getElementById("message-box").innerHTML = "";
            clearGenerationSummary();
        }

        function clearGenerationSummary() {
            const section = document.getElementById("generation-summary-section");
            const content = document.getElementById("generation-summary-content");
            if (content) {
                content.innerHTML = "";
            }
            if (section) {
                section.hidden = true;
            }
            lastGenerationSummary = null;
            updateScheduleInspector();
        }

        function bindScheduleFloatingHeader() {
            const shell = document.querySelector(".schedule-shell");
            if (shell) {
                shell.addEventListener("scroll", syncScheduleFloatingHeader, { passive: true });
            }
            window.addEventListener("scroll", syncScheduleFloatingHeader, { passive: true });
            window.addEventListener("resize", syncScheduleFloatingHeader);
        }

        function syncScheduleFloatingHeader() {
            const floatingHeader = document.getElementById("schedule-floating-header");
            const floatingThead = document.getElementById("schedule-floating-thead");
            const shell = document.querySelector(".schedule-shell");
            const table = shell ? shell.querySelector(".schedule-table") : null;
            const sourceThead = document.getElementById("schedule-thead");
            if (!floatingHeader || !floatingThead || !shell || !table || !sourceThead || !sourceThead.innerHTML.trim()) {
                if (floatingHeader) {
                    floatingHeader.hidden = true;
                    floatingHeader.classList.remove("is-visible");
                }
                return;
            }

            if (floatingThead.innerHTML !== sourceThead.innerHTML) {
                floatingThead.innerHTML = sourceThead.innerHTML;
            }

            const shellRect = shell.getBoundingClientRect();
            const headerHeight = sourceThead.offsetHeight || 0;
            const shouldShow = shellRect.top < 0 && shellRect.bottom - headerHeight > 0;

            if (!shouldShow) {
                floatingHeader.hidden = true;
                floatingHeader.classList.remove("is-visible");
                return;
            }

            const floatingScroller = document.getElementById("schedule-floating-header-scroller");
            const floatingTable = floatingHeader.querySelector(".schedule-floating-table");
            if (!floatingScroller || !floatingTable) {
                return;
            }

            floatingHeader.hidden = false;
            floatingHeader.classList.add("is-visible");
            floatingHeader.style.left = `${Math.max(shellRect.left, 0)}px`;
            floatingHeader.style.width = `${Math.min(shellRect.width, window.innerWidth)}px`;
            floatingTable.style.width = `${table.offsetWidth}px`;
            floatingTable.style.transform = `translateX(${-shell.scrollLeft}px)`;
            floatingScroller.style.height = `${headerHeight}px`;
        }

        function formatGenerationIssueText(issue) {
            if (!issue) return "";
            const parts = [];
            if (issue.date) {
                parts.push(issue.date);
            }
            if (issue.slot && issue.slot.start && issue.slot.end) {
                parts.push(`${issue.slot.start}-${issue.slot.end}`);
            }
            if (issue.shift_category) {
                parts.push(capitalizeFirstLetter(issue.shift_category));
            }

            const prefix = parts.length > 0 ? `${parts.join(" · ")}: ` : "";
            return localizeGenerationWarning(`${prefix}${issue.message || ""}`);
        }

        function formatUnfilledReportText(report) {
            if (!report) return "";

            if (report.kind === "interval") {
                const prefix = `${report.date} · ${report.slot.start}-${report.slot.end}`;
                const missing = `${t("generation_missing_total", "Missing total")}: ${Number(report.missing.total)}; `
                    + `${t("generation_missing_female", "Missing female")}: ${Number(report.missing.female)}; `
                    + `${t("generation_missing_male", "Missing male")}: ${Number(report.missing.male)}`;
                const reasons = report.reasons ? ` ${t("generation_reasons", "Reasons")}: ${localizeGenerationWarning(report.reasons)}` : "";
                return `${escapeHtml(prefix)} - ${escapeHtml(missing)}${reasons}`;
            }

            const prefix = `${report.date} · ${capitalizeFirstLetter(report.shift_category || report.kind || "")}`;
            const missing = `${t("generation_missing_total", "Missing total")}: ${Number(report.missing.total)}; `
                + `${t("generation_missing_female", "Missing female")}: ${Number(report.missing.female)}; `
                + `${t("generation_missing_male", "Missing male")}: ${Number(report.missing.male)}`;
            const reasons = report.reasons ? ` ${t("generation_reasons", "Reasons")}: ${localizeGenerationWarning(report.reasons)}` : "";
            return `${escapeHtml(prefix)} - ${escapeHtml(missing)}${reasons}`;
        }

        function renderGenerationSummary(summary) {
            const section = document.getElementById("generation-summary-section");
            const content = document.getElementById("generation-summary-content");
            if (!section || !content || !summary || !summary.result) {
                return;
            }

            const result = summary.result;
            const hardConstraints = (result.feasibility_report && result.feasibility_report.hard_constraints) || [];
            const softConstraints = (result.feasibility_report && result.feasibility_report.soft_constraints) || [];
            const unfilledReports = result.unfilled_reports || [];
            const warnings = result.errors || [];
            const selectedPosition = allPositions.find(item => item.id === summary.positionId);

            const stats = [
                {
                    label: t("msg_created_count", "Created"),
                    value: Number(result.created_count || 0),
                    note: t("generation_created_note", "New schedule entries added by auto-generation.")
                },
                {
                    label: t("msg_optimization_moved", "Optimized moves"),
                    value: Number(result.optimization_moved_count || 0),
                    note: t("generation_optimized_note", "Existing generated entries reassigned for a better balance.")
                },
                {
                    label: t("generation_day_off_count", "Generated day off"),
                    value: Number(result.day_off_count || 0),
                    note: t("generation_day_off_note", "Automatic day-off statuses created for uncovered employee days.")
                },
                {
                    label: t("generation_hard_constraints", "Hard constraints"),
                    value: hardConstraints.length,
                    note: t("generation_hard_note", "Blocking issues found by the pre-check.")
                },
                {
                    label: t("generation_soft_constraints", "Soft constraints"),
                    value: softConstraints.length,
                    note: t("generation_soft_note", "Warnings that still allowed generation to continue.")
                },
                {
                    label: t("generation_unfilled_count", "Unfilled requirements"),
                    value: unfilledReports.length,
                    note: t("generation_unfilled_note", "Coverage gaps that remained after generation.")
                }
            ];

            const sections = [];

            sections.push(`
                <div class="generation-section-card ${warnings.length > 0 || unfilledReports.length > 0 || hardConstraints.length > 0 ? "warning" : "success"}">
                    <h4 class="generation-section-title">${t("generation_run_overview", "Run overview")}</h4>
                    <div class="generation-summary-muted">
                        ${escapeHtml(t("generation_summary_week", "Week"))}: ${escapeHtml(summary.weekStart)}
                        <br>
                        ${escapeHtml(t("generation_summary_position", "Position"))}: ${escapeHtml(selectedPosition ? selectedPosition.name : String(summary.positionId))}
                        <br>
                        ${escapeHtml(t("schedule_generation_mode", "Generation"))}: ${escapeHtml(getGenerationModeLabel(summary.generationMode || result.generation_mode))}
                        <br>
                        ${escapeHtml(t("generation_summary_status", "Feasibility status"))}: ${escapeHtml(getLocalizedFeasibilityStatus(result.feasibility_report && result.feasibility_report.status))}
                    </div>
                </div>
            `);

            if (hardConstraints.length > 0) {
                sections.push(`
                    <div class="generation-section-card danger">
                        <h4 class="generation-section-title">${t("generation_hard_constraints", "Hard constraints")}</h4>
                        <ul class="generation-section-list">
                            ${hardConstraints.map(issue => `<li>${formatGenerationIssueText(issue)}</li>`).join("")}
                        </ul>
                    </div>
                `);
            }

            if (softConstraints.length > 0) {
                sections.push(`
                    <div class="generation-section-card warning">
                        <h4 class="generation-section-title">${t("generation_soft_constraints", "Soft constraints")}</h4>
                        <ul class="generation-section-list">
                            ${softConstraints.map(issue => `<li>${formatGenerationIssueText(issue)}</li>`).join("")}
                        </ul>
                    </div>
                `);
            }

            if (unfilledReports.length > 0) {
                sections.push(`
                    <div class="generation-section-card warning">
                        <h4 class="generation-section-title">${t("generation_unfilled_title", "Remaining unfilled requirements")}</h4>
                        <ul class="generation-section-list">
                            ${unfilledReports.map(report => `<li>${formatUnfilledReportText(report)}</li>`).join("")}
                        </ul>
                    </div>
                `);
            }

            if (warnings.length > 0) {
                sections.push(`
                    <div class="generation-section-card warning">
                        <h4 class="generation-section-title">${t("msg_warnings", "Warnings")}</h4>
                        <ul class="generation-section-list">
                            ${warnings.map(item => `<li>${localizeGenerationWarning(item)}</li>`).join("")}
                        </ul>
                    </div>
                `);
            }

            if (sections.length === 1) {
                sections.push(`
                    <div class="generation-section-card success">
                        <h4 class="generation-section-title">${t("generation_summary_clean_title", "Clean generation result")}</h4>
                        <div class="generation-summary-muted">
                            ${escapeHtml(t("generation_summary_clean_text", "The run finished without warnings, hard blockers, or remaining uncovered requirements."))}
                        </div>
                    </div>
                `);
            }

            content.innerHTML = `
                <div class="generation-summary-grid">
                    ${stats.map(stat => `
                        <div class="generation-stat">
                            <div class="generation-stat-label">${escapeHtml(stat.label)}</div>
                            <div class="generation-stat-value">${escapeHtml(stat.value)}</div>
                            <div class="generation-stat-note">${escapeHtml(stat.note)}</div>
                        </div>
                    `).join("")}
                </div>
                <div class="generation-sections">
                    ${sections.join("")}
                </div>
            `;
            section.hidden = false;
            updateScheduleInspector();
        }

        /* =========================================================
           BUTTON BINDINGS / ПРИВЯЗКА КНОПОК
           ========================================================= */

        function bindPageButtons() {
            // Main action buttons / Основные кнопки страницы
            document.getElementById("load-btn").addEventListener("click", () => {
                loadSchedulePageData({ showLoadedMessage: false });
            });
            document.getElementById("auto-generate-btn").addEventListener("click", autoGenerateSchedule);
            document.getElementById("auto-generate-all-btn").addEventListener("click", autoGenerateAllSchedules);
            document.getElementById("clear-week-btn").addEventListener("click", clearWeekSchedule);
            document.getElementById("clear-all-week-btn").addEventListener("click", clearAllWeekSchedules);
            document.getElementById("export-excel-btn").addEventListener("click", exportScheduleExcel);
            document.getElementById("export-all-excel-btn").addEventListener("click", exportAllSchedulesExcel);
            document.getElementById("export-word-btn").addEventListener("click", exportScheduleWord);
            document.getElementById("export-all-word-btn").addEventListener("click", exportAllSchedulesWord);
            document.getElementById("clear-message-btn").addEventListener("click", clearMessage);
            document.getElementById("schedule_coverage_display_mode").addEventListener("change", saveScheduleDisplayMode);
            document.getElementById("schedule_card_display_mode").addEventListener("change", saveScheduleCardDisplayMode);
            document.getElementById("generation-summary-clear-btn").addEventListener("click", clearGenerationSummary);
            document.getElementById("week_start").addEventListener("change", handleScheduleContextChanged);
            document.getElementById("position_select").addEventListener("change", handleScheduleContextChanged);
            document.querySelectorAll("[data-generation-view]").forEach(button => {
                button.addEventListener("click", () => {
                    selectedGenerationMode = getGenerationModeFromButton(button);
                    document.querySelectorAll("[data-generation-view]").forEach(item => {
                        item.classList.toggle("is-active", item === button);
                    });
                });
            });
        }

        function getGenerationModeFromButton(button) {
            const mode = button?.dataset?.generationView || "balanced";
            return ["balanced", "coverage", "requests"].includes(mode) ? mode : "balanced";
        }

        function getSelectedGenerationMode() {
            const activeButton = document.querySelector("[data-generation-view].is-active");
            selectedGenerationMode = getGenerationModeFromButton(activeButton);
            return selectedGenerationMode;
        }

        function getGenerationModeLabel(mode) {
            if (mode === "coverage") {
                return t("schedule_generation_coverage_first", "Coverage first");
            }
            if (mode === "requests") {
                return t("schedule_generation_requests_first", "Requests first");
            }
            return t("schedule_generation_balanced", "Balanced");
        }

        function handleScheduleContextChanged() {
            weekDates = [];
            scheduleDataLoaded = false;
            clearGenerationSummary();
            renderScheduleInitialState();
        }

        function normalizeScheduleFilterText(value) {
            return String(value || "").toLowerCase().trim();
        }

        function scheduleFilterCountText(shown, total) {
            return t("common_filter_results", "Showing {shown} of {total}")
                .replace("{shown}", String(shown))
                .replace("{total}", String(total));
        }

        function bindScheduleEmployeeFilters() {
            const searchInput = document.getElementById("schedule_employee_search");
            const modeSelect = document.getElementById("schedule_employee_filter_mode");
            const resetButton = document.getElementById("schedule-filter-reset");

            searchInput?.addEventListener("input", () => {
                scheduleEmployeeFilters.search = searchInput.value;
                rerenderScheduleIfLoaded();
            });
            modeSelect?.addEventListener("change", () => {
                scheduleEmployeeFilters.mode = modeSelect.value;
                rerenderScheduleIfLoaded();
            });
            resetButton?.addEventListener("click", () => {
                scheduleEmployeeFilters = { search: "", mode: "" };
                if (searchInput) searchInput.value = "";
                if (modeSelect) {
                    modeSelect.value = "";
                    if (typeof refreshSelectTrigger === "function") {
                        refreshSelectTrigger(modeSelect);
                    }
                }
                rerenderScheduleIfLoaded();
            });
        }

        function rerenderScheduleIfLoaded() {
            const positionId = Number(document.getElementById("position_select").value);
            if (scheduleDataLoaded && weekDates.length > 0 && positionId) {
                renderScheduleTable(positionId);
            }
        }

        function bindScheduleActionModals() {
            document.querySelectorAll("[data-action-modal]").forEach(button => {
                button.addEventListener("click", () => {
                    openScheduleActionModal(button.dataset.actionModal);
                });
            });

            document.querySelectorAll(".schedule-action-modal-overlay").forEach(modal => {
                modal.addEventListener("click", event => {
                    if (event.target === modal || event.target.closest("[data-close-action-modal]")) {
                        closeScheduleActionModal(modal);
                    }
                });
            });

            document.querySelectorAll(".schedule-action-option").forEach(button => {
                button.addEventListener("click", () => {
                    const modal = button.closest(".schedule-action-modal-overlay");
                    if (modal) {
                        closeScheduleActionModal(modal);
                    }
                });
            });

            document.addEventListener("keydown", event => {
                if (event.key !== "Escape") return;
                const openModal = document.querySelector(".schedule-action-modal-overlay.is-open");
                if (openModal) {
                    closeScheduleActionModal(openModal);
                }
            });
        }

        function openScheduleActionModal(modalId) {
            if (!canEditSchedule() && ["generation-actions-modal", "danger-actions-modal"].includes(modalId)) {
                return;
            }
            const modal = document.getElementById(modalId);
            if (!modal) return;
            modal.classList.add("is-open");
            modal.setAttribute("aria-hidden", "false");
            const firstEnabledButton = modal.querySelector("button:not([disabled])");
            if (firstEnabledButton) {
                firstEnabledButton.focus();
            }
        }

        function closeScheduleActionModal(modal) {
            modal.classList.remove("is-open");
            modal.setAttribute("aria-hidden", "true");
        }

        function renderScheduleWorkspaceEmptyState(options = {}) {
            return typeof renderEmptyState === "function"
                ? renderEmptyState(options)
                : escapeHtml(options.text || "");
        }

        function renderScheduleInitialState() {
            const tbody = document.getElementById("schedule-tbody");
            const thead = document.getElementById("schedule-thead");
            const hasPositions = allPositions.length > 0;
            const actionHtml = hasPositions
                ? ""
                : `<a class="btn btn-secondary" href="/positions">${t("common_open_positions", "Open positions")}</a>`;

            scheduleDataLoaded = false;
            thead.innerHTML = "";
            tbody.innerHTML = `
                <tr>
                    <td style="padding:24px;">
                        ${renderScheduleWorkspaceEmptyState({
                            title: hasPositions ? "" : t("schedule_no_positions_title", "Schedule needs positions"),
                            text: t(
                                hasPositions ? "schedule_initial_hint" : "schedule_no_positions_text",
                                hasPositions
                                    ? "Select a week and a position, then load the schedule."
                                    : "Create at least one position before loading or generating a weekly schedule."
                            ),
                            actionHtml
                        })}
                    </td>
                </tr>
            `;
            updateScheduleActionAvailability();
            updateScheduleBoardRange();
            updateScheduleStatusStrip();
            updateScheduleInspector();
            updateScheduleFilterCount(0, 0);
            syncScheduleFloatingHeader();
        }

        function getVisibleScheduleEntries(positionId) {
            const weekDateSet = new Set(weekDates);
            return allScheduleEntries.filter(entry =>
                entry.position_id === positionId &&
                weekDateSet.has(entry.date) &&
                !entry.no_show
            );
        }

        function employeeHasVisibleWeekShift(employeeId, positionId) {
            return getVisibleScheduleEntries(positionId).some(entry => entry.employee_id === employeeId);
        }

        function getFilteredScheduleEmployees(employeesForPosition, positionId) {
            const query = normalizeScheduleFilterText(scheduleEmployeeFilters.search);
            const mode = scheduleEmployeeFilters.mode;

            return employeesForPosition.filter(employee => {
                const haystack = normalizeScheduleFilterText([
                    employee.id,
                    employee.id_card,
                    employee.full_name,
                    employee.sex,
                ].join(" "));
                if (query && !haystack.includes(query)) return false;

                const hasShift = employeeHasVisibleWeekShift(employee.id, positionId);
                if (mode === "with_shifts" && !hasShift) return false;
                if (mode === "without_shifts" && hasShift) return false;
                return true;
            });
        }

        function updateScheduleFilterCount(shown, total) {
            const count = document.getElementById("schedule-filter-count");
            if (!count) return;
            count.textContent = total ? scheduleFilterCountText(shown, total) : "";
        }

        function countVisibleCoverageGaps(positionId) {
            if (!weekDates.length || !positionId) {
                return 0;
            }

            const coverageRequirements = getCoverageRequirementsForPosition(positionId);
            if (coverageRequirements.length > 0) {
                return weekDates.reduce((count, date) => {
                    return count + coverageRequirements.filter(requirement => {
                        const stats = getIntervalCoverageStats(positionId, date, requirement);
                        return getCoverageClass(stats, requirement) === "danger";
                    }).length;
                }, 0);
            }

            const requirementMap = getRequirementMapForPosition(positionId);
            return weekDates.reduce((count, date) => {
                return count + SHIFT_CATEGORIES.filter(([shiftCategory]) => {
                    const requirement = requirementMap[shiftCategory];
                    if (!requirement) {
                        return false;
                    }
                    const stats = getCoverageStats(positionId, date, shiftCategory);
                    return getCoverageClass(stats, requirement) === "danger";
                }).length;
            }, 0);
        }

        function updateScheduleStatusStrip() {
            const strip = document.getElementById("schedule-status-strip");
            if (!strip) return;

            const positionId = Number(document.getElementById("position_select").value);
            const selectedPosition = allPositions.find(item => item.id === positionId);
            const coverageMode = appSettings.schedule_coverage_display_mode === "category"
                ? t("coverage_display_category", "By shift categories")
                : t("coverage_display_interval", "By time intervals");
            const gapCount = scheduleDataLoaded && positionId && weekDates.length > 0
                ? countVisibleCoverageGaps(positionId)
                : 0;
            const coverageValue = !scheduleDataLoaded || !positionId || weekDates.length === 0
                ? t("schedule_status_no_data", "Not loaded")
                : gapCount > 0
                    ? `${gapCount} ${t("schedule_status_gaps", "gaps")}`
                    : "OK";
            const publishBlocked = scheduleDataLoaded && gapCount > 0;

            const items = [
                {
                    label: t("schedule_status_week", "Week"),
                    value: getBoardWeekDates().length ? `${getBoardWeekDates()[0]} - ${getBoardWeekDates()[6]}` : "-"
                },
                {
                    label: t("schedule_status_position", "Position"),
                    value: selectedPosition ? selectedPosition.name : "-"
                },
                {
                    label: t("schedule_status_coverage", "Coverage"),
                    value: shouldShowCoverageInSchedule() ? `${coverageValue} · ${coverageMode}` : coverageValue
                },
                {
                    label: t("schedule_publish_status", "Publish"),
                    value: publishBlocked
                        ? t("schedule_publish_blocked", "Blocked")
                        : (scheduleDataLoaded ? t("schedule_publish_ready", "Ready") : t("schedule_status_no_data", "Not loaded"))
                }
            ];

            strip.innerHTML = items.map(item => `
                <div class="schedule-status-item">
                    <div class="schedule-status-label">${escapeHtml(item.label)}</div>
                    <div class="schedule-status-value" title="${escapeHtml(item.value)}">${escapeHtml(item.value)}</div>
                </div>
            `).join("");
            strip.classList.add("is-visible");
        }

        function renderInspectorRow(label, value, state = "neutral") {
            return `
                <div class="schedule-ledger-row ${state}">
                    <span>${escapeHtml(label)}</span>
                    <strong>${escapeHtml(value)}</strong>
                </div>
            `;
        }

        function updateScheduleInspector() {
            const ledger = document.getElementById("schedule-rule-ledger");
            const runLog = document.getElementById("schedule-run-log");
            if (!ledger || !runLog) return;

            const positionId = Number(document.getElementById("position_select").value);
            const selectedPosition = allPositions.find(item => item.id === positionId);
            const dates = getBoardWeekDates();

            if (!scheduleDataLoaded || !positionId || weekDates.length === 0) {
                ledger.innerHTML = renderInspectorRow(
                    t("schedule_status_coverage", "Coverage"),
                    t("schedule_status_no_data", "Not loaded"),
                    "neutral"
                );
                runLog.innerHTML = `
                    <div class="schedule-log-line">
                        <strong>${escapeHtml(t("schedule_waiting_log", "Load a week to see schedule activity."))}</strong>
                        <span>${escapeHtml(dates.length ? `${dates[0]} - ${dates[6]}` : "-")}</span>
                    </div>
                `;
                return;
            }

            const gapCount = countVisibleCoverageGaps(positionId);
            const hardCount = (lastGenerationSummary?.result?.feasibility_report?.hard_constraints || []).length;
            const softCount = (lastGenerationSummary?.result?.feasibility_report?.soft_constraints || []).length;
            const unfilledCount = (lastGenerationSummary?.result?.unfilled_reports || []).length;
            const visibleEntries = getVisibleScheduleEntries(positionId);

            ledger.innerHTML = [
                renderInspectorRow(
                    t("schedule_status_coverage", "Coverage"),
                    gapCount > 0 ? `${gapCount} ${t("schedule_status_gaps", "gaps")}` : "OK",
                    gapCount > 0 ? "critical" : "ok"
                ),
                renderInspectorRow(
                    t("generation_hard_constraints", "Hard constraints"),
                    hardCount > 0 ? String(hardCount) : "OK",
                    hardCount > 0 ? "critical" : "ok"
                ),
                renderInspectorRow(
                    t("generation_soft_constraints", "Soft constraints"),
                    softCount > 0 ? String(softCount) : "OK",
                    softCount > 0 ? "warning" : "ok"
                ),
                renderInspectorRow(
                    t("generation_unfilled_count", "Unfilled requirements"),
                    unfilledCount > 0 ? String(unfilledCount) : "OK",
                    unfilledCount > 0 ? "warning" : "ok"
                )
            ].join("");

            const generationLine = lastGenerationSummary
                ? `${t("schedule_generation_created_log", "Created shifts")}: ${Number(lastGenerationSummary.result?.created_count || 0)}`
                : t("schedule_no_generation_log", "No generation run yet");

            runLog.innerHTML = `
                <div class="schedule-log-line">
                    <strong>${escapeHtml(t("schedule_loaded_log", "Loaded schedule data"))}</strong>
                    <span>${escapeHtml(selectedPosition ? selectedPosition.name : "-")} · ${escapeHtml(dates[0])} - ${escapeHtml(dates[6])}</span>
                </div>
                <div class="schedule-log-line">
                    <strong>${escapeHtml(t("schedule_status_entries", "Entries"))}: ${Number(visibleEntries.length)}</strong>
                    <span>${escapeHtml(generationLine)}</span>
                </div>
            `;
        }

        function updateScheduleActionAvailability() {
            const weekStart = document.getElementById("week_start").value;
            const positionId = Number(document.getElementById("position_select").value);
            const hasPositions = allPositions.length > 0;
            const hasContext = Boolean(weekStart && positionId);
            const hasWeek = Boolean(weekStart);
            const loadButton = document.getElementById("load-btn");
            const generateButton = document.getElementById("auto-generate-btn");
            const generateAllButton = document.getElementById("auto-generate-all-btn");
            const clearButton = document.getElementById("clear-week-btn");
            const clearAllButton = document.getElementById("clear-all-week-btn");
            const exportButton = document.getElementById("export-excel-btn");
            const exportAllButton = document.getElementById("export-all-excel-btn");
            const exportWordButton = document.getElementById("export-word-btn");
            const exportAllWordButton = document.getElementById("export-all-word-btn");
            const generationActionsButton = document.getElementById("open-generation-actions-btn");
            const outputActionsButton = document.getElementById("open-output-actions-btn");
            const dangerActionsButton = document.getElementById("open-danger-actions-btn");
            const editable = canEditSchedule();

            loadButton.disabled = !hasPositions || !hasContext;
            generateButton.disabled = !scheduleDataLoaded || !hasContext;
            generateAllButton.disabled = !hasPositions || !hasWeek;
            clearButton.disabled = !scheduleDataLoaded || !hasContext;
            clearAllButton.disabled = !hasPositions || !hasWeek;
            exportButton.disabled = !scheduleDataLoaded || !hasContext;
            exportAllButton.disabled = !hasPositions || !hasWeek;
            exportWordButton.disabled = !scheduleDataLoaded || !hasContext;
            exportAllWordButton.disabled = !hasPositions || !hasWeek;
            generationActionsButton.disabled = !hasPositions || !hasWeek;
            outputActionsButton.disabled = !hasPositions || !hasWeek;
            dangerActionsButton.disabled = !hasPositions || !hasWeek;

            [
                generateButton,
                generateAllButton,
                clearButton,
                clearAllButton,
                generationActionsButton,
                dangerActionsButton
            ].forEach(button => {
                if (!button) return;
                button.hidden = !editable;
                button.style.display = editable ? "" : "none";
                if (!editable) {
                    button.disabled = true;
                }
            });

            loadButton.title = hasPositions ? "" : t("schedule_no_positions_text", "Create at least one position before loading or generating a weekly schedule.");
            generateButton.title = scheduleDataLoaded ? "" : t("schedule_action_generation_hint", "Generation is available after the selected week is loaded.");
            generateAllButton.title = hasWeek ? "" : t("msg_select_week_start", "Please select a week start date.");
            clearButton.title = scheduleDataLoaded ? "" : t("schedule_action_clear_hint", "Clear week becomes available after the selected week is loaded.");
            clearAllButton.title = hasWeek ? "" : t("msg_select_week_start", "Please select a week start date.");
            exportButton.title = scheduleDataLoaded ? "" : t("schedule_action_export_hint", "Export becomes available after the selected week is loaded.");
            exportAllButton.title = hasWeek ? "" : t("msg_select_week_start", "Please select a week start date.");
            exportWordButton.title = scheduleDataLoaded ? "" : t("schedule_action_export_hint", "Export becomes available after the selected week is loaded.");
            exportAllWordButton.title = hasWeek ? "" : t("msg_select_week_start", "Please select a week start date.");
            generationActionsButton.title = hasWeek ? "" : t("msg_select_week_start", "Please select a week start date.");
            outputActionsButton.title = hasWeek ? "" : t("msg_select_week_start", "Please select a week start date.");
            dangerActionsButton.title = hasWeek ? "" : t("msg_select_week_start", "Please select a week start date.");

        }

        /* =========================================================
           LOAD REFERENCE DATA / ЗАГРУЗКА СПРАВОЧНЫХ ДАННЫХ
           ========================================================= */

        async function loadPositions() {
            // Load positions for the selector / Загружаем должности для селекта
            try {
                const response = await fetch("/api/positions");

                if (!response.ok) {
                    showMessage(t("msg_failed_load_positions", "Failed to load positions."), "danger");
                    return;
                }

                allPositions = await response.json();

                const select = document.getElementById("position_select");
                if (allPositions.length === 0) {
                    select.innerHTML = `<option value="">${t("positions_empty_list", "No positions yet")}</option>`;
                    renderScheduleInitialState();
                    return;
                }

                select.innerHTML = `
                    <option value="">${t("schedule_select_position", "Select position")}</option>
                    ${allPositions.map(position => `
                        <option value="${Number(position.id)}">${escapeHtml(position.name)}</option>
                    `).join("")}
                `;
                if (isEmployeeUser()) {
                    const preferredPosition = allPositions.find(position => position.is_primary) || allPositions[0];
                    if (preferredPosition) {
                        select.value = String(preferredPosition.id);
                    }
                }
                renderScheduleInitialState();
            } catch (error) {
                console.error(error);
                showMessage(t("msg_server_error_load_positions", "Server error while loading positions."), "danger");
            }
        }

        function syncScheduleDisplaySelect() {
            const coverageSelect = document.getElementById("schedule_coverage_display_mode");
            if (coverageSelect) {
                coverageSelect.value = appSettings.schedule_coverage_display_mode || "interval";
            }
            const cardSelect = document.getElementById("schedule_card_display_mode");
            if (cardSelect) {
                cardSelect.value = appSettings.schedule_card_display_mode || "detailed";
            }
        }

        function applyScheduleAppearanceSettings() {
            const panel = document.querySelector(".schedule-panel");
            if (!panel) return;

            const colorMap = {
                "--shift-morning-bg": appSettings.schedule_morning_color || "#ecfeff",
                "--shift-evening-bg": appSettings.schedule_evening_color || "#fff7ed",
                "--shift-night-bg": appSettings.schedule_night_color || "#eef2ff",
                "--shift-status-bg": appSettings.schedule_status_color || "#f5f3ff"
            };

            Object.entries(colorMap).forEach(([property, value]) => {
                panel.style.setProperty(property, value);
            });
            panel.classList.toggle("card-display-compact", appSettings.schedule_card_display_mode === "compact");
        }

        async function loadScheduleDisplaySetting() {
            try {
                const response = await fetch("/api/app-settings");
                if (!response.ok) {
                    return;
                }

                appSettings = await response.json();
                const localCoverageMode = localStorage.getItem(getUserScopedStorageKey(LOCAL_COVERAGE_DISPLAY_MODE_PREFIX));
                if (!canEditSchedule() && ["interval", "category"].includes(localCoverageMode)) {
                    appSettings.schedule_coverage_display_mode = localCoverageMode;
                }
                const localCardMode = localStorage.getItem(getUserScopedStorageKey(LOCAL_CARD_DISPLAY_MODE_PREFIX));
                appSettings.schedule_card_display_mode = ["detailed", "compact"].includes(localCardMode)
                    ? localCardMode
                    : "detailed";
                syncScheduleDisplaySelect();
                applyScheduleAppearanceSettings();
            } catch (error) {
                console.error(error);
            }
        }

        async function saveScheduleDisplayMode(event) {
            const select = event.target;
            const nextMode = select.value;
            const previousMode = appSettings.schedule_coverage_display_mode || "interval";
            const positionId = Number(document.getElementById("position_select").value);

            appSettings = {
                ...appSettings,
                schedule_coverage_display_mode: nextMode
            };

            if (weekDates.length > 0 && positionId) {
                renderScheduleTable(positionId);
            }

            if (!canEditSchedule()) {
                localStorage.setItem(getUserScopedStorageKey(LOCAL_COVERAGE_DISPLAY_MODE_PREFIX), nextMode);
                syncScheduleDisplaySelect();
                applyScheduleAppearanceSettings();
                return;
            }

            try {
                const response = await fetch("/api/app-settings", {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ schedule_coverage_display_mode: nextMode })
                });

                if (!response.ok) {
                    appSettings.schedule_coverage_display_mode = previousMode;
                    syncScheduleDisplaySelect();
                    if (weekDates.length > 0 && positionId) {
                        renderScheduleTable(positionId);
                    }
                    showMessage(t("msg_failed_save_schedule_display", "Failed to save coverage display mode."), "danger");
                    return;
                }

                const result = await response.json();
                appSettings = result.settings;
                syncScheduleDisplaySelect();
                applyScheduleAppearanceSettings();
            } catch (error) {
                console.error(error);
                appSettings.schedule_coverage_display_mode = previousMode;
                syncScheduleDisplaySelect();
                if (weekDates.length > 0 && positionId) {
                    renderScheduleTable(positionId);
                }
                showMessage(t("msg_failed_save_schedule_display", "Failed to save coverage display mode."), "danger");
            }
        }

        function saveScheduleCardDisplayMode(event) {
            const nextMode = event.target.value === "compact" ? "compact" : "detailed";
            const positionId = Number(document.getElementById("position_select").value);
            appSettings = {
                ...appSettings,
                schedule_card_display_mode: nextMode
            };
            localStorage.setItem(getUserScopedStorageKey(LOCAL_CARD_DISPLAY_MODE_PREFIX), nextMode);
            syncScheduleDisplaySelect();
            applyScheduleAppearanceSettings();
            if (weekDates.length > 0 && positionId) {
                renderScheduleTable(positionId);
            }
        }

        async function loadSchedulePageData(options = {}) {
            // Main loading flow for the schedule page
            // Основной процесс загрузки данных для страницы расписания
            const showLoadedMessage = options.showLoadedMessage !== false;
            const preserveGenerationSummary = options.preserveGenerationSummary === true;
            const weekStart = document.getElementById("week_start").value;
            const positionId = Number(document.getElementById("position_select").value);

            if (!preserveGenerationSummary) {
                clearGenerationSummary();
            }

            if (!weekStart) {
                showMessage(t("msg_select_week_start", "Please select a week start date."), "warning");
                return;
            }

            if (!positionId) {
                showMessage(t("msg_select_position", "Please select a position."), "warning");
                return;
            }

            weekDates = buildWeekDates(weekStart);

            try {
                const employeeScheduleScopeQuery = isEmployeeUser() && positionId
                    ? `?position_id=${encodeURIComponent(positionId)}`
                    : "";
                const employeeScheduleScopeJoiner = employeeScheduleScopeQuery ? "&" : "?";
                const [
                    employeesResponse,
                    assignmentsResponse,
                    scheduleResponse,
                    requirementsResponse,
                    coverageRequirementsResponse,
                    appSettingsResponse,
                    shiftTemplatesResponse,
                    dayStatusesResponse
                ] = await Promise.all([
                    fetch(`/api/employees${employeeScheduleScopeQuery}`),
                    fetch(`/api/employee-positions${employeeScheduleScopeQuery}`),
                    fetch(`/api/schedule${employeeScheduleScopeQuery}`),
                    fetch(`/api/shift-requirements${employeeScheduleScopeQuery}`),
                    fetch(`/api/coverage-requirements${employeeScheduleScopeQuery}`),
                    fetch("/api/app-settings"),
                    fetch(`/api/shift-templates${employeeScheduleScopeQuery}${employeeScheduleScopeJoiner}active_only=true`),
                    fetch(`/api/employee-day-statuses${employeeScheduleScopeQuery}`)
                ]);

                if (
                    !employeesResponse.ok ||
                    !assignmentsResponse.ok ||
                    !scheduleResponse.ok ||
                    !requirementsResponse.ok ||
                    !coverageRequirementsResponse.ok ||
                    !appSettingsResponse.ok ||
                    !shiftTemplatesResponse.ok ||
                    !dayStatusesResponse.ok
                ) {
                    showMessage(t("msg_failed_load_schedule_data", "Failed to load schedule data."), "danger");
                    return;
                }

                allEmployees = await employeesResponse.json();
                allAssignments = await assignmentsResponse.json();
                allScheduleEntries = await scheduleResponse.json();
                allRequirements = await requirementsResponse.json();
                allCoverageRequirements = await coverageRequirementsResponse.json();
                appSettings = await appSettingsResponse.json();
                const localCoverageMode = localStorage.getItem(getUserScopedStorageKey(LOCAL_COVERAGE_DISPLAY_MODE_PREFIX));
                if (!canEditSchedule() && ["interval", "category"].includes(localCoverageMode)) {
                    appSettings.schedule_coverage_display_mode = localCoverageMode;
                }
                const localCardMode = localStorage.getItem(getUserScopedStorageKey(LOCAL_CARD_DISPLAY_MODE_PREFIX));
                appSettings.schedule_card_display_mode = ["detailed", "compact"].includes(localCardMode)
                    ? localCardMode
                    : "detailed";
                syncScheduleDisplaySelect();
                applyScheduleAppearanceSettings();
                allShiftTemplates = await shiftTemplatesResponse.json();
                allDayStatuses = await dayStatusesResponse.json();
                scheduleDataLoaded = true;

                renderScheduleTable(positionId);
                updateScheduleActionAvailability();
                if (showLoadedMessage) {
                    showMessage(t("msg_schedule_loaded", "Schedule loaded successfully."), "success");
                }
            } catch (error) {
                console.error(error);
                scheduleDataLoaded = false;
                updateScheduleActionAvailability();
                showMessage(t("msg_server_error_load_schedule", "Server error while loading schedule."), "danger");
            }
        }

        /* =========================================================
           EXPORT / ЭКСПОРТ
           ========================================================= */

        async function exportScheduleExcel() {
            // Export current selected week and position to Excel
            // Экспортируем текущую неделю и должность в Excel
            const weekStart = document.getElementById("week_start").value;
            const positionId = Number(document.getElementById("position_select").value);

            if (!weekStart) {
                showMessage(t("msg_select_week_start", "Please select a week start date."), "warning");
                return;
            }

            if (!positionId) {
                showMessage(t("msg_select_position", "Please select a position."), "warning");
                return;
            }

            const lang = localStorage.getItem("scheduleAppLanguage") || "en";
            const url = `/api/schedule/export-excel?week_start_date=${encodeURIComponent(weekStart)}&position_id=${positionId}&lang=${encodeURIComponent(lang)}`;
            const button = document.getElementById("export-excel-btn");
            await downloadFileExport(
                url,
                `schedule_${weekStart}.xlsx`,
                button,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            );
        }

        async function exportScheduleWord() {
            const weekStart = document.getElementById("week_start").value;
            const positionId = Number(document.getElementById("position_select").value);

            if (!weekStart) {
                showMessage(t("msg_select_week_start", "Please select a week start date."), "warning");
                return;
            }

            if (!positionId) {
                showMessage(t("msg_select_position", "Please select a position."), "warning");
                return;
            }

            const lang = localStorage.getItem("scheduleAppLanguage") || "en";
            const url = `/api/schedule/export-word?week_start_date=${encodeURIComponent(weekStart)}&position_id=${positionId}&lang=${encodeURIComponent(lang)}`;
            const button = document.getElementById("export-word-btn");
            await downloadFileExport(
                url,
                `schedule_${weekStart}.docx`,
                button,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            );
        }

        async function downloadFileExport(url, fallbackFilename, button, mediaType) {
            if (window.ScheduleAndroid && typeof window.ScheduleAndroid.downloadFile === "function") {
                const absoluteUrl = new URL(url, window.location.href).href;
                window.ScheduleAndroid.downloadFile(
                    absoluteUrl,
                    fallbackFilename,
                    mediaType
                );
                return;
            }

            button.disabled = true;

            try {
                const headers = new Headers();
                const token = window.scheduleAuth?.getToken?.();
                if (token) {
                    headers.set("Authorization", `Bearer ${token}`);
                }
                const response = await fetch(url, { headers });
                if (!response.ok) {
                    showMessage(t("msg_export_failed", "Export failed."), "danger");
                    return;
                }

                const blob = await response.blob();
                const disposition = response.headers.get("Content-Disposition") || "";
                const filenameMatch = disposition.match(/filename="([^"]+)"/);
                const filename = filenameMatch ? filenameMatch[1] : fallbackFilename;
                const downloadUrl = URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = downloadUrl;
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                link.remove();
                URL.revokeObjectURL(downloadUrl);
            } catch (error) {
                console.error(error);
                showMessage(t("msg_export_failed", "Export failed."), "danger");
            } finally {
                button.disabled = false;
                updateScheduleActionAvailability();
            }
        }

        async function exportAllSchedulesExcel() {
            const weekStart = document.getElementById("week_start").value;

            if (!weekStart) {
                showMessage(t("msg_select_week_start", "Please select a week start date."), "warning");
                return;
            }

            const lang = localStorage.getItem("scheduleAppLanguage") || "en";
            const url = `/api/schedule/export-excel-all?week_start_date=${encodeURIComponent(weekStart)}&lang=${encodeURIComponent(lang)}`;
            const button = document.getElementById("export-all-excel-btn");
            await downloadFileExport(
                url,
                `schedule_all_${weekStart}.xlsx`,
                button,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            );
        }

        async function exportAllSchedulesWord() {
            const weekStart = document.getElementById("week_start").value;

            if (!weekStart) {
                showMessage(t("msg_select_week_start", "Please select a week start date."), "warning");
                return;
            }

            const lang = localStorage.getItem("scheduleAppLanguage") || "en";
            const url = `/api/schedule/export-word-all?week_start_date=${encodeURIComponent(weekStart)}&lang=${encodeURIComponent(lang)}`;
            const button = document.getElementById("export-all-word-btn");
            await downloadFileExport(
                url,
                `schedule_all_${weekStart}.docx`,
                button,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            );
        }

        /* =========================================================
           AUTO GENERATION / АВТОГЕНЕРАЦИЯ
           ========================================================= */

        async function autoGenerateSchedule() {
            // Trigger backend auto-generation / Запускаем backend-автогенерацию
            const weekStart = document.getElementById("week_start").value;
            const positionId = Number(document.getElementById("position_select").value);
            const generationMode = getSelectedGenerationMode();
            const button = document.getElementById("auto-generate-btn");

            if (!weekStart) {
                showMessage(t("msg_select_week_start", "Please select a week start date."), "warning");
                return;
            }

            if (!positionId) {
                showMessage(t("msg_select_position", "Please select a position."), "warning");
                return;
            }

            button.disabled = true;
            setScheduleGenerating(true);

            try {
                const response = await fetch("/api/schedule/auto-generate", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        position_id: positionId,
                        week_start_date: weekStart,
                        generation_mode: generationMode
                    })
                });

                let result = null;
                let rawText = "";

                try {
                    rawText = await response.text();
                    result = rawText ? JSON.parse(rawText) : null;
                } catch (error) {
                    result = null;
                }

                if (!response.ok) {
                    const formattedError =
                        (result && result.detail)
                            ? formatApiError(result.detail)
                            : (rawText ? escapeHtml(rawText) : t("msg_auto_generate_failed", "Auto-generation failed."));

                    showMessage(formattedError, "danger");
                    return;
                }

                const hardCount = (result.feasibility_report?.hard_constraints || []).length;
                const softCount = (result.feasibility_report?.soft_constraints || []).length;
                const unfilledCount = (result.unfilled_reports || []).length;
                const warningCount = (result.errors || []).length;

                await loadSchedulePageData({
                    showLoadedMessage: false,
                    preserveGenerationSummary: true
                });

                lastGenerationSummary = {
                    weekStart,
                    positionId,
                    generationMode,
                    result
                };
                renderGenerationSummary(lastGenerationSummary);

                showMessage(
                    `${t("msg_auto_generate_done", "Auto-generation finished.")}<br>${escapeHtml(t("generation_summary_open_panel", "Detailed generation results are shown in the summary panel."))}`,
                    warningCount > 0 || hardCount > 0 || unfilledCount > 0 ? "warning" : "success"
                );
            } catch (error) {
                console.error(error);
                showMessage(
                    `${t("msg_server_error_auto_generate", "Server error while auto-generating schedule.")}<br>${escapeHtml(error.message || "")}`,
                    "danger"
                );
            } finally {
                button.disabled = false;
                setScheduleGenerating(false);
            }
        }

        async function autoGenerateAllSchedules() {
            const weekStart = document.getElementById("week_start").value;
            const positionId = Number(document.getElementById("position_select").value);
            const generationMode = getSelectedGenerationMode();
            const button = document.getElementById("auto-generate-all-btn");

            if (!weekStart) {
                showMessage(t("msg_select_week_start", "Please select a week start date."), "warning");
                return;
            }

            button.disabled = true;
            setScheduleGenerating(true);

            try {
                const response = await fetch("/api/schedule/auto-generate-all", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        week_start_date: weekStart,
                        generation_mode: generationMode
                    })
                });

                let result = null;
                let rawText = "";

                try {
                    rawText = await response.text();
                    result = rawText ? JSON.parse(rawText) : null;
                } catch (error) {
                    result = null;
                }

                if (!response.ok) {
                    const formattedError =
                        (result && result.detail)
                            ? formatApiError(result.detail)
                            : (rawText ? escapeHtml(rawText) : t("msg_auto_generate_failed", "Auto-generation failed."));

                    showMessage(formattedError, "danger");
                    return;
                }

                clearGenerationSummary();

                if (positionId) {
                    await loadSchedulePageData({
                        showLoadedMessage: false,
                        preserveGenerationSummary: false
                    });
                }

                const failureText = (result.failures || []).length > 0
                    ? `<br>${escapeHtml(t("schedule_generate_all_failures_prefix", "Failed positions"))}: ${escapeHtml(
                        result.failures.map(item => `${item.position_name}: ${item.detail}`).join("; ")
                    )}`
                    : "";

                showMessage(
                    `${escapeHtml(t("schedule_generate_all_done", "Auto-generation for all positions finished."))}<br>` +
                    `${escapeHtml(t("schedule_generate_all_success_summary", "Generated positions"))}: ${Number(result.generated_positions)} · ` +
                    `${escapeHtml(t("schedule_generate_all_created_summary", "Created shifts"))}: ${Number(result.total_created_count)}${failureText}`,
                    (result.failed_positions || 0) > 0 ? "warning" : "success"
                );
            } catch (error) {
                console.error(error);
                showMessage(
                    `${t("msg_server_error_auto_generate", "Server error while auto-generating schedule.")}<br>${escapeHtml(error.message || "")}`,
                    "danger"
                );
            } finally {
                button.disabled = false;
                setScheduleGenerating(false);
            }
        }

        function setScheduleGenerating(isGenerating) {
            const shell = document.querySelector(".schedule-shell");
            const overlay = document.getElementById("schedule-loading-overlay");
            const tableHeader = document.getElementById("schedule-thead");
            const buttons = [
                document.getElementById("load-btn"),
                document.getElementById("auto-generate-btn"),
                document.getElementById("auto-generate-all-btn"),
                document.getElementById("clear-week-btn"),
                document.getElementById("clear-all-week-btn"),
                document.getElementById("export-excel-btn"),
                document.getElementById("export-all-excel-btn"),
                document.getElementById("export-word-btn"),
                document.getElementById("export-all-word-btn"),
                document.getElementById("open-generation-actions-btn"),
                document.getElementById("open-output-actions-btn"),
                document.getElementById("open-danger-actions-btn"),
                document.getElementById("schedule_coverage_display_mode")
            ];

            if (shell) {
                if (isGenerating && tableHeader) {
                    shell.style.setProperty("--schedule-header-offset", `${tableHeader.offsetHeight}px`);
                }
                shell.classList.toggle("is-generating", isGenerating);
            }

            if (overlay) {
                overlay.setAttribute("aria-busy", isGenerating ? "true" : "false");
            }

            buttons.forEach(item => {
                if (item) {
                    item.disabled = isGenerating;
                }
            });
        }

        /* =========================================================
           CLEAR WEEK / ОЧИСТКА НЕДЕЛИ
           ========================================================= */

        async function clearWeekSchedule() {
            // Clear all schedule entries for selected week and position
            // Очищаем все смены за выбранную неделю и должность
            const weekStart = document.getElementById("week_start").value;
            const positionId = Number(document.getElementById("position_select").value);
            const button = document.getElementById("clear-week-btn");

            if (!weekStart) {
                showMessage(t("msg_select_week_start", "Please select a week start date."), "warning");
                return;
            }

            if (!positionId) {
                showMessage(t("msg_select_position", "Please select a position."), "warning");
                return;
            }

            let confirmMessage = `<p>${escapeHtml(t("msg_confirm_clear_week", "Are you sure you want to delete the schedule for this week and this position?"))}</p>`;

            try {
                const previewResponse = await fetch(
                    `/api/schedule/clear-week-preview?position_id=${positionId}&week_start_date=${encodeURIComponent(weekStart)}`
                );
                if (previewResponse.ok) {
                    const preview = await previewResponse.json();
                    confirmMessage += formatConfirmImpactList([
                        { label: t("confirm_impact_position", "Position"), value: preview.position_name },
                        { label: t("confirm_impact_week", "Week"), value: preview.week_start_date },
                        { label: t("confirm_impact_assigned_employees", "Assigned employees"), value: preview.assigned_employees },
                        { label: t("confirm_impact_schedule_entries", "Schedule entries"), value: preview.schedule_entries },
                        { label: t("confirm_impact_day_off_statuses", "Day-off statuses"), value: preview.day_off_statuses }
                    ]);
                } else {
                    confirmMessage += `<p>${escapeHtml(t("confirm_impact_fetch_failed", "Could not load related records. Review carefully before deleting."))}</p>`;
                }
            } catch (error) {
                console.error(error);
                confirmMessage += `<p>${escapeHtml(t("confirm_impact_fetch_failed", "Could not load related records. Review carefully before deleting."))}</p>`;
            }

            const isConfirmed = await appConfirm(confirmMessage, {
                title: t("msg_confirm_clear_week_title", "Clear week schedule"),
                confirmText: t("common_delete", "Delete"),
                html: true
            });

            if (!isConfirmed) return;

            button.disabled = true;

            try {
                const response = await fetch("/api/schedule/clear-week", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        position_id: positionId,
                        week_start_date: weekStart
                    })
                });

                const result = await response.json();

                if (!response.ok) {
                    showMessage(result.detail || t("msg_failed_clear_week", "Failed to clear week schedule."), "danger");
                    return;
                }

                const backupSuffix = result.backup_name
                    ? ` ${t("common_recovery_backup", "Recovery backup")}: ${result.backup_name}`
                    : "";
                showMessage(
                    `${t("msg_week_cleared", "Week schedule cleared.")} ${t("msg_deleted_count", "Deleted")}: ${result.deleted_count}${backupSuffix}`,
                    "success"
                );
                await loadSchedulePageData();
            } catch (error) {
                console.error(error);
                showMessage(t("msg_server_error_clear_week", "Server error while clearing week schedule."), "danger");
            } finally {
                button.disabled = false;
            }
        }

        async function clearAllWeekSchedules() {
            const weekStart = document.getElementById("week_start").value;
            const button = document.getElementById("clear-all-week-btn");

            if (!weekStart) {
                showMessage(t("msg_select_week_start", "Please select a week start date."), "warning");
                return;
            }

            let confirmMessage = `<p>${escapeHtml(t("msg_confirm_clear_all_week", "Are you sure you want to delete the schedule for this week across all positions?"))}</p>`;

            try {
                const previewResponse = await fetch(
                    `/api/schedule/clear-week-all-preview?week_start_date=${encodeURIComponent(weekStart)}`
                );
                if (previewResponse.ok) {
                    const preview = await previewResponse.json();
                    confirmMessage += formatConfirmImpactList([
                        { label: t("confirm_impact_week", "Week"), value: preview.week_start_date },
                        { label: t("confirm_impact_positions", "Positions"), value: preview.positions },
                        { label: t("confirm_impact_schedule_entries", "Schedule entries"), value: preview.schedule_entries },
                        { label: t("confirm_impact_day_off_statuses", "Day-off statuses"), value: preview.day_off_statuses }
                    ]);
                } else {
                    confirmMessage += `<p>${escapeHtml(t("confirm_impact_fetch_failed", "Could not load related records. Review carefully before deleting."))}</p>`;
                }
            } catch (error) {
                console.error(error);
                confirmMessage += `<p>${escapeHtml(t("confirm_impact_fetch_failed", "Could not load related records. Review carefully before deleting."))}</p>`;
            }

            const isConfirmed = await appConfirm(confirmMessage, {
                title: t("msg_confirm_clear_all_week_title", "Clear all week schedules"),
                confirmText: t("common_delete", "Delete"),
                html: true
            });

            if (!isConfirmed) return;

            button.disabled = true;

            try {
                const response = await fetch("/api/schedule/clear-week-all", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        week_start_date: weekStart
                    })
                });

                const result = await response.json();

                if (!response.ok) {
                    showMessage(result.detail || t("msg_failed_clear_all_week", "Failed to clear all week schedules."), "danger");
                    return;
                }

                const backupSuffix = result.backup_name
                    ? ` ${t("common_recovery_backup", "Recovery backup")}: ${result.backup_name}`
                    : "";
                showMessage(
                    `${t("msg_all_week_cleared", "All week schedules cleared.")} ${t("msg_deleted_count", "Deleted")}: ${result.deleted_count}${backupSuffix}`,
                    "success"
                );
                if (document.getElementById("position_select").value) {
                    await loadSchedulePageData({ showLoadedMessage: false });
                } else {
                    allScheduleEntries = allScheduleEntries.filter(entry => !buildWeekDates(weekStart).includes(entry.date));
                    renderScheduleInitialState();
                    updateScheduleActionAvailability();
                }
            } catch (error) {
                console.error(error);
                showMessage(t("msg_server_error_clear_all_week", "Server error while clearing all week schedules."), "danger");
            } finally {
                button.disabled = false;
            }
        }

        /* =========================================================
           DATA HELPERS / ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ДАННЫХ
           ========================================================= */

        function getEmployeesForPosition(positionId) {
            // Get employees assigned to one position
            // Получаем сотрудников, привязанных к должности
            const assignedEmployeeIds = allAssignments
                .filter(item => item.position_id === positionId)
                .map(item => item.employee_id);

            const employeeMap = new Map(allEmployees.map(employee => [employee.id, employee]));
            allAssignments
                .filter(item => item.position_id === positionId && !employeeMap.has(item.employee_id))
                .forEach(item => {
                    employeeMap.set(item.employee_id, {
                        id: item.employee_id,
                        full_name: item.employee_name,
                        min_shifts_per_week: 0,
                        target_shifts_per_week: 0,
                        max_shifts_per_week: 0
                    });
                });

            return Array.from(employeeMap.values())
                .filter(employee => assignedEmployeeIds.includes(employee.id))
                .sort((a, b) => a.full_name.localeCompare(b.full_name));
        }

        function getRequirementMapForPosition(positionId) {
            // Build quick access map for requirements
            // Строим словарь требований для удобного доступа
            const requirementMap = {
                morning: null,
                evening: null,
                night: null
            };

            allRequirements
                .filter(item => item.position_id === positionId)
                .forEach(item => {
                    requirementMap[item.shift_category] = item;
                });

            return requirementMap;
        }

        function getShiftTemplatesForPosition(positionId) {
            return allShiftTemplates.filter(item => item.position_id === positionId);
        }

        function parseTimeToMinutes(value) {
            if (!value) return 0;
            const [hours, minutes] = value.split(":").map(Number);
            return hours * 60 + minutes;
        }

        function buildTimeInterval(startTime, endTime, isOvernight) {
            const start = parseTimeToMinutes(startTime);
            let end = parseTimeToMinutes(endTime);
            if (isOvernight || end <= start) {
                end += 24 * 60;
            }
            return { start, end };
        }

        function intervalContains(container, target) {
            return container.start <= target.start && target.end <= container.end;
        }

        function getCoverageRequirementsForPosition(positionId) {
            return allCoverageRequirements
                .filter(item => item.position_id === positionId)
                .sort((a, b) => parseTimeToMinutes(a.start_time) - parseTimeToMinutes(b.start_time));
        }

        function shiftTemplateCoversRequirement(template, requirement) {
            const templateInterval = buildTimeInterval(
                template.start_time,
                template.end_time,
                template.is_overnight
            );
            const requiredInterval = buildTimeInterval(
                requirement.start_time,
                requirement.end_time,
                requirement.is_overnight
            );
            return intervalContains(templateInterval, requiredInterval);
        }

        function getCoverageRequirementCategories(positionId, requirement) {
            const categories = new Set();
            getShiftTemplatesForPosition(positionId).forEach(template => {
                if (shiftTemplateCoversRequirement(template, requirement)) {
                    categories.add(template.category);
                }
            });
            return categories;
        }

        function buildCategoryCoverageRequirementMap(positionId, coverageRequirements) {
            const map = {
                morning: null,
                evening: null,
                night: null
            };

            coverageRequirements.forEach(requirement => {
                const categories = getCoverageRequirementCategories(positionId, requirement);
                categories.forEach(category => {
                    const current = map[category] || {
                        required_total: 0,
                        required_female_min: 0,
                        required_male_min: 0,
                        interval_count: 0
                    };

                    map[category] = {
                        required_total: Math.max(current.required_total, Number(requirement.required_total) || 0),
                        required_female_min: Math.max(current.required_female_min, Number(requirement.required_female_min) || 0),
                        required_male_min: Math.max(current.required_male_min, Number(requirement.required_male_min) || 0),
                        interval_count: current.interval_count + 1
                    };
                });
            });

            return map;
        }

        function entryCountsTowardCoverage(entry) {
            if (!entry || entry.no_show) {
                return false;
            }

            const dayStatus = getDayStatus(entry.employee_id, entry.date);
            if (dayStatus && ["sick", "day_off", "vacation"].includes(dayStatus.status_type)) {
                return false;
            }

            return true;
        }

        function getCoverageStats(positionId, date, shiftCategory) {
            // Count total and female employees for one shift category
            // Считаем общее число и число женщин по категории смены
            const matchingEntries = allScheduleEntries.filter(entry => (
                entry.position_id === positionId &&
                entry.date === date &&
                entry.shift_category === shiftCategory &&
                entryCountsTowardCoverage(entry)
            ));

            const femaleCount = matchingEntries.filter(entry => {
                const employee = allEmployees.find(item => item.id === entry.employee_id);
                return employee && employee.sex === "female";
            }).length;
            const maleCount = matchingEntries.filter(entry => {
                const employee = allEmployees.find(item => item.id === entry.employee_id);
                return employee && employee.sex === "male";
            }).length;

            return {
                total: matchingEntries.length,
                female: femaleCount,
                male: maleCount
            };
        }

        function getCategoryCoverageStats(positionId, date, shiftCategory, coverageRequirements) {
            const relevantRequirements = coverageRequirements.filter(requirement =>
                getCoverageRequirementCategories(positionId, requirement).has(shiftCategory)
            );

            const matchingEntries = allScheduleEntries.filter(entry => {
                if (
                    entry.position_id !== positionId ||
                    entry.date !== date ||
                    entry.shift_category !== shiftCategory ||
                    !entryCountsTowardCoverage(entry)
                ) {
                    return false;
                }

                if (relevantRequirements.length === 0) {
                    return true;
                }

                const entryInterval = buildTimeInterval(
                    entry.start_time,
                    entry.end_time,
                    entry.is_overnight
                );

                return relevantRequirements.some(requirement => {
                    const requiredInterval = buildTimeInterval(
                        requirement.start_time,
                        requirement.end_time,
                        requirement.is_overnight
                    );
                    return intervalContains(entryInterval, requiredInterval);
                });
            });

            const uniqueEmployeeIds = new Set(matchingEntries.map(entry => entry.employee_id));
            let femaleCount = 0;
            let maleCount = 0;

            uniqueEmployeeIds.forEach(employeeId => {
                const employee = allEmployees.find(item => item.id === employeeId);
                if (employee && employee.sex === "female") {
                    femaleCount += 1;
                }
                if (employee && employee.sex === "male") {
                    maleCount += 1;
                }
            });

            return {
                total: uniqueEmployeeIds.size,
                female: femaleCount,
                male: maleCount
            };
        }

        function getIntervalCoverageStats(positionId, date, requirement) {
            const requiredInterval = buildTimeInterval(
                requirement.start_time,
                requirement.end_time,
                requirement.is_overnight
            );

            const matchingEntries = allScheduleEntries.filter(entry => {
                if (entry.position_id !== positionId || entry.date !== date || !entryCountsTowardCoverage(entry)) {
                    return false;
                }

                const entryInterval = buildTimeInterval(
                    entry.start_time,
                    entry.end_time,
                    entry.is_overnight
                );

                return intervalContains(entryInterval, requiredInterval);
            });

            const femaleCount = matchingEntries.filter(entry => {
                const employee = allEmployees.find(item => item.id === entry.employee_id);
                return employee && employee.sex === "female";
            }).length;
            const maleCount = matchingEntries.filter(entry => {
                const employee = allEmployees.find(item => item.id === entry.employee_id);
                return employee && employee.sex === "male";
            }).length;

            return {
                total: matchingEntries.length,
                female: femaleCount,
                male: maleCount
            };
        }

        function getCoverageClass(stats, requirement) {
            // Decide pill color by coverage state
            // Выбираем цвет плашки по состоянию покрытия
            if (!requirement) {
                return "neutral";
            }

            if (stats.total < requirement.required_total) {
                return "danger";
            }

            if (requirement.required_female_min > 0 && stats.female < requirement.required_female_min) {
                return "warning";
            }

            if (requirement.required_male_min > 0 && stats.male < requirement.required_male_min) {
                return "warning";
            }

            return "success";
        }

        function renderCoveragePill(title, stats, requirement, options = {}) {
            const coverageClass = getCoverageClass(stats, requirement);
            const totalLine = requirement
                ? `${t("coverage_staff", "Staff")}: ${stats.total} / ${requirement.required_total}`
                : `${t("coverage_staff", "Staff")}: ${stats.total} / -`;
            const femaleLine = requirement && requirement.required_female_min > 0
                ? `${t("coverage_women", "Women")}: ${stats.female} / ${requirement.required_female_min}`
                : "";
            const maleLine = requirement && requirement.required_male_min > 0
                ? `${t("coverage_men", "Men")}: ${stats.male} / ${requirement.required_male_min}`
                : "";
            const detailLines = [totalLine, femaleLine, maleLine].filter(Boolean);
            const intervalCount = Number(options.intervalCount || 0);
            const titleMeta = intervalCount > 1
                ? ` · ${intervalCount} ${t("coverage_intervals_short", "slots")}`
                : "";
            const titleText = `${title}${titleMeta}`;

            return `
                <div class="coverage-pill ${coverageClass}" title="${escapeHtml(detailLines.join(" · "))}">
                    <div class="coverage-title">${escapeHtml(titleText)}</div>
                    <div class="coverage-metrics">
                        ${detailLines.map(line => `<span class="coverage-metric">${escapeHtml(line)}</span>`).join("")}
                    </div>
                </div>
            `;
        }

        function getDayStatus(employeeId, date) {
            // Find special employee status on specific date
            // Ищем особый статус сотрудника на дату
            return allDayStatuses.find(item => (
                item.employee_id === employeeId &&
                item.date === date
            ));
        }

        function getCardClassByShiftCategory(shiftCategory) {
            // Choose CSS class by shift type / Выбираем CSS-класс по типу смены
            if (shiftCategory === "evening") return "entry-card evening";
            if (shiftCategory === "night") return "entry-card night";
            return "entry-card morning";
        }

        function getShiftCategoryLabel(shiftCategory) {
            if (shiftCategory === "morning") return t("shift_morning", "Morning");
            if (shiftCategory === "evening") return t("shift_evening", "Evening");
            return t("shift_night", "Night");
        }

        function getGenerationDateSummary(date) {
            if (!lastGenerationSummary || !lastGenerationSummary.result) {
                return null;
            }

            const result = lastGenerationSummary.result;
            const feasibilityIssues = ((result.feasibility_report && result.feasibility_report.issues) || [])
                .filter(issue => issue.date === date);
            const hardCount = feasibilityIssues.filter(issue => issue.constraint_type === "hard").length;
            const softCount = feasibilityIssues.filter(issue => issue.constraint_type === "soft").length;
            const unfilledCount = (result.unfilled_reports || []).filter(report => report.date === date).length;

            const totalCount = hardCount + softCount + unfilledCount;
            if (totalCount === 0) {
                return null;
            }

            return {
                hardCount,
                softCount,
                unfilledCount,
                totalCount,
                severity: hardCount > 0 || unfilledCount > 0 ? "danger" : "warning"
            };
        }

        function renderDateAttentionFlags(date) {
            const summary = getGenerationDateSummary(date);
            if (!summary) {
                return "";
            }

            const flags = [];
            if (summary.hardCount > 0) {
                flags.push(`
                    <span class="day-header-flag danger" title="${escapeHtml(t("generation_hard_constraints", "Hard constraints"))}">
                        ${escapeHtml(`${t("generation_hard_short", "Hard")}: ${summary.hardCount}`)}
                    </span>
                `);
            }
            if (summary.softCount > 0) {
                flags.push(`
                    <span class="day-header-flag warning" title="${escapeHtml(t("generation_soft_constraints", "Soft constraints"))}">
                        ${escapeHtml(`${t("generation_soft_short", "Soft")}: ${summary.softCount}`)}
                    </span>
                `);
            }
            if (summary.unfilledCount > 0) {
                flags.push(`
                    <span class="day-header-flag danger" title="${escapeHtml(t("generation_unfilled_count", "Unfilled requirements"))}">
                        ${escapeHtml(`${t("generation_unfilled_short", "Gap")}: ${summary.unfilledCount}`)}
                    </span>
                `);
            }

            return `<div class="day-header-flags">${flags.join("")}</div>`;
        }

        /* =========================================================
           TABLE RENDER / ОТРИСОВКА ТАБЛИЦЫ
           ========================================================= */

        function renderCoverageSummary(positionId, date) {
            // Build the coverage row cell for one date
            // Строим ячейку строки покрытия для одной даты
            const coverageRequirements = getCoverageRequirementsForPosition(positionId);
            if (
                coverageRequirements.length > 0 &&
                (appSettings.schedule_coverage_display_mode || "interval") === "interval"
            ) {
                return `
                    <div class="coverage-stack">
                        ${coverageRequirements.map(requirement => {
                    const stats = getIntervalCoverageStats(positionId, date, requirement);
                    const title = `${requirement.start_time} - ${requirement.end_time}`;
                    return renderCoveragePill(title, stats, requirement);
                }).join("")}
                    </div>
                `;
            }

            const requirementMap = coverageRequirements.length > 0
                ? buildCategoryCoverageRequirementMap(positionId, coverageRequirements)
                : getRequirementMapForPosition(positionId);

            return `
                <div class="coverage-stack">
                    ${SHIFT_CATEGORIES.map(([shiftCategory, defaultTitle]) => {
                const stats = coverageRequirements.length > 0
                    ? getCategoryCoverageStats(positionId, date, shiftCategory, coverageRequirements)
                    : getCoverageStats(positionId, date, shiftCategory);
                const requirement = requirementMap[shiftCategory];

                const translatedTitle =
                    shiftCategory === "morning" ? t("shift_morning", "Morning") :
                        shiftCategory === "evening" ? t("shift_evening", "Evening") :
                            t("shift_night", "Night");

                return renderCoveragePill(translatedTitle, stats, requirement, {
                    intervalCount: requirement?.interval_count
                });
            }).join("")}
                </div>
            `;
        }

        function getDayStatusLabel(statusType) {
            if (statusType === "day_off") {
                return t("status_day_off", "Day off");
            }
            if (statusType === "vacation") {
                return t("status_vacation", "Vacation");
            }
            return t("status_sick", "Sick");
        }

        function getDayStatusClass(statusType) {
            if (statusType === "vacation") return "vacation";
            return statusType === "day_off" ? "day-off" : "sick";
        }

        function getPositionName(positionId) {
            const position = allPositions.find(item => item.id === positionId);
            return position ? position.name : String(positionId);
        }

        function renderEntryCard(entry, options = {}) {
            const extraClasses = options.muted ? " is-muted-foreign" : "";
            const positionMeta = options.showPosition
                ? ` · ${escapeHtml(getPositionName(entry.position_id))}`
                : "";
            return `
                <div class="${getCardClassByShiftCategory(entry.shift_category)} ${entry.no_show ? "has-no-show" : ""}${extraClasses}">
                    <div class="entry-title">${escapeHtml(entry.shift_template_name)}</div>
                    <div class="entry-meta">
                        ${escapeHtml(getShiftCategoryLabel(entry.shift_category))} · ${escapeHtml(entry.start_time)} - ${escapeHtml(entry.end_time)}${positionMeta}
                    </div>
                    ${entry.no_show ? `
                        <div class="entry-no-show-label">${t("status_no_show", "No-show")}</div>
                        ${options.showActions ? `
                            <button
                                class="entry-status-remove-btn clear-no-show-btn"
                                data-entry-id="${entry.id}"
                                type="button"
                                title="${t("schedule_remove_status", "Remove status")}"
                            >
                                ×
                            </button>
                        ` : ""}
                    ` : ""}
                    ${options.showActions ? `
                        <button
                            class="entry-delete delete-shift-btn"
                            data-entry-id="${entry.id}"
                            type="button"
                            title="${t("schedule_delete_shift_btn", "Delete")}"
                            aria-label="${t("schedule_delete_shift_btn", "Delete")}"
                        >
                            ×
                        </button>
                    ` : ""}
                </div>
            `;
        }

        function getForeignPositionEntries(employeeId, positionId, date) {
            return allScheduleEntries.filter(entry => (
                entry.employee_id === employeeId &&
                entry.position_id !== positionId &&
                entry.date === date
            ));
        }

        function renderCellEntries(dayEntries, employeeId, positionId, date, showActions) {
            const foreignEntries = getForeignPositionEntries(employeeId, positionId, date);
            if (dayEntries.length === 0 && foreignEntries.length === 0) {
                return `<div class="empty-text">${t("schedule_no_shifts_assigned", "No shifts assigned")}</div>`;
            }

            return [
                ...dayEntries.map(entry => renderEntryCard(entry, { showActions })),
                ...foreignEntries.map(entry => renderEntryCard(entry, {
                    muted: true,
                    showPosition: true,
                    showActions: false
                }))
            ].join("");
        }

        function renderReadOnlyCellBody(dayEntries, employeeId, positionId, date) {
            return `
                <div class="entries-list">
                    ${renderCellEntries(dayEntries, employeeId, positionId, date, false)}
                </div>
            `;
        }

        function renderDayStatusCover(employeeId, date, statusType, showActions = true) {
            return `
                <div class="cell-status-cover ${getDayStatusClass(statusType)}">
                    ${showActions ? `
                        <button
                            class="status-remove-btn delete-day-status-btn"
                            data-employee-id="${employeeId}"
                            data-date="${date}"
                            type="button"
                            title="${t("schedule_remove_status", "Remove status")}"
                        >
                            ×
                        </button>
                    ` : ""}
                    <div>${getDayStatusLabel(statusType)}</div>
                </div>
            `;
        }

        function renderScheduleCell(employeeId, positionId, date, dayLabel = "") {
            // Render one employee/day cell
            // Отрисовываем одну ячейку: сотрудник + день
            const dayEntries = allScheduleEntries.filter(entry => (
                entry.employee_id === employeeId &&
                entry.position_id === positionId &&
                entry.date === date
            ));

            const dayStatus = getDayStatus(employeeId, date);
            const hasFullCellStatus = dayStatus && ["sick", "day_off", "vacation"].includes(dayStatus.status_type);
            const editable = canEditSchedule();
            const dayCellAttributes = `data-day-label="${escapeHtml(dayLabel)}" data-date-label="${escapeHtml(date)}"`;

            if (hasFullCellStatus) {
                return `
                    <td class="schedule-day-cell has-day-status" ${dayCellAttributes}>
                        <div class="schedule-day-inner">
                            ${renderReadOnlyCellBody(dayEntries, employeeId, positionId, date)}
                        </div>
                        ${renderDayStatusCover(employeeId, date, dayStatus.status_type, editable)}
                    </td>
                `;
            }

            if (!editable) {
                return `
                    <td class="schedule-day-cell" ${dayCellAttributes}>
                        <div class="schedule-day-inner ${dayEntries.length > 0 ? "has-entries" : ""}">
                            ${renderReadOnlyCellBody(dayEntries, employeeId, positionId, date)}
                        </div>
                    </td>
                `;
            }

            return `
                <td class="schedule-day-cell" ${dayCellAttributes}>
                    <div class="schedule-day-inner ${dayEntries.length > 0 ? "has-entries" : ""}">
                            <div class="add-box">
                            <div class="cell-actions">
                                <button
                                    class="cell-btn primary add-shift-btn"
                                    data-employee-id="${employeeId}"
                                    data-position-id="${positionId}"
                                    data-date="${date}"
                                    type="button"
                                >
                                    ${t("schedule_add_shift", "Add shift")}
                                </button>
                                <button
                                    class="cell-btn secondary open-status-btn"
                                    data-employee-id="${employeeId}"
                                    data-date="${date}"
                                    type="button"
                                >
                                    ${t("schedule_day_status", "Day status")}
                                </button>
                            </div>
                        </div>

                        <div class="entries-list">
                            ${renderCellEntries(dayEntries, employeeId, positionId, date, true)}
                        </div>
                    </div>
                </td>
            `;
        }

        function renderScheduleTable(positionId) {
            // Main table rendering function
            // Главная функция отрисовки таблицы
            const thead = document.getElementById("schedule-thead");
            const tbody = document.getElementById("schedule-tbody");
            const coverageHeaderRow = shouldShowCoverageInSchedule() ? `
                <tr class="coverage-header-row">
                    <th class="employee-column">
                        <div class="coverage-header-cell">
                            <strong>${t("schedule_coverage_header", "Coverage")}</strong>
                        </div>
                    </th>

                    ${weekDates.map(date => {
                const dateSummary = getGenerationDateSummary(date);
                return `
                        <th>
                            <div class="coverage-header-cell ${dateSummary ? `has-attention ${dateSummary.severity}` : ""}">
                                ${renderCoverageSummary(positionId, date)}
                            </div>
                        </th>
                    `;
            }).join("")}
                </tr>
            ` : "";

            const employeesForPosition = getEmployeesForPosition(positionId);
            const filteredEmployees = getFilteredScheduleEmployees(employeesForPosition, positionId);
            const selectedPosition = allPositions.find(item => item.id === positionId);

            thead.innerHTML = `
                <tr class="date-header-row">
                    <th class="employee-column">
                        <div class="day-header">
                            <div class="day-header-title">${t("schedule_employee_header", "Employee")}</div>
                        </div>
                    </th>

                    ${weekDates.map((date, index) => {
                const dateSummary = getGenerationDateSummary(date);
                return `
                        <th>
                            <div class="day-header ${dateSummary ? `has-attention ${dateSummary.severity}` : ""}">
                                <div class="day-header-title">${escapeHtml(getWeekdayName(index))}</div>
                                <div class="day-header-date">${escapeHtml(date)}</div>
                                ${renderDateAttentionFlags(date)}
                            </div>
                        </th>
                    `;
            }).join("")}
                </tr>

                ${coverageHeaderRow}
            `;

            const firstHeaderRow = thead.querySelector(".date-header-row");
            const shell = document.querySelector(".schedule-shell");
            if (firstHeaderRow && shell) {
                shell.style.setProperty("--schedule-date-header-height", `${firstHeaderRow.offsetHeight}px`);
            }
            updateScheduleStatusStrip();
            updateScheduleBoardRange();
            updateScheduleInspector();
            updateScheduleFilterCount(filteredEmployees.length, employeesForPosition.length);

            if (employeesForPosition.length === 0) {
                const actionHtml = [
                    `<a class="btn btn-secondary" href="/employees">${t("common_open_employees", "Open employees")}</a>`,
                    `<a class="btn btn-secondary" href="/employee-positions">${t("common_open_assignments", "Open assignments")}</a>`
                ].join("");
                tbody.innerHTML = `
                    <tr>
                        <td colspan="8" style="padding:24px;">
                            ${renderScheduleWorkspaceEmptyState({
                                title: t("schedule_no_employees_title", "This position has no assigned employees"),
                                text: selectedPosition
                                    ? `${t("schedule_no_employees_for_position", "No employees are assigned to this position.")} ${t("schedule_no_employees_text", "Add employees and link them to this position before filling the week.")}`
                                    : t("schedule_no_employees_text", "Add employees and link them to this position before filling the week."),
                                actionHtml
                            })}
                        </td>
                    </tr>
                `;
                updateScheduleActionAvailability();
                return;
            }

            if (filteredEmployees.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="8" style="padding:24px;">
                            ${renderScheduleWorkspaceEmptyState({
                                title: t("common_filter_no_matches", "No matching records"),
                                text: t("common_search_employee", "Search employee")
                            })}
                        </td>
                    </tr>
                `;
                updateScheduleActionAvailability();
                syncScheduleFloatingHeader();
                return;
            }

            tbody.innerHTML = filteredEmployees.map(employee => `
                <tr>
                    <td class="employee-column">
                        <div class="employee-cell">
                            <div class="employee-name">${escapeHtml(employee.full_name)}</div>
                            <div class="employee-meta">
                                ${escapeHtml(t("employee_min_target_max", "Min/Target/Max"))}:
                                ${Number(employee.min_shifts_per_week)}/${Number(employee.target_shifts_per_week)}/${Number(employee.max_shifts_per_week)}
                            </div>
                        </div>
                    </td>

                    ${weekDates.map((date, index) => renderScheduleCell(employee.id, positionId, date, getWeekdayName(index))).join("")}
                </tr>
            `).join("");

            bindScheduleActions();
            updateScheduleActionAvailability();
            updateScheduleInspector();
            syncScheduleFloatingHeader();
        }

        /* =========================================================
           CELL ACTIONS / ДЕЙСТВИЯ В ЯЧЕЙКАХ
           ========================================================= */

        function bindScheduleActions() {
            if (!canEditSchedule()) {
                return;
            }
            // Bind "Add shift" buttons / Привязываем кнопки добавления смен
            document.querySelectorAll(".add-shift-btn").forEach(button => {
                button.addEventListener("click", () => {
                    const employeeId = Number(button.dataset.employeeId);
                    const positionId = Number(button.dataset.positionId);
                    const date = button.dataset.date;

                    openShiftPicker(employeeId, positionId, date);
                });
            });

            // Bind day status buttons / Привязываем кнопки статуса дня
            document.querySelectorAll(".open-status-btn").forEach(button => {
                button.addEventListener("click", () => {
                    const employeeId = Number(button.dataset.employeeId);
                    const date = button.dataset.date;

                    openStatusPicker(employeeId, date);
                });
            });

            // Bind shift delete buttons / Привязываем кнопки удаления смен
            document.querySelectorAll(".delete-shift-btn").forEach(button => {
                button.addEventListener("click", async () => {
                    const entryId = Number(button.dataset.entryId);

                    button.disabled = true;
                    await deleteScheduleEntry(entryId);
                    button.disabled = false;
                });
            });

            document.querySelectorAll(".delete-day-status-btn").forEach(button => {
                button.addEventListener("click", async () => {
                    const employeeId = Number(button.dataset.employeeId);
                    const date = button.dataset.date;

                    button.disabled = true;
                    await saveDayStatus(employeeId, date, "");
                    button.disabled = false;
                });
            });

            document.querySelectorAll(".clear-no-show-btn").forEach(button => {
                button.addEventListener("click", async () => {
                    const entryId = Number(button.dataset.entryId);

                    button.disabled = true;
                    await updateScheduleEntryNoShow(entryId, false);
                    button.disabled = false;
                });
            });
        }

        function bindShiftPicker() {
            const overlay = document.getElementById("shift-picker-overlay");
            const closeButton = document.getElementById("shift-picker-close");

            closeButton.addEventListener("click", closeShiftPicker);
            overlay.addEventListener("click", event => {
                if (event.target === overlay) {
                    closeShiftPicker();
                }
            });

            document.addEventListener("keydown", event => {
                if (event.key === "Escape" && pendingShiftTarget) {
                    closeShiftPicker();
                }
            });
        }

        function bindStatusPicker() {
            const overlay = document.getElementById("status-picker-overlay");
            const closeButton = document.getElementById("status-picker-close");

            closeButton.addEventListener("click", closeStatusPicker);
            overlay.addEventListener("click", event => {
                if (event.target === overlay) {
                    closeStatusPicker();
                }
            });

            document.addEventListener("keydown", event => {
                if (event.key === "Escape" && pendingStatusTarget) {
                    closeStatusPicker();
                }
            });
        }

        function openShiftPicker(employeeId, positionId, date) {
            if (!canEditSchedule()) return;
            pendingShiftTarget = { employeeId, positionId, date };

            const employee = allEmployees.find(item => item.id === employeeId);
            const overlay = document.getElementById("shift-picker-overlay");
            const context = document.getElementById("shift-picker-context");
            const body = document.getElementById("shift-picker-body");

            context.textContent = `${employee ? employee.full_name : ""} · ${date}`;
            body.innerHTML = renderShiftPickerOptions();

            body.querySelectorAll(".shift-picker-option").forEach(button => {
                button.addEventListener("click", async () => {
                    const shiftTemplateId = Number(button.dataset.templateId);
                    button.disabled = true;
                    await createScheduleEntry(employeeId, positionId, date, shiftTemplateId);
                    closeShiftPicker();
                });
            });

            overlay.classList.add("is-open");
            overlay.setAttribute("aria-hidden", "false");
        }

        function closeShiftPicker() {
            const overlay = document.getElementById("shift-picker-overlay");
            overlay.classList.remove("is-open");
            overlay.setAttribute("aria-hidden", "true");
            pendingShiftTarget = null;
        }

        function renderShiftPickerOptions() {
            const targetPositionId = pendingShiftTarget?.positionId ?? null;
            return SHIFT_CATEGORIES.map(([category]) => {
                const templates = allShiftTemplates.filter(item =>
                    item.category === category && item.position_id === targetPositionId
                );
                if (templates.length === 0) return "";

                return `
                    <div class="shift-picker-group">
                        <div class="shift-picker-group-title">${getShiftCategoryLabel(category)}</div>
                        ${templates.map(template => `
                            <button class="shift-picker-option" type="button" data-template-id="${template.id}">
                                <div class="shift-picker-option-title">${escapeHtml(template.name)}</div>
                                <div class="shift-picker-option-meta">
                                    ${escapeHtml(getShiftCategoryLabel(template.category))} · ${escapeHtml(template.start_time)} - ${escapeHtml(template.end_time)}
                                </div>
                            </button>
                        `).join("")}
                    </div>
                `;
            }).join("") || `<div class="empty-text">${t("templates_empty_list", "No shift templates yet")}</div>`;
        }

        function openStatusPicker(employeeId, date) {
            if (!canEditSchedule()) return;
            pendingStatusTarget = { employeeId, date };

            const employee = allEmployees.find(item => item.id === employeeId);
            const overlay = document.getElementById("status-picker-overlay");
            const context = document.getElementById("status-picker-context");
            const body = document.getElementById("status-picker-body");

            context.textContent = `${employee ? employee.full_name : ""} · ${date}`;
            body.innerHTML = renderStatusPickerOptions();
            bindStatusPickerOptions(employeeId, date);

            overlay.classList.add("is-open");
            overlay.setAttribute("aria-hidden", "false");
        }

        function closeStatusPicker() {
            const overlay = document.getElementById("status-picker-overlay");
            overlay.classList.remove("is-open");
            overlay.setAttribute("aria-hidden", "true");
            pendingStatusTarget = null;
        }

        function renderStatusPickerOptions() {
            const target = pendingStatusTarget || {};
            const dateEntries = allScheduleEntries.filter(entry => (
                entry.employee_id === target.employeeId &&
                entry.date === target.date &&
                !entry.no_show
            ));

            return `
                <div class="shift-picker-group">
                    <div class="shift-picker-group-title">${t("schedule_day_status", "Day status")}</div>
                    <button class="shift-picker-option status-picker-option" type="button" data-status-type="sick">
                        <div class="shift-picker-option-title">${t("status_sick", "Sick")}</div>
                        <div class="shift-picker-option-meta">${t("schedule_status_sick_hint", "Blocks the whole day cell")}</div>
                    </button>
                    <button class="shift-picker-option status-picker-option" type="button" data-status-type="day_off">
                        <div class="shift-picker-option-title">${t("status_day_off", "Day off")}</div>
                        <div class="shift-picker-option-meta">${t("schedule_status_day_off_hint", "Marks the whole day as a day off")}</div>
                    </button>
                    <button class="shift-picker-option status-picker-option" type="button" data-status-type="vacation">
                        <div class="shift-picker-option-title">${t("status_vacation", "Vacation")}</div>
                        <div class="shift-picker-option-meta">${t("schedule_status_vacation_hint", "Marks the whole day as vacation")}</div>
                    </button>
                </div>
                <div class="shift-picker-group">
                    <div class="shift-picker-group-title">${t("schedule_shift_status", "Shift status")}</div>
                    ${dateEntries.length === 0 ? `
                        <div class="empty-text">${t("schedule_no_shifts_for_no_show", "No shifts available for no-show status")}</div>
                    ` : dateEntries.map(entry => `
                        <button class="shift-picker-option no-show-picker-option" type="button" data-entry-id="${entry.id}">
                            <div class="shift-picker-option-title">${escapeHtml(t("status_no_show", "No-show"))}: ${escapeHtml(entry.shift_template_name)}</div>
                            <div class="shift-picker-option-meta">
                                ${escapeHtml(getShiftCategoryLabel(entry.shift_category))} · ${escapeHtml(entry.start_time)} - ${escapeHtml(entry.end_time)}
                            </div>
                        </button>
                    `).join("")}
                </div>
            `;
        }

        function bindStatusPickerOptions(employeeId, date) {
            const body = document.getElementById("status-picker-body");

            body.querySelectorAll(".status-picker-option").forEach(button => {
                button.addEventListener("click", async () => {
                    const statusType = button.dataset.statusType;
                    button.disabled = true;
                    await saveDayStatus(employeeId, date, statusType);
                    closeStatusPicker();
                });
            });

            body.querySelectorAll(".no-show-picker-option").forEach(button => {
                button.addEventListener("click", async () => {
                    const entryId = Number(button.dataset.entryId);
                    button.disabled = true;
                    await updateScheduleEntryNoShow(entryId, true);
                    closeStatusPicker();
                });
            });
        }

        /* =========================================================
           CRUD: SCHEDULE / CRUD: РАСПИСАНИЕ
           ========================================================= */

        async function createScheduleEntry(employeeId, positionId, date, shiftTemplateId) {
            if (!canEditSchedule()) return;
            // Create schedule entry via backend / Создаём запись расписания через backend
            const payload = {
                employee_id: employeeId,
                position_id: positionId,
                date: date,
                shift_template_id: shiftTemplateId
            };

            try {
                const response = await fetch("/api/schedule", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    showMessage(errorData.detail || t("msg_failed_add_shift", "Failed to add shift."), "danger");
                    return;
                }

                await refreshScheduleEntriesOnly();
            } catch (error) {
                console.error(error);
                showMessage(t("msg_server_error_add_shift", "Server error while adding shift."), "danger");
            }
        }

        async function deleteScheduleEntry(entryId) {
            if (!canEditSchedule()) return;
            // Delete one schedule entry / Удаляем одну запись расписания
            try {
                const response = await fetch(`/api/schedule/${entryId}`, {
                    method: "DELETE"
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    showMessage(errorData.detail || t("msg_failed_delete_shift", "Failed to delete shift."), "danger");
                    return;
                }

                await refreshScheduleEntriesOnly();
            } catch (error) {
                console.error(error);
                showMessage(t("msg_server_error_delete_shift", "Server error while deleting shift."), "danger");
            }
        }

        async function updateScheduleEntryNoShow(entryId, noShow) {
            if (!canEditSchedule()) return;
            try {
                const response = await fetch(`/api/schedule/${entryId}/status`, {
                    method: "PATCH",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ no_show: noShow })
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    showMessage(errorData.detail || t("msg_failed_save_shift_status", "Failed to save shift status."), "danger");
                    return;
                }

                await refreshScheduleEntriesOnly();
            } catch (error) {
                console.error(error);
                showMessage(t("msg_server_error_save_shift_status", "Server error while saving shift status."), "danger");
            }
        }

        /* =========================================================
           CRUD: DAY STATUS / CRUD: СТАТУС ДНЯ
           ========================================================= */

        async function saveDayStatus(employeeId, date, statusType) {
            if (!canEditSchedule()) return;
            // Save or remove employee day status
            // Сохраняем или удаляем статус сотрудника на день
            try {
                let response;

                if (!statusType) {
                    // Remove status if user selected empty value
                    // Удаляем статус, если пользователь выбрал пустое значение
                    response = await fetch(
                        `/api/employee-day-statuses?employee_id=${employeeId}&date=${encodeURIComponent(date)}`,
                        { method: "DELETE" }
                    );
                } else {
                    // Save status / Сохраняем статус
                    response = await fetch("/api/employee-day-statuses", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            employee_id: employeeId,
                            date: date,
                            status_type: statusType
                        })
                    });
                }

                if (!response.ok) {
                    const errorData = await response.json();
                    showMessage(errorData.detail || t("msg_failed_save_day_status", "Failed to save day status."), "danger");
                    return;
                }

                await refreshScheduleEntriesOnly();
            } catch (error) {
                console.error(error);
                showMessage(t("msg_server_error_save_day_status", "Server error while saving day status."), "danger");
            }
        }

        /* =========================================================
           PARTIAL REFRESH / ЧАСТИЧНОЕ ОБНОВЛЕНИЕ
           ========================================================= */

        async function refreshScheduleEntriesOnly() {
            // Refresh only entries and statuses, not all reference data
            // Обновляем только смены и статусы, не трогая весь справочник
            const positionId = Number(document.getElementById("position_select").value);

            try {
                const [scheduleResponse, dayStatusesResponse] = await Promise.all([
                    fetch("/api/schedule"),
                    fetch("/api/employee-day-statuses")
                ]);

                if (!scheduleResponse.ok || !dayStatusesResponse.ok) {
                    showMessage(t("msg_failed_refresh_schedule_data", "Failed to refresh schedule data."), "warning");
                    return;
                }

                allScheduleEntries = await scheduleResponse.json();
                allDayStatuses = await dayStatusesResponse.json();
                scheduleDataLoaded = true;
                renderScheduleTable(positionId);
                updateScheduleActionAvailability();
            } catch (error) {
                console.error(error);
                showMessage(t("msg_server_error_refresh_schedule_data", "Server error while refreshing schedule data."), "warning");
            }
        }
