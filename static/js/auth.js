(function () {
    const TOKEN_KEY = window.scheduleAuth?.TOKEN_KEY || "schedule_app_auth_token";
    const USER_KEY = window.scheduleAuth?.USER_KEY || "schedule_app_auth_user";

    const loginForm = document.getElementById("login-form");
    const bootstrapForm = document.getElementById("bootstrap-form");
    const message = document.getElementById("auth-message");
    const sessionPanel = document.getElementById("current-session");
    const loginModal = document.getElementById("login-modal");
    const organizationModal = document.getElementById("organization-modal");
    const openOrganizationModalButton = document.getElementById("open-organization-modal");
    const loginIdentifierInput = document.getElementById("login-email");
    const loginIdentifierLabel = document.getElementById("login-identifier-label");
    const loginMethodButtons = Array.from(document.querySelectorAll("[data-login-method]"));
    let loginMethod = "email";

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

    function getFriendlyAuthError(error) {
        const messageText = error?.message || String(error || "");
        if (messageText === "Failed to fetch") {
            return "Cloud is not reachable. Check the internet connection and try again.";
        }
        return messageText;
    }

    function openModal(modal) {
        if (!modal) return;
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        setMessage("", "");
        const firstInput = modal.querySelector("input, textarea, select, button");
        firstInput?.focus();
    }

    function closeModal(modal) {
        if (!modal) return;
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
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

    function isCloudEmployeePortalMode() {
        return Boolean(window.scheduleAuth?.isHostedCloudOrigin?.());
    }

    function destinationForUser(user) {
        const membership = window.scheduleAuth?.getActiveMembership?.(user) || user?.memberships?.[0] || null;
        if (membership?.role === "employee") return "/weekly-preferences";
        return "/schedule";
    }

    async function renderAuthStatus() {
        if (window.scheduleAuth?.isDesktopLocalOrigin?.()) {
            setMessage("Authorize a cloud user or add a new organization. Work will continue locally on this computer.", "");
            return;
        }
        try {
            const status = await window.scheduleAuth.request("/api/auth/status");
            setMessage(status.bootstrap_available
                ? "Employee portal is ready."
                : "Employee portal is ready. Log in with your employee account.", "");
        } catch (error) {
            setMessage(`Could not check authorization state: ${getFriendlyAuthError(error)}`, "error");
        }
    }

    function applyCloudEmployeePortalMode() {
        if (!isCloudEmployeePortalMode()) return;
        openOrganizationModalButton?.remove();
        organizationModal?.remove();
        document.querySelector(".auth-brand p").textContent = "Employee portal";
        document.querySelector("#open-login-modal strong").textContent = "Employee login";
        document.querySelector("#open-login-modal span").textContent = "Open weekly wishes and read-only schedule";
    }

    function initializeDefaultApiMode() {
        if (!window.scheduleAuth) return;
        window.scheduleAuth.useLocalApi();
    }

    function applyLoginMethod(nextMethod) {
        loginMethod = nextMethod === "id_card" ? "id_card" : "email";
        loginMethodButtons.forEach((button) => {
            const active = button.dataset.loginMethod === loginMethod;
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", active ? "true" : "false");
        });
        if (loginIdentifierLabel) {
            loginIdentifierLabel.textContent = loginMethod === "id_card" ? "ID card" : "Email";
        }
        if (loginIdentifierInput) {
            loginIdentifierInput.value = "";
            loginIdentifierInput.type = loginMethod === "id_card" ? "text" : "email";
            loginIdentifierInput.inputMode = loginMethod === "id_card" ? "numeric" : "email";
            loginIdentifierInput.autocomplete = loginMethod === "id_card" ? "off" : "username";
            loginIdentifierInput.placeholder = loginMethod === "id_card" ? "Example: 123456789" : "name@example.com";
            loginIdentifierInput.focus();
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

    document.getElementById("open-login-modal")?.addEventListener("click", () => openModal(loginModal));
    document.getElementById("open-organization-modal")?.addEventListener("click", () => openModal(organizationModal));
    loginMethodButtons.forEach((button) => {
        button.addEventListener("click", () => applyLoginMethod(button.dataset.loginMethod));
    });

    document.addEventListener("click", (event) => {
        const closeButton = event.target.closest("[data-auth-modal-close]");
        if (closeButton) {
            closeModal(closeButton.closest(".app-modal-overlay"));
            return;
        }
        if (event.target === loginModal) closeModal(loginModal);
        if (event.target === organizationModal) closeModal(organizationModal);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        closeModal(loginModal);
        closeModal(organizationModal);
    });

    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const isDesktopLogin = window.scheduleAuth?.isDesktopLocalOrigin?.();
        setMessage(isDesktopLogin ? "Signing in and loading organization data..." : "Signing in...", "");
        try {
            const payload = await postJson(isDesktopLogin ? "/api/desktop/cloud-login" : "/api/auth/login", {
                email: loginIdentifierInput.value,
                password: document.getElementById("login-password").value,
            });
            storeSession(payload);
            setMessage("Login successful.", "success");
            window.location.href = destinationForUser(payload.user);
        } catch (error) {
            setMessage(getFriendlyAuthError(error), "error");
        }
    });

    bootstrapForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (isCloudEmployeePortalMode()) {
            setMessage("Organization setup is available only in the desktop app.", "error");
            return;
        }
        const isDesktopLogin = window.scheduleAuth?.isDesktopLocalOrigin?.();
        setMessage(isDesktopLogin ? "Creating cloud organization and loading it locally..." : "Creating organization...", "");
        try {
            const payload = await postJson(isDesktopLogin ? "/api/desktop/cloud-create-organization" : "/api/auth/create-organization", {
                organization_name: document.getElementById("bootstrap-organization").value,
                full_name: document.getElementById("bootstrap-name").value,
                email: document.getElementById("bootstrap-email").value,
                password: document.getElementById("bootstrap-password").value,
            });
            storeSession(payload);
            setMessage("Organization created.", "success");
            window.location.href = destinationForUser(payload.user);
        } catch (error) {
            setMessage(getFriendlyAuthError(error), "error");
        }
    });

    initializeDefaultApiMode();
    applyLoginMethod("email");
    applyCloudEmployeePortalMode();
    renderSession();
    renderAuthStatus();
})();
