# Architecture — how the stack fits together

One job: **read and write immutable media on a public ledger.** Everything
in this repository is one of four layers doing that job, and each layer can
survive the death of the layers above it.

```
┌────────────────────────────────────────────────────────────────────┐
│ 4. THE SITE (GitHub Pages serves this repo's root — a convenience) │
│    index.html (The Library) · leaks.html · the Main Viewer              │
│    calculator.html · calculator.html · media.html                     │
├────────────────────────────────────────────────────────────────────┤
│ 3. READERS (each one stands alone)                                 │
│    reader.html — one file, zero deps, MINTED ON-CHAIN              │
│    viewers/koios-cli — stdlib Python · koios-viewer (lsview)       │
├────────────────────────────────────────────────────────────────────┤
│ 2. WRITER TOOLS                                                    │
│    tools/lschain (prepare / mint) · scripts/ (standard scrolls)    │
├────────────────────────────────────────────────────────────────────┤
│ 1. THE PROTOCOL (the only layer that must never break)             │
│    registry/spec/ · docs/PROTOCOL_V1_PROPOSAL.md · conformance/    │
└────────────────────────────────────────────────────────────────────┘
```

## Layer 1 — the protocol

Two queries and a hash. The wire formats (`manifest-chain-v2`,
`utxo-inline-datum-bytes-v1`, `cip25-pages-v1`, metadata label 22025) are
frozen; the `conformance/` fixtures are the contract. Nothing above this
layer is allowed to matter: a stranger with the spec can rebuild everything
else. **The strongest proof lives on the chain itself: the minimal reader
is minted as a scroll** (`9a564165…07de2#0`), so the ledger carries its own
decoder.

## Layer 3 — readers and the source problem

A reader needs chain data, and where it gets it is a *trust choice the
reader's user makes* — never something hard-wired by us:

1. **Your own node + Koios instance** — zero third parties.
2. **Any Koios-compatible endpoint** you run or rent.
3. **`api.koios.rest`** — keyless; perfect for CLI/scripts. ⚠ Its browser
   CORS currently answers only koios.rest itself, which is why browser
   readers need the next two rungs.
4. **A CORS mirror** — [`tools/cors-mirror/`](../tools/cors-mirror/) is a
   ~25-line recipe anyone deploys free in two minutes. A mirror can hide
   data but can never forge it: every reader verifies SHA-256 locally.
5. **Blockfrost with your own free key** — different API, honest CORS;
   `reader.html` speaks it natively.

Site pages default to `[api.koios.rest, BEACN's mirror instance]` and show
which source answered in their trust logs. The BEACN mirror is a courtesy
deployment of the public recipe — the site works out of the box, and nobody
who forks the reader inherits a landlord. The **minted** reader contains no
BEACN endpoint at all.

## Layer 4 — one Library, thin doors

`index.html` (The Library) is the single browser engine: all three scroll
forms, channels, registries, deep links (`#s=<name>`, `#p=<policy>`),
user-set data source and registry head persisted locally. The old
per-scroll standalone viewers (bible, constitution, first-video, latest) and
the testnet rehearsal viewer have been **removed** — the Library reads every
scroll via `#s=<name>` deep links, so they were redundant. `leaks.html` and
`the Main Viewer` remain separate products (channel player, docket terminal) on
the same source discipline.

## Invariants (change these and it stops being Ledger Scrolls)

- A reader never renders bytes it could not verify.
- Published URLs never break; paths cited inside minted scrolls
  (`koios-viewer/`, `tools/lschain/`, `viewers/koios-cli/`) never move.
- Minted sources in `examples/` stay byte-exact, forever.
- Wire identifiers live in specs; humans read "Ledger Scroll."
- No secret, no key, no personal data ever enters the repo or a scroll.
