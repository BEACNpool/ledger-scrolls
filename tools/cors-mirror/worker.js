/* Koios CORS mirror — a small proxy that makes any Koios-API endpoint
 * readable from browsers. Deploy your own copy for free; never depend on
 * anyone else's. See README.md in this folder.
 *
 * This file is byte-for-byte the code BEACN's public instance runs
 * (koios.beacn.workers.dev, redeployed 2026-07-09): it normalizes the
 * /api/v1 prefix, routes /preview/* to the Preview-testnet Koios, echoes the
 * caller's Origin, and mirrors requested CORS headers on real responses —
 * the part api.koios.rest itself omits for browsers.
 *
 * Trust note: a mirror can lie about *absence* but never about *content* —
 * every conforming Ledger Scrolls reader verifies SHA-256 locally, so the
 * worst a malicious mirror can do is fail to serve you, not fool you.
 */
export default {
  async fetch(request) {
    const url = new URL(request.url);

    let path = url.pathname.replace(/\/+/g, "/");
    if (!path.startsWith("/")) {
      path = `/${path}`;
    }

    // /preview/* goes to the Preview-testnet Koios (prefix stripped)
    let base = "https://api.koios.rest";
    if (path === "/preview" || path.startsWith("/preview/")) {
      base = "https://preview.koios.rest";
      path = path.slice("/preview".length) || "/";
    }

    path = path.replace(/^\/api\/v1\/api\/v1(?=\/|$)/, "/api/v1");
    if (!path.startsWith("/api/v1/") && path !== "/api/v1") {
      path = `/api/v1${path}`;
    }

    const target = `${base}${path}${url.search}`;

    const origin = request.headers.get("Origin") || "*";
    const reqHeaders =
      request.headers.get("Access-Control-Request-Headers") || "Content-Type";

    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": origin,
          "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
          "Access-Control-Allow-Headers": reqHeaders,
          "Access-Control-Max-Age": "86400",
          Vary: "Origin, Access-Control-Request-Headers",
        },
      });
    }

    const headers = new Headers(request.headers);
    headers.delete("host");
    headers.delete("origin");
    headers.delete("referer");

    if (request.method === "POST" && !headers.get("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    const init = {
      method: request.method,
      headers,
      body:
        request.method === "GET" || request.method === "HEAD"
          ? undefined
          : await request.arrayBuffer(),
    };

    const resp = await fetch(target, init);

    const outHeaders = new Headers(resp.headers);
    outHeaders.set("Access-Control-Allow-Origin", origin);
    outHeaders.set("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
    outHeaders.set("Access-Control-Allow-Headers", reqHeaders);
    outHeaders.set("Vary", "Origin, Access-Control-Request-Headers");

    return new Response(resp.body, {
      status: resp.status,
      statusText: resp.statusText,
      headers: outHeaders,
    });
  },
};
