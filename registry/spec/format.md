# Registry Data Format (v0)

> **Catalog discovery has moved on-chain:** the live registry is an NFT whose
> scroll list rides in mint-tx metadata label `22027` — see
> [`registry-nft-v2.md`](registry-nft-v2.md). The **entry** and **pointer**
> objects below remain normative (the NFT list expands to them); the datum
> head/list containers are the retired v0 lineage.

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
- Recommended fields:
  - `manifestAsset` — MAY be empty when pages are discoverable by `role`/`payload` metadata alone, but SHOULD be set for unambiguous resolution.
- Optional fields (to avoid hardcoded time windows):
  - `manifestTx`
  - `manifestSlot`, `manifestHash`
  - `startSlot`, `startHash`

3) `manifest-chain-v2`

- Use for media of any size: bare metadata page transactions anchored by a
  Class-A manifest datum. The preferred kind for new large scrolls.
- Required fields:
  - `txHash` — 64 hex chars (manifest transaction)
  - `txIx` — integer output index
- See `registry/spec/manifest-chain-v2.md` for the full format.

4) `url`

- Convenience pointer for off-chain mirrors.
- Required fields:
  - `url`
- Notes:
  - Still verifiable via `sha256` in the entry.

> Add new pointer kinds only when a viewer implementation exists.

#### Legacy aliases (deprecated)

Earlier drafts used different kind names. They MUST NOT be emitted in new
documents; readers MAY accept them and treat them as the canonical kind:

| Legacy kind | Canonical kind | Field mapping |
|---|---|---|
| `utxo-locked-bytes` (`txin`: `HASH#IX`) | `utxo-inline-datum-bytes-v1` | split `txin` into `txHash` + `txIx` |
| `asset-manifest` (`policyId`, `assetName`) | `cip25-pages-v1` | `assetName` → `manifestAsset` |

The live on-chain registry (the `LS_REGISTRY_V6` NFT's label-`22027` list)
uses only the canonical kinds, in compact form — see
[`registry-nft-v2.md`](registry-nft-v2.md).

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
