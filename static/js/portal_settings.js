(function () {
    "use strict";

    function initEmployeePortalSettings() {
        const form = document.getElementById("employee-portal-settings-form");
        if (!form) return;
        const fields = document.getElementById("employee-portal-settings-fields");
        const checkbox = document.getElementById("employee_shift_swap_requests_enabled");
        const retry = document.getElementById("reload-employee-portal-settings-btn");
        const messages = document.getElementById("employee-portal-settings-message-box");
        let loaded = false;
        let busy = false;

        function t(key, fallback) {
            const value = window.translate?.(key);
            return value && value !== key ? value : fallback;
        }

        function message(text, type = "info") {
            const notice = document.createElement("div");
            notice.className = `alert alert-${type}`;
            notice.textContent = text;
            messages.replaceChildren(notice);
        }

        function setBusy(value) {
            busy = value;
            fields.disabled = busy || !loaded;
            retry.disabled = busy;
            form.setAttribute("aria-busy", String(busy));
        }

        async function request(options, failureText) {
            const response = await fetch("/api/app-settings", options);
            const result = await response.json().catch(() => null);
            if (!response.ok || !result || typeof result !== "object") {
                throw new Error(typeof result?.detail === "string" ? result.detail : failureText);
            }
            return result;
        }

        async function load() {
            if (busy) return;
            setBusy(true);
            message(t("settings_msg_loading_employee_portal", "Loading employee portal settings..."));
            try {
                const settings = await request({}, t("settings_msg_failed_load_employee_portal", "Failed to load employee portal settings. Try again."));
                checkbox.checked = settings.employee_shift_swap_requests_enabled !== false;
                loaded = true;
                messages.replaceChildren();
            } catch (error) {
                loaded = false;
                message(t("settings_msg_failed_load_employee_portal", "Failed to load employee portal settings. Try again."), "danger");
            } finally {
                setBusy(false);
            }
        }

        async function save(event) {
            event.preventDefault();
            if (busy || !loaded) return;
            setBusy(true);
            message(t("settings_msg_saving_employee_portal", "Saving employee portal settings..."));
            try {
                const result = await request({
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ employee_shift_swap_requests_enabled: Boolean(checkbox.checked) })
                }, t("settings_msg_failed_save_employee_portal", "Failed to save employee portal settings."));
                if (!result.settings || typeof result.settings.employee_shift_swap_requests_enabled !== "boolean") {
                    throw new Error(t("settings_msg_failed_save_employee_portal", "Failed to save employee portal settings."));
                }
                checkbox.checked = result.settings.employee_shift_swap_requests_enabled;
                message(t("settings_msg_employee_portal_saved", "Employee portal settings saved."), "success");
            } catch (error) {
                message(error instanceof TypeError
                    ? t("settings_msg_failed_save_employee_portal", "Failed to save employee portal settings.")
                    : error.message, "danger");
            } finally {
                setBusy(false);
            }
        }

        form.addEventListener("submit", save);
        retry.addEventListener("click", load);
        load();
    }

    document.addEventListener("DOMContentLoaded", initEmployeePortalSettings);
})();
