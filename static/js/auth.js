(function () {
    const TOKEN_KEY = window.scheduleAuth?.TOKEN_KEY || "schedule_app_auth_token";
    const USER_KEY = window.scheduleAuth?.USER_KEY || "schedule_app_auth_user";

    const loginForm = document.getElementById("login-form");
    const bootstrapForm = document.getElementById("bootstrap-form");
    const message = document.getElementById("auth-message");
    const sessionPanel = document.getElementById("current-session");
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

    renderSession();
})();
