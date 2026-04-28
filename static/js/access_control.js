(function () {
    const ROLE_ACCESS = {
        owner: {
            pages: new Set(["/", "/schedule", "/employees", "/weekly-preferences", "/settings", "/organization", "/guide", "/docs"]),
            nav: new Set(["/", "/schedule", "/employees", "/weekly-preferences", "/settings", "/organization"]),
            canEditSchedule: true,
        },
        admin: {
            pages: new Set(["/", "/schedule", "/employees", "/weekly-preferences", "/settings", "/organization", "/guide", "/docs"]),
            nav: new Set(["/", "/schedule", "/employees", "/weekly-preferences", "/settings", "/organization"]),
            canEditSchedule: true,
        },
        scheduler: {
            pages: new Set(["/", "/schedule", "/employees", "/weekly-preferences", "/settings", "/organization", "/guide", "/docs"]),
            nav: new Set(["/", "/schedule", "/employees", "/weekly-preferences", "/settings", "/organization"]),
            canEditSchedule: true,
        },
        manager: {
            pages: new Set(["/", "/schedule", "/weekly-preferences", "/organization", "/guide", "/docs"]),
            nav: new Set(["/", "/schedule", "/weekly-preferences", "/organization"]),
            canEditSchedule: false,
        },
        read_only: {
            pages: new Set(["/", "/schedule", "/weekly-preferences", "/organization", "/guide", "/docs"]),
            nav: new Set(["/", "/schedule", "/weekly-preferences", "/organization"]),
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
        return ROLE_ACCESS[role] || ROLE_ACCESS.employee;
    }

    function canonicalPath(pathname) {
        if (pathname === "/organizations") return "/organization";
        return pathname || "/";
    }

    function isAuthPage() {
        return ["/login", "/accept-invitation"].includes(canonicalPath(window.location.pathname));
    }

    function translateLocal(key, fallback) {
        if (typeof window.translate === "function") {
            const value = window.translate(key);
            return value === key ? fallback : value;
        }
        return fallback;
    }

    function ensureStandardNav() {
        const nav = document.querySelector(".nav-list");
        if (!nav) return;
        [
            ["/", "⌂", "nav_dashboard", "Dashboard"],
            ["/schedule", "🗓", "nav_schedule", "Schedule"],
            ["/employees", "👥", "nav_employees", "Employees"],
            ["/weekly-preferences", "☑", "nav_requests", "Preferences"],
            ["/organization", "◎", "nav_organization", "Organization"],
            ["/settings", "⚙", "nav_settings", "Settings"],
        ].forEach(([href, icon, key, fallback]) => {
            if (nav.querySelector(`a[href="${href}"]`)) return;
            const item = document.createElement("a");
            item.href = href;
            item.className = "nav-item";
            item.innerHTML = `<span class="nav-icon">${icon}</span><span class="nav-label" data-i18n="${key}">${fallback}</span>`;
            nav.appendChild(item);
        });
    }

    function applyNavLabels() {
        const labels = {
            "/": ["nav_dashboard", "Dashboard"],
            "/schedule": ["nav_schedule", "Schedule"],
            "/employees": ["nav_employees", "Employees"],
            "/weekly-preferences": ["nav_requests", "Preferences"],
            "/settings": ["nav_settings", "Settings"],
            "/organization": ["nav_organization", "Organization"],
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
        ensureStandardNav();
        document.querySelectorAll(".nav-list a[href]").forEach((link) => {
            const path = canonicalPath(new URL(link.getAttribute("href"), window.location.origin).pathname);
            const isAllowed = access.nav.has(path);
            link.hidden = !isAllowed;
            link.style.display = isAllowed ? "" : "none";
        });
        applyNavLabels();
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
    }

    let applyingAccessControl = false;
    function applyAccessControlSoon() {
        if (applyingAccessControl) return;
        applyingAccessControl = true;
        window.requestAnimationFrame(() => {
            applyingAccessControl = false;
            applyAccessControl();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", applyAccessControl);
    } else {
        applyAccessControl();
    }
    document.addEventListener("app-language-changed", applyAccessControl);
    new MutationObserver(applyAccessControlSoon).observe(document.documentElement, {
        childList: true,
        subtree: true,
    });
    window.scheduleAccessControl = { apply: applyAccessControl, accessForRole };
})();
