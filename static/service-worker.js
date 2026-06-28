const CACHE_NAME = "shiftcare-0.20.10-beta-weekly-preference-approval-20260628";

const SHELL_ASSETS = [
  "/",
  "/login",
  "/schedule",
  "/settings",
  "/employees",
  "/departments",
  "/positions",
  "/employee-positions",
  "/shift-templates",
  "/coverage-requirements",
  "/weekly-preferences",
  "/organization",
  "/feedback",
  "/guide",
  "/static/css/style.css?v=0.20.10_beta-desktop-1080p-readability",
  "/static/css/auth.css?v=0.20.10_beta-desktop-1080p-readability",
  "/static/css/schedule.css?v=0.20.10_beta-desktop-1080p-readability",
  "/static/js/i18n.js?v=0.20.10_beta-department-access",
  "/static/js/auth_client.js?v=0.20.10_beta-desktop-local",
  "/static/js/access_control.js?v=0.20.10_beta-department-access",
  "/static/js/auth_i18n.js?v=0.20.10_beta-department-access",
  "/static/js/auth.js?v=0.20.10_beta-portal-entry-employee-mode",
  "/static/js/schedule.js?v=0.20.10_beta-schedule-sync-manual-time",
  "/static/js/organization.js?v=0.20.10_beta-department-access",
  "/static/js/feedback.js?v=0.20.10_beta-feedback",
  "/static/js/online_status.js?v=0.20.10_beta",
  "/static/js/pwa.js?v=0.20.10_beta",
  "/static/js/update_notifier.js?v=0.20.10_beta-startup-updates",
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
    if (requestUrl.searchParams.get("embedded") === "1") {
      event.respondWith(fetch(event.request));
      return;
    }

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
