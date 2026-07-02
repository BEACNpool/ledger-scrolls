/* Koios CORS mirror — a ~25-line proxy that makes any Koios-API endpoint
 * readable from browsers. Deploy your own copy for free; never depend on
 * anyone else's. See README.md in this folder.
 *
 * Trust note: a mirror can lie about *absence* but never about *content* —
 * every conforming Ledger Scrolls reader verifies SHA-256 locally, so the
 * worst a malicious mirror can do is fail to serve you, not fool you.
 */
const UPSTREAM = "https://api.koios.rest";

const cors = (req) => ({
  "Access-Control-Allow-Origin": req.headers.get("Origin") || "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "*",
  "Access-Control-Max-Age": "86400",
  "Vary": "Origin",
});

export default {
  async fetch(req) {
    if (req.method === "OPTIONS")
      return new Response(null, { status: 204, headers: cors(req) });
    if (req.method !== "GET" && req.method !== "POST")
      return new Response("method not allowed", { status: 405, headers: cors(req) });

    const url = new URL(req.url);
    const upstream = await fetch(UPSTREAM + url.pathname + url.search, {
      method: req.method,
      headers: { "Content-Type": req.headers.get("Content-Type") || "application/json" },
      body: req.method === "POST" ? await req.arrayBuffer() : undefined,
    });

    const res = new Response(upstream.body, upstream);
    for (const [k, v] of Object.entries(cors(req))) res.headers.set(k, v);
    return res;
  },
};
