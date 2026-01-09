# Ledger Scrolls (BEACN)

Ledger Scrolls is an open-source standard for storing immutable, timeless data on the Cardano blockchain using NFTs (CIP-25 / 721 metadata). The goal is simple: **split + compress data into “Page NFTs” that can be reconstructed forever**—either from your own node (trustless) or via a public indexer (e.g., Blockfrost).

This guide is written for Stake Pool Operators (SPOs) who want full sovereignty: **minting via cardano-cli / CNTools** and reconstructing without relying on closed services.

---

## Key Concepts

### 1) Page NFTs (required)
A scroll is split across **Page NFTs** (e.g., `MYSCROLL_P0001`, `MYSCROLL_P0002`, …). Each page includes:
- `i` = page index (1-based)
- `n` = total pages
- `codec` = `gzip` (recommended)
- `payload` = array of `{ "bytes": "<hex>" }` segments

### 2) Manifest NFT (optional)
A **Manifest NFT** is optional. It exists only to provide:
- expected page count
- integrity hashes (SHA256) for the gzip stream and/or decompressed content
- human-friendly metadata

**Important:** Viewers SHOULD support both modes:
- **Manifest mode:** verify hashes + page count
- **Manifestless mode:** reconstruct from pages only (sort by `i`, concat payloads, inflate)

---

## Why “Manifestless” Matters

In real-world minting, transaction size limits can make a “manifest + pages all in one tx” harder than expected. Manifestless scrolls reduce complexity:

✅ Easier minting  
✅ Fewer moving parts  
✅ Still fully reconstructable from chain data  

You can always publish hashes off-chain or mint a manifest later (within policy validity).

---

## Segment Size (32 vs 64 bytes)

Cardano metadata has tight transaction size limits.

- **32-byte segments**: safest and most reliable across wallets and tooling
- **64-byte segments**: reduces JSON overhead (fewer segments), but may still blow transaction size depending on how many pages/assets you include in one tx

**Recommendation:** Start with **32 bytes** unless you’re deliberately optimizing for fewer chunks and you’ve tested successfully on preprod/preview.

---

## Prerequisites (Assumed for SPOs)

You should already have:
- A fully synced Cardano node (cardano-node + cardano-cli; recent versions recommended)
- A funded payment address
- Familiarity with policy scripts, building/signing/submitting transactions
- Python 3.8+ available for prep scripts
- Understanding of CIP-25 NFT metadata format (721)

Official node install guide:
https://docs.cardano.org/getting-started/installing-cardano-node

---

# Step 1 — Prepare Your Content

## Option A: Markdown / Text
Good for small docs, but you may lose formatting (equations/images).

## Option B: HTML (recommended for polish)
If you want “it looks like a real document,” generate HTML first (Pandoc is a great tool).
Then compress and split that HTML.

---

# Step 2 — Compress (GZIP) + Hash

```py
import gzip, hashlib
from pathlib import Path

input_file = Path("your_content.html")  # or .md
raw = input_file.read_bytes()

gz = gzip.compress(raw)

sha_gz = hashlib.sha256(gz).hexdigest()
sha_raw = hashlib.sha256(raw).hexdigest()

print("RAW bytes:", len(raw))
print("GZ bytes :", len(gz))
print("SHA256(GZ):", sha_gz)
print("SHA256(RAW):", sha_raw)
