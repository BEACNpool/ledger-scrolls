/* Ledger Chess shell cache — UI only. Never caches chain API or game blob. */
const CACHE = "lc-shell-v1";
const SHELL = [
  "./ledger-chess.html",
  "./favicon.svg",
  "./chess-manifest.webmanifest",
  "./index.html",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (/koios|blockfrost|coingecko|cardanoscan/i.test(url.hostname)) return;
  if (url.origin !== self.location.origin) return;
  // Never cache blob: game frames
  if (url.protocol === "blob:") return;
  e.respondWith(
    caches.match(req).then((hit) => {
      const net = fetch(req)
        .then((res) => {
          if (res && res.ok && /\.(html|svg|webmanifest)$/.test(url.pathname)) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => hit);
      return hit || net;
    })
  );
});
