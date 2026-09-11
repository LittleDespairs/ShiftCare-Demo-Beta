// Generated release asset list: python tools/sync_release_metadata.py
const APP_VERSION = "0.21.1_beta";
const CACHE_NAME = `shiftcare-${APP_VERSION}`;

const SHELL_ASSETS = [
  "/",
  "/login",
  "/schedule",
  "/weekly-preferences",
  "/organization",
  "/feedback",
  "/guide",
  "/accept-invitation",
  "/reset-password",
  "/verify-email",
  "/static/css/auth.css?v=0.21.1_beta",
  "/static/css/schedule.css?v=0.21.1_beta",
  "/static/css/style.css?v=0.21.1_beta",
  "/static/js/accept_invitation.js?v=0.21.1_beta",
  "/static/js/access_control.js?v=0.21.1_beta",
  "/static/js/auth.js?v=0.21.1_beta",
  "/static/js/auth_client.js?v=0.21.1_beta",
  "/static/js/auth_i18n.js?v=0.21.1_beta",
  "/static/js/employees.js?v=0.21.1_beta",
  "/static/js/feedback.js?v=0.21.1_beta",
  "/static/js/home.js?v=0.21.1_beta",
  "/static/js/i18n.js?v=0.21.1_beta",
  "/static/js/online_status.js?v=0.21.1_beta",
  "/static/js/organization.js?v=0.21.1_beta",
  "/static/js/portal_settings.js?v=0.21.1_beta",
  "/static/js/pwa.js?v=0.21.1_beta",
  "/static/js/reset_password.js?v=0.21.1_beta",
  "/static/js/schedule.js?v=0.21.1_beta",
  "/static/js/support.js?v=0.21.1_beta",
  "/static/js/update_notifier.js?v=0.21.1_beta",
  "/static/js/verify_email.js?v=0.21.1_beta",
  "/manifest.webmanifest",
  "/static/icons/app-icon.svg",
  "/static/offline.html"
];

const OPTIONAL_PAGES = [
  "/settings",
  "/employees",
  "/departments",
  "/positions",
  "/employee-positions",
  "/shift-templates",
  "/coverage-requirements",
  "/support"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      await cache.addAll(SHELL_ASSETS);
      // Desktop and developer pages legitimately return 404 on the portal.
      // Their availability must not prevent installation of the shared shell.
      await Promise.all(OPTIONAL_PAGES.map(async (url) => {
        try {
          const response = await fetch(url);
          if (response.ok) await cache.put(url, response);
        } catch (error) {
          // Optional pages will be cached when successfully visited later.
        }
      }));
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys
        .filter((key) => key.startsWith("shiftcare-") && key !== CACHE_NAME)
        .map((key) => caches.delete(key))
    ))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const requestUrl = new URL(event.request.url);

  if (event.request.method !== "GET" || requestUrl.origin !== self.location.origin || requestUrl.pathname.startsWith("/api/")) {
    return;
  }

  if (event.request.mode === "navigate") {
    if (requestUrl.searchParams.get("embedded") === "1") {
      event.respondWith(fetch(event.request));
      return;
    }

    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const responseClone = response.clone();
            event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone)));
          }
          return response;
        })
        .catch(async () => (await caches.match(event.request))
          || (await caches.match(requestUrl.pathname))
          || caches.match("/static/offline.html"))
    );
    return;
  }

  if (
    requestUrl.pathname.startsWith("/static/js/") ||
    requestUrl.pathname.startsWith("/static/css/") ||
    requestUrl.pathname === "/manifest.webmanifest"
  ) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const responseClone = response.clone();
            event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone)));
          }
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request);
    })
  );
});
