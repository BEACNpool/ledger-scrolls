# Building Your Own Ledger Scrolls: A Guide for Stake Pool Operators

Ledger Scrolls is an open-source standard for storing immutable, timeless data on the Cardano blockchain using NFTs. As a Stake Pool Operator (SPO), you already possess the technical expertise—running nodes, using `cardano-cli`, and managing minting policies—to create and preserve truly eternal, decentralized knowledge.

This guide is written specifically for SPOs who want full sovereignty: minting scrolls via `cardano-cli` without relying on third-party services, and reconstructing them directly from your own node. Everyday users can use the web or Python viewers with Blockfrost; this path is for those who value maximum trustlessness.

**Note on Segment Size**: Testing has shown that splitting payload into **32-byte chunks** reliably succeeds during minting, while 64-byte chunks frequently cause transaction failures due to metadata size limits. Always use 32-byte segments unless you've validated larger on testnet.

## Prerequisites (Assumed for SPOs)

You are expected to have:
- A fully synced Cardano node (`cardano-node` + `cardano-cli`, version 8.0+ recommended)
- Operational stake pool keys and a funded payment address
- Familiarity with policy scripts, transaction building, signing, and submission
- Basic scripting ability (Bash or Python for automation)
- Python 3.8+ installed for data preparation
- Understanding of CIP-25 NFT metadata standard

If your node isn't synced, refer to the official guide: https://docs.cardano.org/getting-started/installing-cardano-node

## Step 1: Prepare Your Content

1. **Select Your Data**  
   Any text, HTML, or small document (ideally <1MB uncompressed to keep NFT count reasonable).

2. **Compress with GZIP**
   ```python
   import gzip
   import hashlib
   from pathlib import Path

   input_file = Path("your_content.html")  # Replace with your file
   original_bytes = input_file.read_bytes()
   gz_data = gzip.compress(original_bytes)

   sha_gz = hashlib.sha256(gz_data).hexdigest()
   sha_html = hashlib.sha256(original_bytes).hexdigest()

   gz_file = input_file.with_suffix('.gz')
   gz_file.write_bytes(gz_data)

   print(f"Compressed size: {len(gz_data)} bytes")
   print(f"SHA256 (GZ): {sha_gz}")
   print(f"SHA256 (Original): {sha_html}")

Split into 32-Byte Payload Chunks (Critical for mint success)Pythondef split_payloads(data: bytes, chunk_size: int = 32):
    return [{"bytes": data[i:i+chunk_size].hex()} for i in range(0, len(data), chunk_size)]

payloads = split_payloads(gz_data)
total_pages = len(payloads)  # One page NFT per payload array (or bundle if desired)

# Save for reference
import json
Path("payloads.json").write_text(json.dumps(payloads, indent=2))
print(f"Total payload chunks (pages): {total_pages}")

Step 2: Create CIP-25 Metadata
Generate JSON metadata files:

Manifest (single NFT, e.g., asset name MYSCROLL_MANIFEST):JSON{
  "721": {
    "<policy_id>": {
      "MYSCROLL_MANIFEST": {
        "pages": 123,
        "sha_gz": "abc123...",     // from script
        "sha_html": "def456..."   // from script
      }
    }
  }
}
Page NFTs (e.g., MYSCROLL_P0001, MYSCROLL_P0002, etc.):JSON{
  "721": {
    "<policy_id>": {
      "MYSCROLL_P0001": {
        "i": 1,
        "payload": [
          {"bytes": "first32bytehex"},
          {"bytes": "next32bytehex"},
          ...
        ]
      }
    }
  }
}

You can automate generation with a Python loop over payloads.
Step 3: Mint Using cardano-cli

Create a Minting Policy
Use a simple slot-locked or multi-sig script. For immutability, lock the policy after minting.
Mint Manifest + Pages
Batch assets into transactions to minimize fees:Bashcardano-cli transaction build \
  --alonzo-era \
  --mainnet \
  --tx-in "<your-utxo>" \
  --change-address "<your-address>" \
  --mint "1 <policy>.<MYSCROLL_MANIFEST>+10 <policy>.<MYSCROLL_P0001>+..." \
  --minting-script-file policy.script \
  --metadata-json-file manifest.json \
  --metadata-json-file page_0001.json \
  --out-file tx.draft
Calculate min fee, sign with policy keys + payment keys, submit.
Repeat for remaining pages (group ~10-20 per tx to stay under size limits).

Common Minting Issues & Fixes
Tx too large / metadata overflow: Reduce payloads per page or split across more txs.
Seg 64 failure: Always use 32-byte chunks (as tested).
Invalid metadata: Validate with cardano-cli transaction view --tx-body-file tx.draft
Test everything on preprod first.


Step 4: Reconstruct from Your Own Node (Optional)
For full trustlessness:

Use cardano-db-sync + PostgreSQL to index assets and fetch metadata via SQL queries.
Or query via Ogmios JSON-RPC.
Parse returned metadata and reconstruct using the same Python logic as viewers.

Your node guarantees no third-party dependency—pure on-chain truth.
Final Note
By minting Ledger Scrolls, you're contributing to a new era of eternal, decentralized knowledge preservation. As an SPO, your infrastructure is already perfect for this.
We welcome your improvements—especially minting automation scripts, policy templates, or node integration tools.
Fork the repo and help build the standard: https://github.com/BEACNpool/ledger-scrolls
The ledger remembers. Forever.
textUpload this file to your repository, and you'll have a professional, SPO-focused guide that empowers experienced