#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
#                    VERIFY A STANDARD SCROLL
#                    Ledger Scrolls — A Library That Cannot Burn
#═══════════════════════════════════════════════════════════════════════════════
#
# This script verifies a Standard Scroll: the UTxO exists, the datum is
# readable, and the reconstructed content hashes to the expected sha256
# (the registry publishes the hash of the DECODED content, so pass the
# scroll's codec for gzip scrolls).
#
# Usage:
#   ./verify-scroll.sh <lock-address> <tx-hash> [expected-sha256] [codec]
#
#   codec: none (default) or gzip
#
# Exit codes: 0 = verified, 1 = failed, 2 = present but not verified
#             (no expected sha256 supplied)
#
# Prerequisites:
#   - cardano-cli installed
#   - cardano-node running and synced
#   - CARDANO_NODE_SOCKET_PATH set
#
#═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${PURPLE}"
echo "═══════════════════════════════════════════════════════════════════════"
echo "              🔍 LEDGER SCROLLS — SCROLL VERIFIER 🔍"
echo "═══════════════════════════════════════════════════════════════════════"
echo -e "${NC}"

LOCK_ADDR="${1:-}"
TX_HASH="${2:-}"
EXPECTED_SHA256="${3:-}"
CODEC="${4:-none}"

if [ -z "$LOCK_ADDR" ] || [ -z "$TX_HASH" ]; then
    echo -e "${RED}Usage: $0 <lock-address> <tx-hash> [expected-sha256] [none|gzip]${NC}"
    exit 1
fi

if [ "$CODEC" != "none" ] && [ "$CODEC" != "gzip" ]; then
    echo -e "${RED}Error: codec must be none or gzip${NC}"
    exit 1
fi

# Check for socket
if [ -z "${CARDANO_NODE_SOCKET_PATH:-}" ]; then
    for path in "/opt/cardano/cnode/sockets/node.socket" "$HOME/.cardano/node.socket"; do
        if [ -S "$path" ]; then
            export CARDANO_NODE_SOCKET_PATH="$path"
            break
        fi
    done
fi

NETWORK="--mainnet"
WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

#═══════════════════════════════════════════════════════════════════════════════
# Query UTxO at lock address
#═══════════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[1/3] Querying lock address...${NC}"

cardano-cli query utxo \
    --address "$LOCK_ADDR" \
    $NETWORK \
    --out-file "$WORK_DIR/utxos.json"

# Check if the specific UTxO exists
UTXO_KEY="${TX_HASH}#0"
UTXO_EXISTS=$(jq -r --arg key "$UTXO_KEY" 'has($key)' "$WORK_DIR/utxos.json")

if [ "$UTXO_EXISTS" != "true" ]; then
    echo -e "${RED}✗ UTxO not found at ${TX_HASH}#0${NC}"
    echo ""
    echo "Possible reasons:"
    echo "  - Transaction hasn't been confirmed yet"
    echo "  - Wrong lock address"
    echo "  - Wrong transaction hash"
    exit 1
fi

LOCKED_ADA=$(jq -r --arg key "$UTXO_KEY" '.[$key].value.lovelace' "$WORK_DIR/utxos.json")
echo -e "${GREEN}✓ UTxO found!${NC}"
echo -e "${GREEN}  Locked ADA: $(echo "scale=2; $LOCKED_ADA / 1000000" | bc) ADA${NC}"

#═══════════════════════════════════════════════════════════════════════════════
# Check for inline datum
#═══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BLUE}[2/3] Checking inline datum...${NC}"

HAS_DATUM=$(jq -r --arg key "$UTXO_KEY" '.[$key] | has("inlineDatum")' "$WORK_DIR/utxos.json")

if [ "$HAS_DATUM" != "true" ]; then
    echo -e "${RED}✗ No inline datum found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Inline datum present${NC}"

# Extract content from datum
CONTENT_HEX=$(jq -r --arg key "$UTXO_KEY" '.[$key].inlineDatum.fields[0].bytes // .[$key].inlineDatum.bytes // empty' "$WORK_DIR/utxos.json")

if [ -z "$CONTENT_HEX" ]; then
    echo -e "${RED}✗ Could not extract content from datum (non-standard format)${NC}"
    echo -e "${RED}  The UTxO exists but its content cannot be verified by this tool${NC}"
    exit 1
fi

# Convert hex to bytes, then decode per the scroll's codec — the published
# sha256 is of the DECODED content
echo "$CONTENT_HEX" | xxd -r -p > "$WORK_DIR/content.bin"
CONTENT_SIZE=$(wc -c < "$WORK_DIR/content.bin")
echo -e "${GREEN}  Content size: ${CONTENT_SIZE} bytes (on-chain, codec $CODEC)${NC}"

if [ "$CODEC" = "gzip" ]; then
    if ! gzip -dc "$WORK_DIR/content.bin" > "$WORK_DIR/content.decoded"; then
        echo -e "${RED}✗ Datum bytes are not valid gzip${NC}"
        exit 1
    fi
else
    cp "$WORK_DIR/content.bin" "$WORK_DIR/content.decoded"
fi
DECODED_SIZE=$(wc -c < "$WORK_DIR/content.decoded")

#═══════════════════════════════════════════════════════════════════════════════
# Verify SHA256
#═══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BLUE}[3/3] Verifying integrity...${NC}"

ACTUAL_SHA256=$(sha256sum "$WORK_DIR/content.decoded" | cut -d' ' -f1)
echo -e "${GREEN}  Actual SHA256 (decoded): ${ACTUAL_SHA256}${NC}"

if [ -n "$EXPECTED_SHA256" ]; then
    if [ "$ACTUAL_SHA256" == "$EXPECTED_SHA256" ]; then
        echo -e "${GREEN}✓ SHA256 matches expected hash!${NC}"
    else
        echo -e "${RED}✗ SHA256 mismatch!${NC}"
        echo -e "${RED}  Expected: ${EXPECTED_SHA256}${NC}"
        echo -e "${RED}  Actual:   ${ACTUAL_SHA256}${NC}"
        if [ "$CODEC" = "none" ]; then
            echo -e "${YELLOW}  If this is a gzip scroll, re-run with codec 'gzip'${NC}"
        fi
        exit 1
    fi
fi

#═══════════════════════════════════════════════════════════════════════════════
# Summary
#═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════${NC}"
if [ -n "$EXPECTED_SHA256" ]; then
    echo -e "${GREEN}              ✓ SCROLL VERIFIED ✓${NC}"
else
    echo -e "${YELLOW}          SCROLL PRESENT — NOT VERIFIED (no expected sha256 supplied)${NC}"
fi
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Lock Address: $LOCK_ADDR"
echo "  TX Hash:      $TX_HASH"
echo "  Locked ADA:   $(echo "scale=2; $LOCKED_ADA / 1000000" | bc) ADA"
echo "  Codec:        $CODEC"
echo "  Size:         $DECODED_SIZE bytes decoded ($CONTENT_SIZE on-chain)"
echo "  SHA256:       $ACTUAL_SHA256"
echo ""
if [ -n "$EXPECTED_SHA256" ]; then
    echo -e "${CYAN}This scroll is permanent and verified. 📜✨${NC}"
    exit 0
fi
echo -e "${YELLOW}Pass the published sha256 (and codec) to actually verify the content.${NC}"
exit 2
