const CACHE_NAME = "shiftcare-0.20.4-beta-schedule-sync-manual-time-20260619";

const SHELL_ASSETS = [
  "/",
  "/login",
  "/schedule",
  "/weekly-preferences",
  "/organization",
  "/static/css/style.css?v=0.20.4_beta-schedule-sync-manual-time",
  "/static/css/auth.css?v=0.20.4_beta-employee-portal-account",
  "/static/css/schedule.css?v=0.20.4_beta-schedule-sync-manual-time",
  "/static/js/i18n.js?v=0.20.4_beta-schedule-sync-manual-time",
  "/static/js/auth_client.js?v=0.20.4_beta-desktop-local",
  "/static/js/access_control.js?v=0.20.4_beta-employee-portal-polish",
  "/static/js/auth_i18n.js?v=0.20.4_beta-employee-portal-account",
  "/static/js/auth.js?v=0.20.4_beta-portal-entry-employee-mode",
  "/static/js/schedule.js?v=0.20.4_beta-schedule-sync-manual-time",
  "/static/js/organization.js?v=0.20.4_beta-employee-portal-account",
  "/static/js/online_status.js?v=0.20.4_beta",
  "/static/js/pwa.js?v=0.20.4_beta",
  "/static/manifest.webmanifest",
  "/static/icons/app-icon.svg"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys
        .filter((key) => key !== CACHE_NAME)
        .map((key) => caches.delete(key))
    ))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const requestUrl = new URL(event.request.url);

  if (requestUrl.pathname.startsWith("/api/")) {
    return;
  }

  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  if (
    requestUrl.pathname.startsWith("/static/js/") ||
    requestUrl.pathname.startsWith("/static/css/")
  ) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone));
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
