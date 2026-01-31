#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
#                    MINT A STANDARD SCROLL (LS-LOCK v1)
#                    Ledger Scrolls — A Library That Cannot Burn
#═══════════════════════════════════════════════════════════════════════════════
#
# This script mints any file as a permanent Standard Scroll on Cardano.
# The content is locked forever in an unspendable UTxO.
#
# Usage:
#   ./mint-standard-scroll.sh <content-file> <payment.skey> <payment.addr> [--compress]
#
# Options:
#   --compress    Gzip compress the content before minting (recommended for >4KB)
#
# Prerequisites:
#   - cardano-cli installed
#   - cardano-node running and synced
#   - CARDANO_NODE_SOCKET_PATH set
#   - Payment keys with sufficient ADA (~3-15 ADA depending on size)
#
#═══════════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_banner() {
    echo -e "${PURPLE}"
    echo "═══════════════════════════════════════════════════════════════════════"
    echo "            📜 LEDGER SCROLLS — STANDARD SCROLL MINTER 📜"
    echo "═══════════════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

print_banner

# Parse arguments
CONTENT_FILE=""
PAYMENT_SKEY=""
PAYMENT_ADDR=""
COMPRESS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --compress)
            COMPRESS=true
            shift
            ;;
        *)
            if [ -z "$CONTENT_FILE" ]; then
                CONTENT_FILE="$1"
            elif [ -z "$PAYMENT_SKEY" ]; then
                PAYMENT_SKEY="$1"
            elif [ -z "$PAYMENT_ADDR" ]; then
                PAYMENT_ADDR="$1"
            fi
            shift
            ;;
    esac
done

# Validate arguments
if [ -z "$CONTENT_FILE" ] || [ -z "$PAYMENT_SKEY" ] || [ -z "$PAYMENT_ADDR" ]; then
    echo -e "${RED}Usage: $0 <content-file> <payment.skey> <payment.addr> [--compress]${NC}"
    echo ""
    echo "  content-file  - The file to inscribe permanently"
    echo "  payment.skey  - Path to payment signing key"
    echo "  payment.addr  - Path to payment address file (or address string)"
    echo "  --compress    - Optional: gzip compress before minting"
    exit 1
fi

# Validate content file
if [ ! -f "$CONTENT_FILE" ]; then
    echo -e "${RED}Error: Content file not found: $CONTENT_FILE${NC}"
    exit 1
fi

# If payment.addr is a file, read it
if [ -f "$PAYMENT_ADDR" ]; then
    PAYMENT_ADDR=$(cat "$PAYMENT_ADDR")
fi

# Check for cardano-cli
if ! command -v cardano-cli &> /dev/null; then
    echo -e "${RED}Error: cardano-cli not found${NC}"
    echo "Please install cardano-cli: https://developers.cardano.org/docs/get-started/installing-cardano-node/"
    exit 1
fi

# Check for socket
if [ -z "$CARDANO_NODE_SOCKET_PATH" ]; then
    echo -e "${YELLOW}CARDANO_NODE_SOCKET_PATH not set, trying common locations...${NC}"
    for path in "/opt/cardano/cnode/sockets/node.socket" "$HOME/.cardano/node.socket" "/var/run/cardano/node.socket"; do
        if [ -S "$path" ]; then
            export CARDANO_NODE_SOCKET_PATH="$path"
            echo -e "${GREEN}Found socket at: $path${NC}"
            break
        fi
    done
fi

if [ ! -S "$CARDANO_NODE_SOCKET_PATH" ]; then
    echo -e "${RED}Error: Node socket not found at $CARDANO_NODE_SOCKET_PATH${NC}"
    echo "Set CARDANO_NODE_SOCKET_PATH to your node socket location"
    exit 1
fi

NETWORK="--mainnet"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR=$(mktemp -d)
trap "rm -rf $WORK_DIR" EXIT

echo -e "${CYAN}Work directory: $WORK_DIR${NC}"

#═══════════════════════════════════════════════════════════════════════════════
# STEP 1: Create Always-Fail Script
#═══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BLUE}[1/8] Creating always-fail lock script...${NC}"

cat > "$WORK_DIR/always-fail.plutus" << 'EOF'
{
    "type": "PlutusScriptV2",
    "description": "Always fails - Ledger Scrolls permanent lock",
    "cborHex": "4e4d01000033222220051"
}
EOF

LOCK_ADDR=$(cardano-cli address build \
    --payment-script-file "$WORK_DIR/always-fail.plutus" \
    $NETWORK)

echo -e "${GREEN}  ✓ Lock address: ${LOCK_ADDR:0:50}...${NC}"

#═══════════════════════════════════════════════════════════════════════════════
# STEP 2: Prepare Content
#═══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BLUE}[2/8] Preparing scroll content...${NC}"

ORIGINAL_SIZE=$(wc -c < "$CONTENT_FILE")
ORIGINAL_HASH=$(sha256sum "$CONTENT_FILE" | cut -d' ' -f1)
CONTENT_TYPE="application/octet-stream"

# Try to detect content type
case "${CONTENT_FILE,,}" in
    *.txt) CONTENT_TYPE="text/plain; charset=utf-8" ;;
    *.html|*.htm) CONTENT_TYPE="text/html" ;;
    *.json) CONTENT_TYPE="application/json" ;;
    *.png) CONTENT_TYPE="image/png" ;;
    *.jpg|*.jpeg) CONTENT_TYPE="image/jpeg" ;;
    *.gif) CONTENT_TYPE="image/gif" ;;
    *.pdf) CONTENT_TYPE="application/pdf" ;;
    *.md) CONTENT_TYPE="text/markdown" ;;
esac

echo -e "${GREEN}  Original size: ${ORIGINAL_SIZE} bytes${NC}"
echo -e "${GREEN}  SHA256: ${ORIGINAL_HASH}${NC}"
echo -e "${GREEN}  Content type: ${CONTENT_TYPE}${NC}"

# Compress if requested
CODEC="none"
PROCESS_FILE="$CONTENT_FILE"

if [ "$COMPRESS" = true ]; then
    echo -e "${CYAN}  Compressing with gzip...${NC}"
    gzip -c "$CONTENT_FILE" > "$WORK_DIR/content.gz"
    PROCESS_FILE="$WORK_DIR/content.gz"
    CODEC="gzip"
    COMPRESSED_SIZE=$(wc -c < "$PROCESS_FILE")
    echo -e "${GREEN}  Compressed size: ${COMPRESSED_SIZE} bytes ($(( 100 - (COMPRESSED_SIZE * 100 / ORIGINAL_SIZE) ))% smaller)${NC}"
fi

# Convert to hex
CONTENT_HEX=$(xxd -p "$PROCESS_FILE" | tr -d '\n')
HEX_LENGTH=${#CONTENT_HEX}

echo -e "${GREEN}  Hex length: ${HEX_LENGTH} characters${NC}"

# Warn if too large
if [ $HEX_LENGTH -gt 32000 ]; then
    echo -e "${YELLOW}  ⚠️  Warning: Large content. Consider using Legacy Scrolls for files >16KB${NC}"
fi

#═══════════════════════════════════════════════════════════════════════════════
# STEP 3: Create Inline Datum
#═══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BLUE}[3/8] Creating inline datum...${NC}"

cat > "$WORK_DIR/datum.json" << EOF
{
    "constructor": 0,
    "fields": [
        {
            "bytes": "$CONTENT_HEX"
        }
    ]
}
EOF

echo -e "${GREEN}  ✓ Datum created${NC}"

#═══════════════════════════════════════════════════════════════════════════════
# STEP 4: Estimate Minimum ADA
#═══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BLUE}[4/8] Estimating minimum ADA...${NC}"

# Rough estimation: ~5.5 ADA per 1KB of hex content
CONTENT_KB=$(( (HEX_LENGTH / 2) / 1024 + 1 ))
MIN_ADA=$(( CONTENT_KB * 5500000 + 2000000 ))
MIN_ADA_DISPLAY=$(echo "scale=2; $MIN_ADA / 1000000" | bc)

echo -e "${GREEN}  Estimated minimum: ~${MIN_ADA_DISPLAY} ADA${NC}"

#═══════════════════════════════════════════════════════════════════════════════
# STEP 5: Query UTxOs
#═══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BLUE}[5/8] Querying UTxOs at payment address...${NC}"

cardano-cli query utxo \
    --address "$PAYMENT_ADDR" \
    $NETWORK \
    --out-file "$WORK_DIR/utxos.json"

# Find suitable UTxO
REQUIRED_LOVELACE=$(( MIN_ADA + 500000 ))  # Add buffer for fees
UTXO=$(jq -r --argjson req "$REQUIRED_LOVELACE" 'to_entries | map(select(.value.value.lovelace >= $req)) | .[0].key' "$WORK_DIR/utxos.json")

if [ "$UTXO" == "null" ] || [ -z "$UTXO" ]; then
    AVAILABLE=$(jq -r 'to_entries | .[0].value.value.lovelace // 0' "$WORK_DIR/utxos.json")
    echo -e "${RED}Error: No UTxO with >= $(echo "scale=2; $REQUIRED_LOVELACE / 1000000" | bc) ADA found${NC}"
    echo -e "${RED}Available: $(echo "scale=2; $AVAILABLE / 1000000" | bc) ADA${NC}"
    exit 1
fi

UTXO_BALANCE=$(jq -r --arg utxo "$UTXO" '.[$utxo].value.lovelace' "$WORK_DIR/utxos.json")
echo -e "${GREEN}  ✓ Using UTxO: ${UTXO:0:20}...${NC}"
echo -e "${GREEN}  Balance: $(echo "scale=2; $UTXO_BALANCE / 1000000" | bc) ADA${NC}"

#═══════════════════════════════════════════════════════════════════════════════
# STEP 6: Build Transaction
#═══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BLUE}[6/8] Building transaction...${NC}"

cardano-cli transaction build \
    $NETWORK \
    --tx-in "$UTXO" \
    --tx-out "$LOCK_ADDR+$MIN_ADA" \
    --tx-out-inline-datum-file "$WORK_DIR/datum.json" \
    --change-address "$PAYMENT_ADDR" \
    --out-file "$WORK_DIR/tx.raw"

echo -e "${GREEN}  ✓ Transaction built${NC}"

#═══════════════════════════════════════════════════════════════════════════════
# STEP 7: Sign Transaction
#═══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BLUE}[7/8] Signing transaction...${NC}"

cardano-cli transaction sign \
    --tx-body-file "$WORK_DIR/tx.raw" \
    --signing-key-file "$PAYMENT_SKEY" \
    $NETWORK \
    --out-file "$WORK_DIR/tx.signed"

TX_HASH=$(cardano-cli transaction txid --tx-file "$WORK_DIR/tx.signed")
echo -e "${GREEN}  ✓ Transaction signed${NC}"
echo -e "${GREEN}  TX Hash: ${TX_HASH}${NC}"

#═══════════════════════════════════════════════════════════════════════════════
# STEP 8: Submit Transaction
#═══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BLUE}[8/8] Submitting transaction...${NC}"

cardano-cli transaction submit \
    $NETWORK \
    --tx-file "$WORK_DIR/tx.signed"

echo -e "${GREEN}  ✓ Transaction submitted!${NC}"

#═══════════════════════════════════════════════════════════════════════════════
# SUCCESS!
#═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}              📜 YOUR SCROLL IS NOW ETERNAL! 📜${NC}"
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Scroll Details:${NC}"
echo "  File:         $(basename "$CONTENT_FILE")"
echo "  Lock Address: $LOCK_ADDR"
echo "  Lock TxIn:    ${TX_HASH}#0"
echo "  Content Type: $CONTENT_TYPE"
echo "  Codec:        $CODEC"
echo "  SHA256:       $ORIGINAL_HASH"
echo "  Size:         $ORIGINAL_SIZE bytes"
echo "  Locked ADA:   $(echo "scale=2; $MIN_ADA / 1000000" | bc) ADA"
echo ""
echo -e "${YELLOW}Cardanoscan:${NC}"
echo "  https://cardanoscan.io/transaction/${TX_HASH}"
echo ""
echo -e "${YELLOW}Add to js/scrolls.js:${NC}"
echo ""
cat << EOF
{
    id: '$(basename "$CONTENT_FILE" | tr '.' '-' | tr ' ' '-' | tr '[:upper:]' '[:lower:]')',
    title: '$(basename "$CONTENT_FILE")',
    description: 'Your description here',
    icon: '📜',
    category: 'documents',
    type: SCROLL_TYPES.STANDARD,
    pointer: {
        lock_address: '$LOCK_ADDR',
        lock_txin: '${TX_HASH}#0',
        content_type: '$CONTENT_TYPE',
        codec: '$CODEC',
        sha256: '$ORIGINAL_HASH'
    },
    metadata: {
        size: '~$ORIGINAL_SIZE bytes',
        minted: '$(date +%Y-%m-%d)',
        locked_ada: '$(echo "scale=2; $MIN_ADA / 1000000" | bc) ADA'
    }
}
EOF
echo ""
echo -e "${GREEN}The scroll is now permanent. It cannot be deleted, modified, or censored.${NC}"
echo -e "${CYAN}Welcome to the eternal library. 📜✨${NC}"
