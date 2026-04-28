(function () {
    let backendStatus = "checking";

    function ensureIndicator() {
        let indicator = document.getElementById("online-status-indicator");
        if (!indicator) {
            indicator = document.createElement("div");
            indicator.id = "online-status-indicator";
            indicator.className = "online-status-indicator";
            indicator.setAttribute("role", "status");
            indicator.setAttribute("aria-live", "polite");
            document.body.appendChild(indicator);
        }
        return indicator;
    }

    function backendLabel() {
        const apiBaseUrl = window.scheduleAuth?.getApiBaseUrl?.() || "";
        return apiBaseUrl ? "Cloud API" : "Local API";
    }

    function updateStatus() {
        const indicator = ensureIndicator();
        const isOnline = navigator.onLine;
        const suffix = backendStatus === "ok" ? "ready" : backendStatus === "error" ? "unreachable" : "checking";
        indicator.textContent = `${isOnline ? "Online" : "Offline"} · ${backendLabel()} · ${suffix}`;
        indicator.classList.toggle("offline", !isOnline || backendStatus === "error");
        indicator.classList.toggle("cloud-api", Boolean(window.scheduleAuth?.getApiBaseUrl?.()));
    }

    async function checkBackend() {
        backendStatus = "checking";
        updateStatus();
        try {
            const response = await fetch("/api/health/live", { cache: "no-store" });
            backendStatus = response.ok ? "ok" : "error";
        } catch (error) {
            backendStatus = "error";
        }
        updateStatus();
    }

    window.addEventListener("online", updateStatus);
    window.addEventListener("offline", updateStatus);
    window.addEventListener("storage", (event) => {
        if (event.key === window.scheduleAuth?.API_BASE_URL_KEY) {
            checkBackend();
        }
    });
    document.addEventListener("schedule-api-mode-changed", checkBackend);
    document.addEventListener("DOMContentLoaded", () => {
        updateStatus();
        checkBackend();
        window.setInterval(checkBackend, 60000);
    });
})();
