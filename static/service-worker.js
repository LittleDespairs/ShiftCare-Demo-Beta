const CACHE_NAME = "schedule-app-0.13.6-beta-shell";

const SHELL_ASSETS = [
  "/",
  "/schedule",
  "/employees",
  "/weekly-preferences",
  "/settings",
  "/static/css/style.css?v=0.13.6_beta",
  "/static/css/schedule.css?v=0.13.6_beta",
  "/static/js/i18n.js?v=0.13.6_beta",
  "/static/js/pwa.js?v=0.13.6_beta",
  "/static/js/schedule.js?v=0.13.6_beta",
  "/static/js/employees.js?v=0.13.6_beta",
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

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request);
    })
  );
});
