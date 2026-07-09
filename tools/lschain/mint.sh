#!/usr/bin/env bash
#═══════════════════════════════════════════════════════════════════════════
#   LS-CHAIN v2 MINTER — bare metadata pages + always-fail manifest datum
#   Spec: registry/spec/manifest-chain-v2.md
#
#   Usage:
#     ./mint.sh <workdir> <payment.skey> <payment.addr|file> [lock-ada] [chain-root-txin]
#
#   chain-root-txin: explicit pure-ADA UTxO to fund the chain (RECOMMENDED —
#   auto-selection picks the largest pure-ADA UTxO, which is unsafe if the
#   wallet holds load-bearing UTxOs such as a registry head).
#
#   <workdir> comes from prepare.py (page-NNNN.json + plan.json).
#   Page txs are chained on each other's change output (no confirmation
#   waits). The manifest datum is built from the recorded tx hashes and
#   locked at the always-fail script address. Emits receipts.json.
#
#   Requirements: cardano-cli (Conway), python3, jq, a synced node socket
#   in CARDANO_NODE_SOCKET_PATH.
#═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

WORK="${1:?workdir from prepare.py}"
SKEY="${2:?payment signing key}"
ADDR="${3:?payment address or file}"
LOCK_ADA="${4:-}"
ROOT_TXIN="${5:-}"
[ -f "$ADDR" ] && ADDR=$(cat "$ADDR")

NETWORK_NAME="${LSCHAIN_NETWORK:-mainnet}"
case "$NETWORK_NAME" in
  mainnet) NETWORK="--mainnet" ;;
  preview) NETWORK="--testnet-magic 2" ;;
  *) echo "LSCHAIN_NETWORK must be mainnet or preview"; exit 1 ;;
esac
SOCKET="${CARDANO_NODE_SOCKET_PATH:?set CARDANO_NODE_SOCKET_PATH}"
CLI="cardano-cli latest"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOCK_SCRIPT="$SCRIPT_DIR/../../templates/standard-scroll/always-fail.plutus"

# Verification is part of minting, not an optional follow-up. Fail before any
# permanent transaction if the reference reconstructor cannot run.
PYTHONPATH="$REPO_ROOT/koios-viewer" python3 -c 'import cbor2, lsview' 2>/dev/null || {
  echo "Python verifier dependencies missing; install koios-viewer/requirements.txt before minting"; exit 1;
}

# Sending a datum to a script address needs only the address, not the
# script witness. LSCHAIN_LOCK_ADDR overrides; default derives from the
# template script file. The live Ledger Scrolls always-fail address is
# addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn (Hosky lock).
if [ -n "${LSCHAIN_LOCK_ADDR:-}" ]; then
  LOCK_ADDR="$LSCHAIN_LOCK_ADDR"
else
  LOCK_ADDR=$($CLI address build --payment-script-file "$LOCK_SCRIPT" $NETWORK)
fi
echo "Lock (always-fail) address: $LOCK_ADDR"

PAGES=$(ls "$WORK"/page-*.json | sort)
N=$(echo "$PAGES" | wc -l)
echo "Pages to mint: $N"

# Chain-root UTxO: explicit argument, or the largest pure-ADA UTxO
$CLI query utxo --address "$ADDR" $NETWORK --output-json --socket-path "$SOCKET" > "$WORK/utxos.json"
if [ -n "$ROOT_TXIN" ]; then
  TXIN="$ROOT_TXIN"
  jq -e --arg k "$TXIN" 'has($k)' "$WORK/utxos.json" >/dev/null || { echo "chain-root txin not found at $ADDR: $TXIN"; exit 1; }
else
  TXIN=$(jq -r 'to_entries
    | map(select((.value.value | keys | length) == 1))
    | sort_by(.value.value.lovelace) | last | .key' "$WORK/utxos.json")
  [ "$TXIN" != "null" ] || { echo "No pure-ADA UTxO at $ADDR"; exit 1; }
fi
BAL=$(jq -r --arg k "$TXIN" '.[$k].value.lovelace' "$WORK/utxos.json")
echo "Chain root UTxO: $TXIN ($((BAL/1000000)) ADA)"

# `transaction build` balances against the ledger UTxO set, so each
# chained input must be confirmed before the next build.
wait_for_utxo() {
  local txin="$1" tries=0
  while ! $CLI query utxo --tx-in "$txin" $NETWORK --output-json --socket-path "$SOCKET" \
        | jq -e --arg k "$txin" 'has($k)' >/dev/null 2>&1; do
    tries=$((tries+1))
    [ $tries -gt 60 ] && { echo "timeout waiting for $txin"; exit 1; }
    sleep 5
  done
}

: > "$WORK/page_txids.txt"
i=0
for META in $PAGES; do
  i=$((i+1))
  wait_for_utxo "$TXIN"
  $CLI transaction build $NETWORK --socket-path "$SOCKET" \
    --tx-in "$TXIN" \
    --metadata-json-file "$META" \
    --change-address "$ADDR" \
    --out-file "$WORK/tx-page.raw"
  $CLI transaction sign --tx-body-file "$WORK/tx-page.raw" \
    --signing-key-file "$SKEY" $NETWORK --out-file "$WORK/tx-page.signed"
  $CLI transaction submit $NETWORK --socket-path "$SOCKET" --tx-file "$WORK/tx-page.signed"
  # txid output is bare hex (older cli) or {"txhash": ...} (cli >= 11)
  TXID=$($CLI transaction txid --tx-file "$WORK/tx-page.signed" | grep -oE '[0-9a-f]{64}' | head -1)
  echo "$TXID" >> "$WORK/page_txids.txt"
  echo "  page $i/$N -> $TXID"
  # chain on this tx's change output (page txs have no other outputs)
  TXIN="$TXID#0"
done

# Build manifest datum from recorded txids
python3 "$SCRIPT_DIR/make_manifest.py" "$WORK/plan.json" "$WORK/page_txids.txt" "$WORK/manifest.cbor"

# Min-UTxO for the manifest output (or explicit lock amount)
if [ -z "$LOCK_ADA" ]; then
  MIN=$($CLI transaction calculate-min-required-utxo \
    --protocol-params-file <($CLI query protocol-parameters $NETWORK --socket-path "$SOCKET") \
    --tx-out "$LOCK_ADDR+2000000" \
    --tx-out-inline-datum-cbor-file "$WORK/manifest.cbor" | awk '{print $2}')
  LOCK_LOVELACE=$MIN
else
  LOCK_LOVELACE=$((LOCK_ADA*1000000))
fi
echo "Manifest lock amount: $LOCK_LOVELACE lovelace"

wait_for_utxo "$TXIN"
$CLI transaction build $NETWORK --socket-path "$SOCKET" \
  --tx-in "$TXIN" \
  --tx-out "$LOCK_ADDR+$LOCK_LOVELACE" \
  --tx-out-inline-datum-cbor-file "$WORK/manifest.cbor" \
  --change-address "$ADDR" \
  --out-file "$WORK/tx-manifest.raw"
$CLI transaction sign --tx-body-file "$WORK/tx-manifest.raw" \
  --signing-key-file "$SKEY" $NETWORK --out-file "$WORK/tx-manifest.signed"
$CLI transaction submit $NETWORK --socket-path "$SOCKET" --tx-file "$WORK/tx-manifest.signed"
MANIFEST_TXID=$($CLI transaction txid --tx-file "$WORK/tx-manifest.signed" | grep -oE '[0-9a-f]{64}' | head -1)

echo "Waiting for manifest confirmation, then reconstructing from chain..."
wait_for_utxo "$MANIFEST_TXID#0"
verified=0
if [ "$NETWORK_NAME" = preview ]; then KOIOS_URL="https://preview.koios.rest/api/v1"; else KOIOS_URL="https://api.koios.rest/api/v1"; fi
for attempt in $(seq 1 30); do
  if LS_KOIOS="$KOIOS_URL" LS_EXPECTED_LOCK="$LOCK_ADDR" PYTHONPATH="$REPO_ROOT/koios-viewer" python3 -m lsview reconstruct-chain \
       --txin "$MANIFEST_TXID#0" --out "$WORK/readback.bin"; then verified=1; break; fi
  echo "Indexer has not caught up yet ($attempt/30); retrying in 10s..."
  sleep 10
done
[ "$verified" -eq 1 ] || { echo "Mint confirmed locally, but public read-back did not become available; do not announce until verification succeeds"; exit 1; }
EXPECTED=$(jq -r '.sha256Decoded' "$WORK/plan.json")
ACTUAL=$(sha256sum "$WORK/readback.bin" | awk '{print $1}')
[ "$ACTUAL" = "$EXPECTED" ] || { echo "FATAL: read-back hash mismatch: $ACTUAL != $EXPECTED"; exit 1; }

jq -n --arg m "$MANIFEST_TXID" --arg lock "$LOCK_ADDR" \
      --arg network "$NETWORK_NAME" \
      --slurpfile plan "$WORK/plan.json" \
      --rawfile pages "$WORK/page_txids.txt" '{
  format: "ls-chain-v2-receipts", network: $network,
  pointer: { kind: "manifest-chain-v2", txHash: $m, txIx: 0 },
  lockAddress: $lock,
  pageTxHashes: ($pages | split("\n") | map(select(. != ""))),
  plan: $plan[0]
}' > "$WORK/receipts.json"

echo ""
echo "═══════════════════════════════════════════════════════"
echo " MANIFEST TXIN: $MANIFEST_TXID#0"
echo " Receipts:      $WORK/receipts.json"
echo " Verified:      read back from chain, sha256 $ACTUAL"
echo "═══════════════════════════════════════════════════════"
