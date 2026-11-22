// Faísca's service worker: makes the app installable and its pages open offline.
//
// - Pages and static assets: network first, falling back to the cached copy,
//   so a new version shows as soon as it is deployed.
// - /api/: never cached here. Searches are live, the backend already caches
//   them for a day, and a stale basket would be wrong.

const CACHE_NAME = "faisca-shell-v1";
const SHELL = ["/", "/cesto/", "/definicoes/", "/manifest.webmanifest", "/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  // Drop caches of older versions of this worker.
  event.waitUntil(
    caches
      .keys()
      .then((names) => Promise.all(names.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  const isOwnPage = url.origin === self.location.origin && event.request.method === "GET";
  if (!isOwnPage || url.pathname.startsWith("/api/") || url.pathname.startsWith("/health")) return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        }
        return response;
      })
      .catch(() =>
        caches.match(event.request, { ignoreSearch: url.pathname !== "/" }).then((cached) => cached ?? caches.match("/")),
      ),
  );
});
