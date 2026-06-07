const VERSION = "v2";
const CACHE_STATIC = `linguaalayam-static-${VERSION}`;
const CACHE_PAGES = `linguaalayam-pages-${VERSION}`;

const PRECACHE = [
  "/",
  "/static/manifest.json",
  "/static/logo.svg",
  "/static/logo-mark.svg",
  "/static/locales/en.json",
  "/static/locales/ml.json",
];

function isStatic(url) {
  return url.pathname.startsWith("/static/");
}

function isSearchOrApi(url) {
  return (
    url.pathname.startsWith("/search") ||
    url.pathname.startsWith("/lookup/") ||
    url.pathname.startsWith("/mcp")
  );
}

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_STATIC).then((c) => c.addAll(PRECACHE))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== CACHE_STATIC && k !== CACHE_PAGES)
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);

  // Skip cross-origin (fonts, HTMX CDN)
  if (url.origin !== self.location.origin) return;

  // Search and API: network-only — dynamic content, no value caching
  if (isSearchOrApi(url)) return;

  if (isStatic(url)) {
    // Cache-first: static assets rarely change; serve instantly
    e.respondWith(
      caches.match(e.request).then(
        (cached) =>
          cached ||
          fetch(e.request).then((res) => {
            caches.open(CACHE_STATIC).then((c) => c.put(e.request, res.clone()));
            return res;
          })
      )
    );
  } else {
    // Network-first with cache fallback: pages load fresh when online,
    // fall back to cached version when offline
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          caches.open(CACHE_PAGES).then((c) => c.put(e.request, res.clone()));
          return res;
        })
        .catch(() => caches.match(e.request))
    );
  }
});
