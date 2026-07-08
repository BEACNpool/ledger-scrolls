/* Ledger Scrolls PWA shell — caches UI assets only.
   Never caches chain data or user files. Scroll bytes stay on Cardano. */
const CACHE = "ls-shell-v1";
const SHELL = [
  "./",
  "./index.html",
  "./calculator.html",
  "./favicon.svg",
  "./manifest.webmanifest",
  "./media.html",
  "./robots.txt",
];

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
  // Same-origin shell only
  if (url.origin !== self.location.origin) return;
  event.respondWith(
    caches.match(req).then((hit) => {
      const fetchPromise = fetch(req)
        .then((res) => {
          if (res && res.ok && url.pathname.match(/\.(html|svg|webmanifest|js|css)$/)) {
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
