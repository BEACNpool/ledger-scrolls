# Ledger Scrolls Protocol v1 — Proposal

Status: DRAFT · 2026-06-11 · Companion to [AUDIT_LEDGER_SCROLLS_2026-06.md](history/AUDIT_LEDGER_SCROLLS_2026-06.md)

This document defines the smallest protocol surface a third party needs to
read and write Ledger Scrolls without reading this repository's history. It
freezes what already works on mainnet, names what was previously implicit,
and adds only what v0 demonstrably lacks (signed heads, immutability classes,
manifest-authoritative paging).

Conformance language: MUST / SHOULD / MAY per RFC 2119. Every normative rule
here is (or must become) backed by a fixture in `conformance/`.

## 1. Model

```
name ──(registry entry)──▶ pointer ──(fetch)──▶ encoded bytes ──(decode)──▶ bytes ──(sha256)──▶ verified bytes
```

- **Bytes**: the media a user wants. Identified by SHA-256.
- **Pointer**: typed instructions for fetching bytes from Cardano (or a mirror).
- **Entry**: `name → pointer + contentType + sha256 (+ metadata)`.
- **Registry list**: snapshot array of entries.
- **Head**: points at the latest list; chains to the previous head; signed in v1.

A reader MUST NOT present bytes as canonical unless the SHA-256 matches the
entry. A reader MAY display unverified bytes only with an explicit
unverified/mismatch indication.

## 2. Canonical Pointer Kind Matrix

| Kind | Status | Required fields | Optional fields | Fetch + reconstruct |
|---|---|---|---|---|
| `utxo-inline-datum-bytes-v1` | **Stable** (live) | `txHash` (64-hex), `txIx` (int ≥ 0) | — | §3.1 |
| `cip25-pages-v1` | **Stable** (live) | `policyId` (56-hex) | `manifestAsset`, `manifestTx`, `manifestSlot`, `manifestHash`, `startSlot`, `startHash` | §3.2 |
| `url` | Stable | `url` | — | HTTP(S) GET; bytes verified via entry `sha256` |
| `utxo-locked-bytes` | **Deprecated alias** | `txin` (`HASH#IX`) | — | normalize → `utxo-inline-datum-bytes-v1` |
| `asset-manifest` | **Deprecated alias** | `policyId`, `assetName` | `manifestSha256` | normalize → `cip25-pages-v1` |

Writers MUST emit only canonical kinds. Readers SHOULD accept the aliases and
MUST treat them exactly as their canonical mapping. New kinds MUST NOT ship
before (a) a reference reader exists and (b) conformance vectors are merged.

Reserved names for future work (not yet specified): `utxo-datum-chain-v1`
(multi-datum large files), `reference-script-bytes-v1`.

## 3. Reconstruction Algorithms

### 3.1 `utxo-inline-datum-bytes-v1` (Standard Scroll / LS-LOCK)

1. Fetch the inline datum CBOR of output `txHash#txIx`.
   - Koios: `POST /utxo_info` with `{"_utxo_refs": ["HASH#IX"], "_extended": true}` — `_extended` is REQUIRED.
   - Blockfrost: `GET /txs/{hash}/utxos`, select `output_index`.
   - cardano-cli: `query utxo --tx-in HASH#IX --out-file …` and read `inlineDatum`.
2. Decode the datum:
   - If the CBOR top-level value is a **byte string** (definite or
     indefinite-length; indefinite chunks are each ≤ 64 bytes per
     `registry/spec/cardano-utxo-datum.md`), the decoded bytes are the payload.
   - Else if it is a constructor whose first field is a byte string, that
     field is the payload (legacy datums).
   - Else: fail with `UNSUPPORTED_DATUM`.
3. If entry/pointer codec is `gzip`, gunzip. (§4.2)
4. Verify SHA-256 against the entry. (§5)

The UTxO MUST remain unspent for the scroll to stay readable from the UTxO
set; publishers achieve permanence by locking at an always-fail script
address (Class A, §6).

### 3.2 `cip25-pages-v1` (Legacy Scroll / LS-PAGES)

Page data lives in CIP-25 (metadata label 721) under
`721 → policyId → assetName`.

**Page discovery — manifest-authoritative (v1):**

1. If `manifestAsset` is set and the manifest metadata contains a `pages`
   array (explicit asset names, in order), that list is **authoritative**:
   fetch exactly those assets, in that order.
2. Otherwise (v0-compatible heuristic): enumerate all assets under
   `policyId`; an asset is a *page* iff its metadata has an integer `i` and a
   payload field; assets with `role: "manifest"`, or whose name contains
   `MANIFEST`, are manifests. Pages sort ascending by `i`.
   A page MAY carry `codec`/`sha` fields — their presence MUST NOT
   reclassify it as a manifest (this exact bug shipped twice).

**Payload extraction:**

- The payload field is `payload`, `segments`, or `seg` (first present wins).
- Each segment is either a hex string or an object `{"bytes": "<hex>"}`.
- Strip an optional leading `0x`; hex is case-insensitive; segments are ≤ 64
  hex chars (32 bytes) due to the ledger's metadata string limit.
- Concatenate all segments of a page in array order; concatenate pages in
  index order. The result is the encoded byte stream.

**Manifest fields (v1 writers MUST emit):**

```json
{
  "role": "manifest",
  "spec": "ls-pages-v1",
  "ct": "<MIME type>",
  "codec": "gzip" | "none",
  "pages": ["<ASSET_NAME>", ...],
  "sha256": "<hex of decoded bytes>",
  "sha256_enc": "<hex of encoded bytes, when codec != none>"
}
```

(v0 manifests in the wild use `sha_html`/`sha_gz`/`pages`-as-count and
per-page `sha`; readers SHOULD accept these.)

**Per-page integrity (SHOULD):** when a page carries `sha`, readers SHOULD
verify the page's decoded segment bytes against it, enabling early failure
and per-page mirror repair.

3. Decode per codec (§4.2), verify (§5).

**Immutability caveat:** bytes in 721 metadata are immutable once minted, but
*resolution* depends on asset enumeration; assets can be moved or (if policy
allows) re-minted. Writers MUST time-lock policies for Class A claims (§6).

### 3.3 `url`

Plain HTTP(S) fetch. The mirror is untrusted by construction: the entry
`sha256` is the only authority. Readers MUST verify before presenting and
SHOULD prefer on-chain pointers when both exist.

## 4. Encoding Rules

### 4.1 Hashing

- Algorithm: SHA-256, lowercase hex.
- Every entry MUST carry `sha256` of the **decoded** bytes (the file the user
  receives). Entries for compressed scrolls SHOULD also carry `sha256_enc`
  (encoded/compressed stream) so transport can be verified before
  decompression (zip-bomb guard).
- Registry objects (heads, lists) are hashed over **canonical JSON**: UTF-8,
  lexicographically sorted keys at every level, no insignificant whitespace
  (`json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False)`).
  Fixtures: `conformance/fixtures/registry/`.

### 4.2 Compression

- v1 codecs: `none`, `gzip`. Nothing else.
- Writers MUST produce deterministic gzip: `mtime=0`, no filename field
  (`gzip -n`), so the encoded hash is reproducible from the source file.
- Readers: a declared codec WINS. `codec: "auto"` (legacy) and *absent* codec
  mean: gunzip iff the stream starts `1f 8b`. A declared `none` MUST NOT be
  sniffed into gzip.
- Decompression MUST be bounded (readers SHOULD cap output at a configurable
  limit, default 256 MB) to resist decompression bombs.

### 4.3 Datum encoding (writing)

Per `registry/spec/cardano-utxo-datum.md`: CBOR indefinite-length byte string
(`0x5f` … chunks ≤ 64 bytes … `0xff`). A definite-length byte string is also
valid where tooling permits. The payload inside is the (optionally gzipped)
file bytes — not JSON, not hex-of-hex.

### 4.4 Size selection (writing)

| Decoded size | Mode |
|---|---|
| ≤ ~9 KB (fits one tx after overhead) | Standard Scroll, codec `none` |
| ≤ ~14 KB compressed | Standard Scroll, codec `gzip` |
| larger | LS-PAGES: gzip, split encoded stream into pages of `segments_per_page × 32` bytes (default 169 segments ≈ 5.4 KB/page; keep each mint tx ≤ 15,500 bytes — use `mint/validate_tx_size.sh`) |

Budget rule of thumb (mainnet, 2026 params): a Standard Scroll locks
min-UTxO ADA that grows with datum size (≈ 4–7.5 ADA observed for 1–3 KB
datums) plus ~0.2 ADA fee; LS-PAGES costs one tx fee per page plus the
min-UTxO of each page NFT (recoverable if pages are held, but moving pages
breaks Class A — see §6).

## 5. Verification & Failure Semantics

Readers MUST produce a structured result:

```
{ bytes, contentType, hash, verified: true|false|null, source, proofModel }
```

- `verified: true` — hash matched the entry. Canonical render allowed.
- `verified: false` — mismatch. MUST NOT render as canonical; MUST show the
  expected and computed hashes; MAY offer raw download clearly marked.
- `verified: null` — entry carried no hash. MUST be visibly flagged.
- Pointer fetch failure → `UNRESOLVED` (name exists, bytes unavailable);
  distinct from `NOT_FOUND` (name absent from list).
- **Provider disagreement**: if multiple providers return different bytes for
  the same pointer, a verified copy beats an unverified one; two differing
  unverifiable copies → `CONFLICT`, hard failure with both hashes shown.
- Duplicate names in one list: first occurrence wins, reader MUST warn (v0
  rule, kept).

**Render safety:** `verified` says nothing about safety. Render by *declared*
content type only: text as text, images/video/PDF via browser-native blob
rendering, HTML only in a fully sandboxed iframe (`sandbox=""` — no scripts,
no same-origin), all else download-only. Sniffing MUST NOT upgrade a
non-HTML declared type to HTML rendering.

## 6. Immutability Classes

Every entry SHOULD declare `class`; readers infer it when absent.

| Class | Guarantee | Conditions |
|---|---|---|
| **A** | Bytes + pointer immutable | Inline datum at always-fail script (unspent), or pages under a time-locked policy with explicit manifest `pages` list |
| **B** | Bytes immutable, name routing mutable | Entry resolved via a registry head that can be superseded |
| **C** | Mirror with on-chain hash commitment | `url` pointer + `sha256` |

Marketing language discipline: "permanent" may be claimed only for Class A,
and only with the qualifier that Standard Scroll permanence = "while the
UTxO is unspent (unspendable at an always-fail address)".

## 7. Registry v1: Signed Heads

v0 heads are anonymous JSON. v1 adds:

```json
{
  "format": "ledger-scrolls-registry-head",
  "version": 1,
  "registryList": { "kind": "utxo-inline-datum-bytes-v1", "txHash": "…", "txIx": 0 },
  "prevHead":     { "kind": "utxo-inline-datum-bytes-v1", "txHash": "…", "txIx": 0 },
  "listSha256": "<canonical sha256 of the list bytes>",
  "signer": { "keyId": "<hex of Ed25519 pubkey>", "nextKeys": ["<hex>", "…"] },
  "signature": "<Ed25519 over canonical JSON of head minus signature>"
}
```

- Signature: Ed25519 over the canonical JSON (§4.1) of the head object with
  the `signature` field removed.
- **Rotation**: a head MAY list `nextKeys`; a later head signed by any listed
  key is a valid continuation. Readers following a *key* accept rotations;
  readers pinning a *head hash* are frozen until they re-pin.
- **Forks**: anyone may publish a head referencing your `prevHead`. Trust is
  reader-side: pin (a) a head txin/hash, or (b) a signer key, or (c) a policy
  id + asset (the `LS_REGISTRY` NFT pattern). Clients MUST expose which
  anchor is in use.
- **Equivocation**: two heads signed by the same key with the same `prevHead`
  is detectable misbehavior; readers SHOULD surface it and freeze on the
  earlier head until the user chooses.
- `listSha256` makes the head→list link tamper-evident even through `url`
  mirrors of the list.

## 8. Trust Profiles

Every client mode MUST be able to state its profile:

| Mode | Proof model | You are trusting |
|---|---|---|
| Koios / Blockfrost | Indexer assertion + local hash check | The indexer's UTxO/metadata DB (hash check still catches tampering of bytes, not of *absence*) |
| Local node (cardano-cli / Ogmios) | Chain-validated UTxO set + local hash check | Your own node |
| Mirror (`url`) | Hash check only | Nothing but SHA-256 preimage resistance |
| P2P (future) | Header chain + block fetch | Honest-majority of peers you dialed |

## 9. Legacy Compatibility

- Aliases per §2 table; normalize on read, never write.
- App-internal config (`lock_txin`, `policy_id`, `manifest_asset`,
  `sha256_original`, `sha256_gzip`) is an implementation detail of the
  current viewer; it MUST NOT appear in interchange documents and should be
  migrated to canonical entries when the app adopts the SDK.
- Live v0 data that violates v1 MUSTs (e.g. `bible` / `bitcoin-whitepaper`
  entries lacking `sha256`): grandfathered for reading; the next published
  list SHOULD repair them (verified hashes are now recorded in this repo).
- v0 readers remain compatible with v1 documents except signed heads (new
  fields are additive; `version: 1` signals signature presence).

## 10. Conformance

`conformance/` is the contract: stdlib-only Python and Node runners over one
fixture manifest, exercising hashing, deterministic gzip, both CBOR byte
string forms, page reconstruction (string and object segments, `0x`
prefixes, manifest exclusion), pointer validity (canonical + alias + six
rejection cases), and canonical-JSON registry hashing. Every new rule in
this spec lands with a vector; every reader bug found in the June 2026 audit
already has one.
