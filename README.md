# Ledger Scrolls 📜
**“A library that cannot burn.”**

Publish + read *permissionless, immutable data* on Cardano—without Blockfrost (optional), without chain indexing, and without asking users to download the entire chain history.

Ledger Scrolls is an open-source **format + viewer** for storing documents on-chain as a set of NFTs (pages) plus a single “manifest” NFT that describes how to reconstruct the original file. A **Registry** UTxO (with an inline datum) acts like a “DNS pointer” that tells the viewer what Scrolls exist and how to find their manifests.

This README explains:
- How on-chain data is structured (pages + manifest)
- How the Registry works (zero indexing / single UTxO lookup)
- How a dev creates their own Scroll library and points Ledger Scrolls to it
- How the viewer uses a local node socket (no centralized APIs by default)
- How dev choices affect the viewer (naming, segmentation, hashes, etc.)
- How to build an option-based interface (not “CLI-only”)

## What exists today (default demo Scrolls)

Ledger Scrolls ships with two default Scrolls as proof-of-concept:

### 1) Bible (HTML, gzip compressed)
- Policy: `2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0`
- Manifest tx hash: `cfda418ddc84888ac39116ffba691a4f90b3232f4c2633cd56f102cfebda0ee4`
- Manifest slot: `175750638`
- Reconstruction: `concat_pages + gunzip`
- Segments per page payload: `32`

### 2) Bitcoin Whitepaper (small set of pages)
- Policy: `8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1`
- Manifest tx hash: `2575347068f77b21cfe8d9c23d9082a68bfe4ef7ba7a96608af90515acbe228f`
- Manifest slot: `176360887`

## The key idea: “No indexing” via deterministic pointers

Most “on-chain data” projects fail because reading requires one of:
- A centralized API (Blockfrost, Koios, etc.)
- A custom indexer scanning the chain
- A full-history node or local chain DB queries

Ledger Scrolls avoids that by using **pointers**:
1. **Registry pointer**: a single UTxO at a known address containing an NFT + inline datum
2. **Manifest pointer**: metadata that tells you exactly which policy/asset(s) are the manifest (and optionally where it lives)
3. **Page pointers**: manifest tells you the exact asset names of every page NFT needed

This transforms “find my document somewhere in the blockchain” into:
- **1 address query** (registry UTxO)
- **1 tx query** (manifest via tx hash or utxo)
- **N page fetches** (direct asset metadata lookups)

## On-chain structure (how the data is stored)

A “Scroll” is stored as:

### A) Page NFTs (many)
Each page NFT contains a chunk of data (or references to chunk segments) inside its metadata.

Typical page metadata includes:
- `spec`: identifies the format (e.g., `gzip-pages-v1`)
- `role`: `page`
- `i`: page index (1-based)
- `n`: total pages
- `seg`: segment count (how many chunks in `payload`)
- `sha`: sha256 of the page’s reconstructed bytes
- `payload`: array of segment objects holding bytes (usually hex)

> Why segment at all?  
> Cardano metadata has limits. Splitting payload into segments keeps each piece valid and makes minting more reliable.

### B) Manifest NFT (1)
The manifest NFT describes how to reconstruct the full document:
- What pages exist (asset names / order)
- What codec is used (gzip, raw text, etc.)
- Hashes of the whole file (`sha_gz`, `sha_html`, etc.)
- Content type (`text/html`, `text/plain`, etc.)
- Page count, segment sizes, etc.

The viewer reads the **manifest first**, then fetches every page in order, verifies, and reconstructs.

## The Registry (the “DNS” for Scrolls)

The Registry is a single on-chain “directory” that tells Ledger Scrolls what Scrolls exist.

It is implemented as:
- A **registry NFT** (e.g., `LS_REGISTRY`) minted under a short-lived policy
- Locked at a known **Registry address**
- The UTxO holding that NFT has an **inline datum** with a gzipped JSON object:
  - This JSON lists Scrolls and their manifest pointers

### Registry example (current live registry)
- Registry policy id: `895cbbe0e284b60660ed681e389329483d5ca94677cbb583f3124062`
- Registry asset name hex: `4c535f5245474953545259` (ASCII `LS_REGISTRY`)
- Registry address:  
  `addr1q9x84f458uyf3k23sr7qfalg3mw2hl0nvv4navps2r7vq69esnxrheg9tfpr8sdyfzpr8jch5p538xjynz78lql9wm6qpl6qxy`
- The UTxO with the NFT holds `inlineDatum.bytes` which is gzipped JSON.

## How the viewer works (high-level)

### Step 1 — Connect to a local node via socket
Uses `cardano-cli` or Ogmios against your **local cardano-node** (connects to IOHK relays via your node's topology).

Set:
```bash
export CARDANO_NODE_SOCKET_PATH=/path/to/node.socket
```

### Step 2 — Read the registry in one query
Queries the registry address → finds the NFT UTxO → extracts & gunzips inline datum → gets list of Scrolls.

### Step 3 — Resolve the manifest pointer
Uses `manifest_tx_hash` (or future `manifest_utxo`/`manifest_address`) from registry entry.

### Step 4 — Fetch pages + reconstruct
Fetches page metadata → verifies hashes → concatenates → applies codec → outputs file.

## Why this avoids indexing the entire chain
Everything is **precise pointer lookups** — no scanning, no full policy searches.

## Creating your own library (dev workflow)
See the full instructions in the README sections above (choose format, naming, mint pages/manifest, publish to registry).

Two models:
- Use the **global registry** (submit PR)
- Run your **own registry** (recommended for custom libraries)

## Viewer interface philosophy
Backend is deterministic + scriptable (CLI), but UX is **option-based**:
- Local web UI (Streamlit) — recommended default
- TUI (textual/curses) — optional
- CLI — always available

Run example:
```bash
./ledger-scrolls          # → opens web UI
./ledger-scrolls --cli    # → CLI mode
```

## Registry schema (v1)
```json
{
  "spec": "ledger-scrolls-registry-v1",
  "version": 1,
  "updated": "2026-01-19T00:00:00Z",
  "scrolls": [
    {
      "id": "bible",
      "title": "Bible (HTML, gzip compressed)",
      "policy_id": "2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0",
      "manifest_asset_name_hex": "...",
      "manifest_tx_hash": "cfda418ddc84888ac39116ffba691a4f90b3232f4c2633cd56f102cfebda0ee4",
      "manifest_slot": "175750638",
      "codec": "gzip",
      "content_type": "text/html"
    }
    // ...
  ]
}
```

## Next recommended improvements
- Add `manifest_utxo` / `manifest_address` to registry entries
- Registry selection in UI (default + custom)
- Wizards for creating registry & publishing scrolls
- Full Blockfrost fallback option

## Philosophy
- **Open standard**
- **Permissionless**
- **Non-custodial**
- **Non-indexed**

If you can run a node → you can read the library forever.

Maintained with ❤️ by [@BEACNpool](https://x.com/BEACNpool)
