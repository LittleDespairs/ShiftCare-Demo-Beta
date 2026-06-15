let editingEmployeeId = null; // Track editing mode / Отслеживаем режим редактирования
let currentEmployees = [];
let currentEmployeePositions = [];
let currentEmployeePositionOptions = [];
let currentEmployeeFilters = {
    search: "",
    sex: "",
    positionId: "",
    capability: "",
};
let currentRecurringPreferences = createEmptyRecurringPreferenceState();
let employeeAppSettings = {};
let pendingRecurringTarget = null;

const RECURRING_PREFERENCE_KINDS = ["strict", "soft"];
const RECURRING_PREFERENCE_DAYS = [
    ["weekday_sunday", "Sunday"],
    ["weekday_monday", "Monday"],
    ["weekday_tuesday", "Tuesday"],
    ["weekday_wednesday", "Wednesday"],
    ["weekday_thursday", "Thursday"],
    ["weekday_friday", "Friday"],
    ["weekday_saturday", "Saturday"],
];
const RECURRING_PREFERENCE_OPTIONS = [
    ["no_preference", "preference_no_preference", "No preference"],
    ["off_day", "preference_off_day", "Day off"],
    ["vacation", "preference_vacation", "Vacation"],
    ["only_morning", "preference_only_morning", "Only morning"],
    ["only_evening", "preference_only_evening", "Only evening"],
    ["only_night", "preference_only_night", "Only night"],
    ["not_morning", "preference_not_morning", "Not morning"],
    ["not_evening", "preference_not_evening", "Not evening"],
    ["not_night", "preference_not_night", "Not night"],
    ["no_morning_evening_combo", "preference_no_morning_evening_combo", "No morning + evening combo"],
];
const RECURRING_CATEGORY_LABELS = {
    morning: ["shift_morning", "Morning"],
    evening: ["shift_evening", "Evening"],
    night: ["shift_night", "Night"],
};

function employeeText(key, fallback = "") {
    if (typeof translate === "function") {
        return translate(key);
    }
    return fallback || key;
}

function formatDeleteImpactList(items) {
    const rows = items
        .filter(item => item && item.label)
        .map(item => `<li><strong>${escapeHtml(item.label)}:</strong> ${escapeHtml(item.value ?? 0)}</li>`)
        .join("");
    return rows ? `<ul>${rows}</ul>` : "";
}

function boolBadge(value) {
    return value
        ? `<span class="mini-badge yes">${employeeText("common_yes", "Yes")}</span>`
        : `<span class="mini-badge no">${employeeText("common_no", "No")}</span>`;
}

function employeeSexLabel(sex) {
    if (sex === "male") return employeeText("employees_sex_male", "Male");
    if (sex === "female") return employeeText("employees_sex_female", "Female");
    return sex || "";
}

// Initialize page / Инициализация страницы
document.addEventListener("DOMContentLoaded", async () => {
    const employeeForm = document.getElementById("employee-form");

    if (employeeForm) {
        employeeForm.addEventListener("submit", handleEmployeeSubmit);
    }
    const tableBody = document.getElementById("employees-table-body");
    if (tableBody) {
        tableBody.addEventListener("click", handleEmployeesTableClick);
    }
    bindEmployeeFilters();
    bindEmployeeModal();
    bindRecurringPreferenceModal();
    await loadEmployeeAppSettings();
    renderRecurringPreferenceControls();

    loadEmployees();
});

document.addEventListener("app-language-changed", () => {
    currentRecurringPreferences = collectRecurringPreferenceState();
    fillEmployeePositionFilter();
    renderFilteredEmployeesTable();
    renderRecurringPreferenceControls();
    updateEmployeeModalTitle();
    updateSubmitButtonText();
});

function normalizeEmployeeSearchText(value) {
    return String(value || "").toLowerCase().trim();
}

function filterCountText(shown, total) {
    return employeeText("common_filter_results", "Showing {shown} of {total}")
        .replace("{shown}", String(shown))
        .replace("{total}", String(total));
}

function refreshEmployeeSelect(select) {
    if (select && typeof refreshSelectTrigger === "function") {
        refreshSelectTrigger(select);
    }
}

function buildEmployeePositionOptions(assignments) {
    const optionsById = new Map();
    (assignments || []).forEach(item => {
        const positionId = Number(item?.position_id || 0);
        const positionName = item?.position_name || item?.position?.name || "";
        if (positionId && positionName && !optionsById.has(positionId)) {
            optionsById.set(positionId, positionName);
        }
    });

    return [...optionsById.entries()]
        .map(([id, name]) => ({ id, name }))
        .sort((first, second) => first.name.localeCompare(second.name));
}

function fillEmployeePositionFilter() {
    const select = document.getElementById("employee-position-filter");
    if (!select) return;

    const currentValue = currentEmployeeFilters.positionId;
    select.innerHTML = `
        <option value="">${employeeText("common_filter_all", "All")}</option>
        ${currentEmployeePositionOptions.map(position => `
            <option value="${Number(position.id)}">${escapeHtml(position.name)}</option>
        `).join("")}
    `;

    if ([...select.options].some(option => option.value === currentValue)) {
        select.value = currentValue;
    } else {
        currentEmployeeFilters.positionId = "";
    }

    refreshEmployeeSelect(select);
}

function employeeAssignedToPosition(employeeId, positionId) {
    if (!positionId) return true;
    return currentEmployeePositions.some(item =>
        Number(item?.employee_id) === Number(employeeId)
        && Number(item?.position_id) === Number(positionId)
    );
}

function getEmployeePositionNames(employeeId) {
    return currentEmployeePositions
        .filter(item => Number(item?.employee_id) === Number(employeeId))
        .map(item => item?.position_name || item?.position?.name || "")
        .filter(Boolean)
        .join(" ");
}

function bindEmployeeFilters() {
    const searchInput = document.getElementById("employee-search-input");
    const sexFilter = document.getElementById("employee-sex-filter");
    const positionFilter = document.getElementById("employee-position-filter");
    const capabilityFilter = document.getElementById("employee-capability-filter");
    const resetButton = document.getElementById("employees-filter-reset");

    searchInput?.addEventListener("input", () => {
        currentEmployeeFilters.search = searchInput.value;
        renderFilteredEmployeesTable();
    });
    sexFilter?.addEventListener("change", () => {
        currentEmployeeFilters.sex = sexFilter.value;
        renderFilteredEmployeesTable();
    });
    positionFilter?.addEventListener("change", () => {
        currentEmployeeFilters.positionId = positionFilter.value;
        renderFilteredEmployeesTable();
    });
    capabilityFilter?.addEventListener("change", () => {
        currentEmployeeFilters.capability = capabilityFilter.value;
        renderFilteredEmployeesTable();
    });
    resetButton?.addEventListener("click", () => {
        currentEmployeeFilters = { search: "", sex: "", positionId: "", capability: "" };
        if (searchInput) searchInput.value = "";
        if (sexFilter) sexFilter.value = "";
        if (positionFilter) positionFilter.value = "";
        if (capabilityFilter) capabilityFilter.value = "";
        [sexFilter, positionFilter, capabilityFilter].forEach(refreshEmployeeSelect);
        renderFilteredEmployeesTable();
    });
}

function getFilteredEmployees() {
    const query = normalizeEmployeeSearchText(currentEmployeeFilters.search);
    const sex = currentEmployeeFilters.sex;
    const positionId = Number(currentEmployeeFilters.positionId || 0);
    const capability = currentEmployeeFilters.capability;

    return currentEmployees.filter(employee => {
        const haystack = normalizeEmployeeSearchText([
            employee.id,
            employee.id_card,
            employee.full_name,
            employee.sex,
            getEmployeePositionNames(employee.id),
        ].join(" "));
        if (query && !haystack.includes(query)) return false;
        if (sex && employee.sex !== sex) return false;
        if (positionId && !employeeAssignedToPosition(employee.id, positionId)) return false;
        if (capability && !employee[capability]) return false;
        return true;
    });
}

function updateEmployeeFilterCount(shown, total) {
    const count = document.getElementById("employees-filter-count");
    if (!count) return;
    count.textContent = total ? filterCountText(shown, total) : "";
}

function renderFilteredEmployeesTable() {
    const filteredEmployees = getFilteredEmployees();
    renderEmployeesTable(filteredEmployees);
    updateEmployeeFilterCount(filteredEmployees.length, currentEmployees.length);
}

function createEmptyRecurringPreferenceState() {
    return {
        strict: Array(7).fill("no_preference"),
        soft: Array(7).fill("no_preference"),
    };
}

function canManagePermanentPreferences() {
    const membership = window.scheduleAuth?.getActiveMembership?.();
    if (!membership) return true;
    return ["owner", "admin"].includes(membership.role);
}

function applyEmployeeShiftColorSettings(settings = {}) {
    employeeAppSettings = settings || {};
    const colorMap = {
        "--shift-morning-bg": employeeAppSettings.schedule_morning_color || "#ecfeff",
        "--shift-evening-bg": employeeAppSettings.schedule_evening_color || "#fff7ed",
        "--shift-night-bg": employeeAppSettings.schedule_night_color || "#eef2ff",
        "--shift-status-bg": employeeAppSettings.schedule_status_color || "#f5f3ff",
    };
    [
        document.documentElement,
        document.body,
        document.querySelector(".page-shell"),
        document.getElementById("employee-modal-overlay"),
        document.getElementById("recurring-request-modal-overlay"),
    ].filter(Boolean).forEach((target) => {
        Object.entries(colorMap).forEach(([property, value]) => {
            target.style.setProperty(property, value);
        });
    });
}

async function loadEmployeeAppSettings() {
    try {
        const response = await fetch("/api/app-settings");
        if (!response.ok) throw new Error("Failed to load app settings");
        applyEmployeeShiftColorSettings(await response.json());
    } catch (error) {
        console.error("Load employee app settings error:", error);
        applyEmployeeShiftColorSettings({});
    }
}

function collectRecurringPreferenceState() {
    const state = createEmptyRecurringPreferenceState();
    RECURRING_PREFERENCE_KINDS.forEach(kind => {
        for (let day = 0; day < 7; day += 1) {
            const select = document.querySelector(`[data-recurring-kind="${kind}"][data-recurring-day="${day}"]`);
            if (select && select.tagName === "SELECT") {
                state[kind][day] = select.value || "no_preference";
            } else if (currentRecurringPreferences?.[kind]?.[day]) {
                state[kind][day] = currentRecurringPreferences[kind][day];
            }
        }
    });
    return state;
}

function recurringPreferenceOptionsHtml(selectedValue) {
    return RECURRING_PREFERENCE_OPTIONS.map(([value, key, fallback]) => `
        <option value="${value}" ${selectedValue === value ? "selected" : ""}>
            ${employeeText(key, fallback)}
        </option>
    `).join("");
}

function recurringPreferenceLabel(preferenceType) {
    const option = RECURRING_PREFERENCE_OPTIONS.find(([value]) => value === preferenceType);
    if (!option) return preferenceType || employeeText("preference_no_preference", "No preference");
    return employeeText(option[1], option[2]);
}

function recurringPreferenceCardClass(preferenceType) {
    if (preferenceType === "off_day" || preferenceType === "vacation") return "block";
    if (preferenceType === "no_morning_evening_combo") return "combo";
    if (preferenceType.includes("morning")) return `morning ${preferenceType.startsWith("not_") ? "exclude" : ""}`.trim();
    if (preferenceType.includes("evening")) return `evening ${preferenceType.startsWith("not_") ? "exclude" : ""}`.trim();
    if (preferenceType.includes("night")) return `night ${preferenceType.startsWith("not_") ? "exclude" : ""}`.trim();
    return "";
}

function recurringPreferenceToRequest(preferenceType) {
    if (preferenceType?.startsWith("only_")) {
        return { requestType: "request_shift", category: preferenceType.replace("only_", "") };
    }
    if (preferenceType?.startsWith("not_")) {
        return { requestType: "exclude_shift", category: preferenceType.replace("not_", "") };
    }
    return { requestType: preferenceType || "no_preference", category: "morning" };
}

function recurringRequestToPreference(requestType, category) {
    if (requestType === "request_shift") return `only_${category || "morning"}`;
    if (requestType === "exclude_shift") return `not_${category || "morning"}`;
    return requestType || "no_preference";
}

function renderRecurringPreferenceControls() {
    const canManage = canManagePermanentPreferences();
    const disabledNote = document.getElementById("permanent-preferences-disabled-note");
    if (disabledNote) {
        disabledNote.hidden = canManage;
    }
    RECURRING_PREFERENCE_KINDS.forEach(kind => {
        const container = document.getElementById(`recurring-${kind}-preferences`);
        if (!container) return;
        container.innerHTML = RECURRING_PREFERENCE_DAYS.map(([dayKey, dayFallback], dayIndex) => {
            const selectedValue = currentRecurringPreferences?.[kind]?.[dayIndex] || "no_preference";
            return `
                <div class="recurring-preference-row">
                    <span class="recurring-preference-day">${employeeText(dayKey, dayFallback)}</span>
                    <button
                        class="recurring-preference-card ${recurringPreferenceCardClass(selectedValue)}"
                        type="button"
                        data-recurring-kind="${kind}"
                        data-recurring-day="${dayIndex}"
                        ${canManage ? "" : "disabled"}
                    >
                        <span>${escapeHtml(recurringPreferenceLabel(selectedValue))}</span>
                        <span class="recurring-preference-action">${employeeText("employees_recurring_change", "Change")}</span>
                    </button>
                </div>
            `;
        }).join("");
    });
}

function bindRecurringPreferenceModal() {
    document.querySelectorAll("[data-recurring-request-type]").forEach(button => {
        button.addEventListener("click", () => setRecurringRequestType(button.dataset.recurringRequestType));
    });
    document.querySelectorAll("[data-recurring-category]").forEach(button => {
        button.addEventListener("click", () => setRecurringCategory(button.dataset.recurringCategory));
    });
    document.getElementById("recurring-request-modal-save")?.addEventListener("click", savePendingRecurringPreference);
    document.getElementById("recurring-request-modal-close")?.addEventListener("click", closeRecurringPreferenceModal);
    document.getElementById("recurring-request-modal-cancel")?.addEventListener("click", closeRecurringPreferenceModal);
    document.getElementById("recurring-request-modal-overlay")?.addEventListener("click", event => {
        if (event.target.id === "recurring-request-modal-overlay") closeRecurringPreferenceModal();
    });
    document.addEventListener("click", event => {
        const button = event.target.closest("[data-recurring-kind][data-recurring-day]");
        if (!button || button.disabled || button.tagName !== "BUTTON") return;
        openRecurringPreferenceModal(button.dataset.recurringKind, Number(button.dataset.recurringDay));
    });
}

function openRecurringPreferenceModal(kind, dayIndex) {
    pendingRecurringTarget = { kind, dayIndex };
    const preferenceType = currentRecurringPreferences?.[kind]?.[dayIndex] || "no_preference";
    const { requestType, category } = recurringPreferenceToRequest(preferenceType);
    setRecurringRequestType(requestType);
    setRecurringCategory(category || "morning");
    const title = document.getElementById("recurring-request-modal-title");
    if (title) {
        const day = RECURRING_PREFERENCE_DAYS[dayIndex];
        title.textContent = `${employeeText(day?.[0], day?.[1] || "")} · ${kind === "strict" ? employeeText("employees_permanent_strict_title", "Strict wishes") : employeeText("employees_permanent_soft_title", "Preferences")}`;
    }
    const overlay = document.getElementById("recurring-request-modal-overlay");
    overlay?.classList.add("is-open");
    overlay?.setAttribute("aria-hidden", "false");
}

function closeRecurringPreferenceModal() {
    pendingRecurringTarget = null;
    const overlay = document.getElementById("recurring-request-modal-overlay");
    overlay?.classList.remove("is-open");
    overlay?.setAttribute("aria-hidden", "true");
}

function setRecurringRequestType(requestType) {
    const valueInput = document.getElementById("recurring_request_value");
    if (valueInput) valueInput.value = requestType;
    document.getElementById("recurring-category-field").hidden = !["request_shift", "exclude_shift"].includes(requestType);
    document.querySelectorAll("[data-recurring-request-type]").forEach(button => {
        const isSelected = button.dataset.recurringRequestType === requestType;
        button.classList.toggle("is-selected", isSelected);
        button.setAttribute("aria-checked", String(isSelected));
    });
}

function setRecurringCategory(category) {
    const valueInput = document.getElementById("recurring_category_value");
    if (valueInput) valueInput.value = category;
    document.querySelectorAll("[data-recurring-category]").forEach(button => {
        const isSelected = button.dataset.recurringCategory === category;
        button.classList.toggle("is-selected", isSelected);
        button.setAttribute("aria-checked", String(isSelected));
    });
}

function savePendingRecurringPreference() {
    if (!pendingRecurringTarget) return;
    const requestType = document.getElementById("recurring_request_value")?.value || "no_preference";
    const category = document.getElementById("recurring_category_value")?.value || "morning";
    currentRecurringPreferences[pendingRecurringTarget.kind][pendingRecurringTarget.dayIndex] = recurringRequestToPreference(requestType, category);
    renderRecurringPreferenceControls();
    closeRecurringPreferenceModal();
}

async function loadEmployeeRecurringPreferences(employeeId) {
    currentRecurringPreferences = createEmptyRecurringPreferenceState();
    renderRecurringPreferenceControls();
    if (!employeeId || !canManagePermanentPreferences()) {
        return;
    }
    try {
        const response = await fetch(`/api/employee-recurring-preferences?employee_id=${encodeURIComponent(employeeId)}`);
        if (!response.ok) {
            showMessage(employeeText("msg_failed_load_permanent_preferences", "Failed to load permanent wishes."), "warning");
            return;
        }
        const rules = await response.json();
        const nextState = createEmptyRecurringPreferenceState();
        rules.forEach(rule => {
            if (
                RECURRING_PREFERENCE_KINDS.includes(rule.preference_kind)
                && Number.isInteger(Number(rule.day_of_week))
                && Number(rule.day_of_week) >= 0
                && Number(rule.day_of_week) <= 6
            ) {
                nextState[rule.preference_kind][Number(rule.day_of_week)] = rule.preference_type || "no_preference";
            }
        });
        currentRecurringPreferences = nextState;
        renderRecurringPreferenceControls();
    } catch (error) {
        console.error("Load permanent preferences error:", error);
        showMessage(employeeText("msg_server_error_load_permanent_preferences", "Server error while loading permanent wishes."), "warning");
    }
}

async function saveEmployeeRecurringPreferences(employeeId) {
    if (!employeeId || !canManagePermanentPreferences()) {
        return;
    }
    const state = collectRecurringPreferenceState();
    const rules = [];
    RECURRING_PREFERENCE_KINDS.forEach(kind => {
        state[kind].forEach((preferenceType, dayOfWeek) => {
            rules.push({
                preference_kind: kind,
                day_of_week: dayOfWeek,
                preference_type: preferenceType || "no_preference",
            });
        });
    });
    const response = await fetch("/api/employee-recurring-preferences", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            employee_id: employeeId,
            rules,
        }),
    });
    if (!response.ok) {
        const errorText = await response.text();
        console.error("Save permanent preferences error:", errorText);
        throw new Error(employeeText("msg_failed_save_permanent_preferences", "Failed to save permanent wishes."));
    }
}

function bindEmployeeModal() {
    const addButton = document.getElementById("open-employee-modal-btn");
    const overlay = document.getElementById("employee-modal-overlay");
    const closeButton = document.getElementById("employee-modal-close");
    const cancelButton = document.getElementById("employee-modal-cancel");

    if (addButton) {
        addButton.dataset.employeeModalBound = "1";
        addButton.addEventListener("click", () => {
            resetForm();
            openEmployeeModal("add");
        });
    }

    [closeButton, cancelButton].forEach(button => {
        if (button) {
            button.addEventListener("click", closeEmployeeModal);
        }
    });

    if (overlay) {
        overlay.addEventListener("click", event => {
            if (event.target === overlay) {
                closeEmployeeModal();
            }
        });
    }

    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && overlay?.classList.contains("is-open")) {
            closeEmployeeModal();
        }
    });
}

function openEmployeeModal(mode = "add") {
    const overlay = document.getElementById("employee-modal-overlay");
    if (!overlay) return;
    overlay.dataset.mode = mode;
    updateEmployeeModalTitle();
    updateSubmitButtonText();
    overlay.classList.add("is-open");
    overlay.setAttribute("aria-hidden", "false");
    const firstInput = document.getElementById("full_name");
    if (firstInput) {
        firstInput.focus();
    }
}

function closeEmployeeModal() {
    const overlay = document.getElementById("employee-modal-overlay");
    if (!overlay) return;
    overlay.classList.remove("is-open");
    overlay.setAttribute("aria-hidden", "true");
}

function updateEmployeeModalTitle() {
    const title = document.getElementById("employee-modal-title");
    if (!title) return;
    title.textContent = editingEmployeeId === null
        ? employeeText("employees_add_button", "Add employee")
        : employeeText("employees_update_button", "Update employee");
}

function updateSubmitButtonText() {
    const submitButton = document.getElementById("submit-button");
    if (!submitButton) return;
    submitButton.textContent = editingEmployeeId === null
        ? employeeText("employees_add_button", "Add employee")
        : employeeText("employees_update_button", "Update employee");
}


// Load all employees / Загружаем всех сотрудников
async function loadEmployees() {
    try {
        const [employeesResponse, positionsResponse] = await Promise.all([
            fetch("/api/employees"),
            fetch("/api/employee-positions"),
        ]);

        if (!employeesResponse.ok) {
            showMessage(employeeText("msg_failed_load_employees", "Failed to load employees."), "danger");
            return;
        }

        currentEmployees = await employeesResponse.json();
        if (positionsResponse.ok) {
            currentEmployeePositions = await positionsResponse.json();
        } else {
            currentEmployeePositions = [];
            showMessage(employeeText("msg_failed_load_positions", "Failed to load positions."), "warning");
        }
        currentEmployeePositionOptions = buildEmployeePositionOptions(currentEmployeePositions);
        fillEmployeePositionFilter();
        renderFilteredEmployeesTable();
    } catch (error) {
        console.error("Load employees error:", error);
        showMessage(employeeText("msg_server_error_load_employees", "Server error while loading employees."), "danger");
    }
}


// Handle form submit / Обрабатываем отправку формы
async function handleEmployeeSubmit(event) {
    event.preventDefault();

    const fullName = document.getElementById("full_name").value.trim();
    const idCard = document.getElementById("id_card").value.replace(/\D+/g, "");
    const sex = document.getElementById("sex").value;
    const minShifts = Number(document.getElementById("min_shifts_per_week").value);
    const targetShifts = Number(document.getElementById("target_shifts_per_week").value);
    const maxShifts = Number(document.getElementById("max_shifts_per_week").value);

    const canWorkNight = document.getElementById("can_work_night").checked;
    const canWorkWeekends = document.getElementById("can_work_weekends").checked;
    const canWorkEveningsAfterNight = document.getElementById("can_work_evenings_after_night").checked;
    const canWorkMorningsAndEvenings = document.getElementById("can_work_mornings_and_evenings").checked;

    // Basic validation / Базовая валидация
    if (!fullName) {
        showMessage(employeeText("msg_enter_employee_full_name", "Please enter full name."), "warning");
        return;
    }

    if (!sex) {
        showMessage(employeeText("msg_select_employee_sex", "Please select sex."), "warning");
        return;
    }

    if (minShifts > maxShifts) {
        showMessage(employeeText("msg_min_gt_max_shifts", "Min shifts cannot be greater than max shifts."), "warning");
        return;
    }

    if (targetShifts < minShifts) {
        showMessage(employeeText("msg_target_lt_min_shifts", "Target shifts cannot be less than min shifts."), "warning");
        return;
    }

    if (targetShifts > maxShifts) {
        showMessage(employeeText("msg_target_gt_max_shifts", "Target shifts cannot be greater than max shifts."), "warning");
        return;
    }

    const employeeData = {
        id_card: idCard || null,
        full_name: fullName,
        sex: sex,
        min_shifts_per_week: minShifts,
        target_shifts_per_week: targetShifts,
        max_shifts_per_week: maxShifts,
        can_work_night: canWorkNight,
        can_work_weekends: canWorkWeekends,
        can_work_evenings_after_night: canWorkEveningsAfterNight,
        can_work_mornings_and_evenings: canWorkMorningsAndEvenings
    };

    try {
        let response;

        if (editingEmployeeId !== null) {
            // Update existing employee / Обновляем существующего сотрудника
            response = await fetch(`/api/employees/${editingEmployeeId}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(employeeData)
            });
        } else {
            // Create new employee / Создаём нового сотрудника
            response = await fetch("/api/employees", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(employeeData)
            });
        }

        if (!response.ok) {
            const errorText = await response.text();
            console.error("Submit error:", errorText);
            showMessage(employeeText("msg_employee_operation_failed", "Operation failed."), "danger");
            return;
        }

        const result = await response.json();
        const savedEmployeeId = editingEmployeeId !== null ? editingEmployeeId : result.employee?.id;
        await saveEmployeeRecurringPreferences(savedEmployeeId);
        const backupSuffix = result.backup_name
            ? ` ${employeeText("common_recovery_backup", "Recovery backup")}: ${result.backup_name}`
            : "";
        showMessage(`${result.message}${backupSuffix}`, "success");

        resetForm();
        closeEmployeeModal();
        await loadEmployees();
    } catch (error) {
        console.error("Submit employee error:", error);
        showMessage(error?.message || employeeText("msg_server_error_save_employee", "Server error while saving employee."), "danger");
    }
}


// Fill form for editing / Заполняем форму для редактирования
function editEmployee(employee) {
    currentRecurringPreferences = createEmptyRecurringPreferenceState();
    renderRecurringPreferenceControls();
    document.getElementById("id_card").value = employee.id_card || "";
    document.getElementById("full_name").value = employee.full_name;
    document.getElementById("sex").value = employee.sex;
    document.getElementById("sex").dispatchEvent(new Event("change", { bubbles: true }));
    document.getElementById("min_shifts_per_week").value = employee.min_shifts_per_week;
    document.getElementById("target_shifts_per_week").value = employee.target_shifts_per_week;
    document.getElementById("max_shifts_per_week").value = employee.max_shifts_per_week;

    document.getElementById("can_work_night").checked = employee.can_work_night;
    document.getElementById("can_work_weekends").checked = employee.can_work_weekends;
    document.getElementById("can_work_evenings_after_night").checked = employee.can_work_evenings_after_night;
    document.getElementById("can_work_mornings_and_evenings").checked = employee.can_work_mornings_and_evenings;

    editingEmployeeId = employee.id;

    const submitButton = document.getElementById("submit-button");
    if (submitButton) {
        submitButton.textContent = employeeText("employees_update_button", "Update employee");
    }

    openEmployeeModal("edit");
    loadEmployeeRecurringPreferences(employee.id);
}


// Delete employee / Удаляем сотрудника
async function deleteEmployee(employeeId) {
    let confirmMessage = `<p>${escapeHtml(employeeText("msg_confirm_delete_employee", "Are you sure you want to delete this employee?"))}</p>`;

    try {
        const impactResponse = await fetch(`/api/employees/${employeeId}/delete-impact`);
        if (impactResponse.ok) {
            const impact = await impactResponse.json();
            confirmMessage += formatDeleteImpactList([
                { label: employeeText("confirm_impact_employee", "Employee"), value: impact.employee_name },
                { label: employeeText("confirm_impact_assignments", "Assignments"), value: impact.assignments },
                { label: employeeText("confirm_impact_schedule_entries", "Schedule entries"), value: impact.schedule_entries },
                { label: employeeText("confirm_impact_general_preferences", "General preferences"), value: impact.general_preferences },
                { label: employeeText("confirm_impact_weekly_preferences", "Weekly preferences"), value: impact.weekly_preferences },
                { label: employeeText("confirm_impact_recurring_preferences", "Permanent wishes"), value: impact.recurring_preferences },
                { label: employeeText("confirm_impact_day_statuses", "Day statuses"), value: impact.day_statuses }
            ]);
        } else {
            confirmMessage += `<p>${escapeHtml(employeeText("confirm_impact_fetch_failed", "Could not load related records. Review carefully before deleting."))}</p>`;
        }
    } catch (error) {
        console.error("Load employee delete impact error:", error);
        confirmMessage += `<p>${escapeHtml(employeeText("confirm_impact_fetch_failed", "Could not load related records. Review carefully before deleting."))}</p>`;
    }

    const isConfirmed = await appConfirm(confirmMessage, {
        confirmText: employeeText("common_delete", "Delete"),
        html: true
    });

    if (!isConfirmed) {
        return;
    }

    try {
        const response = await fetch(`/api/employees/${employeeId}`, {
            method: "DELETE"
        });

        if (!response.ok) {
            const errorData = await response.json();
            showMessage(errorData.detail || employeeText("msg_failed_delete_employee", "Failed to delete employee."), "danger");
            return;
        }

        const result = await response.json();
        const backupSuffix = result.backup_name
            ? ` ${employeeText("common_recovery_backup", "Recovery backup")}: ${result.backup_name}`
            : "";
        showMessage(`${result.message}${backupSuffix}`, "success");

        // If deleted employee was being edited / Если удалён редактируемый сотрудник
        if (editingEmployeeId === employeeId) {
            resetForm();
        }

        await loadEmployees();
    } catch (error) {
        console.error("Delete employee error:", error);
        showMessage(employeeText("msg_server_error_delete_employee", "Server error while deleting employee."), "danger");
    }
}


// Reset form state / Сбрасываем состояние формы
function resetForm() {
    const employeeForm = document.getElementById("employee-form");

    if (employeeForm) {
        employeeForm.reset();
    }

    editingEmployeeId = null;
    currentRecurringPreferences = createEmptyRecurringPreferenceState();
    renderRecurringPreferenceControls();

    const submitButton = document.getElementById("submit-button");
    if (submitButton) {
        submitButton.textContent = employeeText("employees_add_button", "Add employee");
    }
    updateEmployeeModalTitle();
}


// Render employees table / Отрисовываем таблицу сотрудников
function renderEmployeesTable(employees) {
    const tableBody = document.getElementById("employees-table-body");

    if (!tableBody) {
        return;
    }

    if (employees.length === 0) {
        const hasStoredEmployees = currentEmployees.length > 0;
        tableBody.innerHTML = `
            <tr>
                <td colspan="10" class="employee-meta-cell">
                    ${typeof renderEmptyState === "function"
                        ? renderEmptyState({
                            title: hasStoredEmployees
                                ? employeeText("common_filter_no_matches", "No matching records")
                                : employeeText("employees_empty_state_title", "No employees yet"),
                            text: hasStoredEmployees
                                ? employeeText("common_search_employee", "Search employee")
                                : employeeText("employees_empty_state_text", "Add employees to start building schedules.")
                        })
                        : employeeText("employees_empty_list", "No employees yet")}
                </td>
            </tr>
        `;
        return;
    }

    tableBody.innerHTML = employees.map(employee => `
        <tr>
            <td>${Number(employee.id)}</td>
            <td class="employee-meta-cell">${escapeHtml(employee.id_card || "—")}</td>
            <td class="employee-name-cell">${escapeHtml(employee.full_name)}</td>
            <td>${escapeHtml(employeeSexLabel(employee.sex))}</td>
            <td>${Number(employee.min_shifts_per_week)} / ${Number(employee.target_shifts_per_week)} / ${Number(employee.max_shifts_per_week)}</td>
            <td>${boolBadge(employee.can_work_night)}</td>
            <td>${boolBadge(employee.can_work_weekends)}</td>
            <td>${boolBadge(employee.can_work_evenings_after_night)}</td>
            <td>${boolBadge(employee.can_work_mornings_and_evenings)}</td>
            <td>
                <div class="table-actions">
                    <button
                        class="table-btn edit"
                        data-action="edit"
                        data-employee-id="${Number(employee.id)}"
                        type="button"
                    >
                        ${employeeText("employees_edit_button", "Edit")}
                    </button>
                    <button
                        class="table-btn delete"
                        data-action="delete"
                        data-employee-id="${Number(employee.id)}"
                        type="button"
                    >
                        ${employeeText("employees_delete_button", "Delete")}
                    </button>
                </div>
            </td>
        </tr>
    `).join("");
}

function handleEmployeesTableClick(event) {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const employeeId = Number(button.dataset.employeeId);
    const employee = currentEmployees.find(item => item.id === employeeId);

    if (button.dataset.action === "edit" && employee) {
        editEmployee(employee);
    }
    if (button.dataset.action === "delete") {
        deleteEmployee(employeeId);
    }
}


// Show message / Показываем сообщение
function showMessage(text, type) {
    renderPageMessage("message-box", text, type || "info");
}
