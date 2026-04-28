(function () {
    const form = document.getElementById("accept-form");
    const message = document.getElementById("accept-message");
    const tokenInput = document.getElementById("accept-token");

    function setMessage(value, type = "") {
        message.textContent = value || "";
        message.className = `auth-message ${type}`.trim();
    }

    document.addEventListener("DOMContentLoaded", () => {
        const params = new URLSearchParams(window.location.search);
        tokenInput.value = params.get("token") || "";
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        setMessage("Accepting invitation...", "");
        try {
            const response = await fetch("/api/auth/accept-invitation", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    token: tokenInput.value,
                    full_name: document.getElementById("accept-name").value,
                    password: document.getElementById("accept-password").value,
                }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.detail || "Invitation could not be accepted");
            }
            window.scheduleAuth.setSession(data);
            setMessage("Invitation accepted.", "success");
            window.location.href = "/organization";
        } catch (error) {
            setMessage(error.message, "error");
        }
    });
})();
