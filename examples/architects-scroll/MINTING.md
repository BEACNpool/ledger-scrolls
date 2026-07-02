# How the Architect's Scroll was minted

This folder contains the exact artifacts used to mint the Architect's Scroll
on January 29, 2026:

- [`architects_scroll.txt`](architects_scroll.txt) — the scroll content, byte-for-byte
- [`mint_architects_scroll.sh`](mint_architects_scroll.sh) — the minting script

The script is kept as a historical receipt and as a readable reference for
how a Standard Scroll mint works end to end. For minting your own scroll
today, use [`scripts/mint-standard-scroll.sh`](../../scripts/mint-standard-scroll.sh)
and the [Your First Scroll guide](../../docs/YOUR_FIRST_SCROLL.md).

## What the script does

1. **Creates an always-fail Plutus script** — the UTxO can never be spent
   (truly locked forever)
2. **Converts the scroll to hex** — prepares the content for the datum
3. **Creates an inline datum** — wraps the hex in proper Plutus data structure
4. **Builds the transaction** — locks ADA with the scroll datum
5. **Signs and submits** — makes it permanent on-chain
6. **Outputs the pointer** — `txHash#ix`, everything a registry entry needs

Prerequisites: `cardano-cli`, a synced Cardano node
(`CARDANO_NODE_SOCKET_PATH` set), and a funded payment key.

```bash
./mint_architects_scroll.sh /path/to/payment.skey /path/to/payment.addr
```

## Minting manually (the whole idea in five steps)

```bash
# 1. Convert the file to hex
xxd -p architects_scroll.txt | tr -d '\n' > scroll.hex

# 2. Record the SHA-256 (your permanent commitment)
sha256sum architects_scroll.txt

# 3. Create datum.json wrapping the hex (see templates/standard-scroll/)
# 4. Build a transaction paying to the always-fail script address
#    with --tx-out-inline-datum-file datum.json
# 5. Sign and submit
```

## Verify it

```bash
cardano-cli query utxo --mainnet \
  --address addr1w9fdc02rkmfyvh5kzzwwwk4kr2l9a8qa3g7feehl3ga022qz2249g
# The UTxO 076d6800…5747#0 shows with an inline datum; decode and hash it —
# it must equal 531a1eba80b297f8822b1505d480bb1c7f1bad2878ab29d8be01ba0e1fc67e12
```

*"In the digital age, true knowledge must be unstoppable."*
