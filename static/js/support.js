(function () {
    const elements = {
        message: document.getElementById("support-message"),
        refreshButton: document.getElementById("support-refresh-btn"),
        organizationsBody: document.getElementById("support-organizations-body"),
        accountsBody: document.getElementById("support-accounts-body"),
        employeesBody: document.getElementById("support-employees-body"),
    };

    function escapeHtml(value) {
        if (window.escapeHtml) return window.escapeHtml(value);
        if (value === null || value === undefined || value === "") return "-";
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function setMessage(text, type) {
        elements.message.textContent = text || "";
        elements.message.className = `organization-message ${type || ""}`.trim();
    }

    function renderRows(tbody, rows, columns) {
        if (!tbody) return;
        if (!rows.length) {
            tbody.innerHTML = `<tr><td colspan="${columns.length}">No records.</td></tr>`;
            return;
        }
        tbody.innerHTML = rows.map((row) => `
            <tr>
                ${columns.map((column) => `<td>${escapeHtml(row[column])}</td>`).join("")}
            </tr>
        `).join("");
    }

    async function requestLocalSupportData() {
        const headers = new Headers();
        const token = window.scheduleAuth?.getToken?.() || "";
        if (token) {
            headers.set("Authorization", `Bearer ${token}`);
        }
        const response = await window.scheduleAuth.nativeFetch("/api/support/accounts", { headers });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || `Request failed with ${response.status}`);
        }
        return data;
    }

    async function loadSupportData() {
        setMessage("Loading support data...", "");
        try {
            const data = await requestLocalSupportData();
            renderRows(elements.organizationsBody, data.organizations || [], [
                "id",
                "name",
                "status",
                "member_count",
                "employee_count",
                "created_at",
            ]);
            renderRows(elements.accountsBody, data.accounts || [], [
                "user_id",
                "full_name",
                "email",
                "organization_name",
                "role",
                "user_status",
                "membership_status",
                "employee_name",
                "last_login_at",
            ]);
            renderRows(elements.employeesBody, data.employees || [], [
                "id",
                "full_name",
                "sex",
                "min_shifts_per_week",
                "target_shifts_per_week",
                "max_shifts_per_week",
            ]);
            setMessage("Support data loaded.", "success");
        } catch (error) {
            setMessage(error.message || "Could not load support data.", "error");
        }
    }

    elements.refreshButton?.addEventListener("click", loadSupportData);
    loadSupportData();
})();
