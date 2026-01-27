# Cardano Constitution Reader (On-Chain, Verified)

This script reconstructs the Cardano Constitution directly from on-chain NFT page payloads (CIP-721 metadata) via Blockfrost, then verifies the SHA-256 hash.

## Quick start (Ubuntu)

```bash
git clone https://github.com/BEACNpool/ledger-scrolls.git
cd ledger-scrolls/cardano_constitution_reader
python3 cardano_constitution_reader.py

