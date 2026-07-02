# Ledger Scrolls Technical Audit — June 2026

Audited: 2026-06-11 · Repo: `BEACNpool/ledger-scrolls` @ `ca8e5ba` · Auditor: Claude (Fable)

Companion documents:

- [PROTOCOL_V1_PROPOSAL.md](PROTOCOL_V1_PROPOSAL.md) — canonical protocol surface for v1
- [RECONSTRUCTION_PLAN.md](RECONSTRUCTION_PLAN.md) — phased repo reconstruction plan

## Executive Verdict

The core idea is sound and already proven on mainnet: **deterministic pointers
to immutable bytes, verified by SHA-256, readable without an indexer**. Eight
scrolls resolve from the live on-chain registry today, including a 4.6 MB
HTML Bible and a 175-page video. That is a real, working permanence primitive
— not vaporware.

But the implementation had decayed underneath the idea. As of `ca8e5ba`:

- **Every Standard Scroll was unreadable** in both the web app (Koios mode)
  and the Python viewer, because Koios requires `_extended: true` to return
  inline datums and no client sent it.
- **The Python CIP-25 path was triply broken**: wrong parameter name for
  `policy_asset_list` (HTTP 404), page NFTs carrying `codec` fields
  misclassified as manifests, and `0x`-prefixed payload segments crashing
  `bytes.fromhex`.
- The JSON schemas and reference tooling used **pointer names that the live
  on-chain registry does not use**.

None of this was visible from the repo: there are no tests, no conformance
fixtures, and no CI. The protocol survived only because the bytes on chain
are immutable; the *readers* are the fragile layer. The single highest-return
investment is therefore the conformance corpus + CI, ahead of any feature.

All of the above defects were fixed and verified against mainnet during this
audit (see "Changes Landed With This Audit" below).

## Repo Health

| Area | State at `ca8e5ba` | Notes |
|---|---|---|
| `app/` (React/Vite viewer) | Builds; 9 lint errors; 4 npm advisories (2 high) | Standard Scrolls broken in Koios mode |
| `koios-viewer/` (Python) | Compiles; all network paths broken vs current Koios v1 | No tests would have caught this |
| `registry/spec/` | Good, thoughtful v0 spec | Matches the live registry |
| `registry/schemas/` | Stale — pre-spec pointer names | Diverged from spec and chain |
| `registry/tooling/` | Stale names; no chain resolution implemented | `lsr-verify` could only verify `url` pointers |
| `viewers/p2p/` | Only orphaned `__pycache__` bytecode, zero source | Removed |
| Root HTML viewers | Work (legacy scrolls only, GET endpoints) | Fourth independent reimplementation of the protocol |
| Docs/README | Rich but drifting (structure section describes deleted dirs) | |
| Tests/CI | None | Root cause of everything above |

## Protocol Risks

1. **Vocabulary drift (now closed at the schema layer).** The live registry
   head (`a9c56fb3…bad9#0`) uses `utxo-inline-datum-bytes-v1` /
   `cip25-pages-v1` — the spec was right, the schemas/tooling/app-configs were
   wrong. The app still uses its own private shape (`lock_txin`, `policy_id`,
   `manifest_asset`); see the v1 proposal for the migration.
2. **Four reader implementations, zero shared code.** `app/src/utils`,
   `koios-viewer/lsview`, `viewers/koios-cli`, and the inline JS in
   `bible.html`/`constitution.html`/`first-video.html` each reimplement
   fetching + reconstruction with slightly different field tolerance
   (`payload` vs `seg` vs `segments`, ascii vs hex metadata keys). Every chain
   or provider quirk must be fixed four times — and historically wasn't.
3. **Underspecified page discovery.** Legacy reconstruction scans *all* assets
   under a policy and applies heuristics to decide what is a page. The
   manifest exists but is not the source of truth in any reader. Heuristics
   differ between readers (this audit found the Python one dropping valid
   pages). v1 must make the manifest authoritative.
4. **Immutability classes are implicit.** "Live on Cardano mainnet and
   permanently verifiable" is true for locked-datum scrolls, but page NFTs
   sitting at spendable addresses can be moved (the README's own "DO NOT MOVE
   NFTs" warning concedes this). Entries should declare their guarantee class
   (see v1 proposal §6).
5. **Registry trust is social, not cryptographic.** The public head txin is
   hardcoded in clients; updates are spend-and-recreate. Anyone watching the
   registry address learns the new head, but nothing authenticates it beyond
   control of the key. Signed heads (spec'd as "future") are the v1 item.

## Security Risks

1. **HTML rendering was not sandboxed** *(fixed)*. The app rendered on-chain
   HTML via a blob URL in a plain `<iframe>` — same-origin, scripts enabled.
   Any hash-valid scroll containing a `<script>` would execute in the app's
   origin. Hash-verified ≠ safe-to-execute. The iframe is now fully sandboxed
   (no scripts, no same-origin); the standalone `bible.html` /
   `constitution.html` / `first-video.html` viewers still need the same
   treatment.
2. **Hash verification was silently skipped or hidden** *(surfaced)*. Legacy
   reconstruction only `console.warn`ed on mismatch and rendered anyway, and
   several catalog entries (`bible`, `bitcoin-whitepaper`, `genesis-scroll`)
   carry no expected hash at all, so "verification" never happened. The viewer
   now displays an explicit badge: verified / mismatch / no hash on record.
   v1 should make hashes mandatory in registry entries (the spec already says
   MUST; the live `bible` and `bitcoin-whitepaper` entries violate it).
3. **Content-type sniffing escalates privilege.** `reconstructLegacy`
   upgrades anything starting with `<!doctype`/`<html` to `text/html`
   regardless of the declared type — turning a plain-text scroll into active
   content. Acceptable only because of the sandbox; v1 should render under the
   *declared* type and offer "open as HTML" as an explicit user action.
4. **Auto-gunzip on magic bytes.** Readers decompress anything starting
   `1f 8b` even when the codec says `none`. Codec declarations should win;
   sniffing should be a fallback for legacy scrolls only.
5. **Dependency advisories** *(fixed)*: vite (path traversal / arbitrary file
   read in dev server, high), picomatch ReDoS (high), postcss XSS (moderate),
   brace-expansion hang (moderate). All resolved via `npm audit fix`; no
   breaking changes.

## Product Gaps

- **No writer product.** `scripts/mint-standard-scroll.sh` is solid plumbing
  but demands a synced local node, key files, and shell literacy. There is no
  `ledger-scrolls write ./file.png` experience and no Legacy-Scroll writer at
  all (the Bible pipeline appears to have been bespoke).
- **No trust profile in UX.** A Koios reader trusts Koios's database; the UI
  presents it identically to local-node verification. The data source, proof
  model, and verification scope should be visible per scroll load.
- **Registry exists but the app doesn't use it.** `app` ships a hardcoded
  `SCROLLS` array; the on-chain registry (which works — verified during this
  audit) is dead code in the main UX. The library should load from the
  registry head with the hardcoded list as bootstrap/fallback.
- **No provider-disagreement story.** Koios → Blockfrost fallback is silent.
  When two providers return different bytes for the same pointer, the reader
  should fail loudly, not pick the first that parses.

## Dependency / Build Findings

- `npm ci` 177 → 251 packages (eslint-plugin-react added); `npm audit` now
  clean at `--audit-level=moderate`.
- `npm run lint` now passes (was 9 errors; 5 were real, 4 were missing
  `react/jsx-uses-vars` config for framer-motion).
- Bundle is ~553 KB minified (~173 KB gzip). Largest contributors:
  framer-motion, cbor-web, React. Code-splitting or replacing cbor-web with
  the ~40-line decoder the protocol actually needs would cut this sharply.
- Python packages have no pinned dev tooling, no tests, no CI. `cbor2` is the
  only runtime dep of `koios-viewer`; `requests` for `registry/tooling`.

## Proposed Architecture

Monorepo (splitting repos now would multiply the drift problem), reshaped
around one rule: **the protocol logic lives in exactly two packages — one JS,
one Python — and everything else consumes them.**

```
ledger-scrolls/
├── protocol/          # specs (moved from registry/spec), schemas, this audit
├── conformance/       # fixture corpus + dual runners  [LANDED]
├── sdk-js/            # @ledger-scrolls/core: pointers, providers, reconstruct, verify
├── sdk-python/        # ledger_scrolls: same surface, same fixtures
├── cli/               # `ledger-scrolls read|write|verify|registry` (thin over sdk-python)
├── web/               # viewer app (thin over sdk-js)
├── examples/          # preserved receipts for every live scroll
└── docs/
```

Key decisions argued for in the v1 proposal:

- Pointer kinds are **the** stable interface; everything else is negotiable.
- Manifest-authoritative page discovery for new LS-PAGES scrolls.
- Trust modes as first-class provider objects (koios / blockfrost / local
  node via cardano-cli or Ogmios / future P2P), each self-describing.
- Verification result is a structured object (`verified`, `hash`, `source`,
  `proofModel`), never a boolean buried in a log.

## Migration Plan (summary — details in RECONSTRUCTION_PLAN.md)

1. **Phase 0 (landed with this audit):** fix all broken readers, sandbox HTML,
   align schemas/tooling with the live chain, seed conformance corpus, clean
   repo hygiene, patch dependencies.
2. **Phase 1:** extract `sdk-js` from `app/src/utils` + root viewers; make
   `app` and a rewritten `bible.html` consume it; CI running conformance on
   both SDKs.
3. **Phase 2:** productize the writer (CLI: chunk → estimate cost → choose
   mode by size → mint → emit registry entry + receipts file).
4. **Phase 3:** registry v1 — signed heads, app loads library from chain,
   trust-anchor pinning UX.
5. **Phase 4:** P2P revival (Ogmios/local-node first; the archived
   mini-protocol client is prior art, not a base).

## Priority Roadmap

| P | Item | Why |
|---|---|---|
| P0 | CI: conformance runners + lint + build on every PR | Everything in this audit's "broken" list was silent |
| P0 | Standalone viewers: sandbox iframes, share resolver | Same XSS exposure as the app had |
| P1 | Extract sdk-js; registry-driven library in app | Kills the 4-way reimplementation |
| P1 | Record missing hashes on-chain (bible, whitepaper, genesis) in next registry list | Spec says sha256 is MUST |
| P1 | Writer CLI MVP (standard scrolls only) | First real "write" product |
| P2 | Signed registry heads + pinning | Trust becomes cryptographic |
| P2 | Trust-profile UI; provider disagreement = hard failure | Honest trust UX |
| P3 | Pages writer (large media), cost estimator | Completes write story |
| P3 | Local node / Ogmios provider; P2P revival decision | Indexer-free reading |

## Changes Landed With This Audit

All verified against mainnet (Hosky PNG byte-exact `798e3296…642f`; BTC
whitepaper 33,887 bytes; live registry head resolves; `lsr-verify` returns
`ok: true` for hosky-png; conformance 22/22 in both runtimes):

1. `chore:` removed committed bytecode (`viewers/p2p` was bytecode-only) and
   build log; `.gitignore` tightened.
2. `chore(app):` dependency advisories fixed; `react/jsx-uses-vars` enabled.
3. `fix(app):` verification badge (verified/mismatch/none), sandboxed HTML
   iframe, working download button, batched Koios asset metadata (Bible:
   ~240 requests → ~5), fixed inverted mint-tx fallback, lint clean.
4. `fix(app)` + `fix(koios-viewer):` `_extended: true` on `utxo_info` /
   `address_utxos` — un-breaks every Standard Scroll read via Koios.
5. `fix(koios-viewer):` `_asset_policy` param, manifest-vs-page
   classification, `0x` segment handling, batched `asset_info`.
6. `feat(registry):` schemas/tooling/examples aligned to live pointer kinds;
   `lsr-verify` now resolves `utxo-inline-datum-bytes-v1` on-chain with a
   minimal stdlib CBOR byte-string decoder; legacy aliases normalized.
7. `feat:` `conformance/` corpus + stdlib-only Python and Node runners.

## Answers to the Required Deep-Dive Questions

1. **Smallest stable protocol surface:** the three pointer kinds with their
   reconstruction algorithms, the datum byte-string encoding, the page
   concat+gunzip rule, SHA-256 verification, and canonical-JSON hashing of
   registry objects. Roughly 4 pages of spec; see PROTOCOL_V1_PROPOSAL.md.
2. **v1 pointer kinds:** `utxo-inline-datum-bytes-v1`, `cip25-pages-v1`,
   `url`. Accept `utxo-locked-bytes`/`asset-manifest` as read-only aliases;
   never emit. The app's private config shape becomes an internal
   representation, deprecated at the interchange layer.
3. **Chunk/compress/hash:** see v1 proposal §4 — gzip with mtime=0 (made
   deterministic), hash both raw and encoded bytes, 64-byte CBOR chunks for
   datums, ≤32-byte hex segments for pages, manifest lists pages explicitly.
4. **Practical Cardano limits:** tx ≤ 16 KB ⇒ ~14–15 KB usable payload per
   tx both for inline datums and for metadata pages; metadata strings ≤ 64
   bytes ⇒ 32-byte segments; min-UTxO scales with datum size (the 1.3 KB
   Hosky datum locks ~7.3 ADA; expect roughly 4–6 ADA per locked datum plus
   ~0.2 ADA fee per tx, and one tx per page for paged scrolls).
5. **Safest write path for ordinary users:** Standard Scroll via CLI against
   a public provider for fee estimation but **signing locally**; never ask
   for keys in a browser until a CIP-30 flow exists. Always emit a receipts
   file and verify the read-back bytes before declaring success.
6. **When providers disagree:** hard failure with both answers shown. Bytes
   that hash-match the entry are trustworthy from *any* provider — that's
   the protocol's superpower; use it to break ties, and only the tie-break
   winner renders.
7. **Proving reconstruction is the intended scroll:** entry `sha256` is the
   commitment; the registry list containing it is itself hash-committed in
   an on-chain datum, and the head datum chains to it. Pin one head txin and
   every byte downstream is verifiable. Gap: heads are unsigned (v1 fixes).
8. **Head signing/rotation/pinning:** Ed25519 over canonical-JSON of the head
   with `signature` envelope + `nextKeys` rotation statements; readers pin
   either a head hash (frozen) or a signer key (followable). See proposal §7.
9. **Render policy:** images/video/PDF via blob URL (browser-native parsers,
   no script risk); text as text; HTML only inside `sandbox=""`; anything
   else download-only. Never auto-upgrade declared type via sniffing.
10. **P2P viewer:** replace, don't revive. Local-node via Ogmios/cardano-cli
    gives the same trust win with maintained dependencies; revisit raw
    mini-protocol clients only if a maintained Python/JS Ouroboros library
    emerges. Keep the archive as documentation of the wire format.
11. **Conformance fixtures from repo examples:** Hosky datum (live, byte
    exact), BTCWP pages (0x-prefixed segments + codec-bearing pages — the
    case that broke the Python reader), constitution manifest (manifest
    naming convention), registry head/list (canonical hashing). All but the
    constitution one are seeded as of this audit.
12. **Remove/rename/archive before public push:** done: `viewers/p2p`
    bytecode, build log, stale schema names. Remaining: README structure
    section (stale), `koios-viewer/lsview/blockfrost.py` (Blockfrost path
    unused in CLI flows), the duplicated root bundle story (`assets/` vs
    `app/dist`) should move to a Pages deploy workflow, and the standalone
    HTML viewers should become thin shells over the shared SDK.
