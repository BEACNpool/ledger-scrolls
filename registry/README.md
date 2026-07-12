# Ledger Scrolls Registry (DNS for Scrolls)

The **Ledger Scrolls Registry** is a *forkable, on-chain directory* that maps human-friendly names to verifiable scroll pointers.

**Mental model:**

- Traditional DNS: `name -> IP`
- Scroll Registry: `name -> pointer -> verified bytes`

This registry is **not a server**. It is just data. A viewer can read it, fetch referenced bytes, and verify integrity locally.

## The current model: a Registry NFT

Since 2026-07-07 the catalog is an NFT. A **Registry Head** is minted under a
library policy with `721` trait `Type = "Registry Head"`; the scroll list rides
in the mint transaction's metadata under **label `22027`**. Updating the
library = minting a new head with a higher `Version`. Readers resolve a bare
policy id, a `policy.ASSET` pin, a `$handle`, or a mint tx hash to the latest
head. The live library's front door is **`$beacn`**.

Spec: [`registry/spec/registry-nft-v2.md`](spec/registry-nft-v2.md) — **start here.**

## Core concepts

- **Entry**: a mapping from a `name` (e.g. `constitution-e608`) to a **pointer** (how to fetch bytes) plus verification metadata (hashes, content-type, etc.).
- **Registry List**: a snapshot list of entries.
- **Head**: the latest canonical update for a registry line. A head carries a registry list snapshot and names its predecessor.
- **Forks**: anyone can mint their own head under their own policy. Readers choose which head to trust.

## Directory layout

- `registry/spec/` — human-readable specification
- `registry/schemas/` — JSON schemas for heads, lists, pointers, entries
- `registry/examples/` — small example registry + head + test vectors
- `registry/tooling/` — reference scripts (build/verify)
- `registry/published/` — tracked mirror of the live on-chain registry (regenerated from chain, never hand-edited)

## Start here

- **Current registry (NFT, label 22027):** [`registry/spec/registry-nft-v2.md`](spec/registry-nft-v2.md)
- Entry & pointer object shapes (v0, still normative): [`registry/spec/format.md`](spec/format.md)
- Legacy datum head resolution (v0, superseded for discovery): [`registry/spec/resolution.md`](spec/resolution.md)
- Forks & trust: [`registry/spec/forks-and-trust.md`](spec/forks-and-trust.md)
