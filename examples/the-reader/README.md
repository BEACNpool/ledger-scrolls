# The Reader — a reader you can rebuild from the chain it reads

`reader.html` is the minimal Ledger Scrolls reader: one dependency-free HTML
file that fetches raw chain data, reassembles it, and refuses to render
anything it cannot verify. On July 2, 2026 it was minted on Cardano mainnet
**as a Ledger Scroll** — so the library now permanently contains its own
pair of glasses.

| Field | Value |
|---|---|
| Pointer | `manifest-chain-v2` · `9a564165ebdc4e0c4a2e1163b5cf9355604ecb8e163b425d834570e5b9007de2#0` |
| Lock address | `addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn` (always-fail) |
| Pages | 1 bare metadata tx, label 22025 |
| Content | `text/html`, gzip, 16,634 → 6,499 bytes |
| SHA-256 (decoded) | `a824298dc5ced0aad1954c7d8d40bb6dda09debf402f062ab402dcebbb6a9215` |
| Total cost | ~0.64 ADA fees + ~1.44 ADA locked with the manifest |

## The spiral

Hand the reader its own pointer and it rebuilds an exact copy of itself from
the chain, verifies its own fingerprint, and renders a working reader inside
the reader. This was tested the day it was minted — screenshot-verified,
hash-pinned.

Why this matters: if this repository, the website, and everyone who ever
worked on the protocol disappear, a conforming reader can be re-extracted
from the ledger using nothing but the spec (two queries and a hash) — and
that recovered file then reads every other scroll. The medium carries its
own decoder.

## Independence

The reader hard-codes no gatekeeper:

- **Koios API mode** — any endpoint you choose (your own node's instance, a
  provider, `api.koios.rest` for CLI use; note the public instance currently
  restricts browser CORS).
- **Blockfrost mode** — your own free project key, sent only to Blockfrost.
- Works from a `file://` USB stick; nothing is uploaded anywhere.

## Reproduce it

```bash
cd koios-viewer
python3 -m lsview reconstruct-chain \
  --txin 9a564165ebdc4e0c4a2e1163b5cf9355604ecb8e163b425d834570e5b9007de2#0 \
  --out reader-from-chain.html
sha256sum reader-from-chain.html   # a824298d…9215
```

`reader.html` in this folder is the **frozen minted copy** — byte-identical
to the chain. The live site copy at `/reader.html` starts identical; if it
ever evolves, a new version should be minted as a new scroll (the chain copy
is the canonical v1, forever).

Build your own: [docs/BUILD_A_READER.md](../../docs/BUILD_A_READER.md).
