# CORS Mirror — be your own gatekeeper

The public Koios API (`api.koios.rest`) is keyless and open — but as of
mid-2026 its **browser** CORS policy only answers its own website. Scripts
and CLIs are unaffected; web readers are stonewalled.

This folder is the fix as a **recipe, not a dependency**: a tiny Cloudflare
Worker that forwards Koios requests and adds honest CORS headers. Anyone can
deploy their own in about two minutes, free.

## Deploy your own (≈2 minutes)

1. Free Cloudflare account → **Workers & Pages → Create Worker**
2. Paste [`worker.js`](worker.js), deploy
3. Your endpoint: `https://<name>.<account>.workers.dev/api/v1`
4. Paste it into any Ledger Scrolls reader as a custom source

Or with the CLI: `npx wrangler deploy worker.js --name koios-mirror`

## Trust model (read this)

A mirror sits between you and the chain, so be precise about what it can and
cannot do:

- **It can never alter content undetected.** Every conforming reader
  verifies SHA-256 locally against the on-chain manifest. Tampered bytes =
  nothing renders.
- **It can lie about absence** (claim a scroll doesn't exist) and it can see
  which pointers you look up. If that matters, run the mirror yourself — or
  run your own Koios instance and skip the mirror entirely.

Independence ladder, strongest first: your node + your Koios instance →
your mirror (this recipe) → someone else's mirror → someone else's API key
service. Ledger Scrolls readers let you pick; nothing is hard-wired.

BEACN runs one public instance of this exact recipe
(`https://koios.beacn.workers.dev/api/v1`) as a courtesy fallback for the
demo pages on the website. Treat it as a convenience, not infrastructure:
the whole point of this folder is that you never have to use it.
