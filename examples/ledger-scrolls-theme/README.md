# Ledger Scrolls — The Theme · the first music on the shelf

The project's own theme: a 1:47 two-drop electronic piece, written by the
librarian himself, extracted from its original video and mastered for the
chain from the lossless mix. The first **music scroll** — proof that sound
survives in stone.

| Field | Value |
|---|---|
| Pointer | `b6d9e70a751398fae0dc86580ce256802e6aea9ae0978b8c92b88b50a536962b#0` |
| Content type | `audio/ogg` (Opus, 32 kbps VBR stereo) |
| Codec | none (Opus is already compressed — no gzip layer) |
| SHA-256 | `8bd5c906744197d94a7252f2607f671037b426eea18a05fa39330a85145b06e7` |
| Size | 473,561 bytes — 39 page txs |
| Duration | 107 s · 44.1 kHz stereo source |
| Lock address | `addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn` |
| Minted | 2026-07-03 |

Mastering chain, for the record: original 16-bit/44.1 kHz FLAC → two-pass
linear loudness normalization (−14 LUFS integrated, −1.5 dBTP true peak —
the source master peaked at +1.75 dBTP) → single Opus encode,
`libopus -b:a 32k -ac 2 -application audio`, Ogg pages at 5 s
(`-page_duration 5000000`) to minimize container overhead. Encoded **once,
from lossless** — never transcode an MP3.

Listen in [The Library](https://beacnpool.github.io/ledger-scrolls/#s=ledger-scrolls-theme),
or verify by hand:

```bash
cd koios-viewer
python3 -m lsview reconstruct-chain \
  --txin b6d9e70a751398fae0dc86580ce256802e6aea9ae0978b8c92b88b50a536962b#0 \
  --out check.ogg
sha256sum check.ogg   # 8bd5c906…06e7
```

`ledger-scrolls-theme.ogg` here is the exact minted file (byte-exact — do
not re-encode); `receipts.json` lists all 39 page transactions.
