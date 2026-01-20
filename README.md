# Ledger Scrolls 📜
**“A library that cannot burn.”**

Ledger Scrolls is an open-source **standard + viewer** for publishing and reading **permissionless, immutable data** on the Cardano blockchain.

The design goal is simple:
- **No chain indexing**
- **No centralized gatekeepers**
- **No “download the whole chain history” requirement**
- **Local-first** (your node + your socket) – prioritized in future updates
- **Forever-readable** as long as the pointer remains valid

Ledger Scrolls supports two storage styles:
1) ✅ **Ledger Scrolls Standard (Lean): Locked UTxO Datum Bytes**
   Best for small files (icons/images/manifests/configs) that fit inside one on-chain inline datum. Supports optional gzip compression for slightly larger files.
   **Default demo: Hosky PNG** (no Blockfrost required in local mode)
2) 🧾 **Legacy Scrolls (Large): Pages + Manifest NFTs (CIP-25 style)**
   Best for large documents (Bible / Whitepaper). Consider migrating to standard + IPFS for new projects.
   **Optional legacy fallback via Blockfrost** for convenience.
---
## What Exists Today (Default Demo Scrolls)
### 1) ✅ Hosky PNG (Ledger Scrolls Standard — lean & local-first)
This demo stores a complete PNG **directly in an inline datum** at a **locked UTxO**.
A viewer can reconstruct the exact image bytes from chain data.

**On-chain pointer**
- Lock address: `addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn`
- Locked UTxO (txin): `728660515c6d9842d9f0ffd273f2b487a4070fd9f4bd5455a42e3a56880389be#0`
- Datum format: **inlineDatum.bytes** = hex of the PNG file
- Content-Type: `image/png`

**Immutability proof (hash)**
- `sha256(hosky.png) == sha256(onchain.png)` (reconstructed from datum bytes)

> Why this is the “Standard”: It’s the minimal possible on-chain data product: **one UTxO, one datum, one fetch, one file.**

### 2) Bible (HTML, gzip compressed) — proof of concept (large document)
- Policy: `2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0`
- Manifest tx hash: `cfda418ddc84888ac39116ffba691a4f90b3232f4c2633cd56f102cfebda0ee4`
- Manifest slot: `175750638`
- Reconstruction: `concat_pages + gunzip`
- Segments per page payload: `32`

### 3) Bitcoin Whitepaper — proof of concept (small doc / legacy pages)
- Policy: `8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1`
- Manifest tx hash: `2575347068f77b21cfe8d9c23d9082a68bfe4ef7ba7a96608af90515acbe228f`
- Manifest slot: `176360887`
---
## The Key Idea: “No Indexing” via Deterministic Pointers
Most “on-chain data” projects fail because reading requires one of:
- A centralized API (Blockfrost, Koios, etc.)
- A custom indexer scanning the chain
- A full-history database query plan

Ledger Scrolls avoids that using **pointers**.

### Pointer Model (first principles)
**A Scroll must be fetchable from a tiny number of deterministic lookups:**
- **Registry pointer (optional):** 1 address query (find the registry UTxO datum)
- **Scroll pointer:** points to either:
  - (Standard) a single locked UTxO holding bytes in an inline datum, or
  - (Legacy) a manifest tx hash + policy/asset names for pages

This transforms “find my document somewhere in the blockchain” into:
- **1 address query** (registry UTxO) OR direct user input
- **1 pointer resolution**
- **0 indexing**
---
## Ledger Scrolls Standard (LS-LOCK v1)
### Standard Storage: Locked UTxO + Inline Datum Bytes
A Standard Scroll stores the file bytes in:
- `inlineDatum.bytes` (hex) at a **locked UTxO**

A Standard Scroll entry needs only:
- a **txin** (`TXHASH#IX`) OR a (lock address + txin)
- a **content_type**
- a **sha256** (recommended)
- (optional) codec: none/gzip (apply gzip to bytes before hexing for datum)

### Why “Locked” Matters
If the UTxO stays **unspent**, the datum remains in the UTxO set and is fetchable forever without indexing.

> Ledger Scrolls ethos: **permanently locked, never spendable.**
To achieve “never spendable,” lock the UTxO at a script address that cannot validate (an “always-fail” script). Then the datum is effectively permanent.
---
## Legacy Scrolls (LS-PAGES v1)
### Pages + Manifest NFT Pattern (CIP-25 Style)
A “Scroll” can be stored as:
- **Page NFTs** (many): each page stores `payload` segments in metadata
- **Manifest NFT** (one): describes how to fetch pages, order them, decode them, and verify hashes

Typical page metadata fields:
- `spec`: format id (e.g., `gzip-pages-v1`)
- `role`: `page`
- `i`: page index (1-based)
- `n`: total pages
- `seg`: segment count
- `sha`: sha256 of the reconstructed page bytes
- `payload`: array of hex segments (variations: `seg`, `segments`)

Manifest describes:
- the codec (gzip/none)
- content_type (`text/html`, `text/plain`, etc.)
- page naming scheme or explicit page list
- full-file hashes (`sha_gz`, `sha_html`, etc.)

> Troubleshooting: If viewer fails on page fetch, check `manifest_metadata.json` for field variations (e.g., `payload` vs `seg`).
---
## The Registry (the “DNS” for Scrolls)
The Registry is a single on-chain directory that tells Ledger Scrolls what exists.

### Registry Implementation
- A **registry NFT** (e.g., `LS_REGISTRY`)
- Locked at a known **Registry address**
- The UTxO holding that NFT has an **inline datum** containing **gzipped JSON** (recommended for compression) listing scrolls and their pointers.

### Current Live Registry Pointer (Example)
- Registry policy id: `895cbbe0e284b60660ed681e389329483d5ca94677cbb583f3124062`
- Registry asset name hex: `4c535f5245474953545259` (ASCII `LS_REGISTRY`)
- Registry address: `addr1q9x84f458uyf3k23sr7qfalg3mw2hl0nvv4navps2r7vq69esnxrheg9tfpr8sdyfzpr8jch5p538xjynz78lql9wm6qpl6qxy`
---
## Registry Schema (v2 — Supports Both Standard + Legacy)
```json
{
  "spec": "ledger-scrolls-registry-v2",
  "version": 2,
  "updated": "2026-01-19T00:00:00Z",
  "scrolls": [
    {
      "id": "hosky-png",
      "title": "Hosky PNG (Ledger Scrolls Standard)",
      "type": "utxo_datum_bytes_v1",
      "lock_address": "addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn",
      "lock_txin": "728660515c6d9842d9f0ffd273f2b487a4070fd9f4bd5455a42e3a56880389be#0",
      "content_type": "image/png",
      "codec": "none",
      "sha256": "798e3296d45bb42e7444dbf64e1eb16b02c86a233310407e7d8baf97277f642f"
    },
    {
      "id": "bible",
      "title": "Bible (HTML, gzip compressed)",
      "type": "cip25_pages_v1",
      "policy_id": "2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0",
      "manifest_tx_hash": "cfda418ddc84888ac39116ffba691a4f90b3232f4c2633cd56f102cfebda0ee4",
      "manifest_slot": "175750638",
      "codec": "gzip",
      "content_type": "text/html",
      "segments_per_page": 32
    },
    {
      "id": "bitcoin-whitepaper",
      "title": "Bitcoin Whitepaper",
      "type": "cip25_pages_v1",
      "policy_id": "8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1",
      "manifest_tx_hash": "2575347068f77b21cfe8d9c23d9082a68bfe4ef7ba7a96608af90515acbe228f",
      "manifest_slot": "176360887",
      "codec": "none",
      "content_type": "text/plain"
    }
  ]
}
```
---
## How to Prove a Standard Scroll Is On-Chain (Hosky Example)
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
```
If hashes match, the image is **byte-for-byte immutable on-chain**.
---
## Running the Viewer
The viewer is a cross-platform Python GUI app (Windows/Mac/Linux) with progress bars, safe file saving, and support for both standard and legacy modes.

### Installation
```bash
git clone <repo-url>
cd ledger-scrolls-viewer
pip install tkinter requests hashlib gzip
python hosky.py  # or your app filename
```

### Features
- GUI with demo buttons for Hosky, Bible, BTC Whitepaper
- Blockfrost integration for fetches (enter API key when prompted)
- Files saved to `~/Downloads/LedgerScrolls/` to avoid permission issues
- Progress explanations during reconstruction
- Known bugs: Legacy page fetching may need manifest tweaks for asset name variations; contribute fixes on GitHub!

### Local-Node Mode (Planned v2)
* Uses your **local cardano-node socket**
* Queries via `cardano-cli` for standard scrolls (no Blockfrost)
```bash
export CARDANO_NODE_SOCKET_PATH=/opt/cardano/cnode/sockets/node.socket
python hosky.py
```

### Blockfrost Mode (Current Default for Legacy + Convenience)
```bash
python hosky.py
# Enter Blockfrost key in GUI for legacy demos
```

> Long-term direction: Full local-node for everything (standard + legacy metadata via CLI queries). Blockfrost as optional fallback.
---
## Developer Workflow: Create Your Own Library
You can:
* Run your own registry (recommended), OR
* Submit a PR to a public registry

To publish a Standard Scroll:
1. Create a permanently locked UTxO containing `inlineDatum.bytes` = your (gzipped) file bytes
2. Add a registry entry pointing to `lock_txin`, with `content_type` + `sha256`

To publish a Legacy Scroll (for large files; prefer standard + IPFS hybrids):
1. Split file into pages + segments
2. Mint pages + manifest NFT(s)
3. Add a registry entry with `policy_id + manifest_tx_hash + codec + hashes`

To extend the viewer app:
- Add local-node support (e.g., subprocess calls to cardano-cli)
- Improve legacy parser for field variations (contribute via PR)
---
## Philosophy
* **Open standard**
* **Permissionless**
* **Non-custodial**
* **Non-indexed**
* **Local-first**
* **Permanently locked**

Maintained with ❤️ by [@BEACNpool](https://x.com/BEACNpool)
