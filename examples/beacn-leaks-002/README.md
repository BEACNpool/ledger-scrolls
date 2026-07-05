# BEACN Leaks — Issue 002: The Year the Archives Blinked

A sourced, fact-labeled chronicle of 2025–26 public-record erasure — the
government page and dataset removals, the withdrawn intelligence reports,
and the year major newspapers began blocking the Wayback Machine — stored
where none of it can happen to the document itself.

| Field | Value |
|---|---|
| Scroll pointer | `manifest-chain-v2` · `1b465d3f9368cf6e1a36ae536631ffed9ca12b35c3bd2843bc423398140174fc#0` |
| Content | `text/html`, gzip, 7,500 → 3,524 bytes, 1 page |
| SHA-256 (decoded) | `16612dfb6cef652e23014fecba3108996edb76c1d62d37562a2d799cb7165a55` |
| Channel NFT | 🟢 **MINTED** — `BEACN_LEAKS_0002` · tx `278046dc1f31a4dcccbdcfe91e03b3ae7154b33a2d5cd5cb9d7207cc45eeb768` (block 13,639,610, 2026-07-05) |

```bash
cd koios-viewer
python3 -m lsview reconstruct-chain \
  --txin 1b465d3f9368cf6e1a36ae536631ffed9ca12b35c3bd2843bc423398140174fc#0 \
  --out issue002.html
sha256sum issue002.html   # 16612dfb…5a55
```

## Completing the byline (channel key holder only)

The scroll is live; the unforgeable byline needs one mint under the BEACN
Leaks policy (`5f569d01614c42003131c40b46d0b58c351a718907645c96d6da5415`),
asset `BEACN_LEAKS_0002`, CIP-25 metadata:

```json
{ "721": { "5f569d01614c42003131c40b46d0b58c351a718907645c96d6da5415": {
  "BEACN_LEAKS_0002": {
    "name": "BEACN Leaks — Issue 002: The Year the Archives Blinked",
    "mediaType": "text/html",
    "publisher": "BEACN",
    "channel": "BEACN Leaks",
    "issue": 2,
    "pointer": { "kind": "manifest-chain-v2",
      "txHash": "1b465d3f9368cf6e1a36ae536631ffed9ca12b35c3bd2843bc423398140174fc",
      "txIx": 0 },
    "sha256": "16612dfb6cef652e23014fecba3108996edb76c1d62d37562a2d799cb7165a55",
    "description": ["2025-26 public-record erasure, chronicled with sources,",
                    "stored where removal is not an operation that exists."]
  }}}}
```

Mint it with the same signature-policy flow used for issues 000/001.
