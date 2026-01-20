# Ledger Scrolls 📜
**“A library that cannot burn.”**

Ledger Scrolls is an open-source **standard + viewer** for publishing and reading *permissionless, immutable data* on Cardano.

The design goal is simple:

> **If you can run a Cardano node, you can read the library forever.**  
> No chain indexing. No centralized gatekeepers. No “trust me bro” servers.

---

## What Ledger Scrolls is

Ledger Scrolls defines **how to put files on-chain** and how to **reconstruct them deterministically**.

There are two supported “families” of Scrolls:

### ✅ Ledger-Scrolls Standard (Lean): **Locked UTxO + Inline Datum Bytes**
**Best for:** small/medium binary files (images, icons, proofs, keys, compact documents)

- The file is stored as **raw bytes** in `inlineDatum.bytes` at a **script address**
- The UTxO is intended to be **permanently locked / never spendable**
- Reading it requires only:
  - **one address query**
  - extracting datum bytes
  - writing them back into a file

> This is the leanest possible proof: the exact bytes exist in the ledger, and anyone can recreate the file from a node.

### 🧾 Legacy Scrolls (Large docs): **NFT Pages + Manifest (CIP-25)**
**Best for:** large documents (Bible HTML, long PDFs, multi-megabyte payloads)

- A document is stored as:
  - **many page NFTs** (each holding chunked payload bytes)
  - **one manifest NFT** describing reconstruction
- Reading it is deterministic and pointer-based (no scanning), but the current MVP viewer uses **Blockfrost** to fetch CIP-25 metadata faster.

---

## What exists today (default demo Scrolls)

### 0) Hosky PNG — **Ledger-Scrolls Standard (Lean)**
This is the flagship “Lean Standard” example.

- **Storage:** `inlineDatum.bytes` contains the raw PNG bytes
- **Locked at:** script address (UTxO intended to be permanently unspendable)
- **Proof:** reconstruct `onchain.png` from datum → SHA-256 matches the original PNG

**On-chain pointer (current live):**
- Locked script address:  
  `addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn`
- Locked UTxO (txin):  
  `728660515c6d9842d9f0ffd273f2b487a4070fd9f4bd5455a42e3a56880389be#0`
- File type: `image/png`
- SHA-256 (original == reconstructed):  
  `798e3296d45bb42e7444dbf64e1eb16b02c86a233310407e7d8baf97277f642f`

✅ **How to verify independently (no Blockfrost required)**

```bash
LOCK_ADDR="addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn"
LOCKED_TXIN="728660515c6d9842d9f0ffd273f2b487a4070fd9f4bd5455a42e3a56880389be#0"

cardano-cli query utxo --mainnet --address "$LOCK_ADDR" --out-file locked_utxo_live.json

jq -r --arg k "$LOCKED_TXIN" '.[$k].inlineDatum' locked_utxo_live.json > datum.json

# write datum hex bytes into a real PNG file
jq -r '.bytes' datum.json | tr -d '\n' | xxd -r -p > onchain.png

file onchain.png
sha256sum onchain.png
````

If you also have the original file:

```bash
sha256sum hosky.png onchain.png
```

Matching hashes = cryptographic proof the exact PNG bytes are stored on-chain.

---

### 1) Bible — Original Proof-of-Concept (HTML, gzip compressed)

This is the original “big-document” Scroll, stored across many NFTs.

* Policy: `2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0`
* Manifest tx hash: `cfda418ddc84888ac39116ffba691a4f90b3232f4c2633cd56f102cfebda0ee4`
* Manifest slot: `175750638`
* Reconstruction: `concat_pages + gunzip`
* Pages: `237` (+ 1 manifest = 238 total assets)
* Segments per page payload: `32`

> Each page NFT holds hex payload segments; the manifest defines ordering + hashes.

---

### 2) Bitcoin Whitepaper — Proof-of-Concept (small multi-page Scroll)

* Policy: `8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1`
* Manifest tx hash: `2575347068f77b21cfe8d9c23d9082a68bfe4ef7ba7a96608af90515acbe228f`
* Manifest slot: `176360887`

---

## The key idea: **No indexing** via deterministic pointers

Most on-chain data projects fail because reading requires one of:

* A centralized API (Blockfrost/Koios/etc.)
* A custom indexer scanning the chain
* A full-history node + database queries

Ledger Scrolls avoids that with **pointers**:

1. **Registry pointer**: one UTxO at a known registry address
2. **Manifest pointer** (for NFT-page Scrolls): tells you exactly where reconstruction rules live
3. **Page pointers**: manifest tells you the exact NFT page asset names to fetch

So “find my document somewhere in the blockchain” becomes:

* **1 address query** (registry UTxO)
* **1 pointer lookup** (manifest tx hash or locked txin)
* **N direct fetches** (pages) OR **1 direct datum extraction** (Lean Standard)

---

## The Registry (the “DNS” for Scrolls)

The Registry is a single on-chain “directory” that tells Ledger Scrolls what Scrolls exist.

Implementation (current MVP):

* A **registry NFT** locked at a known **registry address**
* That UTxO contains an **inline datum** where `inlineDatum.bytes` is **compressed JSON**
* The viewer reads it in one query (no scanning) 

Default registry constants in `viewer.py`: 

* Registry address
* Registry policy id
* Registry asset name hex (`LS_REGISTRY`)

---

## On-chain storage formats

### A) Ledger-Scrolls Standard (Lean): `utxo-inline-datum-bytes-v1`

**Goal:** smallest, cleanest, most “node-native” proof.

**Data lives at:**

* `script_address` (ideally always-fails / unspendable)
* `locked_txin` (txhash#index)
* `inlineDatum.bytes` = file bytes (hex)

**Reconstruction:**

* hex → bytes → write file

**Verification:**

* SHA-256 of reconstructed file equals published hash

---

### B) Legacy Large Docs: `gzip-pages-v1` (NFT pages + manifest)

#### Page NFT metadata (typical)

* `spec`: format id (e.g. `gzip-pages-v1`)
* `role`: `page`
* `i`: page index (1-based)
* `n`: total pages
* `seg`: segment count (how many chunks in `payload`)
* `sha`: sha256 of the page’s reconstructed bytes
* `payload`: array of segment strings holding hex bytes

> Why segment? Cardano metadata has size limits. Segments keep minting reliable.

#### Manifest NFT metadata (typical)

* page ordering (asset names)
* codec (`gzip`, `none`, etc.)
* file hashes (`sha_gz`, `sha_html`, etc.)
* content type (`text/html`, `image/png`, etc.)
* counts (pages, segments)

The viewer reads **manifest first**, then fetches each page, verifies, concatenates, and decodes.

---

## How the viewer works (today)

### UI (Streamlit)

`ui.py` provides an option-based interface (preferred over CLI-only). 

```bash
pip install -U streamlit requests
streamlit run ui.py
```

The UI can:

* load scrolls from the on-chain registry (default) 
* reconstruct a selected document
* download the output

### CLI

`cli.py` supports listing and reconstructing scrolls. 

```bash
python cli.py --list
python cli.py --scroll "Bible" --use-blockfrost --blockfrost-key "$BF_KEY" --output bible_out
```

---

## Blockfrost (Legacy / Optional fallback)

**Lean Standard (Hosky PNG):** does **not** need Blockfrost.

**NFT Pages (Bible/BTC):** the current MVP uses Blockfrost to fetch CIP-25 metadata and reconstruct pages.
`viewer.py` currently raises if you try pure-local manifest fetch. 

---

## Registry schema (v1)

This is the current idea (and what the MVP expects conceptually):

```json
{
  "spec": "ledger-scrolls-registry-v1",
  "version": 1,
  "updated": "2026-01-19T00:00:00Z",
  "scrolls": [
    {
      "id": "hosky-png",
      "title": "Hosky PNG (Ledger-Scrolls Standard)",
      "format": "utxo-inline-datum-bytes-v1",
      "locked_address": "addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn",
      "locked_txin": "728660515c6d9842d9f0ffd273f2b487a4070fd9f4bd5455a42e3a56880389be#0",
      "content_type": "image/png",
      "sha256": "798e3296d45bb42e7444dbf64e1eb16b02c86a233310407e7d8baf97277f642f"
    },
    {
      "id": "bible",
      "title": "Bible (HTML, gzip compressed)",
      "format": "gzip-pages-v1",
      "policy_id": "2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0",
      "manifest_tx_hash": "cfda418ddc84888ac39116ffba691a4f90b3232f4c2633cd56f102cfebda0ee4",
      "manifest_slot": "175750638",
      "codec": "gzip",
      "content_type": "text/html",
      "pages_prefix": "BIBLE_P",
      "pages_total": 237,
      "seg": 32
    },
    {
      "id": "bitcoin-whitepaper",
      "title": "Bitcoin Whitepaper",
      "format": "none-pages-v1",
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

## Creating your own library (dev workflow)

Two ways:

### 1) Use the global registry (submit PR)

You mint your Scroll, then submit a PR adding its pointer entry.

### 2) Run your own registry (recommended)

You deploy your own registry NFT + datum directory so your library is self-contained.

---

## The permanence rule (important)

When a Ledger-Scroll is created, the intent is:

> **permanently locked, never spendable.**

For the Lean Standard, use a script address that cannot be spent (e.g., always-fails),
so the UTxO (and datum bytes) remain pinned forever.

---

## Philosophy

* **Open standard**
* **Permissionless**
* **Non-custodial**
* **No indexing**
* **Node-native verification**

Maintained with ❤️ by [@BEACNpool](https://x.com/BEACNpool)
