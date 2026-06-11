# The Eternal Scroll — first LS-CHAIN v2 scroll on mainnet

A self-contained HTML tutorial on reading and writing Ledger Scrolls,
stored on Cardano mainnet **as a Ledger Scroll** — the technology's own
explainer, preserved by the technology. Minted June 11, 2026 as the first
scroll in the LS-CHAIN v2 format (`registry/spec/manifest-chain-v2.md`).

| Field | Value |
|---|---|
| Pointer | `manifest-chain-v2` · `ef8dce1c6359c7ae6cc44f04d60b32e6bc26987ebf30a78259c65b2063ba3b18#0` |
| Lock address | `addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn` (always-fail) |
| Pages | 2 bare metadata txs, label 22025 |
| Content | `text/html`, gzip, 18,182 → 7,411 bytes |
| SHA-256 (decoded) | `65824f624bc58140a33123d3e2383ea408135e5db666fcb8a0759b2846447dd2` |
| Total cost | ~0.86 ADA fees + ~1.59 ADA locked with the manifest |

Reproduce it from the chain:

```bash
cd koios-viewer
python3 -m lsview reconstruct-chain \
  --txin ef8dce1c6359c7ae6cc44f04d60b32e6bc26987ebf30a78259c65b2063ba3b18#0 \
  --out scroll.html
sha256sum scroll.html   # 65824f62…47dd2
```

`eternal-scroll-tutorial.html` is the exact source that was minted;
`receipts.json` holds every transaction hash and parameter. The scroll is
viewable in the web app as **The Eternal Scroll**.
