# Ledger Scrolls Registry (DNS for Scrolls)

The **Ledger Scrolls Registry** is a *forkable, on-chain directory* that maps human-friendly names to verifiable scroll pointers.

**Mental model:**

- Traditional DNS: `name -> IP`
- Scroll Registry: `name -> pointer -> verified bytes`

This registry is **not a server**. It is just data. A viewer can read it, fetch referenced bytes, and verify integrity locally.

## Core concepts

- **Entry**: a mapping from a `name` (e.g. `constitution-e608`) to a **pointer** (how to fetch bytes) plus verification metadata (hashes, content-type, etc.).
- **Registry List**: a snapshot list of entries.
- **Head**: the latest canonical update for a registry line. A head points to a registry list snapshot, and optionally to a previous head.
- **Forks**: anyone can publish their own head that references your head (or list). Readers choose which head to trust.

## Directory layout

- `registry/spec/` — human-readable specification
- `registry/schemas/` — JSON schemas for heads, lists, pointers, entries
- `registry/examples/` — small example registry + head + test vectors
- `registry/tooling/` — reference scripts (build/verify)

## Start here

- Spec: [`registry/spec/format.md`](spec/format.md)
- Resolution: [`registry/spec/resolution.md`](spec/resolution.md)
- Forks & trust: [`registry/spec/forks-and-trust.md`](spec/forks-and-trust.md)
