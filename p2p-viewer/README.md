# Ledger Scrolls P2P Viewer (Python)

**“A library that cannot burn.”**

Ledger Scrolls is an open-source standard + viewer for publishing and reading **permissionless, immutable data** on Cardano — without centralized gatekeepers. This viewer is the **P2P, no-indexer** path: it connects directly to relays and reads scrolls from the chain.

This repo is a **lightweight Node-to-Node (N2N) Ouroboros client** + **Ledger Scrolls reconstruction engine**.

It’s designed for **selective retrieval**: fetch *only the blocks you need* from a relay, extract **CIP-25 (label 721)** metadata, and reconstruct Ledger Scrolls files (e.g., the Cardano Constitution pages + manifest).

**Design goals (ethos):**
- **No chain indexing**
- **No centralized gatekeepers**
- **No “download the whole chain history” requirement**
- **Local-first / P2P** (your relays, your sockets)
- **Forever-readable** as long as the pointer remains valid

## What this can and cannot do

### ✅ Can do (today)
- Connect to a Cardano relay (N2N, TCP/3001) and perform:
  - Handshake (NodeToNode v14)
  - ChainSync intersection
  - BlockFetch for specific blocks
- Extract TX metadata (label **721**) from fetched blocks
- Reconstruct **CIP-25 “pages + manifest”** scrolls from metadata found in those blocks

### ⚠️ Cannot do without *either* a starting point or a bootstrap source
The N2N protocols used here (**ChainSync** + **BlockFetch**) can stream headers and fetch blocks, but you still need an **initial valid chain point** (slot + header hash) close to your scroll, or you’ll end up streaming from genesis (which defeats the “no full chain history” goal).

**For the Constitution scrolls** you’ll typically provide:
- **manifest_point**: `slot` + `block_header_hash` where the *manifest* mint TX appears
- **policy_id**: the page/manifest policy
- **manifest_asset**: e.g. `CONSTITUTION_E608_MANIFEST`

Once you have the manifest point, this viewer can:
- Stream forward a limited number of headers
- Fetch only those blocks
- Collect manifest + page metadata
- Reconstruct + verify output

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Show relay tip (sanity check)
python -m lsview tip --relay backbone.cardano.iog.io --port 3001

# Reconstruct a legacy scroll (Constitution example)
python -m lsview reconstruct-cip25 \
  --scroll constitution-e608 \
  --max-blocks 400 \
  --out Cardano_Constitution_E608.txt
```

## GUI (Proof‑of‑Concept)

The GUI provides a themed Ledger‑Scrolls interface with:
- Catalog dropdown (one‑click scroll reconstruction)
- Manual entry for new scrolls
- Relay + topology settings

**Run on Windows (PowerShell):**
```powershell
./run-gui.ps1
```

**Run on macOS/Linux:**
```bash
python -m gui.app
```

## Relay topology (P2P fallback)

You can point the viewer at a **Cardano topology JSON** (file path or URL). The CLI will try each relay in order until it can handshake.

```bash
python -m lsview tip \
  --topology /path/to/topology.json
```

Expected JSON shape includes either `Producers` or `AccessPoints`, for example:

```json
{
  "Producers": [
    {"addr": "relays-new.cardano-mainnet.iohk.io", "port": 3001, "valency": 2}
  ]
}
```

## Optional bootstrap via Blockfrost (only if you need it)

The P2P path requires a **valid start point** (slot + block header hash). If you only have a **tx hash**, you can resolve a chain point using Blockfrost (optional, not required for normal P2P use).

```bash
export BLOCKFROST_PROJECT_ID=your_key_here
python -m lsview blockfrost-point --tx-hash <TX_HASH>
```

This prints a slot + block hash you can plug into `--start-slot` / `--start-hash`.

## Known scrolls (legacy / CIP-25)

These are **live on mainnet** and work with `reconstruct-cip25` once you have a start point:

- **Constitution (Epoch 608)**
  - Policy: `ef91a425ef57d92db614085ef03718407fb293cb4b770bc6e03f9750`
  - Manifest asset: `CONSTITUTION_E608_MANIFEST`
  - Pages: 11

- **Constitution (Epoch 541)**
  - Policy: `d7559bbfa87f53674570fd01f564687c2954503b510ead009148a31d`
  - Manifest asset: `CONSTITUTION_E541_MANIFEST`
  - Pages: 7

- **Bible (HTML, gzip)**
  - Policy: `2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0`
  - Manifest TX: `cfda418ddc84888ac39116ffba691a4f90b3232f4c2633cd56f102cfebda0ee4`
  - Manifest slot: `175750638`
  - Pages: 237
  - Note: manifest asset auto-detected from metadata (no manual name needed)

- **Bitcoin Whitepaper**
  - Policy: `8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1`
  - Manifest TX: `2575347068f77b21cfe8d9c23d9082a68bfe4ef7ba7a96608af90515acbe228f`
  - Manifest slot: `176360887`
  - Pages: 3
  - Note: manifest asset auto-detected from metadata (no manual name needed)

## Standard Scrolls (LS-LOCK v1)

Standard Scrolls store the file bytes in a **single inline datum** at a **locked UTxO** (no policy, no pages). You can reconstruct them directly from a relay using `reconstruct-utxo`.

Examples:

```bash
# Hosky PNG (txin index 0)
python -m lsview reconstruct-utxo \
  --scroll hosky-png \
  --out hosky.png

# Architect's Scroll (txin index 0)
python -m lsview reconstruct-utxo \
  --scroll architects-scroll \
  --out architects_scroll.txt
```

If you prefer manual args:
```bash
python -m lsview reconstruct-utxo --tx-hash <TX_HASH> --tx-ix 0 --out output.bin
```

If you already know the **block slot + block hash**, you can avoid Blockfrost entirely:

```bash
python -m lsview reconstruct-utxo \
  --block-slot <SLOT> --block-hash <BLOCK_HASH> \
  --tx-hash <TX_HASH> --tx-ix 0 \
  --out output.bin
```

Catalog-driven usage:

```bash
# List catalog path (default)
ls -la p2p-viewer/examples/scrolls.json

# Show known scrolls
python -m lsview list-scrolls

# Refresh catalog with Blockfrost (optional)
python -m lsview refresh-catalog
```

Known Standard Scrolls:

- **Hosky PNG**
  - Lock address: `addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn`
  - TxIn: `728660515c6d9842d9f0ffd273f2b487a4070fd9f4bd5455a42e3a56880389be#0`

- **The Architect's Scroll**
  - Lock address: `addr1w9fdc02rkmfyvh5kzzwwwk4kr2l9a8qa3g7feehl3ga022qz2249g`
  - TxIn: `076d6800d8ccafbaa31c32a6e23eecfc84f7d1e35c31a9128ec53736d5395747#0`

## Project layout

- `lsview/n2n_client.py` — N2N transport, mux framing, handshake
- `lsview/chainsync.py` — ChainSync messages + streaming headers
- `lsview/blockfetch.py` — BlockFetch messages
- `lsview/block_parser.py` — parse blocks, transactions, metadata
- `lsview/topology.py` — load relay topology JSON (file or URL)
- `lsview/blockfrost.py` — optional Blockfrost bootstrap helper
- `lsview/scrolls/cip25.py` — robust CIP-25 parser (manifest + pages)
- `lsview/scrolls/reconstruct.py` — reconstruct, hash verify, gzip decode
- `lsview/__main__.py` — CLI entrypoint

## License
MIT (same spirit as Ledger Scrolls).
