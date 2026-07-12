# LS-CHAIN v2 — Manifest-Chain Scrolls (`manifest-chain-v2`)

Status: ACTIVE (first mainnet scroll June 2026) · Supersedes LS-PAGES for writing

> **Provenance — this document has been amended since it was etched.**
> On 2026-07-02 this spec was minted as a scroll in its own format:
> pointer `e4845deed98471b29b35689cfdb76f18add189c8d8f5c61b2ef32ea7ce6d5cf9#0`,
> `sha256 = 4793c38349cca60d552c52d68dfd950f3dd945db55c8a6a87f05ca6d98e3b242`
> (`examples/the-spec/receipts.json`). That scroll is immutable and still reads
> exactly as it did then — it is the snapshot, and it is reproducible from the
> chain by anyone.
>
> The file you are reading is the **living** spec. It was amended after the mint
> (dense page packing; multi-part conformance parity), so it no longer hashes to
> the etched copy — the receipt's note that the source "must stay byte-identical"
> was overtaken by those edits and is true only of the snapshot. Nothing on-chain
> changed or could change. To read the etched version, resolve the pointer above;
> to see what moved, `git log registry/spec/manifest-chain-v2.md`. The next mint of
> this spec re-anchors the two.

LS-CHAIN stores media of any size as **bare metadata transactions** (no NFTs,
nothing locked per page) anchored by a **manifest inline datum** locked at an
always-fail script address (Class A: in the UTxO set, readable from any node,
forever, with one query).

## Why this format

Measured against mainnet protocol parameters (2026-06):

| Lane | Cost | Locked | Footguns |
|---|---|---|---|
| Inline datum | ~4.4 ADA/KB | forever | none — but priced for small files |
| CIP-25 NFT pages (LS-PAGES, legacy) | ~0.35 ADA/KB | ~1.4 ADA per page NFT | pages can be moved; policy discipline required |
| **LS-CHAIN bare metadata** | **~0.06 ADA/KB** | **nothing** | none — pages are plain txs, listed explicitly |

Resolution is fully deterministic: one UTxO query for the manifest, then
batched `tx_metadata` lookups by **explicit tx hash list**. No policy scans,
no asset enumeration, no manifest-vs-page heuristics.

## Pointer kind

```json
{ "kind": "manifest-chain-v2", "txHash": "<64-hex manifest tx>", "txIx": 0 }
```

## Manifest (inline datum, valid Plutus Data)

The manifest UTxO sits at an always-fail script address and MUST remain
unspent. Its inline datum is the CBOR encoding of:

```
Constr 0 [                       -- CBOR tag 121
  version        : int           -- 2
  contentType    : bytes         -- UTF-8 MIME, e.g. "text/html"
  codec          : bytes         -- "gzip" | "none" (UTF-8)
  sizeDecoded    : int           -- byte length of the decoded file
  sha256Decoded  : bytes(32)     -- hash of the decoded file
  sha256Encoded  : bytes(32)     -- hash of the encoded stream (= decoded when codec=none)
  pageTxHashes   : [bytes(32)]   -- ordered page transaction hashes
  next           : Constr 0 []                       -- no continuation
               | Constr 1 [bytes(32) txHash, int ix] -- next manifest txin
]
```

- All byte strings are ≤ 64 bytes, satisfying Plutus Data chunk limits.
- `next` chains manifests for files whose page list exceeds one datum.
  Reference writers seal **at most 350 page hashes per manifest**
  (`MAX_PAGES_PER_MANIFEST`; ≈ 5.3 MB per link at default page size) —
  readers MUST accept any count that fits the datum.
  Page lists concatenate in chain order; every manifest in the chain repeats
  the file-level fields, which MUST be identical.

## Page transactions

Each page is a plain transaction (self-send; no mint) carrying metadata under
**label 22025**:

```json
{ "22025": {
    "v": 2,
    "i": 1,            // 1-based page index
    "n": 3,            // total pages
    "sha": "0x<32B>",  // SHA-256 of this page's payload bytes
    "p": [ "0x<64B>", "0x<64B>", … ]   // payload segments, raw CBOR byte strings
} }
```

- Segments are **raw CBOR byte strings of at most 64 bytes** (the ledger
  metadata limit). In cardano-cli "no schema" JSON metadata, a `0x…` string
  produces a byte string. Indexers may render them back as `0x…` strings,
  bare hex, or `{"bytes": "<hex>"}` objects — readers MUST accept all three.
- A page's payload is the concatenation of its segments in array order.
- The encoded stream is the concatenation of page payloads in `pageTxHashes`
  order. Page boundaries are arbitrary; `i`/`n` are integrity aids and MUST
  be consistent with the manifest order.
- RECOMMENDED page payload: pack as many 64-byte segments as fit under
  `max_tx_size − safety_margin` (mainnet `max_tx_size` is typically 16,384;
  writers use a 400 B margin). Reference tools default to **auto** packing —
  at 16,384/400 both calculator.html and prepare.py compute **237 segments
  (15,168 B payload)**; `conformance/` and `scripts/check_cost_model_sync.mjs`
  hold the implementations to the same model. The older 190-segment / 12,160 B
  choice remains valid and more conservative. Larger full pages amortize the
  fixed per-tx fee and need fewer signatures. To REPRODUCE an existing mint's
  page splits, pass the plan.json's `segmentsPerPage` to
  `prepare.py --segments-per-page N` instead of auto.

## Reconstruction algorithm

1. Fetch the inline datum of the pointer txin
   (Koios: `POST /utxo_info` with `"_extended": true`).
2. Decode the manifest; collect `pageTxHashes` (following `next` links).
3. Batch-fetch metadata for all page tx hashes
   (Koios: `POST /tx_metadata`); take label `22025` from each.
4. For each page in manifest order: concatenate segments; if `sha` present,
   verify the page payload hash (MUST fail the page on mismatch).
5. Concatenate page payloads → encoded stream; verify `sha256Encoded`.
6. If codec is `gzip`, gunzip (readers SHOULD bound output size).
7. Verify `sha256Decoded`. Only then present the bytes as the scroll,
   rendered per `contentType` (HTML always fully sandboxed).

Failure semantics follow the v1 proposal §5: any hash mismatch →
`verified: false`, no canonical render.

## Write algorithm

1. Encode: deterministic gzip (`mtime=0`, no filename) if it shrinks the file.
2. Hash decoded + encoded streams; split encoded stream into pages of
   `segments_per_page × 64` bytes (auto-max recommended); hash each page.
3. Submit page transactions (chaining each on the previous change output —
   no confirmation waits); record tx hashes in order.
4. Build the manifest datum from the recorded hashes; lock it with the
   minimum-UTxO ADA at the always-fail script address
   (`addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn`, script
   `templates/standard-scroll/always-fail.plutus`).
5. Read the scroll back from the chain and verify both hashes **before**
   announcing. Keep `receipts.json` (all tx hashes, hashes, parameters).

Reference implementation: `tools/lschain/` (prepare + mint) and
`koios-viewer` (`lsview reconstruct-chain`).

## Trust notes

- The manifest inherits Standard-Scroll permanence (Class A).
- Page bytes are immutable chain history; *serving* them requires an indexer
  or archive node (same trust as CIP-25 metadata) — but because pages are
  listed by explicit hash, any single archive can prove correctness of its
  copy against the manifest hashes alone. Mirrors are verifiable byte-for-byte.
