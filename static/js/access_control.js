(function () {
    const ROLE_ACCESS = {
        owner: {
            pages: new Set(["/", "/schedule", "/employees", "/weekly-preferences", "/settings", "/organization", "/positions", "/shift-templates", "/employee-positions", "/coverage-requirements", "/support", "/guide", "/docs"]),
            nav: new Set(["/", "/schedule", "/employees", "/weekly-preferences", "/settings", "/organization"]),
            canEditSchedule: true,
        },
        admin: {
            pages: new Set(["/", "/schedule", "/employees", "/weekly-preferences", "/settings", "/organization", "/positions", "/shift-templates", "/employee-positions", "/coverage-requirements", "/support", "/guide", "/docs"]),
            nav: new Set(["/", "/schedule", "/employees", "/weekly-preferences", "/settings", "/organization"]),
            canEditSchedule: true,
        },
        scheduler: {
            pages: new Set(["/", "/schedule", "/employees", "/weekly-preferences", "/settings", "/organization", "/positions", "/shift-templates", "/employee-positions", "/coverage-requirements", "/guide", "/docs"]),
            nav: new Set(["/", "/schedule", "/employees", "/weekly-preferences", "/settings", "/organization"]),
            canEditSchedule: true,
        },
        manager: {
            pages: new Set(["/", "/schedule", "/weekly-preferences", "/organization", "/guide", "/docs"]),
            nav: new Set(["/", "/schedule", "/weekly-preferences", "/organization"]),
            canEditSchedule: false,
        },
        read_only: {
            pages: new Set(["/", "/schedule", "/organization", "/guide", "/docs"]),
            nav: new Set(["/", "/schedule", "/organization"]),
            canEditSchedule: false,
        },
        employee: {
            pages: new Set(["/", "/schedule", "/weekly-preferences", "/organization", "/guide", "/docs"]),
            nav: new Set(["/", "/schedule", "/weekly-preferences", "/organization"]),
            canEditSchedule: false,
        },
    };

    const originalFetch = window.fetch.bind(window);

    window.fetch = function authenticatedFetch(input, options = {}) {
        const url = typeof input === "string" ? input : input?.url || "";
        const isSameOriginApi = url.startsWith("/api/") || url.startsWith(window.location.origin + "/api/");
        if (!isSameOriginApi || !window.scheduleAuth?.getToken()) {
            return originalFetch(input, options);
        }

        const headers = new Headers(options.headers || {});
        if (!headers.has("Authorization")) {
            headers.set("Authorization", `Bearer ${window.scheduleAuth.getToken()}`);
        }
        if (options.body && !headers.has("Content-Type")) {
            headers.set("Content-Type", "application/json");
        }
        return originalFetch(input, { ...options, headers });
    };

    function activeMembership() {
        return window.scheduleAuth?.getActiveMembership?.() || null;
    }

    function accessForRole(role) {
        const baseAccess = ROLE_ACCESS[role] || ROLE_ACCESS.employee;
        if (!window.scheduleAuth?.isEmployeePortalMode?.()) {
            return baseAccess;
        }
        const pages = new Set(["/", "/schedule", "/organization", "/guide", "/docs"]);
        const nav = new Set(["/schedule", "/organization"]);
        if (role === "employee") {
            pages.add("/weekly-preferences");
            nav.add("/weekly-preferences");
        }
        return { pages, nav, canEditSchedule: false };
    }

    function canonicalPath(pathname) {
        if (pathname === "/organizations") return "/organization";
        return pathname || "/";
    }

    function isAuthPage() {
        return ["/login", "/accept-invitation", "/reset-password", "/verify-email"].includes(canonicalPath(window.location.pathname));
    }

    function translateLocal(key, fallback) {
        if (typeof window.translate === "function") {
            const value = window.translate(key);
            return value === key ? fallback : value;
        }
        if (typeof window.organizationAuthText === "function") {
            const value = window.organizationAuthText(key);
            return value === key ? fallback : value;
        }
        return fallback;
    }

    async function logoutCurrentUser() {
        try {
            await window.scheduleAuth?.request?.("/api/auth/logout", { method: "POST" });
        } catch (error) {
            // The local session is still cleared when the server logout request cannot finish.
        }
        window.scheduleAuth?.clearSession?.();
        window.location.href = "/login";
    }

    function ensureGlobalLogoutButton() {
        if (isAuthPage()) return;
        const token = window.scheduleAuth?.getToken?.();
        const user = window.scheduleAuth?.getUser?.();
        if (!token || !user) return;

        const actions = document.querySelector(".topbar-actions");
        if (!actions) return;

        let button = document.getElementById("logout-btn") || document.getElementById("global-logout-btn");
        if (!button) {
            button = document.createElement("button");
            button.id = "global-logout-btn";
            button.type = "button";
            actions.appendChild(button);
        }
        button.classList.remove("btn", "btn-secondary");
        button.classList.add("session-logout-button");
        button.dataset.sessionLogout = "true";
        button.setAttribute("aria-label", translateLocal("common_logout", "Logout"));
        button.innerHTML = `
            <span class="session-logout-icon" aria-hidden="true"></span>
            <span class="session-logout-text">${translateLocal("common_logout", "Logout")}</span>
        `;
        if (!button.dataset.accessLogoutBound) {
            button.addEventListener("click", logoutCurrentUser);
            button.dataset.accessLogoutBound = "1";
        }
    }

    function ensureStandardNav() {
        const nav = document.querySelector(".nav-list");
        if (!nav) return;
        const items = [
            ["/", "⌂", "nav_dashboard", "Dashboard"],
            ["/schedule", "🗓", "nav_schedule", "Schedule"],
            ["/employees", "👥", "nav_employees", "Employees"],
            ["/weekly-preferences", "✦", "nav_requests", "Preferences"],
            ["/organization", "◎", "nav_organization", "Personal account"],
            ["/settings", "⚙", "nav_settings", "Settings"],
        ];
        const existing = new Map();
        const duplicates = [];
        Array.from(nav.querySelectorAll("a[href]")).forEach((link) => {
            const path = canonicalPath(new URL(link.getAttribute("href"), window.location.origin).pathname);
            if (!existing.has(path)) {
                existing.set(path, link);
            } else {
                duplicates.push(link);
            }
        });
        duplicates.forEach((link) => link.remove());
        items.forEach(([href, icon, key, fallback], index) => {
            let item = existing.get(href);
            if (!item) {
                item = document.createElement("a");
                item.href = href;
                item.className = "nav-item";
            }
            item.dataset.navPath = href;
            const currentIcon = item.querySelector(".nav-icon")?.textContent?.trim() || "";
            const currentLabel = item.querySelector(".nav-label");
            if (currentIcon !== icon || currentLabel?.dataset.i18n !== key) {
                item.innerHTML = `<span class="nav-icon" aria-hidden="true">${icon}</span><span class="nav-label" data-i18n="${key}">${fallback}</span>`;
            }
            if (nav.children[index] !== item) {
                nav.insertBefore(item, nav.children[index] || null);
            }
        });
    }

    function applyNavLabels() {
        const labels = {
            "/": ["nav_dashboard", "Dashboard"],
            "/schedule": ["nav_schedule", "Schedule"],
            "/employees": ["nav_employees", "Employees"],
            "/weekly-preferences": ["nav_requests", "Preferences"],
            "/settings": ["nav_settings", "Settings"],
            "/organization": ["nav_organization", "Personal account"],
        };
        document.querySelectorAll(".nav-list a[href]").forEach((link) => {
            const path = canonicalPath(new URL(link.getAttribute("href"), window.location.origin).pathname);
            const label = link.querySelector(".nav-label");
            const config = labels[path];
            if (!label || !config) return;
            label.dataset.i18n = config[0];
            label.textContent = translateLocal(config[0], config[1]);
            link.classList.toggle("active", path === canonicalPath(window.location.pathname));
        });
    }

    function applyRoleNavigation() {
        const membership = activeMembership();
        if (!membership) return;
        const access = accessForRole(membership.role);
        document.body.dataset.authRole = membership.role;
        document.body.classList.toggle("employee-portal-shell", Boolean(window.scheduleAuth?.isEmployeePortalMode?.()));
        ensureStandardNav();
        document.querySelectorAll(".nav-list a[href]").forEach((link) => {
            const path = canonicalPath(new URL(link.getAttribute("href"), window.location.origin).pathname);
            const isAllowed = access.nav.has(path);
            link.hidden = !isAllowed;
            link.style.display = isAllowed ? "" : "none";
        });
        applyNavLabels();
        ensureGlobalLogoutButton();
    }

    function enforcePageAccess() {
        if (isAuthPage()) return;
        const token = window.scheduleAuth?.getToken?.();
        const user = window.scheduleAuth?.getUser?.();
        if (!token || !user) {
            window.location.replace("/login");
            return;
        }
        const membership = activeMembership();
        if (!membership) {
            window.location.replace("/login");
            return;
        }
        const access = accessForRole(membership.role);
        const path = canonicalPath(window.location.pathname);
        if (!access.pages.has(path)) {
            window.location.replace(membership.role === "employee" ? "/weekly-preferences" : "/");
        }
    }

    function disableScheduleEditingForReadOnlyRoles() {
        const membership = activeMembership();
        if (!membership || accessForRole(membership.role).canEditSchedule) return;
        [
            "#generation-actions-btn",
            "#danger-actions-btn",
            "#open-generation-actions-btn",
            "#open-danger-actions-btn",
            "#add-shift-btn",
            "#auto-generate-btn",
            "#auto-generate-all-btn",
            "#clear-week-btn",
            "#clear-all-week-btn",
            "[data-action='delete']",
        ].forEach((selector) => {
            document.querySelectorAll(selector).forEach((element) => {
                element.disabled = true;
                element.hidden = true;
                element.style.display = "none";
            });
        });
        document.body.classList.add("role-read-only-schedule");
    }

    function applyAccessControl() {
        enforcePageAccess();
        applyRoleNavigation();
        disableScheduleEditingForReadOnlyRoles();
        ensureGlobalLogoutButton();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", applyAccessControl);
    } else {
        applyAccessControl();
    }
    document.addEventListener("app-language-changed", applyAccessControl);
    window.scheduleAccessControl = { apply: applyAccessControl, accessForRole };
})();
