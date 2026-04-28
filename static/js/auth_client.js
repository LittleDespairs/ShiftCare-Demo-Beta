(function () {
    const TOKEN_KEY = "schedule_app_auth_token";
    const USER_KEY = "schedule_app_auth_user";
    const ACTIVE_ORGANIZATION_KEY = "schedule_app_active_organization_id";
    const API_BASE_URL_KEY = "schedule_app_api_base_url";
    const CLOUD_API_BASE_URL = "https://schedule-app-beta-api-eoewa4enxa-zf.a.run.app";
    const nativeFetch = window.fetch.bind(window);

    function normalizeApiBaseUrl(value) {
        const trimmed = String(value || "").trim().replace(/\/+$/, "");
        if (!trimmed || trimmed === window.location.origin) return "";
        try {
            const parsed = new URL(trimmed);
            if (!["http:", "https:"].includes(parsed.protocol)) return "";
            return parsed.origin;
        } catch (error) {
            return "";
        }
    }

    function getApiBaseUrl() {
        return normalizeApiBaseUrl(localStorage.getItem(API_BASE_URL_KEY));
    }

    function setApiBaseUrl(value) {
        const normalized = normalizeApiBaseUrl(value);
        if (!normalized) {
            localStorage.removeItem(API_BASE_URL_KEY);
            return "";
        }
        localStorage.setItem(API_BASE_URL_KEY, normalized);
        return normalized;
    }

    function useLocalApi() {
        localStorage.removeItem(API_BASE_URL_KEY);
    }

    function useCloudApi() {
        return setApiBaseUrl(CLOUD_API_BASE_URL);
    }

    function resolveApiUrl(input) {
        const apiBaseUrl = getApiBaseUrl();
        const rawUrl = typeof input === "string" ? input : input?.url || "";
        if (!apiBaseUrl || !rawUrl) return input;
        if (rawUrl.startsWith("/api/")) {
            return `${apiBaseUrl}${rawUrl}`;
        }
        if (rawUrl.startsWith(window.location.origin + "/api/")) {
            return `${apiBaseUrl}${new URL(rawUrl).pathname}${new URL(rawUrl).search}`;
        }
        return input;
    }

    function isApiRequest(input) {
        const rawUrl = typeof input === "string" ? input : input?.url || "";
        if (rawUrl.startsWith("/api/") || rawUrl.startsWith(window.location.origin + "/api/")) return true;
        const apiBaseUrl = getApiBaseUrl();
        return Boolean(apiBaseUrl && rawUrl.startsWith(`${apiBaseUrl}/api/`));
    }

    window.fetch = function scheduleApiFetch(input, options = {}) {
        const rewrittenInput = resolveApiUrl(input);
        const headers = new Headers(options.headers || {});
        const token = getToken();
        if (isApiRequest(input) && token && !headers.has("Authorization")) {
            headers.set("Authorization", `Bearer ${token}`);
        }
        if (isApiRequest(input) && options.body && !headers.has("Content-Type")) {
            headers.set("Content-Type", "application/json");
        }
        return nativeFetch(rewrittenInput, { ...options, headers });
    };

    function getToken() {
        return localStorage.getItem(TOKEN_KEY) || "";
    }

    function getUser() {
        const raw = localStorage.getItem(USER_KEY);
        if (!raw) return null;
        try {
            return JSON.parse(raw);
        } catch (error) {
            localStorage.removeItem(USER_KEY);
            return null;
        }
    }

    function setSession(payload) {
        localStorage.setItem(TOKEN_KEY, payload.access_token);
        localStorage.setItem(USER_KEY, JSON.stringify(payload.user));
    }

    function clearSession() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        localStorage.removeItem(ACTIVE_ORGANIZATION_KEY);
    }

    function getActiveOrganizationId() {
        const value = localStorage.getItem(ACTIVE_ORGANIZATION_KEY);
        return value ? Number(value) : null;
    }

    function setActiveOrganizationId(organizationId) {
        if (!organizationId) {
            localStorage.removeItem(ACTIVE_ORGANIZATION_KEY);
            return;
        }
        localStorage.setItem(ACTIVE_ORGANIZATION_KEY, String(organizationId));
    }

    function getActiveMembership(user = getUser()) {
        const memberships = user?.memberships || [];
        const activeMemberships = memberships.filter((membership) => membership.status === "active");
        const savedOrganizationId = getActiveOrganizationId();
        return activeMemberships.find((membership) => membership.organization_id === savedOrganizationId)
            || activeMemberships[0]
            || memberships[0]
            || null;
    }

    async function request(url, options = {}) {
        const headers = new Headers(options.headers || {});
        const token = getToken();
        if (token) {
            headers.set("Authorization", `Bearer ${token}`);
        }
        if (options.body && !headers.has("Content-Type")) {
            headers.set("Content-Type", "application/json");
        }

        const response = await fetch(url, { ...options, headers });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            if (response.status === 401) {
                clearSession();
            }
            throw new Error(data.detail || `Request failed with ${response.status}`);
        }
        return data;
    }

    function requireSession(redirectTo = "/login") {
        const token = getToken();
        const user = getUser();
        if (!token || !user) {
            window.location.href = redirectTo;
            return null;
        }
        return user;
    }

    window.scheduleAuth = {
        TOKEN_KEY,
        USER_KEY,
        ACTIVE_ORGANIZATION_KEY,
        getToken,
        getUser,
        setSession,
        clearSession,
        getActiveOrganizationId,
        setActiveOrganizationId,
        getActiveMembership,
        request,
        requireSession,
        API_BASE_URL_KEY,
        CLOUD_API_BASE_URL,
        getApiBaseUrl,
        setApiBaseUrl,
        useLocalApi,
        useCloudApi,
        isApiRequest,
    };
})();
