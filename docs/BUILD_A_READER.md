# Build Your Own Reader

Ledger Scrolls has one job: **read and write immutable media on a public
ledger.** A format only deserves the word *immutable* if anyone can rebuild
the media without asking permission — so the most important program in this
ecosystem is not ours. It's the one **you** write.

This page is everything you need. The whole protocol is two chain queries
and a hash.

## The algorithm (all of it)

```
pointer (txHash#ix)
  → fetch that output's inline datum            [1 query]
  → decode 8 CBOR fields: contentType, codec,
    sizes, two SHA-256s, the ordered page-tx list
  → fetch metadata label 22025 for those txs    [1 query]
  → concatenate the byte segments, in order
  → gunzip if codec says gzip
  → sha256(result) == the manifest's fingerprint, or you show NOTHING
```

Tiny files skip the pages: the datum itself **is** the file
(a "single-coin" / Standard Scroll). If the datum's top-level CBOR value is
a byte string rather than a manifest, those bytes are the media.

The golden rule of every conforming reader: **never render bytes you could
not verify.**

## Reference readers to copy from (all in this repo)

| Reader | Language | Lines that matter | Best starting point for |
|---|---|---|---|
| [`reader.html`](../reader.html) | Browser JS, one file, zero deps | ~200 | Web readers. This exact file is minted on-chain — see below. |
| [`viewers/koios-cli/read_scroll.py`](../viewers/koios-cli/read_scroll.py) | Python, stdlib only | ~150 | Scripts, air-gapped verification |
| [`koios-viewer/`](../koios-viewer/) (`lsview`) | Python package | — | Full tooling: every format, registry, catalogs |

## The two queries, concretely (Koios API flavor)

```bash
# 1. the manifest datum
curl -X POST https://api.koios.rest/api/v1/utxo_info \
  -H 'Content-Type: application/json' \
  -d '{"_utxo_refs":["<txHash>#0"], "_extended":true}'
# → .inline_datum.bytes is CBOR: [2, contentType, codec, sizeDecoded,
#    sha256Decoded, sha256Encoded, [pageTxHashes…], next]

# 2. the pages it names
curl -X POST https://api.koios.rest/api/v1/tx_metadata \
  -H 'Content-Type: application/json' \
  -d '{"_tx_hashes":["<page-tx-1>","<page-tx-2>"]}'
# → label "22025" of each: { v, i, n, sha, p: ["0x<64-byte segment>", …] }
```

Segment encodings vary by indexer — accept `0x`-prefixed hex, bare hex, and
`{"bytes":"<hex>"}` objects. Concatenate segments in array order, pages in
manifest order. Full normative rules: [PROTOCOL_V1_PROPOSAL.md](PROTOCOL_V1_PROPOSAL.md)
and [the chain-format spec](../registry/spec/manifest-chain-v2.md).

## Choosing a data source (and staying independent)

A reader is only as independent as its data source. The Koios API is an
**open-source query layer** anyone can run against their own node
([koios.rest](https://koios.rest), or `koios-lite` + db-sync at home) — that
is why our readers speak it. Your options, most independent first:

1. **Your own node + your own Koios instance** — zero third parties.
2. **Any Koios-compatible provider** — same API, your choice of operator.
3. **The public `api.koios.rest`** — keyless and great for scripts/CLI.
   ⚠ As of mid-2026 its **browser** CORS policy only answers its own
   website, so web readers need option 1, 2, 4 — or a CORS mirror you
   deploy yourself in two minutes: [`tools/cors-mirror/`](../tools/cors-mirror/).
4. **Blockfrost with your own free key** — different API, proper browser
   CORS; `reader.html` supports it natively.

A conforming reader should let the user pick the endpoint — trust is
reader-side, always. Never hard-wire someone else's proxy into your reader;
an endpoint you don't control is a landlord.

## Prove your reader is correct

The [conformance suite](../conformance/) is the contract. Point your
implementation at its fixtures — hashing, deterministic gzip, both CBOR
byte-string forms, segment variants, pointer validity — and your thirty
lines and ours can prove they agree:

```bash
python3 conformance/run_conformance.py     # or: node conformance/run_conformance.mjs
```

Then read something real: the [live scrolls](SCROLL_INVENTORY.md) all carry
their expected hashes. If your reader reconstructs the Eternal Scroll to
`65824f62…47dd2`, it works.

## The reader that reads itself

`reader.html` is minted on Cardano **as a Ledger Scroll**. Hand any
conforming reader its pointer and you get back `reader.html`, byte for
byte — a reader you can extract from the chain using nothing but the spec,
which then reads every other scroll, including itself.

That loop is the whole point. The library holds its own pair of glasses.
If this repository, this website, and everyone who ever worked on this
protocol disappear, the spec is two queries and a hash — and a working
implementation is carved into the ledger it reads.

*(The pointer lives in [SCROLL_INVENTORY.md](SCROLL_INVENTORY.md) and in
`examples/the-reader/` with full receipts.)*
