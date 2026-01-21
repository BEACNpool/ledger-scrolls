# Ledger Scrolls 📜
**"A library that cannot burn."**

Ledger Scrolls is an open-source **standard + viewer** for publishing and reading **permissionless, immutable data** on the Cardano blockchain.

## Design Principles

The design goal is simple:
- ✅ **No chain indexing required**
- ✅ **No centralized gatekeepers**
- ✅ **No "download the whole chain history" requirement**
- ✅ **Local-first** (your node + your socket) – prioritized in future updates
- ✅ **Forever-readable** as long as the pointer remains valid

---

## Two Storage Standards

Ledger Scrolls supports two storage styles:

### 1. ✅ Ledger Scrolls Standard (Lean): Locked UTxO Datum Bytes
**Best for:** Small files (icons/images/manifests/configs) that fit inside one on-chain inline datum.

- Supports optional gzip compression for slightly larger files
- **Default demo:** Hosky PNG (no Blockfrost required in local mode)
- **Minimal on-chain footprint:** One UTxO, one datum, one fetch, one file

### 2. 🧾 Legacy Scrolls (Large): Pages + Manifest NFTs (CIP-25 style)
**Best for:** Large documents (Bible / Whitepaper)

- Consider migrating to standard + IPFS for new projects
- **Optional legacy fallback via Blockfrost** for convenience
- Multiple page NFTs with reconstruction logic

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
- **Reconstruction:** `concat_pages + gunzip`
- **Segments per page payload:** `32`
- **Content-Type:** `text/html`
- **Codec:** `gzip`

### 3) Bitcoin Whitepaper — Legacy Pages
Small document demonstration using the legacy pattern.

- **Policy ID:** `8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1`
- **Manifest tx hash:** `2575347068f77b21cfe8d9c23d9082a68bfe4ef7ba7a96608af90515acbe228f`
- **Manifest slot:** `176360887`
- **Content-Type:** `text/plain`
- **Codec:** `none`

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
  - **(Legacy)** A manifest tx hash + policy/asset names for pages

This transforms "find my document somewhere in the blockchain" into:
- **1 address query** (registry UTxO) OR direct user input
- **1 pointer resolution**
- **0 indexing**

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
2. **Extract datum:** Read `inlineDatum.bytes` field
3. **Hex decode:** Convert hex string to binary bytes
4. **Optional decompression:** Apply gunzip if `codec: gzip`
5. **Verify hash:** Compare `sha256` of reconstructed file
6. **Deliver file:** Save or display based on `content_type`

---

## Technical Specification: Legacy Scrolls (LS-PAGES v1)

### Storage Mechanism: Pages + Manifest NFT Pattern (CIP-25 Style)

A Legacy Scroll is stored as:
- **Page NFTs** (many): Each page stores `payload` segments in metadata
- **Manifest NFT** (one): Describes how to fetch pages, order them, decode them, and verify hashes

### Typical Page Metadata Fields

```json
{
  "spec": "gzip-pages-v1",
  "role": "page",
  "i": 1,
  "n": 100,
  "seg": 32,
  "sha": "abc123...",
  "payload": ["hex1", "hex2", ...]
}
```

**Field definitions:**
- `spec` — Format identifier (e.g., `gzip-pages-v1`)
- `role` — Must be `page` for page NFTs
- `i` — Page index (1-based)
- `n` — Total number of pages
- `seg` — Number of segments in this page
- `sha` — SHA256 of reconstructed page bytes
- `payload` — Array of hex-encoded segments

**Known variations:**
- Some implementations use `segments` instead of `payload`
- Some use `seg` as the array instead of `payload`

### Manifest Metadata Fields

```json
{
  "spec": "gzip-pages-v1",
  "role": "manifest",
  "codec": "gzip",
  "content_type": "text/html",
  "pages": 100,
  "sha_gz": "def456...",
  "sha_html": "ghi789..."
}
```

**Field definitions:**
- `codec` — Compression format: `gzip` or `none`
- `content_type` — MIME type of final reconstructed file
- `pages` — Total page count
- `sha_gz` — SHA256 of concatenated pages (before decompression)
- `sha_html` — SHA256 of final decompressed file

### Data Flow: Legacy Scroll Reading

1. **Fetch manifest:** Query transaction by `manifest_tx_hash`
2. **Parse manifest:** Extract codec, page count, naming scheme
3. **Fetch pages:** Query each page NFT by policy + asset name
4. **Order pages:** Sort by page index `i`
5. **Concatenate segments:** Join hex segments within each page
6. **Concatenate pages:** Join all pages in order
7. **Hex decode:** Convert full hex string to binary
8. **Optional decompression:** Apply gunzip if `codec: gzip`
9. **Verify hashes:** Compare against manifest hashes
10. **Deliver file:** Save or display based on `content_type`

---

## The Registry: "DNS" for Scrolls

The Registry is a single on-chain directory that tells Ledger Scrolls what exists.

### Registry Implementation

- A **registry NFT** (e.g., `LS_REGISTRY`)
- Locked at a known **Registry address**
- The UTxO holding that NFT has an **inline datum** containing **gzipped JSON** (recommended for compression) listing scrolls and their pointers

### Current Live Registry Pointer

- **Registry policy ID:** `895cbbe0e284b60660ed681e389329483d5ca94677cbb583f3124062`
- **Registry asset name (hex):** `4c535f5245474953545259` (ASCII: `LS_REGISTRY`)
- **Registry address:** `addr1q9x84f458uyf3k23sr7qfalg3mw2hl0nvv4navps2r7vq69esnxrheg9tfpr8sdyfzpr8jch5p538xjynz78lql9wm6qpl6qxy`

### Registry Schema v2 (Supports Both Standard + Legacy)

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
jq -r '.bytes' datum.json | tr -d '\n' | xxd -r -p > onchain.png
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

The viewer is a cross-platform Python GUI app (Windows/Mac/Linux) with progress bars, safe file saving, and support for both standard and legacy modes.

### System Requirements

- Python 3.7 or higher
- `tkinter` (usually included with Python)
- Internet connection (for Blockfrost API calls)

### Installation

```bash
# Clone the repository
git clone https://github.com/BEACNpool/ledger-scrolls.git
cd ledger-scrolls

# Install dependencies
pip install requests

# Run the viewer
python viewer.py
```

### Viewer Features

- ✅ **GUI with demo buttons** for Hosky, Bible, BTC Whitepaper
- ✅ **Blockfrost integration** for fetches (enter API key when prompted)
- ✅ **Safe file saving** to `~/Downloads/LedgerScrolls/` to avoid permission issues
- ✅ **Progress explanations** during reconstruction
- ✅ **Hash verification** for integrity checking
- ✅ **Custom scroll input** for viewing any scroll by parameters

### Configuration

**Blockfrost API Key:**
The viewer requires a Blockfrost API key for querying the Cardano blockchain.

1. Get a free API key at [blockfrost.io](https://blockfrost.io)
2. Enter it in the viewer GUI when prompted
3. The key is saved locally for convenience

### Usage

**Quick start with demos:**
1. Launch `python viewer.py`
2. Click "Load Hosky PNG" for a fast standard scroll demo
3. Click "Load Bible" or "Load Bitcoin Whitepaper" for legacy demos

**View custom scrolls:**
1. Click "Custom Scroll" button
2. Select scroll type (Standard or Legacy)
3. Enter required parameters
4. Click "Fetch Scroll"

### Local-Node Mode (Planned v2)

Future versions will support direct queries to your local Cardano node:

```bash
# Set node socket path
export CARDANO_NODE_SOCKET_PATH=/opt/cardano/cnode/sockets/node.socket

# Run in local mode
python viewer.py --local-node
```

**Benefits of local-node mode:**
- No API key required
- No rate limits
- No third-party dependencies
- True local-first operation

### Current Mode: Blockfrost (Default)

The current viewer uses Blockfrost API for convenience:

```bash
python viewer.py
# Enter Blockfrost key in GUI
```

> **Long-term direction:** Full local-node support for everything (standard + legacy metadata via CLI queries). Blockfrost as optional fallback.

### Known Issues

- **Legacy page fetching:** Some scrolls may use field variations (`payload` vs `seg` vs `segments`). The viewer attempts to handle common variations.
- **Large files:** Very large legacy scrolls may take time to fetch all pages.
- **Network errors:** Retry logic is built-in but temporary Blockfrost outages may occur.

**Contribute fixes via GitHub!** Pull requests welcome.

---

## Developer Guide: Create Your Own Scroll

### Publishing a Standard Scroll

**Recommended for:** Files under ~16KB (or ~8KB compressed with gzip)

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

7. **Create registry entry**
   ```json
   {
     "id": "my-scroll",
     "title": "My Custom Scroll",
     "type": "utxo_datum_bytes_v1",
     "lock_address": "addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn",
     "lock_txin": "YOUR_TX_HASH#0",
     "content_type": "image/png",
     "codec": "gzip",
     "sha256": "YOUR_SHA256_HASH"
   }
   ```

### Publishing a Legacy Scroll

**Recommended for:** Large files (>16KB) - though consider IPFS + standard pointer hybrid for new projects

**Steps:**

1. **Split file into pages**
   - Divide file into chunks (e.g., 32 segments of 64 bytes each per page)
   - Each segment becomes a hex string in the `payload` array

2. **Mint page NFTs**
   - Create one NFT per page with metadata containing segments
   - Follow CIP-25 metadata standard

3. **Mint manifest NFT**
   - Create manifest with reconstruction instructions
   - Include hashes, codec, page count

4. **Create registry entry**
   ```json
   {
     "id": "my-large-scroll",
     "title": "My Large Document",
     "type": "cip25_pages_v1",
     "policy_id": "YOUR_POLICY_ID",
     "manifest_tx_hash": "MANIFEST_TX_HASH",
     "manifest_slot": "SLOT_NUMBER",
     "codec": "gzip",
     "content_type": "text/html",
     "segments_per_page": 32
   }
   ```

### Running Your Own Registry

**Why run your own registry:**
- Full control over listed scrolls
- No dependency on public registry availability
- Can theme/curate for specific use cases

**Steps:**

1. **Mint registry NFT**
   ```bash
   # Create unique policy for your registry
   # Mint asset named "LS_REGISTRY" or custom name
   ```

2. **Create registry JSON**
   ```json
   {
     "spec": "ledger-scrolls-registry-v2",
     "version": 2,
     "updated": "2026-01-21T00:00:00Z",
     "scrolls": [
       // Your scroll entries
     ]
   }
   ```

3. **Compress registry**
   ```bash
   gzip -c registry.json > registry.json.gz
   xxd -p registry.json.gz | tr -d '\n' > registry.hex
   ```

4. **Create registry UTxO**
   - Lock UTxO at known address
   - Include registry NFT
   - Add inline datum with compressed JSON

5. **Distribute pointer**
   - Share registry address and asset name
   - Document in viewer configuration

### Extending the Viewer

**Areas for contribution:**

1. **Local-node support**
   - Add subprocess calls to `cardano-cli`
   - Parse `query utxo` output
   - Parse `query tx` output for legacy metadata

2. **Improved legacy parser**
   - Handle more metadata field variations
   - Add auto-detection for page naming schemes
   - Better error messages for failed reconstructions

3. **UI/UX improvements**
   - Dark mode toggle
   - Better progress visualization
   - Drag-and-drop custom scroll parameters

4. **Advanced features**
   - Batch downloading multiple scrolls
   - Scroll comparison tools
   - Hash verification automation

**How to contribute:**
1. Fork the repository
2. Create a feature branch
3. Submit pull request with clear description
4. Include tests if applicable

---

## Philosophy

Ledger Scrolls is built on these core principles:

- ✅ **Open standard** — Anyone can implement, no gatekeepers
- ✅ **Permissionless** — No approval needed to publish or read
- ✅ **Non-custodial** — You control your data and keys
- ✅ **Permanently locked** — Data that cannot be deleted or modified

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

### Use Cases

- 📜 **Permanent documents** — Historical records, manifestos, declarations
- 🖼️ **NFT metadata** — Store image/metadata without IPFS dependency
- ⚙️ **Configuration files** — Immutable configs for dApps
- 📝 **Censorship-resistant publishing** — Unstoppable text/documents
- 🔐 **Proof of existence** — Timestamp + hash verification
- 📚 **Digital libraries** — Collections that cannot be erased

---

## FAQ

### Q: How much does it cost to publish a scroll?

**A:** Only the Cardano transaction fee (typically 0.17-0.5 ADA depending on size). There are no ongoing hosting costs.

### Q: What's the maximum file size?

**A:** 
- **Standard scrolls:** ~16KB uncompressed or ~8KB compressed (datum size limit)
- **Legacy scrolls:** Theoretically unlimited (split into pages), but consider IPFS for very large files

### Q: Can scrolls be deleted or modified?

**A:** No. Once locked on-chain, they are permanent and immutable. This is by design.

### Q: Do I need to run a Cardano node?

**A:** Currently, no (Blockfrost API is used). Future versions will support local node queries for true decentralization.

### Q: What happens if Blockfrost goes down?

**A:** Your data is still on-chain. You can query directly with `cardano-cli` or wait for Blockfrost to return. Local-node mode (coming soon) eliminates this dependency.


---

## Roadmap

### Current (v1.0)
- ✅ Standard scroll specification (locked UTxO + inline datum)
- ✅ Legacy scroll specification (pages + manifest NFTs)
- ✅ Registry specification v2
- ✅ Python viewer with Blockfrost integration
- ✅ Demo scrolls (Hosky, Bible, Bitcoin Whitepaper)

### Near-term (v1.5)
- 🔄 Local node support via `cardano-cli` queries
- 🔄 Improved error handling and retry logic
- 🔄 Better legacy metadata parser (handle more variations)
- 🔄 CLI tool for scroll creation
- 🔄 Documentation site

### Mid-term (v2.0)
- 📋 Web-based viewer (no installation required)
- 📋 Scroll creation GUI tool
- 📋 IPFS hybrid mode (pointer on-chain, data off-chain)
- 📋 Multi-chain support (other UTXO blockchains)
- 📋 Enhanced registry management tools

### Long-term (v3.0)
- 💡 Smart contract-gated scrolls
- 💡 Decentralized registry discovery
- 💡 Scroll collections and galleries
- 💡 Integration with popular Cardano wallets
- 💡 Mobile apps (iOS/Android)

---

## Contributing

We welcome contributions! Areas where you can help:

1. **Code contributions**
   - Local node integration
   - Legacy metadata parser improvements
   - Bug fixes and optimizations

2. **Documentation**
   - Tutorials and guides
   - API documentation
   - Translation to other languages

3. **Testing**
   - Test with different scrolls
   - Report bugs and edge cases
   - Platform-specific testing (Windows/Mac/Linux)

4. **Community**
   - Share your scrolls
   - Write blog posts or tutorials
   - Help others in discussions

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

## License

MIT License - See LICENSE file for details

---

## Acknowledgments

Built with ❤️ by [@BEACNpool](https://x.com/BEACNpool)

**"In the digital age, true knowledge must be unstoppable."**
