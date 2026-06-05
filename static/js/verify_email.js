(function () {
    "use strict";

    const form = document.getElementById("verify-email-form");
    const tokenInput = document.getElementById("verify-token");
    const tokenField = document.getElementById("verify-token-field");
    const message = document.getElementById("verify-message");

    function setMessage(text, type = "") {
        message.textContent = text || "";
        message.className = `auth-message ${type}`.trim();
    }

    const token = new URLSearchParams(window.location.search).get("token") || "";
    if (token) {
        tokenInput.value = token;
        tokenField.hidden = true;
    }

    async function verifyEmail() {
        setMessage("Verifying email...", "");
        try {
            const response = await fetch("/api/auth/verify-email", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ token: tokenInput.value.trim() }),
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(payload.detail || "Email verification failed.");
            }
            setMessage("Email verified successfully.", "success");
            setTimeout(() => {
                window.location.href = "/login";
            }, 1200);
        } catch (error) {
            setMessage(error.message, "error");
        }
    }

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        verifyEmail();
    });

    if (token) {
        verifyEmail();
    }
})();
