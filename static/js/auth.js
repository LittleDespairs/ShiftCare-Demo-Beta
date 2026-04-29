(function () {
    const TOKEN_KEY = window.scheduleAuth?.TOKEN_KEY || "schedule_app_auth_token";
    const USER_KEY = window.scheduleAuth?.USER_KEY || "schedule_app_auth_user";

    const loginForm = document.getElementById("login-form");
    const bootstrapForm = document.getElementById("bootstrap-form");
    const message = document.getElementById("auth-message");
    const sessionPanel = document.getElementById("current-session");
    const apiLocalButton = document.getElementById("api-local-btn");
    const apiCloudButton = document.getElementById("api-cloud-btn");
    const apiAdvancedToggle = document.getElementById("api-advanced-toggle");
    const apiModePanel = document.querySelector(".api-mode-panel");
    const apiModeStatus = document.getElementById("api-mode-status");
    const tabs = Array.from(document.querySelectorAll("[data-auth-tab]"));

    function escapeHtml(value) {
        if (window.escapeHtml) return window.escapeHtml(value);
        if (value === null || value === undefined) return "";
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function setMessage(text, type) {
        message.textContent = text || "";
        message.className = `auth-message ${type || ""}`.trim();
    }

    function setActiveTab(mode) {
        tabs.forEach((tab) => {
            tab.classList.toggle("active", tab.dataset.authTab === mode);
        });
        loginForm.classList.toggle("hidden", mode !== "login");
        bootstrapForm.classList.toggle("hidden", mode !== "bootstrap");
        setMessage("", "");
    }

    function storeSession(payload) {
        if (window.scheduleAuth) {
            window.scheduleAuth.setSession(payload);
        } else {
            localStorage.setItem(TOKEN_KEY, payload.access_token);
            localStorage.setItem(USER_KEY, JSON.stringify(payload.user));
        }
        renderSession();
    }

    function clearSession() {
        if (window.scheduleAuth) {
            window.scheduleAuth.clearSession();
        } else {
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(USER_KEY);
        }
        renderSession();
    }

    function renderSession() {
        const token = localStorage.getItem(TOKEN_KEY);
        const rawUser = localStorage.getItem(USER_KEY);
        if (!token || !rawUser) {
            sessionPanel.innerHTML = "";
            return;
        }

        let user;
        try {
            user = JSON.parse(rawUser);
        } catch (error) {
            clearSession();
            return;
        }

        const membership = user.memberships && user.memberships[0];
        sessionPanel.innerHTML = `
            <strong>${escapeHtml(user.full_name)}</strong><br>
            <span>${escapeHtml(user.email)}</span><br>
            <span>${membership ? `${escapeHtml(membership.organization_name)} · ${escapeHtml(membership.role)}` : "No organization"}</span><br>
            <button id="auth-clear-session" class="btn btn-secondary" type="button">Clear local session</button>
        `;
        document.getElementById("auth-clear-session").addEventListener("click", clearSession);
    }

    function renderApiMode() {
        if (!apiModeStatus) return;
        const apiBaseUrl = window.scheduleAuth?.getApiBaseUrl?.() || "";
        apiModeStatus.textContent = apiBaseUrl
            ? `Cloud workspace: ${apiBaseUrl}`
            : `Local recovery mode: ${window.location.origin}`;
        apiLocalButton?.classList.toggle("btn-primary", !apiBaseUrl);
        apiLocalButton?.classList.toggle("btn-secondary", Boolean(apiBaseUrl));
        apiCloudButton?.classList.toggle("btn-primary", Boolean(apiBaseUrl));
        apiCloudButton?.classList.toggle("btn-soft", !apiBaseUrl);
    }

    async function renderAuthStatus() {
        try {
            const status = await window.scheduleAuth.request("/api/auth/status");
            const apiBaseUrl = window.scheduleAuth?.getApiBaseUrl?.() || "";
            if (status.bootstrap_available) {
                if (apiBaseUrl) {
                    setMessage(
                        "Cloud workspace is ready for first owner setup.",
                        "success",
                    );
                } else {
                    setMessage(
                        "Local recovery mode is active. Use it only for migration or emergency access.",
                        "",
                    );
                }
                return;
            }
            if (apiBaseUrl) {
                setMessage("Cloud workspace already has an owner. Log in with that account.", "");
                return;
            }
            setMessage("Local recovery database already has an owner. Log in only if you need migration or emergency access.", "");
        } catch (error) {
            setMessage(`Could not check authorization state: ${error.message}`, "error");
        }
    }

    function initializeCloudFirstMode() {
        if (!window.scheduleAuth) return;
        const modePreference = window.scheduleAuth.getApiModePreference?.() || "";
        const apiBaseUrl = window.scheduleAuth.getApiBaseUrl?.() || "";
        if (!modePreference && !apiBaseUrl) {
            window.scheduleAuth.useCloudApi();
        }
    }

    async function postJson(url, payload) {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || "Request failed");
        }
        return data;
    }

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => setActiveTab(tab.dataset.authTab));
    });

    apiLocalButton?.addEventListener("click", () => {
        window.scheduleAuth?.useLocalApi?.();
        clearSession();
        renderApiMode();
        document.dispatchEvent(new CustomEvent("schedule-api-mode-changed"));
        setMessage("Local API selected. Please log in again.", "success");
        renderAuthStatus();
    });

    apiCloudButton?.addEventListener("click", () => {
        window.scheduleAuth?.useCloudApi?.();
        clearSession();
        renderApiMode();
        document.dispatchEvent(new CustomEvent("schedule-api-mode-changed"));
        setMessage("Cloud beta API selected. Please log in again.", "success");
        renderAuthStatus();
    });

    apiAdvancedToggle?.addEventListener("click", () => {
        apiModePanel?.classList.toggle("expanded");
    });

    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        setMessage("Signing in...", "");
        try {
            const payload = await postJson("/api/auth/login", {
                email: document.getElementById("login-email").value,
                password: document.getElementById("login-password").value,
            });
            storeSession(payload);
            setMessage("Login successful.", "success");
            window.location.href = "/organization";
        } catch (error) {
            setMessage(error.message, "error");
        }
    });

    bootstrapForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        setMessage("Creating owner account...", "");
        try {
            const payload = await postJson("/api/auth/bootstrap", {
                organization_name: document.getElementById("bootstrap-organization").value,
                full_name: document.getElementById("bootstrap-name").value,
                email: document.getElementById("bootstrap-email").value,
                password: document.getElementById("bootstrap-password").value,
            });
            storeSession(payload);
            setActiveTab("login");
            setMessage("Owner account created.", "success");
            window.location.href = "/organization";
        } catch (error) {
            setMessage(error.message, "error");
        }
    });

    initializeCloudFirstMode();
    renderSession();
    renderApiMode();
    renderAuthStatus();
})();
