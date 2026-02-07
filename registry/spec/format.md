# Registry Data Format (v0)

This document specifies the **Ledger Scrolls Registry** data structures.

The registry is designed to be:

- **verifiable** (hash-based integrity)
- **append-only** (updates publish new heads; history is retained)
- **forkable** (anyone can extend; readers choose trust anchors)

## Terms

- **Bytes**: the raw scroll content a user ultimately wants (image, pdf, text, etc.).
- **Pointer**: structured data that tells a viewer *how* to fetch bytes.
- **Entry**: `name -> pointer (+ verification metadata)`
- **Registry list**: snapshot list of entries.
- **Head**: points to the latest registry list snapshot; may reference the previous head.

## Canonical objects

### 1) Registry Entry

A registry entry MUST include:

- `name` — human-friendly identifier
- `pointer` — a typed pointer object
- `contentType` — MIME type (e.g. `image/png`, `application/pdf`)
- `sha256` — hex or base16 of SHA-256 of the resolved bytes

It MAY include:

- `sizeBytes`
- `description`
- `createdAt`
- `tags` (array)
- `license`

#### Name rules (v0)

- lowercase a-z, digits 0-9, and hyphen `-`
- 1–64 chars
- regex: `^[a-z0-9-]{1,64}$`

### 2) Pointer

Pointers are tagged unions with a `kind` field.

#### Pointer kinds (v0)

v0 defines a minimal set of pointer kinds.

1) `utxo-inline-datum-bytes-v1`

- Use when the bytes are stored in a **Cardano UTxO inline datum** (datum transports raw bytes).
- Required fields:
  - `txHash` — 64 hex chars
  - `txIx` — integer output index
- Notes:
  - See `registry/spec/cardano-utxo-datum.md` for the datum encoding used by this project.

2) `cip25-pages-v1` (declared)

- Use when bytes are stored as **CIP-25 (label 721) pages + manifest** assets.
- Required fields:
  - `policyId`
  - `manifestAsset`
- Optional fields (to avoid hardcoded time windows):
  - `manifestTx`
  - `manifestSlot`, `manifestHash`
  - `startSlot`, `startHash`

3) `url`

- Convenience pointer for off-chain mirrors.
- Required fields:
  - `url`
- Notes:
  - Still verifiable via `sha256` in the entry.

> Add new pointer kinds only when a viewer implementation exists.

### 3) Registry List

A registry list is a snapshot array of entries plus minimal metadata.

Required:

- `format`: `"ledger-scrolls-registry-list"`
- `version`: integer (v0 => `0`)
- `entries`: array of registry entries

Optional:

- `generatedAt`
- `generator`

### 4) Head

A head points to the latest registry list.

Required:

- `format`: `"ledger-scrolls-registry-head"`
- `version`: integer (v0 => `0`)
- `registryList` — a pointer to the registry list bytes

Optional:

- `prevHead` — pointer to prior head
- `createdAt`
- `author`
- `signature` (future; see forks/trust doc)

## Deterministic hashing

Viewers MUST define how to hash heads/lists deterministically.

v0 recommendation:

- Serialize the JSON with **stable key ordering** and no insignificant whitespace.
- Hash with SHA-256.

See `registry/spec/resolution.md` for verification flow.
