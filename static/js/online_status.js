(function () {
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

    function updateStatus() {
        const indicator = ensureIndicator();
        const isOnline = navigator.onLine;
        indicator.textContent = isOnline ? "Online" : "Offline";
        indicator.classList.toggle("offline", !isOnline);
    }

    window.addEventListener("online", updateStatus);
    window.addEventListener("offline", updateStatus);
    document.addEventListener("DOMContentLoaded", updateStatus);
})();
