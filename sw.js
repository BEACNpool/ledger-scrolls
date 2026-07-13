/* Ledger Scrolls PWA shell — caches UI assets only.
   Never caches chain data or user files. Scroll bytes stay on Cardano.

   HTML is NETWORK-FIRST: the mint page builds and signs real mainnet
   transactions, so a deploy must reach users on their next load. The cache is
   only an offline fallback. Static assets (svg/webmanifest/txt) are
   cache-first with background revalidation. Bump CACHE on every deploy that
   changes SHELL semantics.

   ONE worker for the whole origin. A scope holds a single registration, so a
   second worker (chess used to ship its own) does not coexist with this one —
   it replaces it, and every page inherits whatever caching policy that other
   worker happened to have. Every page registers this file. */
/* addAll() is atomic: one 404 rejects the whole install and the worker never
   activates. Every path here must exist. (The second PWA manifest was removed
   with the second PWA — one house, one installable app.) */
const CACHE = "ls-shell-v4";
const SHELL = [
  "./",
  "./index.html",
  "./calculator.html",
  "./ledger-book.html",
  "./ledger-chess.html",
  "./media.html",
  "./favicon.svg",
  "./manifest.webmanifest",
  "./robots.txt",
];

const isHtml = (req, url) =>
  req.mode === "navigate" ||
  url.pathname.endsWith("/") ||
  url.pathname.endsWith(".html");

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  // Never intercept API / chain queries
  if (/koios|blockfrost|coingecko|cardanoscan/i.test(url.hostname)) return;
  // Never touch the blob: frames the chess arcade executes from
  if (url.protocol === "blob:") return;
  // Same-origin shell only
  if (url.origin !== self.location.origin) return;

  if (isHtml(req, url)) {
    // Network-first: fresh mint logic whenever online; cache only as offline fallback.
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // Static assets: cache-first with background revalidation.
  event.respondWith(
    caches.match(req).then((hit) => {
      const fetchPromise = fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => hit);
      return hit || fetchPromise;
    })
  );
});
