# Ledger Scrolls Viewer (Python, Koios-first)

**“A library that cannot burn.”**

Ledger Scrolls is an open-source standard + viewer for publishing and reading **permissionless, immutable data** on Cardano.

This viewer is the **Koios-first** path:

- **No relay / node-to-node requirements**
- **Koios public REST API** (no API key)
- Optional **Blockfrost failover** (only if you set `BLOCKFROST_PROJECT_ID`)

The goal is that the open-source viewer **just works** for normal users.

## What this can do

- Read **Standard Scrolls** stored as **UTxO inline datum bytes** (via Koios `utxo_info`)
- Read **Chain Scrolls (LS-CHAIN v2)** from a manifest txin + label-22025 page metadata
- Read **Legacy CIP-25 pages + manifest** scrolls by aggregating **CIP-721 (label 721)** metadata via Koios
- Resolve the **on-chain registry NFT** (latest Registry Head → label-22027 list) to discover public libraries

## Public default registry

The catalog is an on-chain NFT. The stable trust anchor is the library **policy id**:

- `8d6d38b3967028a15fc0e401b53c73a75ac654affc3f817c750c8b80`

Resolution (same as the web reader): list the policy's assets, keep those whose
CIP-721 metadata says `Type == "Registry Head"`, take the highest numeric
`Version`, and read the scroll list from that NFT's mint-tx metadata **label
22027**. `lsview registry-dump` does this by default.

Legacy datum-era heads (pre-NFT, all spent) remain readable via
`--legacy-head <TXHASH#IX>`; the tool warns when a head UTxO is spent.
Viewers may allow users to add private heads for private libraries.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Dump the live registry (registry NFT -> label-22027 scroll list)
lsview registry-dump

# Merge a private datum head on top (private overrides public)
lsview registry-dump --private-head <TXHASH#IX>

# List the bundled catalog (mirrors the on-chain registry list)
lsview list-scrolls

# Reconstruct a Standard Scroll (by catalog id)
lsview reconstruct-utxo --scroll hosky-png --out hosky.png

# Reconstruct a Chain Scroll (LS-CHAIN v2)
lsview reconstruct-chain --scroll the-spec --out spec.html

# Reconstruct a CIP-25 pages scroll
lsview reconstruct-cip25 --scroll constitution-e608 --out constitution.txt
```

`python -m lsview` works too if you prefer not to install.

## Notes

- Koios endpoints can rate limit; the viewer batches metadata calls and should back off on errors.
- Blockfrost is reserved as a failover path (not required). If used, export:

```bash
export BLOCKFROST_PROJECT_ID=...your_key...
```

## License
MIT.
