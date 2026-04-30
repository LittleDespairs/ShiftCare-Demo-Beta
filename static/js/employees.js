let editingEmployeeId = null; // Track editing mode / Отслеживаем режим редактирования
let currentEmployees = [];

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
document.addEventListener("DOMContentLoaded", () => {
    const employeeForm = document.getElementById("employee-form");

    if (employeeForm) {
        employeeForm.addEventListener("submit", handleEmployeeSubmit);
    }
    const tableBody = document.getElementById("employees-table-body");
    if (tableBody) {
        tableBody.addEventListener("click", handleEmployeesTableClick);
    }
    bindEmployeeModal();

    loadEmployees();
});

document.addEventListener("app-language-changed", () => {
    renderEmployeesTable(currentEmployees);
    updateEmployeeModalTitle();
    updateSubmitButtonText();
});

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
        const response = await fetch("/api/employees");

        if (!response.ok) {
            showMessage(employeeText("msg_failed_load_employees", "Failed to load employees."), "danger");
            return;
        }

        const employees = await response.json();
        currentEmployees = employees;
        renderEmployeesTable(employees);
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
        const backupSuffix = result.backup_name
            ? ` ${employeeText("common_recovery_backup", "Recovery backup")}: ${result.backup_name}`
            : "";
        showMessage(`${result.message}${backupSuffix}`, "success");

        resetForm();
        closeEmployeeModal();
        await loadEmployees();
    } catch (error) {
        console.error("Submit employee error:", error);
        showMessage(employeeText("msg_server_error_save_employee", "Server error while saving employee."), "danger");
    }
}


// Fill form for editing / Заполняем форму для редактирования
function editEmployee(employee) {
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
        tableBody.innerHTML = `
            <tr>
                <td colspan="10" class="employee-meta-cell">
                    ${typeof renderEmptyState === "function"
                        ? renderEmptyState({
                            title: employeeText("employees_empty_state_title", "No employees yet"),
                            text: employeeText("employees_empty_state_text", "Add employees to start building schedules.")
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
            <td class="employee-meta-cell">${escapeHtml(employee.id_card || "")}</td>
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
