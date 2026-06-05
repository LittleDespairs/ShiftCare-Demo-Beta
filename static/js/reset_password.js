(function () {
    "use strict";

    const form = document.getElementById("reset-password-form");
    const tokenInput = document.getElementById("reset-token");
    const tokenField = document.getElementById("reset-token-field");
    const passwordInput = document.getElementById("reset-password");
    const confirmInput = document.getElementById("reset-confirm-password");
    const message = document.getElementById("reset-message");

    function setMessage(text, type = "") {
        message.textContent = text || "";
        message.className = `auth-message ${type}`.trim();
    }

    const token = new URLSearchParams(window.location.search).get("token") || "";
    if (token) {
        tokenInput.value = token;
        tokenField.hidden = true;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (passwordInput.value !== confirmInput.value) {
            setMessage("Password confirmation does not match.", "error");
            confirmInput.focus();
            return;
        }
        setMessage("Resetting password...", "");
        try {
            const response = await fetch("/api/auth/reset-password", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    token: tokenInput.value.trim(),
                    new_password: passwordInput.value,
                }),
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(payload.detail || "Password reset failed.");
            }
            setMessage("Password reset successfully. You can sign in now.", "success");
            form.reset();
            setTimeout(() => {
                window.location.href = "/login";
            }, 1200);
        } catch (error) {
            setMessage(error.message, "error");
        }
    });
})();
