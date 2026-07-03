# LEDGER_SCROLLS — Release 000: The Library Opens

The project's release announcement, published the only honest way: as a
scroll, under the project's own **publisher channel** — a policy ID that is
the project's permanent, unforgeable release feed.

| Field | Value |
|---|---|
| Scroll pointer | `manifest-chain-v2` · `d8875be1a21dffca56252ddd22e701ae088645518e48c49f873449b87802e96d#0` |
| Channel policy | `8d6d38b3967028a15fc0e401b53c73a75ac654affc3f817c750c8b80` |
| Channel asset | `LEDGER_SCROLLS_0000` (mint tx `c4b0548c…25ae`) |
| Content | `text/html`, gzip, 5,055 → 2,593 bytes, 1 page |
| SHA-256 (decoded) | `19ba8fccd3bd7e5ac997c3a4a0ff768a2699959bfd3bcf9db2ae073c09fe5013` |

Follow the release feed (free, keyless):

```bash
curl -X POST https://api.koios.rest/api/v1/policy_asset_list \
  -H 'Content-Type: application/json' \
  -d '{"_asset_policy":"8d6d38b3967028a15fc0e401b53c73a75ac654affc3f817c750c8b80"}'
```

Reconstruct and verify the announcement:

```bash
cd koios-viewer
python3 -m lsview reconstruct-chain \
  --txin d8875be1a21dffca56252ddd22e701ae088645518e48c49f873449b87802e96d#0 \
  --out release000.html
sha256sum release000.html   # 19ba8fcc…5013
```

Two channels now exist, deliberately separate: **BEACN Leaks**
(`5f569d01…5415`) is the publisher's personal voice for suppressed truths;
**LEDGER_SCROLLS** (`8d6d38b3…8b80`) is the project's release feed. Each is
one key; neither can be faked, seized, or reassigned.
