(function () {
    const TOKEN_KEY = "schedule_app_auth_token";
    const USER_KEY = "schedule_app_auth_user";

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
        getToken,
        getUser,
        setSession,
        clearSession,
        request,
        requireSession,
    };
})();
