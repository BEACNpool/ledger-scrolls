# The Protocol on One Page — the first PDF scroll

The whole idea of Ledger Scrolls on a single printed page — what it is, how
it works, the formats, the verify-it-yourself queries, the five rules — as
a **PDF, stored in the system it describes**. Print it, hand it out, pin it
to a corkboard; the original can never be lost, and any copy can be checked
against the chain to the byte.

| Field | Value |
|---|---|
| Pointer | `5fdadf5158f78afb70a74693b595889406652f3eeddb9a76f44e6f0d481a797e#0` |
| Content type | `application/pdf` |
| Codec | gzip |
| SHA-256 (file) | `89de5c64b0d2a05b0199875399a47506a75554d0d8613b0d88889667d2122adb` |
| Size | 58,946 bytes (53,771 gzipped) — 5 page txs |
| Lock address | `addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn` |
| Minted | 2026-07-03 |

Page transactions, in order:

```
fc7396731bb118c29d94ca5892a12cae41ad427014da8ddd3f3391d743e052bf
b6b146ede497268a5809a8e3c4a4726610ad83561bf5073459fb06114a7f8bae
3f957020965ebd8b503663caddb3f225bcf30929554f596d0aaab40f7eec4cb6
e2ad7f6e3495779cd4febdc7bcc535ac2cd05b321cdf9b346c966d2eec5de3c2
252465ef6b06ffd21a6eceb0d808e7ef7e647f4d4391da8868140036c3072b45
```

Read it in [The Library](https://beacnpool.github.io/ledger-scrolls/#s=protocol-one-pager),
or verify by hand:

```bash
cd koios-viewer
python3 -m lsview reconstruct-chain \
  --txin 5fdadf5158f78afb70a74693b595889406652f3eeddb9a76f44e6f0d481a797e#0 \
  --out check.pdf
sha256sum check.pdf   # 89de5c64…2adb
```

Files here: `ledger-scrolls-one-pager.pdf` is the exact minted document
(**do not regenerate — byte-exact**); `one-pager-source.html` is the print
source it was rendered from (chromium `--print-to-pdf`, then ghostscript
`/ebook`); `receipts.json` holds the full mint receipts.
