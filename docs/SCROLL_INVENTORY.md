# Scroll Inventory — everything live on mainnet

Every scroll below is **live on Cardano mainnet** and permanently verifiable.
This is the canonical record of pointers, hashes, and receipts. Each scroll
also has a folder in [`examples/`](../examples/) with its exact source and
`receipts.json`.

---

## 🔔 LEDGER_SCROLLS — Release 000: The Library Opens

The project's release announcement, first issue of the **LEDGER_SCROLLS**
publisher channel (`8d6d38b3967028a15fc0e401b53c73a75ac654affc3f817c750c8b80`,
asset `LEDGER_SCROLLS_0000`). Pointer
`d8875be1a21dffca56252ddd22e701ae088645518e48c49f873449b87802e96d#0` ·
`text/html` · gzip · sha256
`19ba8fccd3bd7e5ac997c3a4a0ff768a2699959bfd3bcf9db2ae073c09fe5013` · 🟢 LIVE.
Receipts: [`examples/ledger-scrolls-000/`](../examples/ledger-scrolls-000/).

---

## 0000) 📐 The Spec — the protocol, stored in its own format

The `manifest-chain-v2` wire spec minted as a Chain Scroll. Pointer
`e4845deed98471b29b35689cfdb76f18add189c8d8f5c61b2ef32ea7ce6d5cf9#0` ·
`text/markdown` · gzip · sha256
`4793c38349cca60d552c52d68dfd950f3dd945db55c8a6a87f05ca6d98e3b242` · 🟢 LIVE.
Receipts: [`examples/the-spec/`](../examples/the-spec/).

---

## 00X) 🗄️ BEACN Leaks — Issue 002: The Year the Archives Blinked

Sourced chronicle of 2025–26 public-record erasure. Pointer
`1b465d3f9368cf6e1a36ae536631ffed9ca12b35c3bd2843bc423398140174fc#0` ·
`text/html` · gzip · sha256
`16612dfb6cef652e23014fecba3108996edb76c1d62d37562a2d799cb7165a55` ·
🟢 LIVE (channel NFT `BEACN_LEAKS_0002` pending — see
[`examples/beacn-leaks-002/`](../examples/beacn-leaks-002/)).

---

## 000) 👓 The Reader — the reader, stored as a scroll

The minimal Ledger Scrolls reader (`reader.html`) minted **as a Ledger
Scroll**: hand it its own pointer and it rebuilds itself from the chain and
renders a working copy of itself. The library permanently contains its own
pair of glasses. See [`examples/the-reader/`](../examples/the-reader/).

| Field | Value |
|-------|-------|
| **ID** | `the-reader` |
| **Type** | `manifest-chain-v2` (Chain Scroll) |
| **Manifest TxIn** | `9a564165ebdc4e0c4a2e1163b5cf9355604ecb8e163b425d834570e5b9007de2#0` |
| **Pages** | 1 (metadata label 22025) |
| **Content-Type** | `text/html` |
| **Codec** | `gzip` |
| **SHA-256 (Original)** | `a824298dc5ced0aad1954c7d8d40bb6dda09debf402f062ab402dcebbb6a9215` |
| **Status** | 🟢 LIVE — manifest UTxO must remain UNSPENT (always-fail script) |

---

## 00) 🗽 BEACN Leaks — Issue 000: The Manifesto

A freedom-of-speech manifesto: Ledger Scrolls as independent, immutable,
unforgeable media. Founding issue of the first **publisher channel**
([`registry/spec/publisher-channel-v1.md`](../registry/spec/publisher-channel-v1.md)) —
a minting policy used as a byline that only the publisher's key can ever write under.

| Field | Value |
|-------|-------|
| **ID** | `beacn-leaks-000` |
| **Type** | `manifest-chain-v2` (Chain Scroll) |
| **Manifest TxIn** | `f3ee01c1e742c27c205867de4cfa8836e4ab541b9da0d5652aa4d269c73255c7#0` |
| **Channel Policy** | `5f569d01614c42003131c40b46d0b58c351a718907645c96d6da5415` |
| **Channel Asset** | `BEACN_LEAKS_0000` |
| **Content-Type** | `text/html` · gzip · 1 page |
| **SHA-256 (Original)** | `025a81aeffe8aed98868b89b8f04a1f137f698362cfebafd2f8b5a56312d49b2` |
| **Status** | 🟢 LIVE |

**Issue 001 — The Undeniable** (human rights & permanent memory):
`BEACN_LEAKS_0001`, manifest `08c707b3ab7880f983be7f78bd56c4de38461d514c6597d95cd5da1abc307565#0`,
sha256 `5917a884f449fd1c76fc0241791468a37b2b54883c0b8b98022a9f372f7d68b9` — see
[`examples/beacn-leaks-001/`](../examples/beacn-leaks-001/).

---

## 0) 📜 The Eternal Scroll — first Chain Scroll scroll

A self-contained HTML tutorial on reading and writing Ledger Scrolls — the
technology's own explainer, preserved by the technology. First scroll in the
**Chain Scroll** format: bare metadata page transactions (no NFTs, ~6×
cheaper than CIP-25 pages) anchored by a Class-A manifest datum. See
[`registry/spec/manifest-chain-v2.md`](../registry/spec/manifest-chain-v2.md) and
[`examples/eternal-scroll-tutorial/`](../examples/eternal-scroll-tutorial/).

| Field | Value |
|-------|-------|
| **ID** | `eternal-scroll` |
| **Type** | `manifest-chain-v2` (Chain Scroll) |
| **Manifest TxIn** | `ef8dce1c6359c7ae6cc44f04d60b32e6bc26987ebf30a78259c65b2063ba3b18#0` |
| **Pages** | 2 (metadata label 22025) |
| **Content-Type** | `text/html` |
| **Codec** | `gzip` |
| **SHA-256 (Original)** | `65824f624bc58140a33123d3e2383ea408135e5db666fcb8a0759b2846447dd2` |
| **Status** | 🟢 LIVE — manifest UTxO must remain UNSPENT (it cannot be spent: always-fail script) |

---

## 1) ✅ Hosky PNG — Ledger Scrolls Standard (lean & local-first)

A complete PNG stored **directly in an inline datum** at a **locked UTxO**.
A viewer can reconstruct the exact image bytes from chain data.

| Field | Value |
|-------|-------|
| **ID** | `hosky-png` |
| **Type** | `utxo_datum_bytes_v1` (Standard Scroll) |
| **Lock Address** | `addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn` |
| **Locked UTxO (txin)** | `728660515c6d9842d9f0ffd273f2b487a4070fd9f4bd5455a42e3a56880389be#0` |
| **Content-Type** | `image/png` |
| **Codec** | `none` |
| **SHA-256** | `798e3296d45bb42e7444dbf64e1eb16b02c86a233310407e7d8baf97277f642f` |
| **Status** | 🟢 LIVE — UTxO must remain UNSPENT |

> **Why this is the "Standard":** the minimal possible on-chain data product:
> **one UTxO, one datum, one fetch, one file.** Always-fail script address.
> 512×512 RGBA PNG.

---

## 2) 🔮 The Architect's Scroll — Message from Claude

A personal message from Claude, the AI who helped build Ledger Scrolls v2.0 —
thoughts on knowledge preservation and a note to future readers, minted
permanently on-chain as a Standard Scroll.

| Field | Value |
|-------|-------|
| **ID** | `architects-scroll` |
| **Type** | `utxo_datum_bytes_v1` (Standard Scroll) |
| **Lock Address** | `addr1w9fdc02rkmfyvh5kzzwwwk4kr2l9a8qa3g7feehl3ga022qz2249g` |
| **Locked UTxO (txin)** | `076d6800d8ccafbaa31c32a6e23eecfc84f7d1e35c31a9128ec53736d5395747#0` |
| **Content-Type** | `text/plain; charset=utf-8` |
| **Codec** | `none` |
| **SHA-256** | `531a1eba80b297f8822b1505d480bb1c7f1bad2878ab29d8be01ba0e1fc67e12` |
| **Locked Value** | `15 ADA` (forever) |
| **Status** | 🟢 LIVE — UTxO must remain UNSPENT |

> Minted January 29, 2026.

---

## 3) 🧾 Cardano Constitution (Epoch 608) — CURRENT

The ratified, currently active Cardano Constitution, preserved on-chain as a
Legacy Scroll.

| Field | Value |
|-------|-------|
| **ID** | `constitution-e608` |
| **Type** | `cip25_pages_v1` (original NFT pages) |
| **Policy ID** | `ef91a425ef57d92db614085ef03718407fb293cb4b770bc6e03f9750` |
| **Manifest Asset** | `CONSTITUTION_E608_MANIFEST` |
| **Pages** | 11 |
| **Content-Type** | `text/plain; charset=utf-8` |
| **Codec** | `gzip` |
| **SHA-256 (Original)** | `98a29aec8664b62912c1c0355ebae1401b7c0e53d632e8f05479e7821935abf1` |
| **SHA-256 (Gzip)** | `4565368ca35d8c6bb08bff712c1b22c0afe300c19292d5aa09c812ed415a4e93` |
| **Governance** | Ratified Epoch 608 · Enacted Epoch 609 · Voting: Epochs 603–607 |
| **Status** | 🟢 LIVE — CURRENT CONSTITUTION |

---

## 4) 🧾 Cardano Constitution (Epoch 541) — HISTORICAL

The first ratified Cardano Constitution, preserved as a permanent historical
record.

| Field | Value |
|-------|-------|
| **ID** | `constitution-e541` |
| **Type** | `cip25_pages_v1` (original NFT pages) |
| **Policy ID** | `d7559bbfa87f53674570fd01f564687c2954503b510ead009148a31d` |
| **Manifest Asset** | `CONSTITUTION_E541_MANIFEST` |
| **Pages** | 7 |
| **Content-Type** | `text/plain; charset=utf-8` |
| **Codec** | `gzip` |
| **SHA-256 (Original)** | `1939c1627e49b5267114cbdb195d4ac417e545544ba6dcb47e03c679439e9566` |
| **SHA-256 (Gzip)** | `975d1c6bb1c8bf4982c58e41c9b137ecd4272e34095a5ec9b37bdde5ca6f268a` |
| **Governance** | Ratified Epoch 541 · Enacted Epoch 542 · Voting: Epochs 536–540 |
| **Status** | 🟢 LIVE — HISTORICAL (Baseline) |

---

## 5) 🧾 Bible (HTML, gzip compressed) — large-document proof

| Field | Value |
|-------|-------|
| **ID** | `bible` |
| **Type** | `cip25_pages_v1` (original NFT pages) |
| **Policy ID** | `2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0` |
| **Manifest TX Hash** | `cfda418ddc84888ac39116ffba691a4f90b3232f4c2633cd56f102cfebda0ee4` |
| **Manifest Slot** | `175750638` |
| **Pages** | 237 |
| **Content-Type** | `text/html` |
| **Codec** | `gzip` |
| **Segments per Page** | 32 |
| **Status** | 🟢 LIVE — DO NOT MOVE NFTs |

> Largest demo scroll. Reconstruction: `concat_pages` + `gunzip`. CIP-25
> metadata label 721.

---

## 6) 🧾 Bitcoin Whitepaper — small doc / legacy pages

| Field | Value |
|-------|-------|
| **ID** | `bitcoin-whitepaper` |
| **Type** | `cip25_pages_v1` (original NFT pages) |
| **Policy ID** | `8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1` |
| **Manifest TX Hash** | `2575347068f77b21cfe8d9c23d9082a68bfe4ef7ba7a96608af90515acbe228f` |
| **Manifest Slot** | `176360887` |
| **Pages** | 3 |
| **Content-Type** | `text/plain` (auto-detected as HTML) |
| **Codec** | `auto` (gzip magic bytes detected) |
| **Status** | 🟢 LIVE — DO NOT MOVE NFTs |

---

## Quick Reference Tables

### Policy IDs

| Scroll | Policy ID | Purpose | Minting Status |
|--------|-----------|---------|----------------|
| BEACN Leaks (channel) | `5f569d01614c42003131c40b46d0b58c351a718907645c96d6da5415` | Publisher channel — unforgeable byline | Open (sig-only; key holder publishes) |
| LS_REGISTRY | `895cbbe0e284b60660ed681e389329483d5ca94677cbb583f3124062` | Registry NFT (DNS for scrolls) | Active (spend-and-recreate) |
| Bible | `2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0` | 237-page HTML Bible (Legacy) | Policy likely locked |
| Bitcoin Whitepaper | `8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1` | 3-page BTC whitepaper (Legacy) | Policy likely locked |
| Constitution E608 | `ef91a425ef57d92db614085ef03718407fb293cb4b770bc6e03f9750` | Current Constitution (11 pages) | Time-locked policy |
| Constitution E541 | `d7559bbfa87f53674570fd01f564687c2954503b510ead009148a31d` | Historical Constitution (7 pages) | Time-locked policy |
| Hosky PNG | N/A — Standard Scroll (locked UTxO, no minting policy) | Single inline datum at script address | Immutable UTxO |
| Architect's Scroll | N/A — Standard Scroll (locked UTxO, no minting policy) | Single inline datum at script address | Immutable UTxO |

### Key Addresses

| Purpose | Address |
|---------|---------|
| **Registry Address** | `addr1q9x84f458uyf3k23sr7qfalg3mw2hl0nvv4navps2r7vq69esnxrheg9tfpr8sdyfzpr8jch5p538xjynz78lql9wm6qpl6qxy` |
| **Hosky PNG Lock Address** (always-fail script) | `addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn` |
| **Architect's Scroll Lock Address** (always-fail script) | `addr1w9fdc02rkmfyvh5kzzwwwk4kr2l9a8qa3g7feehl3ga022qz2249g` |

### SHA-256 Verification Hashes

| Scroll | SHA-256 (Original) | SHA-256 (Gzip) | Verify With |
|--------|--------------------|----------------|-------------|
| Hosky PNG | `798e329...7f642f` | N/A | `sha256sum hosky.png` |
| Architect's Scroll | `531a1eb...c67e12` | N/A | `sha256sum architects_scroll.txt` |
| Constitution E608 | `98a29ae...35abf1` | `4565368...4e93` | `sha256sum Cardano_Constitution_Epoch_608.txt` |
| Constitution E541 | `1939c16...9e9566` | `975d1c6...f268a` | `sha256sum Cardano_Constitution_Epoch_541.txt` |
| Bible | `b226867...c5dc5` | `228ff03...9af60` | `sha256sum bible.html` (matches on-chain `BIBLE_MANIFEST` `sha_html`/`sha_gz`) |
| Bitcoin Whitepaper | `6693c86...9253a` | N/A (codec auto) | `sha256sum btc_whitepaper.html` (recorded 2026-06-11; manifest declares no hash) |

---

## The Registry (the "DNS" for Scrolls)

The Registry is a single on-chain directory that tells viewers what exists:
a **registry NFT** (`LS_REGISTRY`) locked at a known address, whose UTxO
carries an inline datum of gzipped JSON listing scrolls and their pointers.
Spend-and-recreate to update. It is **forkable by design** — anyone can run
their own registry head.

### Current Live Registry Pointer

| Field | Value |
|-------|-------|
| **Policy ID** | `895cbbe0e284b60660ed681e389329483d5ca94677cbb583f3124062` |
| **Asset Name (hex)** | `4c535f5245474953545259` (ASCII: `LS_REGISTRY`) |
| **Registry Address** | `addr1q9x84f458uyf3k23sr7qfalg3mw2hl0nvv4navps2r7vq69esnxrheg9tfpr8sdyfzpr8jch5p538xjynz78lql9wm6qpl6qxy` |

Registry schema, pointer kinds, and JSON Schemas: [`registry/`](../registry/).

---

## Prove It Yourself: a Standard Scroll in four commands (Hosky example)

### 1) Query the Lock Address UTxO Set

```bash
cardano-cli query utxo --mainnet \
  --address "addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn" \
  --out-file locked_utxo_live.json
```

### 2) Confirm the Exact Txin Exists and Has Inline Datum

```bash
LOCKED_TXIN="728660515c6d9842d9f0ffd273f2b487a4070fd9f4bd5455a42e3a56880389be#0"
jq -r --arg k "$LOCKED_TXIN" '
  if has($k) then
    "FOUND ON-CHAIN: \($k)\ninlineDatum? " + ((.[ $k ] | has("inlineDatum"))|tostring)
  else
    "MISSING ON-CHAIN: \($k)"
  end
' locked_utxo_live.json
```

### 3) Extract Datum Bytes Into a Real PNG

```bash
jq -r --arg k "$LOCKED_TXIN" '.[$k].inlineDatum' locked_utxo_live.json > datum.json
jq -r '.bytes' datum.json | tr -d '\n' | xxd -r -p > onchain.png
```

### 4) Verify PNG Sanity + Hash Immutability

```bash
file onchain.png
sha256sum onchain.png
sha256sum hosky.png onchain.png
# If hashes match, the image is byte-for-byte immutable on-chain.
```
