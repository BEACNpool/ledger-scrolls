Building Your Own Ledger Scrolls: A Guide for Stake Pool Operators
Ledger Scrolls is an open-source standard for storing immutable, timeless data on the Cardano blockchain using NFTs.

As a Stake Pool Operator (SPO), you are uniquely positioned to leverage this technology. Your familiarity with running nodes, using cardano-cli, and minting assets makes you the ideal candidate for creating and preserving decentralized "scrolls" of knowledge—data or records that persist forever on the ledger.

This guide focuses on minting your own scrolls via cardano-cli, giving you full control without relying on third-party APIs like Blockfrost. While the standard is neutral and extensible, this guide emphasizes the SPO's ability to interact directly with the chain.

⚠️ Important Note on Segment Sizes
The Ledger Scrolls standard relies on splitting data into manageable chunks (segments).

Recommendation: Use 32-byte segments.

Why? While larger segments (e.g., 64 bytes) might seem efficient, they often cause transaction failures during minting due to Cardano's transaction metadata size limits (~16KB per tx). Metadata hex strings bloat quickly. Sticking to 32 bytes ensures reliability and compatibility with standard transaction limits.

1. Prerequisites
We assume you are an SPO or advanced user with the following:

Synced Cardano Node: A fully synced node (mainnet or testnet) running cardano-node and cardano-cli (v8.0+ recommended).

Funded Wallet: Access to a wallet with ADA for transaction fees and minting deposits (keys available via CLI).

Python 3.8+: Installed on your machine (only standard libraries like gzip, hashlib, json are required).

Technical Knowledge: Familiarity with Bash scripting, CIP-25 (NFT metadata standard), and building raw transactions.

Note: No external internet access is required for reconstruction if you run your own node—the data lives entirely on-chain.

2. Step 1: Preparing Your Content
To create a Ledger Scroll, you must first compress and segment your data.

Choose Data: Select your file (HTML, text, PDF, etc.). Keep the uncompressed size reasonable (under ~1MB is recommended for cost-efficiency).

Compress: Use GZIP to minimize on-chain storage costs.

Segment: Split the compressed data into small hex chunks.

Automation Script (prepare_scroll.py)
Save the following code as prepare_scroll.py and run it to generate your payloads.

Python

import gzip
import hashlib
import json
from pathlib import Path
import math

# CONFIGURATION
INPUT_FILENAME = 'your_content.html'  # Replace with your actual file
SEGMENT_SIZE = 32                     # Bytes per hex chunk (32 recommended)

def prepare_scroll():
    input_file = Path(INPUT_FILENAME)
    
    if not input_file.exists():
        print(f"Error: File '{INPUT_FILENAME}' not found.")
        return

    # 1. Compress Data
    raw_data = input_file.read_bytes()
    gz_data = gzip.compress(raw_data)
    
    # 2. Calculate Checksums
    sha_html = hashlib.sha256(raw_data).hexdigest()
    sha_gz = hashlib.sha256(gz_data).hexdigest()
    
    print(f"Original SHA256: {sha_html}")
    print(f"Compressed SHA256: {sha_gz}")
    
    # 3. Save GZIP locally for verification (optional)
    gz_file = input_file.with_suffix('.gz')
    gz_file.write_bytes(gz_data)
    print(f"Saved compressed file: {gz_file}")

    # 4. Split into Payloads
    payloads = []
    # Loop through data in chunks of SEGMENT_SIZE
    for i in range(0, len(gz_data), SEGMENT_SIZE):
        chunk = gz_data[i : i + SEGMENT_SIZE]
        payloads.append(chunk.hex())

    total_chunks = len(payloads)
    print(f"Total Segments: {total_chunks}")

    # 5. Export to JSON for Metadata Creation
    output_json = input_file.with_suffix('.payloads.json')
    with open(output_json, 'w') as f:
        json.dump({
            "meta": {
                "filename": INPUT_FILENAME,
                "sha_original": sha_html,
                "sha_compressed": sha_gz,
                "segment_size": SEGMENT_SIZE,
                "total_segments": total_chunks
            },
            "payloads": payloads
        }, f, indent=2)
    
    print(f"Payload data saved to: {output_json}")

if __name__ == "__main__":
    prepare_scroll()
3. Step 2: Generating Metadata (CIP-25)
Ledger Scrolls use CIP-25 metadata (Label 721). You will need two types of NFTs:

Manifest NFT: The "Cover Page." Contains global checksums and total page counts.

Page NFTs: The data carriers. These hold the actual hex payloads.

A. Manifest Structure (manifest.json)
This NFT tells the decoder how to interpret the rest of the collection.

JSON

{
  "721": {
    "<YOUR_POLICY_ID>": {
      "<ASSET_NAME_MANIFEST>": {
        "name": "Ledger Scroll Manifest",
        "project": "Ledger Scrolls",
        "files": [
            {
                "mediaType": "application/json",
                "src": "ipfs://..." 
            }
        ],
        "scroll_meta": {
            "pages": <TOTAL_PAGES>,
            "sha_gz": "<SHA_GZ_FROM_SCRIPT>",
            "sha_html": "<SHA_ORIGINAL_FROM_SCRIPT>",
            "encoding": "gzip",
            "mediaType": "text/html"
        }
      }
    }
  }
}
B. Page Structure (page_001.json)
Each page contains a sequence of hex strings. You can bundle multiple segments into one NFT, provided you stay within the ~16KB transaction metadata limit.

JSON

{
  "721": {
    "<YOUR_POLICY_ID>": {
      "<ASSET_NAME_PAGE_01>": {
        "name": "Scroll Page 01",
        "order": 1,
        "payload": [
            "1f8b0800...", 
            "a4f32c01...",
            "..." 
        ] 
      }
    }
  }
}
4. Step 3: Minting with cardano-cli
1. Create Policy
Generate your keys and policy script. A simple time-locked policy is recommended if you want the scroll to be truly immutable (cannot be burned or modified after a certain slot).

Bash

cardano-cli address key-gen \
    --verification-key-file policy.vkey \
    --signing-key-file policy.skey

# Create a policy.script file (standard JSON script definition)
cardano-cli transaction policyid --script-file policy.script > policy.id
2. Build & Submit Transactions
You will likely need to mint in batches to avoid exceeding transaction size limits.

Drafting the Transaction:

Bash

cardano-cli transaction build \
  --mainnet \
  --tx-in <YOUR_UTXO> \
  --change-address <YOUR_ADDRESS> \
  --mint "1 <POLICY_ID>.<HEX_ASSET_NAME>" \
  --mint-script-file policy.script \
  --metadata-json-file page_001.json \
  --out-file tx.draft
Sign and Submit:

Bash

cardano-cli transaction sign \
  --tx-body-file tx.draft \
  --signing-key-file payment.skey \
  --signing-key-file policy.skey \
  --mainnet \
  --out-file tx.signed

cardano-cli transaction submit --tx-file tx.signed --mainnet
Troubleshooting
"Metadata Too Large": If the transaction fails, reduce the number of payloads in that specific Page NFT.

Segment Errors: If minting fails due to specific string errors, ensure your SEGMENT_SIZE in the python script is set to 32.

5. Step 4: Reconstructing from Your Node
To verify or read the data, you reverse the process. Because the data is on-chain, you can query it directly using cardano-db-sync or by pulling the transaction metadata from your local node history.

The Reconstruction Logic:

Fetch Metadata: Retrieve the JSON metadata for all assets under the Policy ID.

Sort: Order the Page NFTs by their index/name (e.g., Page 1, Page 2).

Extract: Pull the payload arrays from each page.

Concatenate: Join all hex strings into one long string.

Convert: Convert the hex string back to bytes.

Verify: Check the SHA256 of these bytes against the sha_gz in the Manifest NFT.

Decompress: Run gzip -d on the bytes to recover the original HTML/File.

Contributing
Ledger Scrolls is open source. We encourage SPOs to fork this repo, improve the minting scripts, and add integrations for other node implementations.

Let's decentralize knowledge together.

Would you like me to also write a Python script for the "Step 4: Reconstruction" part mentioned in the file?
