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

1. `utxo-locked-bytes`
   - Intended for content stored/referenced by a **locked UTxO**.
   - Required fields:
     - `txin` — `"<txHash>#<index>"`

2. `asset-manifest`
   - Intended for content referenced by a **policy id + asset name** that itself represents a manifest.
   - Required fields:
     - `policyId`
     - `assetName`
     - `manifestSha256` — hash of the manifest bytes

3. `url`
   - Convenience pointer for off-chain mirrors.
   - Required fields:
     - `url`
   - Notes:
     - Still verifiable via `sha256` in the entry.

> v0 is intentionally small. Add more pointer kinds only when a viewer implementation exists.

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
