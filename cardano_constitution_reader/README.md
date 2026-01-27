# Cardano Constitution Reader (On-Chain, Verified)

This script reconstructs the Cardano Constitution directly from on-chain NFT page payloads (CIP-721 metadata) via Blockfrost, then verifies the SHA-256 hash.

## Quick start (Ubuntu)

```bash
git clone https://github.com/YOURNAME/cardano-constitution-reader.git
cd cardano-constitution-reader

# Option A (recommended): use an env var so you don't paste the key interactively
export BLOCKFROST_PROJECT_ID="mainnet_yourkeyhere"
python3 cardano_constitution_reader.py --epoch 541

# Or epoch 608
python3 cardano_constitution_reader.py --epoch 608
