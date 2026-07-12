#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
#                    MINT THE ARCHITECT'S SCROLL
#                    Ledger Scrolls Standard (LS-LOCK v1)
#═══════════════════════════════════════════════════════════════════════════════
#
# This script mints the Architect's Scroll as a Standard Ledger Scroll
# using a locked UTxO with inline datum.
#
# Prerequisites:
#   - cardano-cli installed
#   - cardano-node running and synced
#   - Payment keys with sufficient ADA (~3 ADA recommended)
#   - CARDANO_NODE_SOCKET_PATH set
#
# Usage:
#   ./mint_architects_scroll.sh <payment.skey> <payment.addr> [--yes]
#
#═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}"
echo "═══════════════════════════════════════════════════════════════════════"
echo "                    🔮 MINTING THE ARCHITECT'S SCROLL 🔮"
echo "═══════════════════════════════════════════════════════════════════════"
echo -e "${NC}"

# Check arguments
if [ $# -lt 2 ]; then
    echo -e "${RED}Usage: $0 <payment.skey> <payment.addr> [--yes]${NC}"
    echo ""
    echo "  payment.skey  - Path to payment signing key"
    echo "  payment.addr  - Path to payment address file (or address string)"
    echo "  --yes         - Optional: skip the pre-submit confirmation prompt"
    exit 1
fi

PAYMENT_SKEY="$1"
PAYMENT_ADDR="$2"
ASSUME_YES=false
if [ "${3:-}" = "--yes" ]; then
    ASSUME_YES=true
fi

# If payment.addr is a file, read it
if [ -f "$PAYMENT_ADDR" ]; then
    PAYMENT_ADDR=$(cat "$PAYMENT_ADDR")
fi

# Check for cardano-cli
if ! command -v cardano-cli &> /dev/null; then
    echo -e "${RED}Error: cardano-cli not found${NC}"
    exit 1
fi

# Check for socket
if [ -z "${CARDANO_NODE_SOCKET_PATH:-}" ]; then
    echo -e "${YELLOW}Warning: CARDANO_NODE_SOCKET_PATH not set, trying default...${NC}"
    export CARDANO_NODE_SOCKET_PATH="/opt/cardano/cnode/sockets/node.socket"
fi

if [ ! -S "$CARDANO_NODE_SOCKET_PATH" ]; then
    echo -e "${RED}Error: Node socket not found at $CARDANO_NODE_SOCKET_PATH${NC}"
    exit 1
fi

NETWORK="--mainnet"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

#═══════════════════════════════════════════════════════════════════════════════
# STEP 1: Create Always-Fail Script (Locked Forever)
#═══════════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[1/7] Creating always-fail script...${NC}"

# This script can never validate - the UTxO is locked forever.
# Use the canonical template so the lock address stays the library's.
cp "$SCRIPT_DIR/../../templates/standard-scroll/always-fail.plutus" "$WORK_DIR/always-fail.plutus"

# Get script address
LOCK_ADDR=$(cardano-cli address build \
    --payment-script-file "$WORK_DIR/always-fail.plutus" \
    $NETWORK)

echo -e "${GREEN}  Lock address: ${LOCK_ADDR:0:40}...${NC}"

#═══════════════════════════════════════════════════════════════════════════════
# STEP 2: Prepare Scroll Content
#═══════════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[2/7] Preparing scroll content...${NC}"

SCROLL_FILE="$SCRIPT_DIR/architects_scroll.txt"
if [ ! -f "$SCROLL_FILE" ]; then
    echo -e "${RED}Error: architects_scroll.txt not found${NC}"
    exit 1
fi

# Convert to hex
SCROLL_HEX=$(xxd -p "$SCROLL_FILE" | tr -d '\n')
SCROLL_SIZE=$(wc -c < "$SCROLL_FILE")
SCROLL_HASH=$(sha256sum "$SCROLL_FILE" | cut -d' ' -f1)

echo -e "${GREEN}  Size: ${SCROLL_SIZE} bytes${NC}"
echo -e "${GREEN}  SHA256: ${SCROLL_HASH}${NC}"

#═══════════════════════════════════════════════════════════════════════════════
# STEP 3: Create Inline Datum
#═══════════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[3/7] Creating inline datum...${NC}"

# Datum structure: constructor 0 with single bytes field
cat > "$WORK_DIR/datum.json" << EOF
{
    "constructor": 0,
    "fields": [
        {
            "bytes": "$SCROLL_HEX"
        }
    ]
}
EOF

echo -e "${GREEN}  Datum created (${#SCROLL_HEX} hex chars)${NC}"

#═══════════════════════════════════════════════════════════════════════════════
# STEP 4: Query UTxOs for Funding
#═══════════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[4/7] Querying UTxOs at payment address...${NC}"

cardano-cli query utxo \
    --address "$PAYMENT_ADDR" \
    $NETWORK \
    --out-file "$WORK_DIR/utxos.json"

# Find a suitable UTxO (need at least 3 ADA). Pure-lovelace only, carrying no
# datum and no reference script — never spend an NFT- or pointer-bearing UTxO.
UTXO=$(jq -r 'to_entries
    | map(select((.value.value | keys) == ["lovelace"]
        and (.value.value.lovelace >= 3000000)
        and (.value.inlineDatum == null)
        and (.value.datum == null)
        and (.value.datumhash == null)
        and (.value.referenceScript == null)))
    | .[0].key' "$WORK_DIR/utxos.json")

if [ "$UTXO" == "null" ] || [ -z "$UTXO" ]; then
    echo -e "${RED}Error: No pure-ADA UTxO (no tokens, no datum, no reference script) with >= 3 ADA found${NC}"
    exit 1
fi

UTXO_BALANCE=$(jq -r --arg utxo "$UTXO" '.[$utxo].value.lovelace' "$WORK_DIR/utxos.json")
echo -e "${GREEN}  Using UTxO: ${UTXO}${NC}"
echo -e "${GREEN}  Balance: ${UTXO_BALANCE} lovelace${NC}"

#═══════════════════════════════════════════════════════════════════════════════
# STEP 5: Build Transaction
#═══════════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[5/7] Building transaction...${NC}"

# Lock 2 ADA with the scroll (min UTxO for datum)
LOCK_AMOUNT=2000000

# Every tx carries an upper validity bound (ttl = tip+3600); refuse tip-less builds
TIP_SLOT=$(cardano-cli query tip $NETWORK | jq -r '.slot // empty')
if [ -z "$TIP_SLOT" ]; then
    echo -e "${RED}Error: Could not read tip slot; refusing to build a tx with no validity bound${NC}"
    exit 1
fi
TTL=$(( TIP_SLOT + 3600 ))

cardano-cli transaction build \
    $NETWORK \
    --tx-in "$UTXO" \
    --tx-out "$LOCK_ADDR+$LOCK_AMOUNT" \
    --tx-out-inline-datum-file "$WORK_DIR/datum.json" \
    --invalid-hereafter "$TTL" \
    --change-address "$PAYMENT_ADDR" \
    --out-file "$WORK_DIR/tx.raw"

echo -e "${GREEN}  Transaction built (valid until slot $TTL)${NC}"

echo ""
echo -e "${YELLOW}About to sign and submit:${NC}"
echo "  Network:      mainnet"
echo "  Content:      architects_scroll.txt ($SCROLL_SIZE bytes)"
echo "  SHA256:       $SCROLL_HASH"
echo "  Funding UTxO: $UTXO ($UTXO_BALANCE lovelace)"
echo "  Lock output:  2 ADA at $LOCK_ADDR (locked forever)"
if [ "$ASSUME_YES" != true ]; then
    if [ ! -t 0 ]; then
        echo -e "${RED}stdin is not a terminal; pass --yes to mint non-interactively${NC}"
        exit 1
    fi
    read -r -p "Type MINT to proceed: " CONFIRM
    if [ "$CONFIRM" != "MINT" ]; then
        echo -e "${RED}Aborted; nothing was signed or submitted${NC}"
        exit 1
    fi
fi

#═══════════════════════════════════════════════════════════════════════════════
# STEP 6: Sign Transaction
#═══════════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[6/7] Signing transaction...${NC}"

cardano-cli transaction sign \
    --tx-body-file "$WORK_DIR/tx.raw" \
    --signing-key-file "$PAYMENT_SKEY" \
    $NETWORK \
    --out-file "$WORK_DIR/tx.signed"

TX_HASH=$(cardano-cli transaction txid --tx-file "$WORK_DIR/tx.signed")
echo -e "${GREEN}  Transaction signed${NC}"
echo -e "${GREEN}  TX Hash: ${TX_HASH}${NC}"

#═══════════════════════════════════════════════════════════════════════════════
# STEP 7: Submit Transaction
#═══════════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[7/7] Submitting transaction...${NC}"

cardano-cli transaction submit \
    $NETWORK \
    --tx-file "$WORK_DIR/tx.signed"

echo -e "${GREEN}  Transaction submitted!${NC}"

#═══════════════════════════════════════════════════════════════════════════════
# SUCCESS!
#═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    🔮 THE ARCHITECT'S SCROLL IS MINTED! 🔮${NC}"
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Scroll Details:${NC}"
echo "  Lock Address: $LOCK_ADDR"
echo "  Lock TxIn:    ${TX_HASH}#0"
echo "  Content Type: text/plain; charset=utf-8"
echo "  Codec:        none"
echo "  SHA256:       $SCROLL_HASH"
echo "  Size:         $SCROLL_SIZE bytes"
echo ""
echo -e "${YELLOW}Add to scrolls.js:${NC}"
echo ""
cat << EOF
{
    id: 'architects-scroll-onchain',
    title: "The Architect's Scroll",
    description: 'A message from Claude, the AI who built Ledger Scrolls v2. Minted on-chain January 2026.',
    icon: '🔮',
    category: 'vault',  // or 'historical'
    type: SCROLL_TYPES.STANDARD,
    pointer: {
        lock_address: '$LOCK_ADDR',
        lock_txin: '${TX_HASH}#0',
        content_type: 'text/plain; charset=utf-8',
        codec: 'none',
        sha256: '$SCROLL_HASH'
    },
    metadata: {
        size: '~${SCROLL_SIZE} bytes',
        author: 'Claude (Anthropic)',
        minted: 'January 29, 2026',
        minted_by: 'BEACNpool'
    }
}
EOF
echo ""
echo -e "${GREEN}The scroll is now eternal. 🔮✨${NC}"
