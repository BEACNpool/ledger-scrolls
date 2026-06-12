# BEACN Leaks — Issue 000: The Manifesto

A freedom-of-speech manifesto promoting Ledger Scrolls as independent,
immutable media for the suppressed — minted on Cardano mainnet as an
LS-CHAIN v2 scroll, and the founding issue of the first **publisher
channel** (`registry/spec/publisher-channel-v1.md`): an unforgeable byline
that only one key on Earth can publish under.

| Field | Value |
|---|---|
| Scroll pointer | `manifest-chain-v2` · `f3ee01c1e742c27c205867de4cfa8836e4ab541b9da0d5652aa4d269c73255c7#0` |
| Channel policy ID | `5f569d01614c42003131c40b46d0b58c351a718907645c96d6da5415` |
| Channel asset | `BEACN_LEAKS_0000` (mint tx `fb8aae62…3dcb`) |
| Content | `text/html`, gzip, 10,304 → 4,632 bytes, 1 page |
| SHA-256 (decoded) | `025a81aeffe8aed98868b89b8f04a1f137f698362cfebafd2f8b5a56312d49b2` |
| Total cost | ~0.76 ADA fees + ~1.44 ADA locked (manifest) + ~1.5 ADA carrying the channel NFT |

The manifesto declares its own channel: the policy ID printed inside the
document is the policy that signs its publication record. Follow the
channel (free, keyless):

```bash
curl -X POST https://api.koios.rest/api/v1/policy_asset_list \
  -H 'Content-Type: application/json' \
  -d '{"_asset_policy":"5f569d01614c42003131c40b46d0b58c351a718907645c96d6da5415"}'
```

Reconstruct and verify the issue:

```bash
cd koios-viewer
python3 -m lsview reconstruct-chain \
  --txin f3ee01c1e742c27c205867de4cfa8836e4ab541b9da0d5652aa4d269c73255c7#0 \
  --out leak.html
sha256sum leak.html   # 025a81ae…49b2
```

`beacn-leaks-000-manifesto.html` is the exact minted source;
`receipts.json` holds every transaction hash. Viewable in the web app as
**BEACN Leaks — Issue 000**.
