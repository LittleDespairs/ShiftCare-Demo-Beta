(function () {
    const WEEK_START = getCurrentWeekStart();
    const WEEK_DATES = buildWeekDates(WEEK_START);
    let lastModel = null;

    function t(key, fallback = "") {
        if (typeof translate !== "function") {
            return fallback || key;
        }
        const value = translate(key);
        return value === key ? (fallback || key) : value;
    }

    function getCurrentWeekStart() {
        const today = new Date();
        const day = today.getDay();
        today.setHours(0, 0, 0, 0);
        today.setDate(today.getDate() - day);
        return formatDate(today);
    }

    function buildWeekDates(weekStart) {
        const base = new Date(`${weekStart}T00:00:00`);
        return Array.from({ length: 7 }, (_, index) => {
            const current = new Date(base);
            current.setDate(base.getDate() + index);
            return formatDate(current);
        });
    }

    function formatDate(date) {
        return date.toISOString().slice(0, 10);
    }

    function setText(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    function setNextStep(step) {
        setText("home-next-title", t(step.titleKey, step.titleFallback));
        setText("home-next-text", t(step.textKey, step.textFallback));
        const action = document.getElementById("home-next-action");
        if (action) {
            action.href = step.href;
            action.textContent = t(step.actionKey, step.actionFallback);
        }
    }

    async function requestJson(url) {
        const response = await fetch(url);
        const payload = await response.json().catch(() => null);
        if (!response.ok) {
            const error = new Error(payload?.detail || `Request failed with ${response.status}`);
            error.status = response.status;
            throw error;
        }
        return payload;
    }

    async function safeRequest(url) {
        try {
            return { data: await requestJson(url), error: null };
        } catch (error) {
            return { data: null, error };
        }
    }

    function arrayData(result) {
        return Array.isArray(result?.data) ? result.data : [];
    }

    function getProtectedError(results) {
        return Object.values(results).find(result => [401, 403].includes(Number(result?.error?.status)))?.error || null;
    }

    function getFirstPosition(positions) {
        return positions.find(position => position && Number(position.id)) || null;
    }

    function isReady(result, minimum = 1) {
        if (result?.error) return false;
        return arrayData(result).length >= minimum;
    }

    function isLicenseReady(license) {
        if (license.error) return false;
        const status = String(license.data?.status || "").toLowerCase();
        return ["active", "trial", "grace"].includes(status);
    }

    function countCurrentWeekEntries(entries) {
        return entries.filter(entry => WEEK_DATES.includes(entry.date)).length;
    }

    function resolveNextStep(model) {
        const protectedError = getProtectedError({
            employees: model.employees,
            positions: model.positions,
            assignments: model.assignments,
            templates: model.templates,
            coverage: model.coverage,
            preferences: model.preferences,
            schedule: model.schedule
        });

        if (protectedError) {
            return {
                titleKey: "home_auth_required_title",
                titleFallback: "Sign in to continue",
                textKey: "home_auth_required_text",
                textFallback: "The workspace is protected. Sign in before editing employees, positions, and schedules.",
                actionKey: "home_auth_required_action",
                actionFallback: "Open login",
                href: "/login"
            };
        }

        if (model.auth.data?.bootstrap_available) {
            return {
                titleKey: "home_setup_auth_title",
                titleFallback: "Create organization access",
                textKey: "home_setup_auth_text",
                textFallback: "No active users are configured yet. Start by creating or authorizing an organization user.",
                actionKey: "home_setup_auth_action",
                actionFallback: "Set up access",
                href: "/login"
            };
        }

        if (!isReady(model.employees)) {
            return {
                titleKey: "home_setup_employees_title",
                titleFallback: "Add the care team",
                textKey: "home_setup_employees_text",
                textFallback: "The schedule needs employees before positions, preferences, and generation can be useful.",
                actionKey: "home_setup_employees_action",
                actionFallback: "Open employees",
                href: "/employees"
            };
        }

        if (!isReady(model.positions)) {
            return {
                titleKey: "home_setup_positions_title",
                titleFallback: "Create positions",
                textKey: "home_setup_positions_text",
                textFallback: "Positions define where people can work and how the schedule is separated.",
                actionKey: "home_setup_positions_action",
                actionFallback: "Open settings",
                href: "/settings"
            };
        }

        if (!isReady(model.assignments)) {
            return {
                titleKey: "home_setup_assignments_title",
                titleFallback: "Assign people to positions",
                textKey: "home_setup_assignments_text",
                textFallback: "The generator ignores employees who are not linked to the selected position.",
                actionKey: "home_setup_assignments_action",
                actionFallback: "Open assignments",
                href: "/settings"
            };
        }

        if (!isReady(model.templates)) {
            return {
                titleKey: "home_setup_templates_title",
                titleFallback: "Create shift templates",
                textKey: "home_setup_templates_text",
                textFallback: "Templates describe the real shift times used by manual editing and auto-generation.",
                actionKey: "home_setup_templates_action",
                actionFallback: "Open templates",
                href: "/settings"
            };
        }

        if (!isReady(model.coverage)) {
            return {
                titleKey: "home_setup_coverage_title",
                titleFallback: "Set coverage rules",
                textKey: "home_setup_coverage_text",
                textFallback: "Coverage rules tell the app how many employees are needed across the week.",
                actionKey: "home_setup_coverage_action",
                actionFallback: "Open coverage",
                href: "/settings"
            };
        }

        if (model.currentWeekEntries === 0) {
            return {
                titleKey: "home_setup_schedule_title",
                titleFallback: "Build this week's schedule",
                textKey: "home_setup_schedule_text",
                textFallback: "The setup is ready. Open the schedule page and fill the current week.",
                actionKey: "home_setup_schedule_action",
                actionFallback: "Open schedule",
                href: "/schedule"
            };
        }

        return {
            titleKey: "home_setup_review_title",
            titleFallback: "Review the current week",
            textKey: "home_setup_review_text",
            textFallback: "The workspace has live schedule data. Review coverage and employee preferences before sharing.",
            actionKey: "home_setup_review_action",
            actionFallback: "Review schedule",
            href: "/schedule"
        };
    }

    function renderReadinessItem(name, options) {
        const item = document.querySelector(`[data-home-readiness="${name}"]`);
        if (!item) return false;

        item.classList.remove("ready", "attention", "unknown");
        const value = item.querySelector("strong");
        if (options.error) {
            item.classList.add("unknown");
            value.textContent = t("home_status_unknown", "Unknown");
            return false;
        }

        if (options.ready) {
            item.classList.add("ready");
            value.textContent = options.value || t("home_status_ready", "Ready");
            return true;
        }

        item.classList.add("attention");
        value.textContent = options.value || t("home_status_attention", "Needs setup");
        return false;
    }

    function renderModel(model) {
        lastModel = model;
        const employees = arrayData(model.employees);
        const positions = arrayData(model.positions);
        const assignments = arrayData(model.assignments);
        const templates = arrayData(model.templates);
        const coverage = arrayData(model.coverage);
        const preferences = arrayData(model.preferences);
        const scheduleEntries = arrayData(model.schedule);
        const position = getFirstPosition(positions);
        const positionCoverage = position ? coverage.filter(item => item.position_id === position.id) : coverage;
        const readyStates = [
            renderReadinessItem("employees", {
                ready: employees.length > 0,
                value: employees.length ? String(employees.length) : "",
                error: model.employees.error
            }),
            renderReadinessItem("positions", {
                ready: positions.length > 0,
                value: positions.length ? String(positions.length) : "",
                error: model.positions.error
            }),
            renderReadinessItem("assignments", {
                ready: assignments.length > 0,
                value: assignments.length ? String(assignments.length) : "",
                error: model.assignments.error
            }),
            renderReadinessItem("templates", {
                ready: templates.length > 0,
                value: templates.length ? String(templates.length) : "",
                error: model.templates.error
            }),
            renderReadinessItem("coverage", {
                ready: coverage.length > 0,
                value: coverage.length ? String(coverage.length) : "",
                error: model.coverage.error
            }),
            renderReadinessItem("license", {
                ready: isLicenseReady(model.license),
                value: model.license.data?.status || "",
                error: model.license.error
            })
        ];

        model.currentWeekEntries = countCurrentWeekEntries(scheduleEntries);
        setNextStep(resolveNextStep(model));
        setText("home-week-label", `${WEEK_DATES[0]} - ${WEEK_DATES[6]}`);
        setText("home-primary-position", position?.name || t("home_primary_position_fallback", "No position yet"));
        setText("home-schedule-count", String(model.currentWeekEntries));
        setText("home-preferences-count", model.preferences.error ? t("home_status_unknown", "Unknown") : String(preferences.length));
        setText("home-coverage-count", model.coverage.error ? t("home_status_unknown", "Unknown") : String(positionCoverage.length));

        const readyCount = readyStates.filter(Boolean).length;
        const readySummary = document.getElementById("home-ready-summary");
        if (readySummary) {
            readySummary.textContent = `${readyCount}/${readyStates.length}`;
            readySummary.classList.toggle("ready", readyCount === readyStates.length);
            readySummary.classList.toggle("attention", readyCount !== readyStates.length);
        }

        setText("home-active-users", model.auth.error ? t("home_status_unknown", "Unknown") : String(model.auth.data?.active_user_count ?? 0));
        setText("home-environment", model.auth.error ? t("home_status_unknown", "Unknown") : String(model.auth.data?.environment || "-"));
        setText("home-app-version", model.auth.data?.app_version || document.body?.dataset?.appVersion || "-");
        setText("home-license-status", model.license.error ? t("home_status_unknown", "Unknown") : String(model.license.data?.status || "-"));
        setText("home-license-usage", formatLicenseUsage(model.license.data));
    }

    function formatLicenseUsage(license) {
        if (!license) return t("home_status_unknown", "Unknown");
        const count = Number.isFinite(Number(license.employee_count)) ? Number(license.employee_count) : 0;
        const limit = Number.isFinite(Number(license.employee_limit)) ? Number(license.employee_limit) : null;
        return limit ? `${count}/${limit}` : String(count);
    }

    async function loadHome() {
        const [
            auth,
            license,
            employees,
            positions,
            assignments,
            templates,
            coverage,
            preferences
        ] = await Promise.all([
            safeRequest("/api/auth/status"),
            safeRequest("/api/license/status"),
            safeRequest("/api/employees"),
            safeRequest("/api/positions"),
            safeRequest("/api/employee-positions"),
            safeRequest("/api/shift-templates"),
            safeRequest("/api/coverage-requirements"),
            safeRequest(`/api/employee-week-preferences?week_start_date=${encodeURIComponent(WEEK_START)}`)
        ]);

        const firstPosition = getFirstPosition(arrayData(positions));
        const schedule = firstPosition
            ? await safeRequest(`/api/schedule?position_id=${encodeURIComponent(firstPosition.id)}`)
            : { data: [], error: positions.error };

        renderModel({
            auth,
            license,
            employees,
            positions,
            assignments,
            templates,
            coverage,
            preferences,
            schedule,
            currentWeekEntries: 0
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        loadHome().catch(() => {
            setNextStep({
                titleKey: "home_load_error_title",
                titleFallback: "Could not read workspace",
                textKey: "home_load_error_text",
                textFallback: "Refresh the page or open the schedule directly if the local API is still starting.",
                actionKey: "home_setup_schedule_action",
                actionFallback: "Open schedule",
                href: "/schedule"
            });
        });
    });

    document.addEventListener("app-language-changed", () => {
        if (lastModel) {
            renderModel(lastModel);
        }
    });
})();
