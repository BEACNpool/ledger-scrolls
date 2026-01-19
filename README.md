# Updated Ledger-Scrolls Repo Based on New README

Based on my analysis of the GitHub repo at https://github.com/BEACNpool/ledger-scrolls, the current implementation relies on drivers (Oura for P2P streaming from IOHK relays, Ogmios for WebSocket queries to a local node, and planned Mithril) to fetch and reconstruct data without centralized APIs like Blockfrost (though Blockfrost can be added as an option per your request). The current code in src/ includes driver-specific files (oura_driver.py, ogmios_driver.py), a beacon_protocol.py for protocol logic, viewer.py for reconstruction, main.py as entrypoint, and hailo_ai.py (possibly for AI-related features, but not core).

To update to the new README's registry/manifest system:
- Shift from streaming/scanning to pointer-based lookups: query registry UTxO via cardano-cli or Ogmios for datum, then resolve manifest (using tx hash to get metadata), then fetch page NFTs' metadata.
- Since cardano-cli can't fetch historical tx metadata directly, I'll use Ogmios for local node queries (as in current repo) for main path, and add Blockfrost as an option for fallback or no-local-node mode. This allows connecting to IOHK topology via relays (for Oura/Ogmios) without full indexing.
- Prompt for local node vs Blockfrost in UI/CLI.
- Keep options for custom registries, local nodes, and Blockfrost.
- Use subprocess for cardano-cli where possible (e.g., UTxO queries), but use pyogmios or requests for Ogmios/Blockfrost for tx metadata.
- Update to use inline datum for registry, metadata for manifest/pages.
- Add UI (Streamlit) and CLI as per new README philosophy.

I'll provide the updated files below. This is a full overhaul of src/, with new structure. You can replace the current src/ with this, update README.md, and add requirements.

### README.md
(Direct copy of your updated README, as provided.)

```
# Ledger Scrolls 📜
**“A library that cannot burn.”**
Publish + read *permissionless, immutable data* on Cardano—without Blockfrost, without chain indexing, and without asking users to download the entire chain history.
Ledger Scrolls is an open-source **format + viewer** for storing documents on-chain as a set of NFTs (pages) plus a single “manifest” NFT that describes how to reconstruct the original file. A **Registry** UTxO (with an inline datum) acts like a “DNS pointer” that tells the viewer what Scrolls exist and how to find their manifests.
This README explains:
- How on-chain data is structured (pages + manifest)
- How the Registry works (zero indexing / single UTxO lookup)
- How a dev creates their own Scroll library and points Ledger Scrolls to it
- How the viewer uses a local node socket (no centralized APIs)
- How dev choices affect the viewer (naming, segmentation, hashes, etc.)
- How to build an option-based interface (not “CLI-only”)
---
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
---
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
- **1 address query** (manifest holder address) *or* **1 tx-in query** (if you store txhash#ix)
- **N page fetches** (direct asset lookups, not scans)
---
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
- `codec`: gzip, raw text, etc.
- Hashes of the whole file (`sha_gz`, `sha_html`, etc.)
- Content type (`text/html`, `text/plain`, etc.)
- Page count, segment sizes, etc.
The viewer reads the **manifest first**, then fetches every page in order, verifies, and reconstructs.
---
## The Registry (the “DNS” for Scrolls)
The Registry is a single on-chain “directory” that tells Ledger Scrolls what Scrolls exist.
It is implemented as:
- A **registry NFT** (e.g., `LS_REGISTRY`) minted under a short-lived policy
- Locked at a known **Registry address**
- The UTxO holding that NFT has an **inline datum** with a gzipped JSON object:
  - This JSON lists Scrolls and their manifest pointers
### Why inline datum instead of metadata?
- Metadata has strict size constraints (notably text strings <= 64 bytes)
- Inline datum is better for larger structured payloads
- Datum is read directly from `query utxo` output
### Registry example (current live registry)
- Registry policy id: `895cbbe0e284b60660ed681e389329483d5ca94677cbb583f3124062`
- Registry asset name hex: `4c535f5245474953545259` (ASCII `LS_REGISTRY`)
- Registry address:
  `addr1q9x84f458uyf3k23sr7qfalg3mw2hl0nvv4navps2r7vq69esnxrheg9tfpr8sdyfzpr8jch5p538xjynz78lql9wm6qpl6qxy`
- The UTxO with the NFT holds `inlineDatum.bytes` which is gzipped JSON.
---
## How the viewer works (high-level)
### Step 1 — Connect to a local node via socket
Ledger Scrolls uses `cardano-cli` against your **local node** (no Blockfrost).
Your node exposes a UNIX socket file, e.g.:
- `/opt/cardano/cnode/sockets/node.socket`
You set:
```bash
export CARDANO_NODE_SOCKET_PATH=/opt/cardano/cnode/sockets/node.socket
```
### Step 2 — Read the registry in one query
The viewer:
1. queries the registry address UTxO set
2. finds the UTxO containing the registry NFT (policy + asset name hex)
3. extracts `.inlineDatum.bytes` (hex)
4. gunzips + JSON parses it
That produces a list of Scrolls the viewer can display in a menu.
### Step 3 — Resolve the manifest pointer (without scanning)
The registry entry for each Scroll includes the manifest identity:
* `policy_id`
* `manifest_asset_name_hex`
* `manifest_asset_id`
* and optionally `manifest_tx_hash`, `manifest_slot`
**Important design note:**
To make manifest resolution *fully deterministic with zero scanning*, you should include **one of**:
* `manifest_utxo`: `"txhash#ix"` (best)
* OR `manifest_address`: `"addr..."` where the manifest is kept
* OR a “manifest anchor address” convention used by that Scroll library
The demo Scrolls are already known and resolvable by convention (and can be made even cleaner by adding `manifest_utxo` in a future registry schema revision). For now, we keep the registry “as-is” and prove the core idea: the registry itself is non-indexed and trivially readable.
### Step 4 — Fetch pages + reconstruct
Once the viewer knows the manifest, it:
1. reads page asset names in order
2. fetches each page payload from chain
3. verifies hashes
4. concatenates bytes
5. applies codec (`gunzip`, etc.)
6. outputs final content (HTML file, text file, etc.)
---
## Why this avoids indexing the entire chain
Chain indexing is required when you only know something vague like:
* “Find all NFTs with policy X”
* “Find the latest manifest for Y”
* “Search transactions containing …”
Ledger Scrolls avoids that by always giving the viewer **precise pointers**:
* Registry is **at a known address**
* Registry UTxO is **identified by one NFT**
* Datum contains **exact identifiers**
* Manifest contains **exact page identifiers**
Everything becomes direct lookups, not searches.
---
## Creating your own library (dev workflow)
You can create your own Scroll library by following this sequence:
### 1) Choose your format
Decide:
* Content type: `text/plain`, `text/html`, `application/pdf`, etc.
* Codec: `none`, `gzip`, etc.
* Page sizing + segmentation (`seg`)
* Hashing rules: sha256 of gzipped bytes, sha256 of final bytes, etc.
**How this affects the viewer:**
* If you use gzip, the viewer must decompress after concatenation.
* If you split into segments, viewer must reassemble segments per page.
* If you provide hashes, viewer can verify integrity page-by-page and full-file.
### 2) Choose naming conventions (critical!)
Choose:
* Asset prefix for pages (e.g. `MYDOC_P0001`)
* Manifest asset name (e.g. `MYDOC_MANIFEST`)
* Page ordering rules (lexicographic vs numeric fields)
**How this affects the viewer:**
* If your page names don’t sort cleanly, the manifest MUST provide explicit order.
* If you change prefixes, the viewer doesn’t care as long as the manifest lists them.
### 3) Mint page NFTs
Mint page NFTs under a policy you control.
Each page should include:
* index `i`, total `n`
* payload segments containing the bytes
* sha256 of reconstructed page bytes
### 4) Mint the manifest NFT
Mint a single manifest NFT under the same policy describing:
* reconstruction rules
* list of pages in order
* hashes for validation
* content type / codec
### 5) Publish your library in a Registry
You have two models:
#### Model A — Use the “global registry”
You submit a PR to this repo (or publish an update request) so your Scroll appears in the shared registry.
#### Model B — Run your own registry (recommended for personalization)
You create your own registry address + registry NFT, and Ledger Scrolls points to it.
This is how you become your own “library”.
---
## Creating your own Registry (how-to, conceptually)
A registry consists of:
1. A policy (often time-limited) used to mint one registry NFT
2. A registry address that will hold the NFT
3. A datum payload listing Scroll entries
4. A single UTxO at the registry address holding:
   * the registry NFT
   * enough ADA for min-UTxO
   * inline datum with gzipped JSON
**How this affects the viewer:**
* The viewer only needs:
  * registry address
  * registry policy id
  * registry asset name hex
* Once it reads the registry datum, everything else is discovered.
---
## Viewer interface philosophy (option-based, not “CLI-only”)
The backend must be deterministic + scriptable (CLI is good for that),
but the **user experience** should be option-based.
Recommended UX layers:
### A) TUI (Terminal UI) — fast + portable
Use something like:
* Python `textual`
* curses-based menu
Flow:
1. “Connect to node” status indicator
2. “Select registry” (default preloaded)
3. “Select Scroll”
4. “Build / verify / output”
5. “Open output in browser” button
### B) Local web UI (best for mainstream)
Use:
* `streamlit` or a tiny `flask` server that opens a page
* a single “Run” command: `./ledger-scrolls`
Flow:
* dropdown registry
* dropdown scroll
* progress bar (fetch pages, verify hashes, reconstruct)
* output preview + download button
The repo should ship with defaults so a user can run it without knowing Cardano internals.
---
## “How it creates a socket” (what devs need to know)
The “socket” is created by **cardano-node** when it runs.
Typical setup:
* `cardano-node run ... --socket-path /opt/cardano/cnode/sockets/node.socket`
Your viewer does not create the socket — it uses it.
You must ensure:
* `cardano-node` is running and synced enough for queries
* the socket path exists
* the user has permission to read the socket file (group perms often matter)
* `CARDANO_NODE_SOCKET_PATH` is set OR you pass `--socket-path`
---
## Dev choices that matter (and why)
### 1) Metadata vs Datum
* Metadata has strict limits (e.g., text strings max 64 bytes)
* Datum can hold bigger structured payloads and avoids the metadata constraints
  **Registry should be datum-based.** Page/manifest can remain metadata-based.
### 2) “Pointer completeness”
If you want a fully deterministic viewer without any “searching”:
* store `manifest_utxo` (txhash#ix) in the registry, OR
* store `manifest_address` (where the manifest is kept)
If you omit these, you can still operate by convention, but it’s less universal.
### 3) Hash strategy
If you include:
* per-page sha256 → viewer can detect page corruption early
* full-document sha256 → viewer can prove final output integrity
  This directly improves trust in the reconstruction.
### 4) Segment size / count
Segments keep your payload valid and reliable during minting.
Viewer must know:
* how to join segments (simple concatenation)
* whether payload is hex bytes or base64
  Keep it explicit in the manifest spec.
---
## Registry schema (v1) — what the viewer expects
Registry datum JSON (gzipped) contains:
* `spec`: `"ledger-scrolls-registry-v1"`
* `version`: integer
* `updated`: ISO timestamp
* `registry_address`: address holding the registry NFT
* `registry_asset`: `"<policy>.<assetNameHex>"`
* `scrolls`: list of scroll entries
Each scroll entry minimally includes:
* `id`: stable identifier
* `title`
* `policy_id`
* `manifest_asset_name_hex`
* `manifest_asset_id`
* optional: `manifest_tx_hash`, `manifest_slot`
* plus format fields (`codec`, `content_type`, etc.)
---
## Architecture diagram (mental model)
```mermaid
flowchart LR
  User[User clicks "Run Ledger Scrolls"] --> UI[Option-based UI]
  UI --> Viewer[Viewer Engine]
  Viewer -->|cardano-cli query utxo| Node[Local cardano-node socket]
  Node --> Viewer
  Viewer -->|1 query| RegAddr[Registry Address UTxOs]
  RegAddr -->|inline datum bytes| Viewer
  Viewer -->|resolve manifest pointer| Manifest[Manifest NFT]
  Manifest -->|list of pages| Viewer
  Viewer --> Pages[Page NFTs]
  Pages --> Viewer
  Viewer --> Output[Reconstructed Document]
```
---
## Default behavior (what a new user experiences)
1. Install / run
2. Viewer connects to socket
3. Viewer reads the default registry
4. User selects:
   * “Bible (HTML)”
   * “Bitcoin Whitepaper”
5. Viewer reconstructs and produces the output file
No Blockfrost. No indexer. No scanning.
---
## Next recommended improvements (without changing the live registry today)
We are keeping the current registry “as-is” for stability.
For broader dev friendliness, the next evolution is:
* Add `manifest_utxo` OR `manifest_address` per Scroll entry
* Add “registry selection” in UI:
  * Default registry (ships with the repo)
  * Custom registry (user enters address + policy + asset hex)
* Add a “Create your registry” wizard:
  * generates policy
  * mints registry NFT
  * creates datum payload
  * builds/signs/submits the tx
* Add a “Publish a Scroll” wizard:
  * prompts for title, file, codec, page size
  * generates page payloads + manifest JSON
  * guides minting
---
## Philosophy (open source + permissionless)
Ledger Scrolls is intentionally:
* **Open standard**: anyone can publish a Scroll format that a viewer can read
* **Permissionless**: anyone can run a library (their own registry)
* **Non-custodial**: no central service required
* **Non-indexed**: pointer-based lookups only
If you can run a node, you can read the library—forever.
```

### requirements.txt
```
streamlit>=1.29.0
pyogmios # For Ogmios client, pip install pyogmios if available, or use requests for WebSocket
blockfrost-python # For Blockfrost option, pip install blockfrost-python
zlib # Built-in
hashlib # Built-in
json # Built-in
subprocess # Built-in
textual # For TUI if added later
requests # For Blockfrost or Ogmios fallback
hexbytes # pip install hexbytes
```

### ledger-scrolls (entrypoint script, make executable with chmod +x)
```
#!/usr/bin/env python3
import sys
from src.ui import run_ui
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        from src.cli import run_cli
        run_cli()
    else:
        run_ui() # Default to web UI
```

### src/__init__.py
(Empty file)

### src/viewer.py
(This is the core. Uses cardano-cli for UTxO queries, Ogmios for tx metadata if local, Blockfrost as option. Assume pyogmios or requests for Ogmios; install pyogmios if available, or replace with your current ogmios_driver logic. For page fetch, since pages are NFTs, to get metadata, need their mint tx. But if registry or manifest provides tx hashes for pages, we can query them. For simplicity, assume manifest provides page tx hashes or use Blockfrost/Ogmios to query asset info. I've completed the placeholders using Blockfrost for tx metadata as fallback, and assumed Ogmios for local. For IOHK topology, the local node connects to it via config/topology.json in cardano-node.)

```
import os
import subprocess
import json
import zlib
import hashlib
from hexbytes import HexBytes
import requests  # For Blockfrost
from blockfrost import BlockfrostApi, ApiUrls  # For Blockfrost option

# Default registry details from README
DEFAULT_REGISTRY_ADDRESS = "addr1q9x84f458uyf3k23sr7qfalg3mw2hl0nvv4navps2r7vq69esnxrheg9tfpr8sdyfzpr8jch5p538xjynz78lql9wm6qpl6qxy"
DEFAULT_REGISTRY_POLICY_ID = "895cbbe0e284b60660ed681e389329483d5ca94677cbb583f3124062"
DEFAULT_REGISTRY_ASSET_NAME_HEX = "4c535f5245474953545259"  # LS_REGISTRY

# Default scrolls for demo (if registry fetch fails)
DEFAULT_SCROLLS = [
    {
        "id": "bible",
        "title": "Bible (HTML, gzip compressed)",
        "policy_id": "2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0",
        "manifest_tx_hash": "cfda418ddc84888ac39116ffba691a4f90b3232f4c2633cd56f102cfebda0ee4",
        "manifest_slot": "175750638",
        "codec": "gzip",
        "content_type": "text/html",
        "segments_per_page": 32
    },
    {
        "id": "btcwp",
        "title": "Bitcoin Whitepaper",
        "policy_id": "8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1",
        "manifest_tx_hash": "2575347068f77b21cfe8d9c23d9082a68bfe4ef7ba7a96608af90515acbe228f",
        "manifest_slot": "176360887",
        "codec": "none",
        "content_type": "text/plain"
    }
]

class Viewer:
    def __init__(self, mode="local", blockfrost_api_key=None, ogmios_url="ws://localhost:1337"):
        self.mode = mode
        if mode == "blockfrost":
            if not blockfrost_api_key:
                raise ValueError("Blockfrost API key required for blockfrost mode")
            self.blockfrost = BlockfrostApi(project_id=blockfrost_api_key, base_url=ApiUrls.mainnet.value)
        elif mode == "local":
            self.ogmios_url = ogmios_url  # Assume Ogmios running locally with node
            # TODO: Implement pyogmios client or WebSocket connection for queries
        self.socket_path = os.environ.get("CARDANO_NODE_SOCKET_PATH")

    def run_cardano_cli(self, args):
        if not self.socket_path:
            raise ValueError("CARDANO_NODE_SOCKET_PATH not set")
        base_cmd = ["cardano-cli", "query"] + args + ["--mainnet"]
        result = subprocess.run(base_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"cardano-cli error: {result.stderr}")
        return result.stdout

    def fetch_registry_datum(self, registry_address=DEFAULT_REGISTRY_ADDRESS, policy_id=DEFAULT_REGISTRY_POLICY_ID, asset_name_hex=DEFAULT_REGISTRY_ASSET_NAME_HEX):
        # Use cardano-cli for UTxO query (current state)
        utxo_output = self.run_cardano_cli(["utxo", "--address", registry_address, "--output-json"])
        utxo_json = json.loads(utxo_output)
        for tx_in, data in utxo_json.items():
            assets = data.get("value", {}).get("lovelace", {})
            asset_key = f"{policy_id}.{asset_name_hex}"
            if asset_key in assets:
                datum = data.get("inlineDatum")
                if datum:
                    datum_hex = datum["bytes"] if isinstance(datum, dict) else datum
                    datum_bytes = bytes.fromhex(datum_hex)
                    unzipped = zlib.decompress(datum_bytes)
                    return json.loads(unzipped)
        raise ValueError("Registry datum not found")

    def fetch_tx_metadata(self, tx_hash):
        if self.mode == "blockfrost":
            tx = self.blockfrost.transaction_metadata(tx_hash)
            return tx.metadata if tx else {}
        elif self.mode == "local":
            # Implement Ogmios query for tx by hash
            # Example using requests for WebSocket (simplified, use pyogmios for production)
            # Send {"type": "jsonwsp/request", "method": "queryLedgerState/tx", "args": {"tx": tx_hash}}
            # This is placeholder; Ogmios doesn't have direct tx query, may need chain sync or extension
            raise NotImplementedError("Ogmios tx query to be implemented using WebSocket")
        raise ValueError("Invalid mode")

    def fetch_manifest(self, scroll):
        tx_hash = scroll["manifest_tx_hash"]
        metadata = self.fetch_tx_metadata(tx_hash)
        # Assume manifest is under a specific label or policy key in metadata
        manifest_label = "721"  # Common for NFT metadata
        manifest = metadata.get(manifest_label, {}).get(scroll["policy_id"], {})
        return manifest

    def fetch_page(self, policy_id, asset_name_hex, page_tx_hash=None):
        if page_tx_hash:
            metadata = self.fetch_tx_metadata(page_tx_hash)
            page_label = "721"
            page_data = metadata.get(page_label, {}).get(policy_id, {}).get(asset_name_hex, {})
            return page_data
        else:
            # If no tx hash, would need to search asset, but to avoid indexing, assume tx provided or use Blockfrost asset query
            if self.mode == "blockfrost":
                asset_id = f"{policy_id}{asset_name_hex}"
                asset = self.blockfrost.asset(asset_id)
                mint_tx = asset.mint_tx_hash if asset else None
                if mint_tx:
                    return self.fetch_tx_metadata(mint_tx).get("721", {}).get(policy_id, {}).get(asset_name_hex, {})
            raise ValueError("Page tx hash required for local mode")

    def reconstruct_scroll(self, manifest, policy_id, page_tx_hashes=None):
        pages = manifest.get("pages", [])  # List of asset_name_hex
        full_bytes = b""
        for i, asset_hex in enumerate(pages):
            page_tx = page_tx_hashes[i] if page_tx_hashes else None
            page_data = self.fetch_page(policy_id, asset_hex, page_tx)
            payload = page_data.get("payload", [])
            page_bytes = b"".join(bytes.fromhex(seg) for seg in payload)
            # Verify sha
            if "sha" in page_data:
                if hashlib.sha256(page_bytes).hexdigest() != page_data["sha"]:
                    raise ValueError(f"Page {i} hash mismatch")
            full_bytes += page_bytes
        # Apply codec
        codec = manifest.get("codec", "none")
        if codec == "gzip":
            full_bytes = zlib.decompress(full_bytes)
        # Verify full sha
        if "sha" in manifest:
            if hashlib.sha256(full_bytes).hexdigest() != manifest["sha"]:
                raise ValueError("Full hash mismatch")
        return full_bytes, manifest.get("content_type", "text/plain")

def get_scrolls(use_default=True, **kwargs):
    viewer = Viewer(**kwargs)
    if use_default:
        return DEFAULT_SCROLLS
    return viewer.fetch_registry_datum().get("scrolls", [])

def process_scroll(scroll, **kwargs):
    viewer = Viewer(**kwargs)
    manifest = viewer.fetch_manifest(scroll)
    # Assume manifest has page_tx_hashes if needed; otherwise, use mint tx lookup via Blockfrost
    page_tx_hashes = manifest.get("page_tx_hashes", None)  # Optional field
    content, content_type = viewer.reconstruct_scroll(manifest, scroll["policy_id"], page_tx_hashes)
    return content, content_type
```

(Note: For full local mode without Blockfrost, implement Ogmios to fetch tx by hash. Ogmios can use 'findIntersect' and 'nextBlock' to get to the slot/tx, but it's complex for specific tx. If manifest_utxo is provided, query utxo --tx-in for datum if manifest uses datum instead of metadata. For now, Blockfrost is fallback. Update registry schema to include page mint tx hashes if needed.)

### src/ui.py
(Streamlit UI, with mode selection for local/Blockfrost.)

```
import streamlit as st
from src.viewer import get_scrolls, process_scroll, DEFAULT_SCROLLS

def run_ui():
    st.title("Ledger Scrolls Viewer")

    mode = st.selectbox("Connection Mode", ["local", "blockfrost"])
    blockfrost_key = None
    if mode == "blockfrost":
        blockfrost_key = st.text_input("Blockfrost API Key", type="password")
    ogmios_url = st.text_input("Ogmios URL (for local)", "ws://localhost:1337") if mode == "local" else None

    socket_path = os.environ.get("CARDANO_NODE_SOCKET_PATH", "Not set")
    st.info(f"Node Socket: {socket_path}")

    use_default = st.checkbox("Use default registry", value=True)
    try:
        scrolls = get_scrolls(use_default, mode=mode, blockfrost_api_key=blockfrost_key, ogmios_url=ogmios_url)
    except Exception as e:
        st.error(f"Error fetching scrolls: {str(e)}")
        scrolls = DEFAULT_SCROLLS

    scroll_titles = [s["title"] for s in scrolls]
    selected_title = st.selectbox("Choose Scroll", scroll_titles)
    selected_scroll = next(s for s in scrolls if s["title"] == selected_title)

    if st.button("Build and Reconstruct"):
        with st.spinner("Fetching and reconstructing..."):
            try:
                content, content_type = process_scroll(selected_scroll, mode=mode, blockfrost_api_key=blockfrost_key, ogmios_url=ogmios_url)
                output_file = f"{selected_title.replace(' ', '_')}.{ 'html' if 'html' in content_type else 'txt' }"
                with open(output_file, "wb") as f:
                    f.write(content)
                st.success(f"Output saved to {output_file}")

                if "html" in content_type:
                    st.markdown(content.decode('utf-8'), unsafe_allow_html=True)
                else:
                    st.text_area("Preview", content.decode('utf-8'))

                with open(output_file, "rb") as f:
                    st.download_button("Download", data=f, file_name=output_file)
            except Exception as e:
                st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    run_ui()
```

### src/cli.py
(CLI with mode option.)

```
import argparse
from src.viewer import get_scrolls, process_scroll

def run_cli():
    parser = argparse.ArgumentParser(description="Ledger Scrolls CLI")
    parser.add_argument("--mode", default="local", choices=["local", "blockfrost"], help="Connection mode")
    parser.add_argument("--blockfrost-key", type=str, help="Blockfrost API key if mode=blockfrost")
    parser.add_argument("--ogmios-url", type=str, default="ws://localhost:1337", help="Ogmios URL if mode=local")
    parser.add_argument("--default", action="store_true", help="Use default registry")
    parser.add_argument("--scroll", type=str, help="Scroll title to reconstruct")
    parser.add_argument("--output", type=str, default="output", help="Output file prefix")
    args = parser.parse_args()

    kwargs = {"mode": args.mode, "blockfrost_api_key": args.blockfrost_key, "ogmios_url": args.ogmios_url}
    scrolls = get_scrolls(args.default, **kwargs)
    if args.scroll:
        selected = next((s for s in scrolls if s["title"] == args.scroll), None)
        if not selected:
            print("Scroll not found")
            return
        content, content_type = process_scroll(selected, **kwargs)
        ext = "html" if "html" in content_type else "txt"
        output_file = f"{args.output}.{ext}"
        with open(output_file, "wb") as f:
            f.write(content)
        print(f"Saved to {output_file}")
    else:
        print("Available scrolls:")
        for s in scrolls:
            print(s["title"])

if __name__ == "__main__":
    run_cli()
```
