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
- `kind=utxo-inline-datum-bytes-v1` pointers (and the deprecated
  `utxo-locked-bytes` alias) resolve live via Koios `utxo_info`. Override the
  endpoint with `LSR_KOIOS_BASE` (default `https://api.koios.rest/api/v1`).
- `kind=cip25-pages-v1` (and the deprecated `asset-manifest` alias) is not
  implemented here; use koios-viewer (`lsview reconstruct-cip25`) for paged
  scrolls.
- `--trusted-key <hex>` pins a 32-byte Ed25519 public key and is fail-closed:
  unsigned heads and heads signed by any other key are rejected.
