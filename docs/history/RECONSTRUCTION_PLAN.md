# Ledger Scrolls Reconstruction Plan

2026-06-11 · Companion to [AUDIT_LEDGER_SCROLLS_2026-06.md](AUDIT_LEDGER_SCROLLS_2026-06.md) and [PROTOCOL_V1_PROPOSAL.md](PROTOCOL_V1_PROPOSAL.md)

Goal: turn a working prototype into **the** open-source read/writer for
immutable media on Cardano — implementable by strangers, verifiable by
anyone, usable by non-experts.

## Target Directory Layout

Monorepo. One protocol, two SDKs, thin products on top:

```
ledger-scrolls/
├── protocol/                  # the spec is the product
│   ├── spec/                  # moved from registry/spec + v1 proposal split into chapters
│   └── schemas/               # moved from registry/schemas
├── conformance/               # fixture corpus + runners  [EXISTS]
├── sdk-js/                    # @ledger-scrolls/core (ESM, browser+Node)
│   └── src/
│       ├── pointers.js        # parse/normalize/validate pointer kinds
│       ├── providers/         # koios.js, blockfrost.js, (ogmios.js)
│       ├── reconstruct.js     # standard + pages algorithms
│       ├── registry.js        # head/list resolution, canonical JSON, (signatures)
│       └── verify.js          # structured verification results
├── sdk-python/                # ledger_scrolls package — same module map
├── cli/                       # `ledger-scrolls` command (thin over sdk-python)
├── web/                       # the viewer app (thin over sdk-js; today's app/)
├── viewers-static/            # bible.html etc., rebuilt as shells over sdk-js
├── scripts/                   # node-side shell tooling (mint, verify) [KEEP]
├── examples/                  # one dir per live scroll, with receipts [EXPAND]
└── docs/
```

Don't physically move everything on day one — adopt the layout as code is
*rewritten into* it, so history stays reviewable.

## What to Keep / Rewrite / Delete

**Keep as-is (proven, load-bearing):**
- `registry/spec/*` — accurate; becomes `protocol/spec/`.
- `scripts/mint-standard-scroll.sh`, `verify-scroll.sh`, `mint/validate_tx_size.sh` — correct cardano-cli plumbing; later wrapped, not replaced.
- All mainnet receipts in README/examples (tx hashes, policy IDs, hashes) — these are the project's crown jewels. Never edit historical receipts.
- `conformance/` — grow it; it is the contract.

**Rewrite into SDKs (logic is right, placement is wrong):**
- `app/src/utils/{blockchain,reconstruct,scrolls}.js` → `sdk-js`.
- `koios-viewer/lsview/*` → `sdk-python` (+ `cli/`).
- Inline JS in `bible.html`/`constitution.html`/`first-video.html`/`latest.html` → thin pages importing `sdk-js`. Until then they carry the audit's known bug classes (no sandbox, duplicated parsing).
- `registry/tooling/` → absorbed by `sdk-python` (`lsr-verify` survives as `ledger-scrolls verify`).

**Delete / archive:**
- `viewers/p2p/` — done (was bytecode-only).
- `koios-viewer/lsview/blockfrost.py` — unused in CLI flows; Blockfrost support returns as an SDK provider.
- `app/dist` + root `assets/` committed bundles — replace with a GitHub
  Actions Pages deploy; the repo should not carry build output (root
  `bible.html` etc. stay until rebuilt as SDK shells).
- `archived/experimental-p2p-viewer/` — keep, clearly labeled prior art.

## Phases

### Phase 0 — Stabilize (LANDED with the June 2026 audit)

Broken readers fixed and verified on mainnet; HTML sandboxed; verification
surfaced in UI; schemas/tooling aligned with the live chain; conformance
corpus (21 vectors, dual runners); hygiene + dependency advisories cleared;
Bible/whitepaper hashes recorded.

### Phase 1 — One protocol implementation per language (1–3 weeks)

1. **CI first**: GitHub Actions running both conformance runners, `npm run
   lint`, `npm run build`, `python -m compileall` on every PR. (Highest
   return of any item in this plan.)
2. Extract `sdk-js` from `app/src/utils` with the v1 structured verification
   result; `web/` consumes it. Add the SDK's own unit tests fed by
   `conformance/manifest.json`.
3. Reshape `koios-viewer` into `sdk-python` + `cli` skeleton
   (`ledger-scrolls read NAME|--txin|--policy`, `verify`, `registry dump`).
4. Rebuild `bible.html`/`constitution.html`/`first-video.html` as ~50-line
   shells over `sdk-js` (sandboxed, badge, download). 
5. Pages deploy workflow; stop committing bundles.

Exit criteria: zero duplicated reconstruction logic; conformance + lint
gating PRs; static viewers sandboxed.

### Phase 2 — The writer becomes a product (2–4 weeks)

1. `ledger-scrolls write <file> --mode auto|standard|pages` —
   chunk/compress per spec §4.4, **estimate cost and ask for confirmation**,
   build txs (cardano-cli via local node first), mint, then *read back and
   verify* before reporting success.
2. Every write emits `receipts.json` (txids, policy, hashes, parameters) and
   a ready-to-merge registry entry JSON.
3. Pages writer reproduces the Bible/whitepaper format exactly (manifest with
   explicit `pages` list + hashes — v1 §3.2) and is itself covered by a
   conformance vector generated from its output.
4. Document the "ordinary user" path honestly: local signing only; no keys
   in browsers until a CIP-30 flow ships.

Exit criteria: a stranger with a synced node and 10 ADA publishes a verified
scroll in one command.

### Phase 3 — Registry v1 + trust UX (2–4 weeks)

1. Signed heads per spec §7 (Ed25519 over canonical JSON), `lsr`-equivalents
   in both SDKs, vectors for sign/verify/rotation/equivocation.
2. `web/` loads its library from the on-chain registry head (hardcoded list
   becomes bootstrap fallback); shows the trust anchor in use.
3. Trust-profile panel per provider; provider disagreement → CONFLICT UI.
4. Publish BEACN's signing key + head pinning instructions.

### Phase 4 — Beyond indexers (exploratory)

- Ogmios/local-node provider in both SDKs (same trust as cardano-cli, works
  from the browser against your own endpoint).
- Decision gate on P2P: only build a raw Ouroboros client if a maintained
  library exists; otherwise document local-node as the trust-minimized path.
- Verifiable mirror kit: static export of all scrolls + hashes, so archives
  (IPFS, web servers, USB sticks) can serve Class C copies that any reader
  verifies against chain.

## Test & Conformance Strategy

- `conformance/` stays implementation-neutral and offline; every spec MUST
  gets a vector, every fixed bug gets a regression vector (BTCWP codec-page,
  Bible object-segments, `_extended`, `0x` prefixes are already in).
- SDK unit tests may hit the network only behind an opt-in flag; CI is
  offline.
- One **live smoke job** (scheduled weekly, not per-PR): reconstruct
  hosky-png + bitcoin-whitepaper via Koios and compare to recorded hashes —
  this is what would have caught the Koios API drift that silently broke
  every reader.

## Risks

| Risk | Mitigation |
|---|---|
| Provider API drift (it already happened) | Weekly live smoke job; provider code isolated in SDK modules |
| Refactor breaks live site | Pages deploy only from CI-green main; root HTML untouched until SDK shells are conformance-clean |
| Solo-maintainer bus factor | Spec + conformance are designed so a stranger can re-implement; that is the real durability story |
| Scope creep toward "platform" | The north star stays: publish bytes, point at bytes, verify bytes. Everything else is a viewer. |
