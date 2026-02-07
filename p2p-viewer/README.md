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
- Read **Legacy CIP-25 pages + manifest** scrolls by aggregating **CIP-721 (label 721)** metadata via Koios
- Read the **on-chain Registry Head** and **Registry List** (inline datum) to discover public libraries

## Public default registry

The open-source default trust anchor is the BEACN public head:

- `ce86a174e1b35c37dea6898ef16352d447d11833549b1f382db22c5bb6358cab#0`

Viewers may allow users to add private heads for private libraries.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Dump the public registry head+list
python -m lsview registry-dump

# Reconstruct a Standard Scroll (by catalog id)
python -m lsview reconstruct-utxo --scroll hosky-png --out hosky.png

# Reconstruct a CIP-25 pages scroll
python -m lsview reconstruct-cip25 --scroll constitution-e608 --out constitution.txt
```

## Notes

- Koios endpoints can rate limit; the viewer batches metadata calls and should back off on errors.
- Blockfrost is reserved as a failover path (not required). If used, export:

```bash
export BLOCKFROST_PROJECT_ID=...your_key...
```

## License
MIT.
