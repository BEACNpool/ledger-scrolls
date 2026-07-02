# Standard Scrolls (the Standard Scroll format)

> Choosing what and how to publish? Start with the per-media-type guide:
> [CREATING_SCROLLS.md](CREATING_SCROLLS.md).

Standard Scrolls are the simplest and most elegant way to inscribe permanent content on Cardano. A single locked UTxO contains your entire document, protected by an always-fail script that makes it impossible to ever spend.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    STANDARD SCROLL                          │
├─────────────────────────────────────────────────────────────┤
│  Address: Script address (always-fail)                      │
│  Value:   2-15 ADA (minimum UTxO based on datum size)       │
│  Datum:   Your content encoded as inline datum              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Datum Structure                                     │   │
│  │  {                                                   │   │
│  │    "constructor": 0,                                 │   │
│  │    "fields": [                                       │   │
│  │      { "bytes": "48656c6c6f20576f726c64..." }       │   │
│  │    ]                                                 │   │
│  │  }                                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  🔒 LOCKED FOREVER — No spending key exists                 │
└─────────────────────────────────────────────────────────────┘
```

---

## The Always-Fail Script

The magic of Standard Scrolls is the lock script. It's a Plutus script that **always fails validation**, meaning:

- No one can ever spend the UTxO
- The ADA is locked permanently
- Your content is preserved forever

```json
{
    "type": "PlutusScriptV2",
    "description": "Always fails - Ledger Scrolls permanent lock",
    "cborHex": "4e4d010000332222200510"
}
```

This tiny script (just 11 bytes!) creates an address that accepts funds but can never release them.

---

## Step-by-Step Guide

### 1. Prepare Your Content

```bash
# Your content file
cat > my_scroll.txt << 'EOF'
This message will exist on Cardano forever.
No one can delete it. No one can modify it.
It will outlive us all.
EOF

# Check the size
wc -c my_scroll.txt
# Output: 123 my_scroll.txt
```

**Size limits:**
- Recommended: Up to 16KB
- Maximum: ~64KB (but expensive)
- For larger files, use Legacy Scrolls

### 2. Create the Lock Script

```bash
cat > always-fail.plutus << 'EOF'
{
    "type": "PlutusScriptV2",
    "description": "Always fails - Ledger Scrolls permanent lock",
    "cborHex": "4e4d010000332222200510"
}
EOF
```

### 3. Get the Lock Address

```bash
LOCK_ADDR=$(cardano-cli address build \
    --payment-script-file always-fail.plutus \
    --mainnet)

echo $LOCK_ADDR
# addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn
```

### 4. Convert Content to Hex

```bash
CONTENT_HEX=$(xxd -p my_scroll.txt | tr -d '\n')
echo $CONTENT_HEX
```

### 5. Calculate SHA256 Hash

```bash
SHA256=$(sha256sum my_scroll.txt | cut -d' ' -f1)
echo $SHA256
```

### 6. Create the Datum

```bash
cat > datum.json << EOF
{
    "constructor": 0,
    "fields": [
        {
            "bytes": "$CONTENT_HEX"
        }
    ]
}
EOF
```

### 7. Query Your UTxOs

```bash
cardano-cli query utxo \
    --address $(cat payment.addr) \
    --mainnet
```

Pick a UTxO with enough ADA (minimum 3 ADA recommended).

### 8. Build the Transaction

```bash
# Calculate minimum ADA for the datum
# Rule of thumb: ~5.5 ADA per 1KB of content

cardano-cli transaction build \
    --mainnet \
    --tx-in "YOUR_UTXO_HASH#INDEX" \
    --tx-out "$LOCK_ADDR+2000000" \
    --tx-out-inline-datum-file datum.json \
    --change-address $(cat payment.addr) \
    --out-file tx.raw
```

### 9. Sign the Transaction

```bash
cardano-cli transaction sign \
    --tx-body-file tx.raw \
    --signing-key-file payment.skey \
    --mainnet \
    --out-file tx.signed
```

### 10. Submit!

```bash
cardano-cli transaction submit \
    --mainnet \
    --tx-file tx.signed
```

### 11. Get Your Scroll Pointer

```bash
TX_HASH=$(cardano-cli transaction txid --tx-file tx.signed)
echo "Lock Address: $LOCK_ADDR"
echo "Lock TxIn: ${TX_HASH}#0"
echo "SHA256: $SHA256"
```

---

## Compression (Optional)

For larger content, compress with gzip:

```bash
# Compress
gzip -c my_scroll.txt > my_scroll.txt.gz

# Convert compressed file to hex
CONTENT_HEX=$(xxd -p my_scroll.txt.gz | tr -d '\n')

# When adding to viewer, set codec: 'gzip'
```

---

## Cost Estimation

| Content Size | Approximate Cost |
|-------------|------------------|
| 1 KB | ~2-3 ADA |
| 5 KB | ~5-6 ADA |
| 10 KB | ~8-10 ADA |
| 16 KB | ~12-15 ADA |

The ADA is locked forever — think of it as paying for eternal storage.

---

## Register Your Scroll

Make it findable with a **registry entry** (canonical pointer kinds — see
[registry/spec/format.md](../registry/spec/format.md)); PR it into this
repo's registry or run your own forkable registry head:

```json
{
  "name": "my-scroll",
  "pointer": { "kind": "utxo-inline-datum-bytes-v1", "txHash": "…", "txIx": 0 },
  "contentType": "text/plain; charset=utf-8",
  "codec": "none",
  "sha256": "…",
  "description": "A message locked on Cardano forever"
}
```

---

## Content Types

| Type | content_type |
|------|-------------|
| Plain text | `text/plain; charset=utf-8` |
| HTML | `text/html` |
| JSON | `application/json` |
| PNG image | `image/png` |
| JPEG image | `image/jpeg` |
| PDF | `application/pdf` |

---

## Example: The Architect's Scroll

The actual registry entry for The Architect's Scroll, minted January 2026:

```json
{
  "name": "architects-scroll",
  "pointer": {
    "kind": "utxo-inline-datum-bytes-v1",
    "txHash": "076d6800d8ccafbaa31c32a6e23eecfc84f7d1e35c31a9128ec53736d5395747",
    "txIx": 0
  },
  "contentType": "text/plain; charset=utf-8",
  "codec": "none",
  "sha256": "531a1eba80b297f8822b1505d480bb1c7f1bad2878ab29d8be01ba0e1fc67e12",
  "description": "A hidden tribute, locked forever (15 ADA)"
}
```

---

## Security Considerations

1. **Content is public** — Anyone can read your scroll
2. **Permanent means permanent** — No undo, no delete
3. **ADA is locked forever** — Consider the cost
4. **Verify before minting** — Double-check your content
5. **Keep your hash** — SHA256 proves authenticity

---

## Troubleshooting

**"Minimum UTxO not met"**
- Increase the ADA amount in `--tx-out`
- Larger datums require more ADA

**"Transaction too large"**
- Your content might be too big
- Try compressing with gzip
- Consider using Legacy Scrolls instead

---

*Once minted, your scroll joins the eternal library. Choose your words wisely.*
