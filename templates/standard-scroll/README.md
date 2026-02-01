# Standard Scroll Template

This template provides everything you need to mint a Standard Scroll (LS-LOCK v1).

## Files

- `always-fail.plutus` — The lock script (produces a unique lock address)
- `datum-template.json` — Datum structure template

## Quick Start

Use the main minting script in `scripts/`:

```bash
# Navigate to scripts directory
cd scripts

# Make executable
chmod +x mint-standard-scroll.sh

# Mint your scroll
./mint-standard-scroll.sh \
    /path/to/content.txt \
    /path/to/payment.skey \
    /path/to/payment.addr
```

## Manual Process

1. Convert your content to hex:
```bash
xxd -p content.txt | tr -d '\n' > content.hex
```

2. Get SHA256:
```bash
sha256sum content.txt
```

3. Create datum:
```bash
CONTENT_HEX=$(cat content.hex)
cat > datum.json << EOF
{
    "constructor": 0,
    "fields": [{ "bytes": "$CONTENT_HEX" }]
}
EOF
```

4. Build and submit transaction (see `mint.sh` for full example)

## Lock Address

All Standard Scrolls use the same lock address (the always-fail script):
```
addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn
```

This address can receive funds but can never spend them — true permanence.
