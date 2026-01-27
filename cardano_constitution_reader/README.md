# Cardano Constitution Reader (On-Chain, Verified)

This tool reconstructs the Cardano Constitution directly from **on-chain NFT page payloads** (CIP-721 metadata) via **Blockfrost**, then verifies integrity with **SHA-256**.

## Prereqs

- Python 3 (`python3 --version`)
- Internet access
- A **Blockfrost Cardano Mainnet** API key (starts with `mainnet...`)
  - You can create a free account at Blockfrost; the free tier is typically sufficient for this script.

## Quick start (recommended)

```bash
git clone https://github.com/BEACNpool/ledger-scrolls.git
cd ledger-scrolls/cardano_constitution_reader

# Run (it will prompt for your Blockfrost key + epoch 541/608)
python3 cardano_constitution_reader.py
```

## Quick start (no prompts)

```bash
git clone https://github.com/BEACNpool/ledger-scrolls.git
cd ledger-scrolls/cardano_constitution_reader

export BLOCKFROST_PROJECT_ID="mainnet_...yourkey..."
python3 cardano_constitution_reader.py --epoch 608 --non-interactive
```

## Output

The script writes a file like:

- `Cardano_Constitution_Epoch_608.txt`

and prints the computed SHA-256 hash.

Tip (Linux):

```bash
xdg-open Cardano_Constitution_Epoch_608.txt
```
