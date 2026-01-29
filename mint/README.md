# 🔮 Mint the Architect's Scroll

This directory contains everything needed to mint the Architect's Scroll as a permanent Ledger Scroll on Cardano mainnet.

## Files

- `architects_scroll.txt` - The scroll content (Claude's message)
- `mint_architects_scroll.sh` - Automated minting script
- `README.md` - This file

## Prerequisites

1. **cardano-cli** installed and in PATH
2. **cardano-node** running and fully synced to mainnet
3. **Payment keys** with at least 3 ADA (2 ADA locked + fees)
4. `CARDANO_NODE_SOCKET_PATH` environment variable set

## Quick Start

### On your relay node (10.30.0.6):

```bash
# 1. Copy this mint directory to the relay
scp -r mint/ relay:~/

# 2. SSH to relay
ssh relay

# 3. Set socket path (adjust if different)
export CARDANO_NODE_SOCKET_PATH=/opt/cardano/cnode/sockets/node.socket

# 4. Run the minting script
cd ~/mint
./mint_architects_scroll.sh /path/to/payment.skey /path/to/payment.addr
```

## What the Script Does

1. **Creates an always-fail Plutus script** - This ensures the UTxO can never be spent (truly locked forever)
2. **Converts the scroll to hex** - Prepares the content for the datum
3. **Creates an inline datum** - Wraps the hex in proper Plutus data structure
4. **Builds the transaction** - Locks 2 ADA with the scroll datum
5. **Signs and submits** - Makes it permanent on-chain
6. **Outputs the pointer** - Gives you everything needed for scrolls.js

## After Minting

The script will output a JavaScript object you can add to `js/scrolls.js`:

```javascript
{
    id: 'architects-scroll-onchain',
    title: "The Architect's Scroll",
    description: 'A message from Claude...',
    icon: '🔮',
    category: 'vault',
    type: SCROLL_TYPES.STANDARD,
    pointer: {
        lock_address: 'addr1w...',
        lock_txin: 'txhash#0',
        content_type: 'text/plain; charset=utf-8',
        codec: 'none',
        sha256: '...'
    },
    metadata: { ... }
}
```

## Manual Minting (Alternative)

If you prefer to mint manually:

```bash
# 1. Convert scroll to hex
xxd -p architects_scroll.txt | tr -d '\n' > scroll.hex

# 2. Get SHA256
sha256sum architects_scroll.txt

# 3. Create datum.json with the hex
# 4. Build transaction with --tx-out-inline-datum-file
# 5. Sign and submit
```

## Verification

After minting, verify the scroll:

```bash
# Query the lock address
cardano-cli query utxo --address <lock_address> --mainnet

# The UTxO should show with inline datum
```

---

*"In the digital age, true knowledge must be unstoppable."*

🔮 Make it eternal.
