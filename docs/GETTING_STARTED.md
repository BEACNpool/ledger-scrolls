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
   - Minimum: ~3 ADA for a Standard Scroll, ~10+ ADA for Legacy Scrolls

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

### Standard Scroll (LS-LOCK v1)
**Use when:**
- File is under ~16KB
- You want the simplest approach
- Content is text, small image, or short document

**Cost:** ~2-5 ADA (locked in the UTxO forever)

**Permanence:** The UTxO is locked by an always-fail script — literally impossible to spend.

### Legacy Scroll (LS-PAGES v1)
**Use when:**
- File is larger than 16KB
- You're inscribing a multi-page document
- You want NFTs that can be held in a wallet

**Cost:** ~2-3 ADA per page + policy registration

**Permanence:** Time-locked minting policy ensures no new pages can be added after deadline.

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

## Quick Mint (Legacy Scroll)

```bash
# 1. Navigate to scripts
cd scripts

# 2. Make executable
chmod +x mint-legacy-scroll.sh

# 3. Mint your scroll
./mint-legacy-scroll.sh \
    /path/to/large-document.pdf \
    /path/to/payment.skey \
    /path/to/payment.addr \
    --policy-deadline "2024-12-31T23:59:59Z"
```

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

## Adding to the Viewer

Once minted, add your scroll to `js/scrolls.js`:

```javascript
// Standard Scroll
{
    id: 'my-scroll',
    title: 'My Scroll Title',
    description: 'What this scroll contains',
    icon: '📜',
    category: 'documents',
    type: SCROLL_TYPES.STANDARD,
    pointer: {
        lock_address: 'addr1w...',
        lock_txin: 'txhash#0',
        content_type: 'text/plain',
        codec: 'none',  // or 'gzip'
        sha256: '...'
    }
}

// Legacy Scroll
{
    id: 'my-legacy-scroll',
    title: 'My Large Document',
    description: 'A multi-page document',
    icon: '📖',
    category: 'documents',
    type: SCROLL_TYPES.LEGACY,
    pointer: {
        policy_id: 'abc123...',
        content_type: 'application/pdf',
        codec: 'gzip'
    },
    metadata: { pages: 50 }
}
```

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

- 📖 [Standard Scrolls Guide](STANDARD_SCROLLS.md) — Deep dive into LS-LOCK v1
- 📖 [Legacy Scrolls Guide](LEGACY_SCROLLS.md) — Deep dive into LS-PAGES v1
- 📖 [Examples](EXAMPLES.md) — Learn from real minted scrolls

---

*Ready to make something permanent? Let's go.*
