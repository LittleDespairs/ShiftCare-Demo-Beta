(function () {
    const form = document.getElementById("accept-form");
    const message = document.getElementById("accept-message");
    const tokenInput = document.getElementById("accept-token");
    const tokenField = document.getElementById("accept-token-field");
    const nameField = document.getElementById("accept-name-field");
    const nameInput = document.getElementById("accept-name");
    const passwordInput = document.getElementById("accept-password");
    const confirmPasswordInput = document.getElementById("accept-confirm-password");
    const summary = document.getElementById("accept-invitation-summary");

    function escapeHtml(value) {
        if (window.escapeHtml) return window.escapeHtml(value);
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function setMessage(value, type = "") {
        message.textContent = value || "";
        message.className = `auth-message ${type}`.trim();
    }

    function renderPreview(preview) {
        const displayName = preview.employee_name || preview.email;
        summary.innerHTML = `
            <strong>${escapeHtml(displayName)}</strong><br>
            <span>${escapeHtml(preview.organization_name)}</span><br>
            <span>${escapeHtml(preview.email)}</span>
        `;
        nameField.hidden = !preview.requires_name;
        nameInput.required = Boolean(preview.requires_name);
        if (preview.employee_name) {
            nameInput.value = preview.employee_name;
        }
    }

    async function loadInvitationPreview() {
        const token = tokenInput.value.trim();
        if (!token) {
            summary.innerHTML = "";
            tokenField.hidden = false;
            return;
        }
        try {
            const response = await fetch(`/api/auth/invitation-preview?token=${encodeURIComponent(token)}`);
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.detail || "Invitation not found or expired");
            }
            tokenField.hidden = true;
            renderPreview(data);
        } catch (error) {
            summary.innerHTML = "";
            tokenField.hidden = false;
            setMessage(error.message, "error");
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        const params = new URLSearchParams(window.location.search);
        tokenInput.value = params.get("token") || "";
        loadInvitationPreview();
    });

    tokenInput.addEventListener("change", loadInvitationPreview);

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (passwordInput.value !== confirmPasswordInput.value) {
            setMessage("Password confirmation does not match.", "error");
            return;
        }
        setMessage("Accepting invitation...", "");
        try {
            const response = await fetch("/api/auth/accept-invitation", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    token: tokenInput.value,
                    full_name: nameInput.value || null,
                    password: passwordInput.value,
                    confirm_password: confirmPasswordInput.value,
                }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.detail || "Invitation could not be accepted");
            }
            window.scheduleAuth.setSession(data);
            setMessage("Invitation accepted.", "success");
            const membership = window.scheduleAuth.getActiveMembership(data.user);
            window.location.href = membership?.role === "employee" ? "/weekly-preferences" : "/schedule";
        } catch (error) {
            setMessage(error.message, "error");
        }
    });
})();
