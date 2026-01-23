
# Ledger Scrolls 📜

**"A library that cannot burn."**

Ledger Scrolls is an open-source **standard + viewer** for publishing and reading **permissionless, immutable data** on the Cardano blockchain.

## Design Principles

The design goal is simple:

* ✅ **No chain indexing required**
* ✅ **No centralized gatekeepers**
* ✅ **No "download the whole chain history" requirement**
* ✅ **Local-first** (your node + your socket) – fully supported
* ✅ **Forever-readable** as long as the pointer remains valid

---

## Two Storage Standards

Ledger Scrolls supports two storage styles, used together in a **Hybrid Architecture**:

### 1. ✅ Ledger Scrolls Standard (The "Pointer")

**Best for:** Registries, Icons, Manifests, Configurations.

* **Mechanism:** Locked UTxO with Inline Datum.
* **Why:** It lives in the "Hot State" (UTxO set) of every Cardano node. It can be read instantly with **1 query**.
* **Role:** This is the "Card Catalog" of the library.

### 2. 🧾 Legacy Scrolls (The "Content")

**Best for:** Large documents (Bible, Whitepapers), Audio, High-Res Images.

* **Mechanism:** CIP-25 style NFTs (Pages + Manifest).
* **Why:** Unlimited storage capacity using multiple transactions.
* **Role:** These are the "Books" on the shelf.

---

## Core Concept: The Hybrid "Library & Shelf" Model

Most "on-chain data" projects fail because reading requires a massive, centralized indexer (like Blockfrost) to find *where* a token is located.

Ledger Scrolls solves this using a **Hybrid Pointer System**:

1. **The Registry (Standard Scroll):** A lightweight map stored in a Locked UTxO. It tells you *what* exists.
2. **The Location Hint:** The Registry tells you exactly *where* the author keeps the data (e.g., `addr1...library`).
3. **The Content (Legacy Scroll):** The heavy data lives at that specific address.

**The Result:**
Instead of scanning the entire blockchain history for a Policy ID (slow/expensive), the viewer simply asks the local node: *"Give me the UTxOs at Address X."* (fast/free).

---

## Live Demo Scrolls

### 1) ✅ Hosky PNG (Standard Scroll — Lean)

This demo stores a complete PNG **directly in an inline datum** at a **locked UTxO**.

* **Lock address:** `addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn`
* **Locked UTxO (txin):** `728660515c6d9842d9f0ffd273f2b487a4070fd9f4bd5455a42e3a56880389be#0`
* **Datum format:** `inlineDatum.bytes` = hex of the PNG file
* **Immutability proof:** `sha256(hosky.png) == 798e3296...`

### 2) Bible (Legacy Scroll — Hybrid Mode)

Large document demonstration using the legacy pages pattern, pointed to by the Registry.

* **Policy ID:** `2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0`
* **Pages:** 237 NFTs
* **Reconstruction:** `concat_pages + gunzip`
* **Location Hint:** Registry points to the holding address for fast retrieval.

---

## The Registry: "DNS" for Scrolls

The Registry is a single on-chain directory that acts as the "Card Catalog."

### Registry Implementation

* A **registry NFT** (e.g., `LS_REGISTRY`)
* Locked at a known **Registry address**
* The UTxO holding that NFT has an **inline datum** containing **gzipped JSON**.

### Registry Schema v2 (Hybrid Support)

This schema supports both **Standard** (direct retrieval) and **Legacy** (hint-based retrieval) scrolls.

```json
{
  "spec": "ledger-scrolls-registry-v2",
  "version": 2,
  "updated": "2026-01-22T00:00:00Z",
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
      "location_hint": "addr1q9x84f458uyf3k23sr7qfalg3mw2hl0nvv4navps2r7vq69esnxrheg9tfpr8sdyfzpr8jch5p538xjynz78lql9wm6qpl6qxy",
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
      "location_hint": "addr1_author_public_library_address_example",
      "manifest_tx_hash": "2575347068f77b21cfe8d9c23d9082a68bfe4ef7ba7a96608af90515acbe228f",
      "manifest_slot": "176360887",
      "codec": "none",
      "content_type": "text/plain"
    }
  ]
}

```

### How `location_hint` Works

1. **Fast Path:** The Viewer checks the `location_hint` address first. If the NFTs are there, it loads them instantly via local query.
2. **Resilience Path:** If the author moved the NFTs or sold them, the Viewer falls back to scanning the Policy ID (slower, requires indexer), but the data remains found.

---

## Technical Specification: Standard (LS-LOCK v1)

A Standard Scroll stores the file bytes in `inlineDatum.bytes` at a **permanently locked UTxO**.

**Required fields:**

* `txin` — Transaction input `TXHASH#INDEX`
* `lock_address` — The script address holding the UTxO
* `content_type` — MIME type
* `codec` — `none` or `gzip`

**Why "Locked"?**
If the UTxO stays **unspent**, the datum remains in the UTxO set and is fetchable forever without indexing.

---

## Technical Specification: Legacy (LS-PAGES v1)

A Legacy Scroll is stored as **Page NFTs** with `i` index and `payload` segments.

**The simplified reading logic:**

1. Fetch all assets (either from `location_hint` or Policy ID).
2. Filter for NFTs with `payload` and `i` fields.
3. Sort by `i` index.
4. Concatenate payloads.

**Supported payload formats:**

* `[{"bytes": "hex"}, {"bytes": "hex"}]` (CIP-25 style)
* `["hex1", "hex2"]` (direct strings)

---

## Running the Viewer

The viewer is a cross-platform Python GUI app (Windows/Mac/Linux) with **three connection modes**.

### Installation

```bash
git clone https://github.com/BEACNpool/ledger-scrolls.git
cd ledger-scrolls
pip install -r requirements.txt
python viewer.py

```

### Connection Modes

#### 1. 📡 Blockfrost API Mode (Default)

**Best for:** Quick start, no local infrastructure.

* Requires API key from [blockfrost.io](https://blockfrost.io).

#### 2. 🖥️ Local Node Mode (Maximum Sovereignty)

**Best for:** Node operators.

* Queries your local `node.socket`.
* **Note on Hybrid Model:** This mode benefits most from the Registry `location_hint`, allowing large file retrieval without external indexers.

#### 3. ⚡ P2P Lightweight Mode (Experimental)

**Status:** 🚧 Under Development.

* Vision: Connect directly to P2P network without full sync.

---

## Developer Guide: Create Your Own Scroll

### Publishing a Standard Scroll (Small Files)

1. Prepare file (optional gzip).
2. Convert to hex.
3. Send to an "always-fail" script address with **Inline Datum**.
4. Record the `txin`.

### Publishing a Legacy Scroll (Large Files)

1. Mint Page NFTs (CIP-25) with `i` and `payload`.
2. **Crucial Step:** Keep these NFTs at a stable "Library Address."
3. Register that address in the Ledger Scrolls Registry as the `location_hint`.

---

## FAQ

### Q: Why use Standard over Legacy?

**A:** Standard Scrolls live in the "Hot State" (UTxO set). They require **zero dependencies** to read. Use them for your "Pointers" (Registry).

### Q: Why use Legacy over Standard?

**A:** Standard scrolls are limited by transaction size constraints (~16KB). Legacy scrolls can be infinite in size. Use them for your "Content."

### Q: What if I move my Legacy NFTs?

**A:** The `location_hint` in the Registry will become stale. The Viewer will fail the "Fast Path" and switch to the "Slow Path" (scanning the chain for the Policy ID). The data is never lost, just harder to find.

### Q: How much does it cost?

**A:** Only the Cardano transaction fees. No hosting costs.

---

## License & Links

* **License:** MIT
* **GitHub:** [https://github.com/BEACNpool/ledger-scrolls](https://github.com/BEACNpool/ledger-scrolls)
* **Twitter/X:** [@BEACNpool](https://x.com/BEACNpool)

**"In the digital age, true knowledge must be unstoppable."**
