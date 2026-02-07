# Tooling (reference, Python)

This directory contains **reference Python tooling** for the Ledger Scrolls Registry.

## Install (editable)

From this folder:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Commands

### Canonical JSON hash (SHA-256)

```bash
lsr-hash ../examples/example-registry-list.json
```

### Verify resolution (v0)

```bash
lsr-verify --head ../examples/example-head.json --name hosky-png
```

Notes:

- `kind=url` pointers are supported (http(s), file://, and relative paths).
- Cardano pointer kinds (`utxo-locked-bytes`, `asset-manifest`) are **declared in the spec** but require a Cardano provider/indexer integration; this reference tool currently raises a clear "not implemented" error for them.
