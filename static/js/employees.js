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

    loadEmployees();
});


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
        await loadEmployees();
    } catch (error) {
        console.error("Submit employee error:", error);
        showMessage(employeeText("msg_server_error_save_employee", "Server error while saving employee."), "danger");
    }
}


// Fill form for editing / Заполняем форму для редактирования
function editEmployee(employee) {
    document.getElementById("full_name").value = employee.full_name;
    document.getElementById("sex").value = employee.sex;
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

    showMessage(`${employeeText("msg_editing_employee", "Editing employee")}: ${employee.full_name}`, "info");
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
                <td colspan="9" class="text-center text-muted">${employeeText("employees_empty_list", "No employees yet")}</td>
            </tr>
        `;
        return;
    }

    tableBody.innerHTML = employees.map(employee => `
        <tr>
            <td>${Number(employee.id)}</td>
            <td>${escapeHtml(employee.full_name)}</td>
            <td>${escapeHtml(employee.sex === "male" ? employeeText("employees_sex_male", "Male") : employeeText("employees_sex_female", "Female"))}</td>
            <td>${Number(employee.min_shifts_per_week)} / ${Number(employee.target_shifts_per_week)} / ${Number(employee.max_shifts_per_week)}</td>
            <td>${employee.can_work_night ? employeeText("common_yes", "Yes") : employeeText("common_no", "No")}</td>
            <td>${employee.can_work_weekends ? employeeText("common_yes", "Yes") : employeeText("common_no", "No")}</td>
            <td>${employee.can_work_evenings_after_night ? employeeText("common_yes", "Yes") : employeeText("common_no", "No")}</td>
            <td>${employee.can_work_mornings_and_evenings ? employeeText("common_yes", "Yes") : employeeText("common_no", "No")}</td>
            <td>
                <button
                    class="btn btn-sm btn-warning me-1"
                    data-action="edit"
                    data-employee-id="${Number(employee.id)}"
                >
                    ${employeeText("employees_edit_button", "Edit")}
                </button>
                <button
                    class="btn btn-sm btn-danger"
                    data-action="delete"
                    data-employee-id="${Number(employee.id)}"
                >
                    ${employeeText("employees_delete_button", "Delete")}
                </button>
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
