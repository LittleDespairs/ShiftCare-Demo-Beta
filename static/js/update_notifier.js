(function () {
    const STARTUP_CHECK_DELAY_MS = 900;

    function t(key, fallback = "") {
        if (typeof window.translate === "function") {
            const translated = window.translate(key);
            return translated && translated !== key ? translated : (fallback || key);
        }
        return fallback || key;
    }

    function escapeHtml(value) {
        if (value === null || value === undefined) return "";
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function shouldSkipUpdateNotifier() {
        if (!document.body || document.body.dataset.demoMode === "1") return true;
        if (document.body.dataset.employeePortalMode === "1") return true;
        try {
            if (new URLSearchParams(window.location.search).get("embedded") === "1") {
                return true;
            }
        } catch (error) {
            return false;
        }
        return false;
    }

    function ensureModal() {
        let modal = document.getElementById("update-notifier-modal");
        if (modal) return modal;

        modal = document.createElement("div");
        modal.id = "update-notifier-modal";
        modal.className = "app-modal-overlay update-notifier-overlay";
        modal.setAttribute("aria-hidden", "true");
        modal.innerHTML = `
            <div class="app-modal update-notifier-modal" role="dialog" aria-modal="true" aria-labelledby="update-notifier-title">
                <div class="app-modal-header">
                    <h2 id="update-notifier-title" class="app-modal-title"></h2>
                    <button class="app-modal-close" type="button" data-update-action="close" aria-label="Close">×</button>
                </div>
                <div class="app-modal-body" id="update-notifier-body"></div>
                <div class="app-modal-actions" id="update-notifier-actions"></div>
            </div>
        `;
        document.body.appendChild(modal);
        return modal;
    }

    function renderSummaryList(items) {
        const summary = Array.isArray(items) ? items.filter(item => String(item || "").trim()) : [];
        if (!summary.length) {
            return `<p class="update-notifier-muted">${escapeHtml(t("updates_changelog_empty", "No short changelog was provided for this release."))}</p>`;
        }
        return `
            <ul class="update-notifier-list">
                ${summary.map(item => `<li>${escapeHtml(item)}</li>`).join("")}
            </ul>
        `;
    }

    function openUpdateModal({ title, bodyHtml, actions = [], closeAction = "close" }) {
        const modal = ensureModal();
        const titleElement = modal.querySelector("#update-notifier-title");
        const bodyElement = modal.querySelector("#update-notifier-body");
        const actionsElement = modal.querySelector("#update-notifier-actions");

        titleElement.textContent = title || "";
        bodyElement.innerHTML = bodyHtml || "";
        actionsElement.innerHTML = actions.map(action => `
            <button class="btn ${action.className || "btn-secondary"}" type="button" data-update-action="${escapeHtml(action.id)}">
                ${escapeHtml(action.label)}
            </button>
        `).join("");

        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        const primaryButton = actionsElement.querySelector(".btn-primary") || actionsElement.querySelector(".btn") || modal.querySelector(".app-modal-close");
        primaryButton?.focus();

        return new Promise(resolve => {
            const finish = result => {
                modal.classList.remove("is-open");
                modal.setAttribute("aria-hidden", "true");
                modal.removeEventListener("click", onClick);
                document.removeEventListener("keydown", onKeyDown);
                resolve(result);
            };
            const onClick = event => {
                const button = event.target.closest("[data-update-action]");
                if (button) {
                    finish(button.dataset.updateAction || closeAction);
                    return;
                }
                if (event.target === modal) {
                    finish(closeAction);
                }
            };
            const onKeyDown = event => {
                if (event.key === "Escape") {
                    finish(closeAction);
                }
            };
            modal.addEventListener("click", onClick);
            document.addEventListener("keydown", onKeyDown);
        });
    }

    async function requestJson(url, options = {}) {
        const response = await fetch(url, {
            cache: "no-store",
            ...options,
            headers: {
                ...(options.headers || {})
            }
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            const error = new Error(payload.detail || `Request failed with ${response.status}`);
            error.payload = payload;
            throw error;
        }
        return payload;
    }

    function formatVersion(value) {
        return String(value || "").replace(/_/g, "-");
    }

    function getSessionValue(key) {
        try {
            return sessionStorage.getItem(key);
        } catch (error) {
            return null;
        }
    }

    function setSessionValue(key, value) {
        try {
            sessionStorage.setItem(key, value);
        } catch (error) {
            // The notifier can run without session storage; it will just be less quiet.
        }
    }

    async function showPostUpdateChangelog(changelog) {
        const title = t("updates_changelog_title", "What's new");
        const bodyHtml = `
            <p class="update-notifier-lead">
                ${escapeHtml(t("updates_changelog_text", "ShiftCare was updated. Main changes in this version:"))}
            </p>
            <p class="update-notifier-version">${escapeHtml(formatVersion(changelog.release_name || changelog.version))}</p>
            ${renderSummaryList(changelog.summary)}
        `;
        await openUpdateModal({
            title,
            bodyHtml,
            actions: [
                { id: "ack", label: t("common_ok", "OK"), className: "btn-primary" }
            ],
            closeAction: "ack"
        });
        await requestJson("/api/updates/post-install-changelog/ack", { method: "POST" }).catch(() => null);
    }

    async function startInstall(latest) {
        const modal = ensureModal();
        modal.querySelector("#update-notifier-title").textContent = t("updates_modal_installing_title", "Installing update");
        modal.querySelector("#update-notifier-body").innerHTML = `<p class="update-notifier-lead">${escapeHtml(t("updates_modal_installing_text", "Downloading the update installer and preparing to close the app."))}</p>`;
        modal.querySelector("#update-notifier-actions").innerHTML = "";
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");

        try {
            await requestJson("/api/updates/install", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    download_url: latest.download_url,
                    asset_name: latest.asset_name
                })
            });
            await openUpdateModal({
                title: t("updates_modal_install_started_title", "Update started"),
                bodyHtml: `<p class="update-notifier-lead">${escapeHtml(t("updates_modal_install_started_text", "The installer has started. ShiftCare will close shortly."))}</p>`,
                actions: [
                    { id: "close", label: t("common_ok", "OK"), className: "btn-primary" }
                ]
            });
        } catch (error) {
            await openUpdateModal({
                title: t("updates_modal_install_error_title", "Could not start update"),
                bodyHtml: `<p class="update-notifier-error">${escapeHtml(error.message || t("settings_updates_install_failed", "Failed to start update installer."))}</p>`,
                actions: [
                    { id: "close", label: t("common_ok", "OK"), className: "btn-primary" }
                ]
            });
        }
    }

    async function showAvailableUpdate(updateStatus) {
        const latest = updateStatus?.latest;
        if (!latest || !updateStatus.update_available) return;

        const appVersion = document.body?.dataset?.appVersion || updateStatus.current_version || "";
        const sessionKey = `shiftcare:update-offered:${appVersion}:${latest.version || latest.tag_name || ""}`;
        if (getSessionValue(sessionKey) === "1") {
            return;
        }
        setSessionValue(sessionKey, "1");

        const bodyHtml = `
            <p class="update-notifier-lead">${escapeHtml(t("updates_modal_text", "A newer ShiftCare version is available."))}</p>
            <div class="update-notifier-version-grid">
                <span>${escapeHtml(t("updates_modal_current_version", "Current version"))}</span>
                <strong>${escapeHtml(formatVersion(updateStatus.current_version || appVersion))}</strong>
                <span>${escapeHtml(t("updates_modal_new_version", "New version"))}</span>
                <strong>${escapeHtml(formatVersion(latest.version || latest.tag_name))}</strong>
            </div>
            ${renderSummaryList(latest.changelog_summary)}
        `;
        const action = await openUpdateModal({
            title: t("updates_modal_title", "Update available"),
            bodyHtml,
            actions: [
                { id: "later", label: t("updates_modal_later", "Later"), className: "btn-secondary" },
                { id: "install", label: t("updates_modal_install", "Install update"), className: "btn-primary" }
            ],
            closeAction: "later"
        });
        if (action === "install") {
            await startInstall(latest);
        }
    }

    async function runStartupUpdateFlow() {
        if (shouldSkipUpdateNotifier()) return;
        const appVersion = document.body?.dataset?.appVersion || "unknown";
        const startupCheckKey = `shiftcare:update-startup-check:${appVersion}`;
        if (getSessionValue(startupCheckKey) === "1") return;
        try {
            const payload = await requestJson("/api/updates/startup");
            setSessionValue(startupCheckKey, "1");
            if (!payload.updates_enabled) return;
            if (payload.post_update_changelog) {
                await showPostUpdateChangelog(payload.post_update_changelog);
            }
            await showAvailableUpdate(payload.update_status);
        } catch (error) {
            // Startup update checks should never block the application itself.
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        window.setTimeout(runStartupUpdateFlow, STARTUP_CHECK_DELAY_MS);
    });
})();
