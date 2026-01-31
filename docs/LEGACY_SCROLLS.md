# Legacy Scrolls (LS-PAGES v1)

Legacy Scrolls are designed for large documents that exceed the practical limits of a single UTxO. They use CIP-25 NFTs to store content across multiple "pages," which are concatenated to reconstruct the original document.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    LEGACY SCROLL                            │
├─────────────────────────────────────────────────────────────┤
│  Policy ID: Time-locked minting policy                      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  NFT Page 0                                          │   │
│  │  {                                                   │   │
│  │    "i": 0,                                           │   │
│  │    "payload": ["chunk1", "chunk2", ...]              │   │
│  │  }                                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  NFT Page 1                                          │   │
│  │  {                                                   │   │
│  │    "i": 1,                                           │   │
│  │    "payload": ["chunk1", "chunk2", ...]              │   │
│  │  }                                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  NFT Page N...                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  🔒 Time-locked policy — No new pages after deadline        │
└─────────────────────────────────────────────────────────────┘
```

---

## The Reconstruction Process

1. **Query** all NFTs under the policy ID
2. **Sort** by index (`i` field)
3. **Concatenate** all payload chunks in order
4. **Decompress** if codec is gzip
5. **Render** based on content type

---

## Step-by-Step Guide

### 1. Prepare Your Document

```bash
# Large document
ls -la constitution.pdf
# -rw-r--r-- 1 user user 4823456 Jan 29 constitution.pdf

# Compress it
gzip -c constitution.pdf > constitution.pdf.gz
ls -la constitution.pdf.gz
# -rw-r--r-- 1 user user 1245678 Jan 29 constitution.pdf.gz
```

### 2. Calculate Hash

```bash
# Hash the ORIGINAL file (before compression)
SHA256=$(sha256sum constitution.pdf | cut -d' ' -f1)
echo $SHA256
```

### 3. Split Into Pages

```bash
# Each NFT metadata has a ~16KB limit
# We'll use 14KB chunks to be safe

split -b 14336 constitution.pdf.gz constitution_page_

# This creates:
# constitution_page_aa
# constitution_page_ab
# constitution_page_ac
# ...
```

### 4. Create Time-Locked Policy

The policy must have a deadline after which no more NFTs can be minted:

```bash
# Get current slot
CURRENT_SLOT=$(cardano-cli query tip --mainnet | jq -r '.slot')

# Set deadline 1 hour from now (3600 slots)
DEADLINE_SLOT=$((CURRENT_SLOT + 3600))

# Create policy script
cat > policy.script << EOF
{
  "type": "all",
  "scripts": [
    {
      "type": "sig",
      "keyHash": "$(cardano-cli address key-hash --payment-verification-key-file payment.vkey)"
    },
    {
      "type": "before",
      "slot": $DEADLINE_SLOT
    }
  ]
}
EOF

# Get policy ID
POLICY_ID=$(cardano-cli transaction policyid --script-file policy.script)
echo "Policy ID: $POLICY_ID"
```

### 5. Convert Pages to Metadata

For each page, create CIP-25 compliant metadata:

```bash
# Convert page to hex
PAGE_HEX=$(xxd -p constitution_page_aa | tr -d '\n')

# Split hex into 64-character chunks for CIP-25
# (NFT metadata has string length limits)

# Create metadata for page 0
cat > metadata_page_0.json << EOF
{
  "721": {
    "$POLICY_ID": {
      "ConstitutionPage0": {
        "name": "Constitution Page 0",
        "i": 0,
        "payload": [
          "${PAGE_HEX:0:64}",
          "${PAGE_HEX:64:64}",
          ...
        ]
      }
    }
  }
}
EOF
```

### 6. Mint Each Page

```bash
# For each page, mint an NFT
cardano-cli transaction build \
    --mainnet \
    --tx-in "UTXO#INDEX" \
    --tx-out "$(cat payment.addr)+2000000+1 $POLICY_ID.ConstitutionPage0" \
    --mint "1 $POLICY_ID.ConstitutionPage0" \
    --mint-script-file policy.script \
    --metadata-json-file metadata_page_0.json \
    --invalid-hereafter $DEADLINE_SLOT \
    --change-address $(cat payment.addr) \
    --out-file tx_page_0.raw

cardano-cli transaction sign \
    --tx-body-file tx_page_0.raw \
    --signing-key-file payment.skey \
    --mainnet \
    --out-file tx_page_0.signed

cardano-cli transaction submit \
    --mainnet \
    --tx-file tx_page_0.signed
```

Repeat for each page.

### 7. Verify Completion

After all pages are minted and the deadline passes:

```bash
# Query all NFTs under the policy
# Use blockfrost or koios API
curl "https://cardano-mainnet.blockfrost.io/api/v0/assets/policy/$POLICY_ID" \
    -H "project_id: YOUR_API_KEY"
```

---

## FIRST WORDS: A Real Example

The FIRST WORDS collection (minted January 2026) is a Legacy Scroll containing seven meditations:

```javascript
{
    id: 'first-words',
    title: 'FIRST WORDS',
    description: 'Seven meditations on existence',
    icon: '💜',
    category: 'philosophical',
    type: SCROLL_TYPES.LEGACY,
    pointer: {
        policy_id: 'beec4b31f21ae4567f9c849eada2f23f4f0b76c7949a1baaef623cba',
        content_type: 'text/plain; charset=utf-8',
        codec: 'none'
    },
    metadata: {
        nfts: 4,
        tx: 'cb0a2087c4ed1fd16dc3707e716e1a868cf4772b7340f4db7205a8344796dfae',
        minted: 'January 29, 2026'
    }
}
```

**TX:** [cb0a2087c4ed1fd16dc3707e716e1a868cf4772b7340f4db7205a8344796dfae](https://cardanoscan.io/transaction/cb0a2087c4ed1fd16dc3707e716e1a868cf4772b7340f4db7205a8344796dfae)

---

## Metadata Structure

### CIP-25 Compliant Format

```json
{
  "721": {
    "<policy_id>": {
      "<asset_name>": {
        "name": "Document Page 0",
        "i": 0,
        "payload": [
          "48656c6c6f20576f726c64",
          "0a5468697320697320706167",
          "6520302e"
        ],
        "description": "Part of a larger document"
      }
    }
  }
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `i` | integer | Page index (0-based) |
| `payload` | array of strings | Hex-encoded content chunks |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Human-readable name |
| `description` | string | Description |
| `image` | string | IPFS image URL |

---

## Cost Estimation

| Document Size | Pages | Approximate Cost |
|--------------|-------|------------------|
| 50 KB | 4 | ~10 ADA |
| 500 KB | 35 | ~80 ADA |
| 1 MB | 70 | ~150 ADA |
| 5 MB | 350 | ~700 ADA |

---

## Advantages vs Standard Scrolls

| Feature | Standard | Legacy |
|---------|----------|--------|
| Max size | ~16KB | Unlimited |
| Complexity | Simple | Moderate |
| NFT ownership | No | Yes |
| Wallet visible | No | Yes |
| Permanence | Locked UTxO | Time-locked policy |

---

## Best Practices

1. **Compress first** — Always gzip large documents
2. **Use 14KB chunks** — Stay under CIP-25 limits
3. **Set reasonable deadline** — Give yourself time to mint all pages
4. **Verify page order** — Double-check `i` indices
5. **Keep the hash** — Store SHA256 of original file

---

## Troubleshooting

**"Metadata too large"**
- Your payload chunks are too big
- Split into smaller pieces (64 chars per string)

**"Policy expired"**
- The time-lock deadline has passed
- You'll need a new policy for remaining pages

**"Pages out of order"**
- Verify `i` values are sequential
- Check for duplicate indices

---

*Legacy Scrolls preserve knowledge at scale. Libraries that cannot burn.*
