# Ledger Scrolls 📜
**"A library that cannot burn."**

Ledger Scrolls is an open-source **standard + viewer** for publishing and reading **permissionless, immutable data** on the Cardano blockchain.

## Design Principles

The design goal is simple:
- ✅ **No chain indexing required**
- ✅ **No centralized gatekeepers**
- ✅ **No "download the whole chain history" requirement**
- ✅ **Local-first** (your node + your socket) — fully supported
- ✅ **Forever-readable (by design rules):**
  - **Standard Scrolls:** readable forever **as long as the locked UTxO remains unspent**.
  - **Legacy Scrolls:** readable forever **as long as the collection stays at its declared Library Address**.
    **Rule:** DO NOT MOVE the Legacy NFTs. If you move them, you have intentionally broken the registry and must publish a new registry head.

---

## Two Storage Standards

Ledger Scrolls supports two storage styles:

### 1. ✅ Ledger Scrolls Standard (Lean): Locked UTxO Datum Bytes
**Best for:** Small files (icons/images/manifests/configs) that fit inside one on-chain inline datum.

- Supports optional gzip compression for slightly larger files
- **Default demo:** Hosky PNG (works in all modes)
- **Minimal on-chain footprint:** One UTxO, one datum, one fetch, one file

### 2. 🧾 Legacy Scrolls (Large): Pages + Manifest NFTs (CIP-25 style)
**Best for:** Large documents (Bible / Whitepaper)

- Multiple page NFTs with reconstruction logic
- Automatic detection of page index (`i` field)
- Supports both explicit page lists and indexed pages

---

## Live Demo Scrolls

### 1) ✅ Hosky PNG (Ledger Scrolls Standard — lean & local-first)
This demo stores a complete PNG **directly in an inline datum** at a **locked UTxO**.
A viewer can reconstruct the exact image bytes from chain data.

**On-chain pointer:**
- Lock address: `addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn`
- Locked UTxO (txin): `728660515c6d9842d9f0ffd273f2b487a4070fd9f4bd5455a42e3a56880389be#0`
- Datum format: **inlineDatum.bytes** = hex of the PNG file
- Content-Type: `image/png`
- Codec: `none`

**Immutability proof (hash):**
```
sha256(hosky.png) == 798e3296d45bb42e7444dbf64e1eb16b02c86a233310407e7d8baf97277f642f
```

> **Why this is the "Standard":** It's the minimal possible on-chain data product: **one UTxO, one datum, one fetch, one file.**

### 2) Bible (HTML, gzip compressed) — Legacy Pages
Large document demonstration using the legacy pages + manifest pattern.

- **Policy ID:** `2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0`
- **Manifest tx hash:** `cfda418ddc84888ac39116ffba691a4f90b3232f4c2633cd56f102cfebda0ee4`
- **Manifest slot:** `175750638`
- **Pages:** 237 NFTs, each with `i` index and `payload` segments
- **Reconstruction:** `concat_pages + gunzip`
- **Content-Type:** `text/html`
- **Codec:** `gzip`

### 3) Bitcoin Whitepaper — Legacy Pages
Small document demonstration using the legacy pattern.

- **Policy ID:** `8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1`
- **Manifest tx hash:** `2575347068f77b21cfe8d9c23d9082a68bfe4ef7ba7a96608af90515acbe228f`
- **Manifest slot:** `176360887`
- **Pages:** 3 NFTs with automatic gzip detection
- **Content-Type:** Automatically detected as HTML
- **Codec:** Auto-detected (gzip magic bytes)

---

## Core Concept: "No Indexing" via Deterministic Pointers

Most "on-chain data" projects fail because reading requires one of:
- A centralized API (Blockfrost, Koios, etc.)
- A custom indexer scanning the chain
- A full-history database query plan

Ledger Scrolls avoids that using **deterministic pointers**.

### Pointer Model (First Principles)

**A Scroll must be fetchable from a tiny number of deterministic lookups:**
- **Registry pointer (optional):** 1 address query (find the registry UTxO datum)
- **Scroll pointer:** points to either:
  - **(Standard)** A single locked UTxO holding bytes in an inline datum, OR
  - **(Legacy)** A policy ID where all NFTs with `i` index are pages

This transforms "find my document somewhere in the blockchain" into:
- **1 address query** (registry UTxO) OR direct user input
- **1 pointer resolution**
- **0 indexing**

---

## Rules of the Library (Non-Negotiable)

Ledger Scrolls works because authors follow library rules.

### Rule 1 — Do Not Move Legacy Scrolls
Legacy Scrolls (CIP-25 Pages + Manifest) MUST remain at the declared **Library Address** (`location_hint`).

- Moving the NFTs breaks the Registry's Fast Path by definition.
- If you choose to move them, you MUST publish a new registry head (or a superseding entry) with the new location.

### Rule 2 — Standard Scrolls Must Remain Unspent
Standard Scrolls live in the UTxO set (Hot State). If the locked UTxO is spent, the pointer is destroyed.

- Use an always-fail validator.
- Treat the funding keys like production infrastructure (monitor, alert, and never "clean up" the script UTxO).

---

## Technical Specification: Ledger Scrolls Standard (LS-LOCK v1)

### Storage Mechanism: Locked UTxO + Inline Datum Bytes

A Standard Scroll stores the file bytes in:
- `inlineDatum.bytes` (hex-encoded) at a **permanently locked UTxO**

**Required fields for a Standard Scroll:**
- `txin` — Transaction input in format `TXHASH#INDEX`
- `lock_address` — The script address holding the UTxO (optional if txin is globally unique)
- `content_type` — MIME type (e.g., `image/png`, `text/html`)
- `sha256` — Hash of the reconstructed file (recommended for verification)
- `codec` — Compression format: `none` or `gzip`

### Why "Locked" Matters

If the UTxO stays **unspent**, the datum remains in the UTxO set and is fetchable forever without indexing.

> **Ledger Scrolls ethos:** Permanently locked, never spendable.

To achieve "never spendable," lock the UTxO at a script address that cannot validate (an "always-fail" script or similar construct). The datum is then effectively permanent.

### Data Flow: Standard Scroll Creation

1. **Prepare file:** Original file (e.g., `hosky.png`)
2. **Optional compression:** Apply gzip if `codec: gzip`
3. **Hex encode:** Convert bytes to hex string
4. **Create datum:** Build inline datum with hex as `bytes` field
5. **Lock UTxO:** Send to always-fail script address with inline datum
6. **Record pointer:** Note the `txin` (transaction hash + output index)
7. **Compute hash:** Calculate `sha256` of original file for verification

### Data Flow: Standard Scroll Reading

1. **Query UTxO:** Fetch UTxO at `lock_address` or by `txin`
2. **Extract datum:** Read `inlineDatum.bytes` field (handle CBOR encoding)
3. **Hex decode:** Convert hex string to binary bytes
4. **Optional decompression:** Apply gunzip if `codec: gzip`
5. **Verify hash:** Compare `sha256` of reconstructed file
6. **Deliver file:** Save or display based on `content_type`

---

## Technical Specification: Legacy Scrolls (LS-PAGES v1)

### Storage Mechanism: Pages + Optional Manifest (Index-Based)

A Legacy Scroll is stored as:
- **Page NFTs** (many): Each page has `i` index and `payload` segments in metadata
- **Manifest NFT** (optional): Provides additional metadata like hashes and codec

**The viewer now uses a simplified approach:**
1. Fetch ALL assets under the policy
2. Filter for NFTs with `payload` and `i` fields
3. Sort by `i` index
4. Concatenate payloads

This eliminates dependency on manifest format variations.

### Typical Page Metadata Fields

```json
{
  "i": 1,
  "payload": [
    {"bytes": "hex_data_1"},
    {"bytes": "hex_data_2"}
  ]
}
```

**Field definitions:**
- `i` — Page index (required for ordering)
- `payload` — Array of hex-encoded segments (supports both `{"bytes": "..."}` and direct string formats)

**Supported payload formats:**
- `[{"bytes": "hex"}, {"bytes": "hex"}]` (CIP-25 style)
- `["hex1", "hex2"]` (direct strings)
- Mixed formats

### Data Flow: Legacy Scroll Reading

1. **Fetch all assets:** Query all NFTs under policy ID
2. **Filter pages:** Find all NFTs with `payload` and `i` fields
3. **Sort by index:** Order pages by `i` value
4. **Concatenate segments:** Join hex segments within each page
5. **Concatenate pages:** Join all pages in order
6. **Clean hex:** Remove `0x` prefixes and whitespace
7. **Hex decode:** Convert to binary
8. **Auto-detect compression:** Check for gzip magic bytes (`1f 8b`)
9. **Decompress if needed:** Apply gunzip if detected
10. **Auto-detect file type:** Check for HTML markers
11. **Save with correct extension:** `.html`, `.png`, `.txt`, etc.

---

## The Registry: "DNS" for Scrolls

The Registry is a single on-chain directory that tells Ledger Scrolls what exists.

## Registry Governance Modes

Ledger Scrolls supports two governance models:

### A) Personal Registry (Single Author)
A single registry UTxO contains gzipped JSON of all scrolls.
- Simple and recommended for personal libraries.
- Update = spend-and-recreate the registry UTxO under your own rules.

### B) Community Registry (Append-Only, Hash-Chained)
A community registry is an append-only chain of immutable entries.

**Structure:**
- **Entry UTxO (immutable):** each new scroll entry is stored in its own locked UTxO with an inline datum:
  - `entry`: the scroll metadata
  - `prev`: the previous entry's `txin`
  - `prev_hash`: sha256 of the previous entry datum (chain integrity)
- **Head UTxO (pointer):** a small UTxO that stores the `latest_entry_txin` (the "head" pointer).

**Why this works:**
- Entries are immutable forever.
- The chain is verifiable from any chosen head.
- Viewers do not need to "trust the network"—they only need to choose which head they follow.

### Current Live Registry Pointer (Personal Registry)

- **Registry policy ID:** `895cbbe0e284b60660ed681e389329483d5ca94677cbb583f3124062`
- **Registry asset name (hex):** `4c535f5245474953545259` (ASCII: `LS_REGISTRY`)
- **Registry address:** `addr1q9x84f458uyf3k23sr7qfalg3mw2hl0nvv4navps2r7vq69esnxrheg9tfpr8sdyfzpr8jch5p538xjynz78lql9wm6qpl6qxy`

### Registry Schema v2 (Supports Both Standard + Legacy)

```json
{
  "spec": "ledger-scrolls-registry-v2",
  "version": 2,
  "updated": "2026-01-21T00:00:00Z",
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
      "content_type": "text/html"
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

## Security Model: Trusted Heads

Registries are not globally "trusted." Viewers follow a **trusted head**.

- If someone publishes a malicious registry head, you simply do not point to it.
- A viewer can pin a specific `registry_head_txin` (or pinned hash) as the last-known-good anchor.
- From that anchor, the hash-chained history is verifiable.

**Result:** attackers can publish garbage, but they cannot force your viewer to accept it.

---

## Verification Guide: Prove a Standard Scroll Is On-Chain

This guide uses the Hosky PNG as an example.

### Prerequisites

- `cardano-cli` installed and configured for mainnet
- `jq` for JSON parsing
- `xxd` for hex manipulation

### Step 1: Query the Lock Address UTxO Set

```bash
cardano-cli query utxo --mainnet \
  --address "addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn" \
  --out-file locked_utxo_live.json
```

This queries all UTxOs at the lock address and saves them to `locked_utxo_live.json`.

### Step 2: Confirm the Exact Txin Exists and Has Inline Datum

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

Expected output:
```
FOUND ON-CHAIN: 728660515c6d9842d9f0ffd273f2b487a4070fd9f4bd5455a42e3a56880389be#0
inlineDatum? true
```

### Step 3: Extract Datum Bytes Into a Real PNG

```bash
# Extract the inline datum object
jq -r --arg k "$LOCKED_TXIN" '.[$k].inlineDatum' locked_utxo_live.json > datum.json

# Extract the hex bytes field
jq -r '.fields[0].bytes' datum.json | tr -d '\n' | xxd -r -p > onchain.png
```

This converts the hex-encoded bytes back into binary PNG format.

### Step 4: Verify PNG Sanity + Hash Immutability

```bash
# Check file type
file onchain.png

# Compute hash
sha256sum onchain.png

# Compare with original (if you have it)
sha256sum hosky.png onchain.png
```

Expected output:
```
onchain.png: PNG image data, 512 x 512, 8-bit/color RGBA, non-interlaced
798e3296d45bb42e7444dbf64e1eb16b02c86a233310407e7d8baf97277f642f  onchain.png
798e3296d45bb42e7444dbf64e1eb16b02c86a233310407e7d8baf97277f642f  hosky.png
```

If hashes match, the image is **byte-for-byte immutable on-chain**. ✅

---

## Running the Viewer

The viewer is a cross-platform Python GUI app (Windows/Mac/Linux) with **three connection modes**, progress tracking, safe file saving, and comprehensive error logging.

### System Requirements

- Python 3.7 or higher
- `tkinter` (usually included with Python)
- `cbor2` library (for datum decoding)
- Internet connection (for Blockfrost API mode)
- **Optional:** Cardano node + `cardano-cli` (for Local Node mode)

### Installation

```bash
# Clone the repository
git clone https://github.com/BEACNpool/ledger-scrolls.git
cd ledger-scrolls

# Install dependencies
pip install -r requirements.txt

# Run the viewer
python viewer.py
```

### Three Connection Modes

The viewer supports three modes of operation, giving users choice based on their needs:

#### 1. 📡 Blockfrost API Mode (Default - Easy Setup)

**Best for:** Quick start, casual users, no local infrastructure

**Pros:**
- ✅ Fast and convenient
- ✅ No node required
- ✅ Works immediately with free API key

**Cons:**
- ⚠️ Requires third-party service
- ⚠️ Rate limits (free tier: 50,000 requests/day)

**Setup:**
1. Get free API key at [blockfrost.io](https://blockfrost.io)
2. Create a **Mainnet** project (important!)
3. Copy your `project_id` (starts with `mainnet...`)
4. Enter in viewer and click "Save"

#### 2. 🖥️ Local Node Mode (Maximum Sovereignty)

**Best for:** Node operators, privacy-focused users, unlimited queries

**Pros:**
- ✅ No API dependency
- ✅ Unlimited queries
- ✅ Maximum privacy
- ✅ True decentralization

**Cons:**
- ⚠️ Requires running full Cardano node
- ⚠️ ~150GB disk space
- ⚠️ 2-3 days initial sync

**Setup:**
1. Install Cardano node: https://developers.cardano.org/docs/get-started/installing-cardano-node
2. Wait for full sync
3. Configure in viewer:
   - Host: `localhost`
   - Port: `3001` (not used for queries)
   - Socket Path: `/opt/cardano/cnode/sockets/node.socket`
4. Click "Test & Save"

#### 3. ⚡ P2P Lightweight Mode (EXPERIMENTAL - Under Construction)

**Best for:** Future - direct P2P without full node

**Status:** 🚧 Under development

**Vision:**
- Connect directly to Cardano P2P network
- Query specific blocks without full sync
- No API, no full node, ~100MB usage

**Current State:**
- UI ready
- Configuration interface complete
- Protocol implementation in progress (estimated 3 months)

**What Works:** Configuration and error messages
**What Doesn't Work:** Actual P2P queries

See `P2P_DEVELOPMENT_ROADMAP.md` for technical details and implementation timeline.

### Viewer Features

- ✅ **Three connection modes** with easy switching
- ✅ **GUI with demo buttons** for Hosky, Bible, BTC Whitepaper
- ✅ **Automatic format detection** (gzip, HTML, image types)
- ✅ **Smart file naming** with correct extensions
- ✅ **Progress tracking** with detailed status messages
- ✅ **Hash verification** for data integrity
- ✅ **Error logging** to `~/.ledger-scrolls/logs/` for debugging
- ✅ **Safe file saving** to `~/Downloads/LedgerScrolls/`
- ✅ **Custom scroll input** for any scroll by pointer
- ✅ **Retry logic** with exponential backoff
- ✅ **CBOR datum decoding** for Standard Scrolls
- ✅ **0x prefix handling** for hex data
- ✅ **Multiple metadata field support** for Legacy Scrolls

### Usage

#### Quick Start with Blockfrost:

1. Launch `python viewer.py`
2. Select "Blockfrost API" mode (default)
3. Enter API key and click "Save"
4. Click "Load Hosky PNG" (~5 seconds)
5. File saved to `~/Downloads/LedgerScrolls/Hosky PNG.png`

#### Load Legacy Scrolls:

- **Bible:** ~60 seconds (237 pages, 4.6MB)
- **Bitcoin Whitepaper:** ~15 seconds (3 pages, 33KB)

Both auto-detect as HTML and save with `.html` extension.

#### Custom Scrolls:

1. Click "Custom Scroll"
2. Choose scroll type (Standard or Legacy)
3. Enter pointer details
4. Click "Fetch Scroll"

### Debug Logging

All operations are logged to:
```
~/.ledger-scrolls/logs/viewer_YYYYMMDD_HHMMSS.log
```

Logs include:
- Connection attempts
- API calls and responses
- CBOR decoding steps
- Error stack traces
- Performance metrics

Check logs when troubleshooting issues.

### Known Issues & Solutions

#### Issue: Blockfrost 403 Errors
**Solution:** Ensure API key is for **Mainnet** (not Testnet), and is valid/not expired

#### Issue: Files Save as .txt Instead of .html
**Solution:** Now fixed! Viewer auto-detects HTML content and uses correct extension

#### Issue: "Non-hexadecimal digit found"
**Solution:** Now fixed! Viewer strips `0x` prefixes and handles all hex formats

#### Issue: Bible Takes Long to Load
**This is normal!** 237 pages = 237 API calls = ~60 seconds due to rate limiting

#### Issue: cardano-cli Not Found (Local Mode)
**Solution:** Install Cardano node tools or use Blockfrost mode instead

---

## Developer Guide: Create Your Own Scroll

### Publishing a Standard Scroll

**Recommended for:** Files under ~10KB practical payload territory (accounting for datum structure and metadata overhead)

**Steps:**

1. **Prepare your file**
   ```bash
   # Original file
   cp my_image.png scroll_data.bin
   
   # Optional: compress with gzip
   gzip -c my_image.png > scroll_data.bin
   ```

2. **Convert to hex**
   ```bash
   xxd -p scroll_data.bin | tr -d '\n' > scroll_data.hex
   ```

3. **Create inline datum JSON**
   ```json
   {
     "constructor": 0,
     "fields": [
       {
         "bytes": "PASTE_HEX_HERE"
       }
     ]
   }
   ```

4. **Build transaction with locked UTxO**
   ```bash
   # Use an always-fail script address
   LOCK_ADDR="addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn"
   
   cardano-cli transaction build \
     --mainnet \
     --tx-in YOUR_INPUT_UTXO \
     --tx-out "$LOCK_ADDR+2000000" \
     --tx-out-inline-datum-file datum.json \
     --change-address YOUR_CHANGE_ADDR \
     --out-file tx.raw
   
   cardano-cli transaction sign \
     --tx-body-file tx.raw \
     --signing-key-file payment.skey \
     --mainnet \
     --out-file tx.signed
   
   cardano-cli transaction submit \
     --mainnet \
     --tx-file tx.signed
   ```

5. **Record the pointer**
   ```bash
   # Note the transaction hash and output index
   TXIN="YOUR_TX_HASH#0"
   ```

6. **Compute verification hash**
   ```bash
   sha256sum my_image.png
   ```

7. **Share your scroll**
   ```json
   {
     "title": "My Custom Scroll",
     "type": "utxo_datum_bytes_v1",
     "lock_address": "addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn",
     "lock_txin": "YOUR_TX_HASH#0",
     "content_type": "image/png",
     "codec": "none",
     "sha256": "YOUR_SHA256_HASH"
   }
   ```

### Publishing a Legacy Scroll

**Recommended for:** Large files (>10KB)

**Simplified approach:** Just ensure each page NFT has:
- `i` field (page index, 1-based)
- `payload` field (array of hex segments or `{"bytes": "hex"}` objects)

The viewer will automatically:
- Find all pages under your policy
- Sort by `i` index
- Handle both hex formats
- Auto-detect compression
- Auto-detect file type

### Extending the Viewer

The viewer is designed to be extended. Key areas for contribution:

1. **P2P Protocol Implementation** - See `P2P_DEVELOPMENT_ROADMAP.md`
2. **Additional File Formats** - Add support for more MIME types
3. **UI Improvements** - Dark mode, preview pane, batch operations
4. **Performance** - Caching, parallel fetches, optimizations

**How to contribute:**
1. Fork the repository
2. Create a feature branch
3. Follow existing code style
4. Add tests if applicable
5. Submit pull request with clear description

---

## Philosophy

Ledger Scrolls is built on these core principles:

- ✅ **Open standard** — Anyone can implement, no gatekeepers
- ✅ **Permissionless** — No approval needed to publish or read
- ✅ **Non-custodial** — You control your data and keys
- ✅ **Permanently locked** — Data that cannot be deleted or modified
- ✅ **Multiple access paths** — API, local node, or P2P (coming soon)
- ✅ **Auto-detection** — Smart handling of formats and compression

### Why This Matters

Traditional web hosting:
- ❌ Can be taken down (censorship, server failures)
- ❌ Can be modified (no immutability guarantees)
- ❌ Requires ongoing payment (hosting fees)
- ❌ Centralized control (hosting provider decides)

Ledger Scrolls:
- ✅ Cannot be taken down (as long as Cardano exists)
- ✅ Cannot be modified (cryptographic immutability)
- ✅ One-time cost (transaction fee only)
- ✅ Decentralized (no single point of failure)
- ✅ Multiple access methods (choose your tradeoff)

### Use Cases

- 📜 **Permanent documents** — Historical records, manifestos, declarations
- 🖼️ **NFT metadata** — Store image/metadata without IPFS dependency
- ⚙️ **Configuration files** — Immutable configs for dApps
- 🔒 **Censorship-resistant publishing** — Unstoppable text/documents
- 🔐 **Proof of existence** — Timestamp + hash verification
- 📚 **Digital libraries** — Collections that cannot be erased
- 🏛️ **Archives** — Preserve knowledge for future generations

---

## FAQ

### Q: How much does it cost to publish a scroll?

**A:** Only the Cardano transaction fee (typically 0.17-0.5 ADA depending on size). There are no ongoing hosting costs.

### Q: What's the maximum file size?

**A:** 
- **Standard scrolls:** Standard Scrolls are bounded by protocol parameters (tx/UTxO size). In practice, treat LS-LOCK v1 as **~10KB payload territory** once you account for datum structure and metadata overhead.
- **Legacy scrolls:** Theoretically unlimited (split into pages), but practical limit is a few MB

### Q: Can scrolls be deleted or modified?

**A:** No. Once locked on-chain, they are permanent and immutable. This is by design.

### Q: Do I need to run a Cardano node?

**A:** No! Blockfrost API mode works without a node. Local Node mode is optional for those who want maximum sovereignty.

### Q: What happens if Blockfrost goes down?

**A:** 
1. Use Local Node mode (if you have a node)
2. Wait for Blockfrost to return
3. Query directly with `cardano-cli` 
4. Your data is still on-chain and accessible

### Q: Will P2P Lightweight mode really work?

**A:** Yes! The protocol design is sound and achievable. It will take ~3 months to implement. See `P2P_DEVELOPMENT_ROADMAP.md` for details.

### Q: How do I get a Blockfrost API key?

**A:** 
1. Go to https://blockfrost.io
2. Sign up (free)
3. Create a **Mainnet** project
4. Copy your `project_id`
5. Free tier: 50,000 requests/day

### Q: Can I verify scrolls are really on-chain?

**A:** Yes! See the "Verification Guide" section for step-by-step instructions using `cardano-cli`.

---

## Roadmap

### Current (v1.0) ✅
- ✅ Standard scroll specification (locked UTxO + inline datum)
- ✅ Legacy scroll specification (index-based pages)
- ✅ Three-mode viewer (Blockfrost, Local Node, P2P UI)
- ✅ CBOR datum decoding
- ✅ Auto-detection (gzip, HTML, file types)
- ✅ Comprehensive error logging
- ✅ Demo scrolls (Hosky, Bible, Bitcoin Whitepaper)
- ✅ Smart hex handling (0x prefixes, multiple formats)

### Near-term (v1.1 - February 2026)
- 🔄 Bug fixes based on user feedback
- 🔄 Performance optimizations
- 🔄 Improved error messages
- 🔄 Registry browser
- 🔄 Batch scroll downloads

### Mid-term (v2.0 - Q2 2026)
- 📋 P2P Lightweight mode fully functional
- 📋 Web-based viewer (no installation)
- 📋 CLI tool for scroll creation
- 📋 Scroll creation GUI
- 📋 Enhanced documentation

### Long-term (v3.0 - Q3+ 2026)
- 💡 Mithril integration
- 💡 Mobile apps (iOS/Android)
- 💡 Smart contract-gated scrolls
- 💡 Decentralized registry discovery
- 💡 Multi-chain support

---

## BEACN Curated Editions (Luxury Publishing Layer)

Ledger Scrolls is MIT open-source. Anyone can publish their own library.

BEACN's long-term vision is a **luxury publishing layer** built on top of this standard:
- Curated collections ("editions")
- Provenance-focused metadata
- Immutability certificates (hash + on-chain pointers)
- White-glove publishing for institutions, collectors, and archives

Open protocol. Premium execution.

---

## Technical Details

### Dependencies

```
requests>=2.28.0  # HTTP client for Blockfrost
cbor2>=5.4.0      # CBOR encoding/decoding for datums
```

### File Structure

```
ledger-scrolls/
├── viewer.py                          # Main GUI application
├── requirements.txt                    # Python dependencies
├── README.md                          # This file
├── P2P_DEVELOPMENT_ROADMAP.md        # P2P implementation plan
├── lightweight_p2p_client_design.md  # P2P technical design
└── ~/.ledger-scrolls/                # User data directory
    ├── config.json                    # Saved configuration
    ├── logs/                          # Debug logs
    │   └── viewer_*.log
    └── p2p_cache/                     # Future P2P cache
```

### Key Improvements in v1.0

1. **CBOR Decoding** - Proper handling of Blockfrost's CBOR datum format
2. **Auto-Detection** - Gzip magic bytes and HTML content detection
3. **0x Prefix Handling** - Strips `0x` before hex decoding
4. **Multiple Payload Formats** - Handles `{"bytes": "..."}` and direct strings
5. **Index-Based Legacy** - Simplified approach using `i` field
6. **Smart File Extensions** - Auto-detects and uses correct extensions
7. **Comprehensive Logging** - Every operation logged for debugging
8. **Three Modes** - Blockfrost, Local Node, and P2P (UI ready)

---

## Contributing

We welcome contributions! Areas where you can help:

### Code Contributions
- 🔥 **P2P Protocol Implementation** (high priority - see roadmap)
- Local node optimizations
- UI/UX improvements
- Bug fixes and testing

### Documentation
- Tutorials and guides
- Video walkthroughs
- Translation to other languages
- API documentation

### Testing
- Test with different scrolls
- Report bugs and edge cases
- Platform-specific testing (Windows/Mac/Linux)
- Performance benchmarking

### Community
- Share your scrolls
- Write blog posts or tutorials
- Help others in discussions
- Spread the word about Ledger Scrolls

**How to contribute:**
1. Check existing issues on GitHub
2. Open a new issue to discuss your idea
3. Fork the repository
4. Create a feature branch
5. Submit a pull request

---

## Links

- **GitHub:** https://github.com/BEACNpool/ledger-scrolls
- **Twitter/X:** [@BEACNpool](https://x.com/BEACNpool)
- **Blockfrost:** https://blockfrost.io (for API keys)
- **Cardano Developers:** https://developers.cardano.org

---

## Troubleshooting

**For more help:**
- Check logs in `~/.ledger-scrolls/logs/`
- Open GitHub issue with log excerpts
- Contact @BEACNpool on Twitter/X

---

## License

MIT License - See LICENSE file for details

---

## Acknowledgments

Built with ❤️ by [@BEACNpool](https://x.com/BEACNpool)

Special thanks to:
- The Cardano community
- Blockfrost team for API access
- All contributors and testers
- Early adopters preserving knowledge on-chain

---

**"In the digital age, true knowledge must be unstoppable."**

The chain is the library. The scrolls are eternal.
