#!/usr/bin/env bash
set -euo pipefail

# Validate CIP-25 page metadata fits under MaxTxSize before minting.
# Usage:
#   validate_tx_size.sh <metadata.json> <assets.list> <policy.id> <policy.script> <payment.addr> <assets_to_value.py> <socket>
# Example:
#   ./validate_tx_size.sh part01.json part01.assets policy/policy.id policy/policy.script ~/payment.addr ./assets_to_value.py ~/relay/db/node.socket

META=${1:?metadata.json required}
ASSETS_FILE=${2:?assets.list required}
POLICY_ID_FILE=${3:?policy.id required}
POLICY_SCRIPT=${4:?policy.script required}
PAYMENT_ADDR_FILE=${5:?payment.addr required}
ASSETS_TO_VALUE=${6:?assets_to_value.py required}
SOCKET=${7:?socket required}

POLICY=$(cat "$POLICY_ID_FILE")
ADDR=$(cat "$PAYMENT_ADDR_FILE")

TMP_UTXO=/tmp/utxo_validate.json
TX_RAW=/tmp/tx_validate.raw

cardano-cli latest query utxo --testnet-magic 2 --socket-path "$SOCKET" --address "$ADDR" --out-file "$TMP_UTXO"

# Largest ADA-only UTxO
TXIN=$(jq -r "to_entries \
  | map(select((.value.value | keys | length == 1) and (.value.value | has(\"lovelace\")))) \
  | sort_by(.value.value.lovelace|tonumber) \
  | reverse \
  | .[0].key" "$TMP_UTXO")

if [ -z "$TXIN" ] || [ "$TXIN" = "null" ]; then
  echo "No ADA-only UTxO available" >&2
  exit 1
fi

MINT_VALUE=$(python3 "$ASSETS_TO_VALUE" "$POLICY" < "$ASSETS_FILE")

cardano-cli latest transaction build --testnet-magic 2 --socket-path "$SOCKET" \
  --tx-in "$TXIN" \
  --tx-out "$ADDR+2000000+$MINT_VALUE" \
  --mint "$MINT_VALUE" \
  --minting-script-file "$POLICY_SCRIPT" \
  --metadata-json-file "$META" \
  --change-address "$ADDR" \
  --out-file "$TX_RAW" >/dev/null

SIZE=$(stat -c%s "$TX_RAW")
LIMIT=16384
BUFFER=15500

echo "tx_raw_bytes=$SIZE"
if [ "$SIZE" -le "$BUFFER" ]; then
  echo "PASS (<= $BUFFER)"
  exit 0
fi
if [ "$SIZE" -le "$LIMIT" ]; then
  echo "WARN (<= $LIMIT but > $BUFFER)"
  exit 0
fi

echo "FAIL (> $LIMIT)"
exit 2
