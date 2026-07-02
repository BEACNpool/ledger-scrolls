# Getting Started with Ledger Scrolls

This guide will help you set up everything you need to create your own permanent scrolls on Cardano.

---

## Prerequisites

### Required

1. **cardano-cli** (v8.0+)
   - The official Cardano command-line interface
   - [Installation guide](https://developers.cardano.org/docs/get-started/installing-cardano-node/)

2. **A running Cardano node** (fully synced to mainnet)
   - Or access to a node via SSH

3. **A funded wallet**
   - Payment signing key (`.skey`)
   - Payment address with ADA
   - Minimum: ~3 ADA for a Standard Scroll; for a Chain Scroll budget ~0.06 ADA/KB
     of file (e.g. a 500 KB clip ≈ ~30 ADA, nothing locked)

4. **Basic command-line knowledge**
   - Comfortable with bash/terminal

### Optional (but recommended)

- **jq** — JSON processing tool
- **xxd** — Hex dump utility (usually pre-installed)
- **sha256sum** — Hash verification (usually pre-installed)

---

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/BEACNpool/ledger-scrolls.git
cd ledger-scrolls
```

### 2. Set Environment Variables

```bash
# Point to your Cardano node socket
export CARDANO_NODE_SOCKET_PATH="/path/to/node.socket"

# Verify connection
cardano-cli query tip --mainnet
```

If you see the current slot and block, you're connected!

### 3. Prepare Your Wallet

You'll need:
- `payment.skey` — Your signing key (keep this secret!)
- `payment.addr` — Your payment address

**Check your balance:**
```bash
cardano-cli query utxo --address $(cat payment.addr) --mainnet
```

---

## Choosing Your Scroll Type

### Standard Scroll (the Standard Scroll format)
**Use when:**
- File is under ~14KB (after gzip)
- You want the simplest approach
- Content is text, a small image, or a short document

**Cost:** ~2-5 ADA (locked in the UTxO forever)

**Permanence:** The UTxO is locked by an always-fail script — literally impossible to spend.

### Chain Scroll — the preferred format for anything larger
**Use when:**
- File is larger than one datum (documents, audio, video, datasets)
- You want the cheapest on-chain storage with nothing locked

**Cost:** ~0.06 ADA/KB, **nothing locked per page** (bare metadata transactions
anchored by a Class-A manifest datum — no NFTs to custody).

**Permanence:** The manifest is a locked always-fail UTxO; pages are immutable
chain history, listed by explicit tx hash. Spec:
[registry/spec/manifest-chain-v2.md](../registry/spec/manifest-chain-v2.md);
tooling in `tools/lschain/`.

### Legacy Scroll (the original NFT-page format / CIP-25) — legacy, read-only
The original large-file format: one CIP-25 NFT per page. Every legacy scroll is
still read this way, but it is **no longer recommended for new scrolls** — it
costs ~6× more than a Chain Scroll and locks ~1.4 ADA in an NFT per page. Reach for
it only if you specifically need wallet-visible per-page NFTs.

---

## Quick Mint (Standard Scroll)

```bash
# 1. Navigate to scripts
cd scripts

# 2. Make executable
chmod +x mint-standard-scroll.sh

# 3. Mint your scroll
./mint-standard-scroll.sh \
    /path/to/your-content.txt \
    /path/to/payment.skey \
    /path/to/payment.addr
```

The script will:
1. Create an always-fail lock script
2. Convert your content to hex
3. Create the inline datum
4. Build, sign, and submit the transaction
5. Output the scroll pointer for the viewer

---

## Quick Mint (Chain Scroll — large files)

For anything bigger than a Standard Scroll, use the `tools/lschain/` pipeline:

```bash
# 1. Prepare: gzip (if it helps), hash, and split into page payloads
python3 tools/lschain/prepare.py /path/to/your-file --out build/

# 2. Mint the page transactions, then build + lock the manifest datum
tools/lschain/mint.sh build/ /path/to/payment.skey /path/to/payment.addr

# 3. Read it back from chain and confirm both hashes BEFORE announcing
cd koios-viewer && python3 -m lsview reconstruct-chain --txin <MANIFEST_TX>#0 --out check.bin
```

The manifest records the content type, codec, decoded/encoded hashes, and the
ordered page tx hashes — reconstruction is one manifest query plus a batched
`tx_metadata` lookup. Full write algorithm:
[registry/spec/manifest-chain-v2.md](../registry/spec/manifest-chain-v2.md).

> **Legacy CIP-25 pages:** to read or maintain an older page-based scroll, see
> `docs/LEGACY_SCROLLS.md`. Not recommended for new scrolls.

---

## Verifying Your Scroll

After minting, verify it exists:

```bash
# For Standard Scrolls
cardano-cli query utxo --address <lock_address> --mainnet

# For Legacy Scrolls
# Check your policy on pool.pm or cardanoscan
```

---

## Register Your Scroll

Once minted and verified, make it findable: write a **registry entry** with
your pointer and hash (the canonical form — see
[registry/spec/format.md](../registry/spec/format.md)):

```json
{
  "name": "my-scroll",
  "pointer": { "kind": "utxo-inline-datum-bytes-v1", "txHash": "…", "txIx": 0 },
  "contentType": "text/plain; charset=utf-8",
  "codec": "none",
  "sha256": "…",
  "description": "…"
}
```

For Chain Scroll scrolls the pointer is
`{ "kind": "manifest-chain-v2", "txHash": "<manifest tx>", "txIx": 0 }`.

The registry is **forkable by design**: open a PR adding your entry (and your
`receipts.json`) to this repo, or run your own registry head — see
[registry/](../registry/).

---

## Troubleshooting

### "Node socket not found"
Make sure `CARDANO_NODE_SOCKET_PATH` points to a valid socket:
```bash
ls -la $CARDANO_NODE_SOCKET_PATH
```

### "Insufficient funds"
Check your UTxOs:
```bash
cardano-cli query utxo --address $(cat payment.addr) --mainnet
```

### "Transaction failed"
- Check the node is fully synced: `cardano-cli query tip --mainnet`
- Verify your keys match your address
- Ensure you have enough ADA (including fees)

---

## Next Steps

- 🚀 [Your First Scroll](YOUR_FIRST_SCROLL.md) — the 10-minute creator quickstart
- 📖 [Creating Scrolls](CREATING_SCROLLS.md) — best practices by media type
- 📖 [Standard Scrolls Guide](STANDARD_SCROLLS.md) — Deep dive into the Standard Scroll format
- 📖 [Chain Scroll spec](../registry/spec/manifest-chain-v2.md) — large-file format (preferred)
- 📖 [Legacy Scrolls Guide](LEGACY_SCROLLS.md) — the original NFT-page format (legacy / read-only)
- 📖 [Examples](EXAMPLES.md) — Learn from real minted scrolls

---

*Ready to make something permanent? Let's go.*
