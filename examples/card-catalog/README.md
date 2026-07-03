# The Card Catalog — the library's index, as a dataset

The first **dataset scroll** on the shelf: every scroll in the BEACN Public
Library — name, title, media type, storage form, pointer, SHA-256, size,
page count, mint date — as one plain CSV. The library's card catalog,
stored inside the library it describes.

Because it's on-chain, the catalog can be **cited by hash**: anyone can
prove their copy is the copy, and the state of the library on 2026-07-03
is now a permanent, timestamped fact.

| Field | Value |
|---|---|
| Pointer | `358060520666d99793a9d68ccc85c68207d8c5032ea33d3a550d1461a6e8ee7e#0` |
| Content type | `text/csv` |
| Codec | gzip |
| SHA-256 (file) | `bd11925a30f925f065345717f5c504992564c24899695a9c1720a83fb7baf9fb` |
| Size | 5,272 bytes (2,948 gzipped) — 1 page tx |
| Page tx | `3f1f87ef1d7c27acb033c2b1ea16b4ad5108d413cd51a6af463a34bc61e7a611` |
| Lock address | `addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn` |
| Minted | 2026-07-03 |

A catalog can never contain itself: this snapshot lists the 17 scrolls that
were live the moment before it was minted. Later snapshots supersede it in
usefulness — never in truth.

Read it in [The Library](https://beacnpool.github.io/ledger-scrolls/#s=card-catalog),
or verify by hand:

```bash
cd koios-viewer
python3 -m lsview reconstruct-chain \
  --txin 358060520666d99793a9d68ccc85c68207d8c5032ea33d3a550d1461a6e8ee7e#0 \
  --out check.csv
sha256sum check.csv   # bd11925a…f9fb
```

`card-catalog.csv` in this folder is the exact minted file; `receipts.json`
holds the full mint receipts.
