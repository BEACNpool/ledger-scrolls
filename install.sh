#!/bin/bash

# --- Styling ---
BOLD="\033[1m"
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[1;33m"
RESET="\033[0m"

echo -e "${BOLD}Ledger Scrolls Installer${RESET}"
echo "======================================"

# --- Step 1: Check Dependencies ---

# 1. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[X] Python 3 is missing.${RESET}"
    echo "    Please install Python 3 to continue."
    exit 1
fi
echo -e "${GREEN}[✔] Python 3 detected.${RESET}"

# 2. Install Python dependencies
echo "Installing Python requirements..."
pip3 install -r requirements.txt
echo -e "${GREEN}[✔] Python dependencies installed.${RESET}"

# 3. Check/Install Rust/Cargo for Oura
if ! command -v cargo &> /dev/null; then
    echo -e "${YELLOW}[!] Rust/Cargo not found. Installing...${RESET}"
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
else
    echo -e "${GREEN}[✔] Rust/Cargo detected.${RESET}"
fi

# 4. Check/Install Oura
if ! command -v oura &> /dev/null; then
    echo -e "${YELLOW}[!] Installing Oura via Cargo...${RESET}"
    cargo install oura
else
    echo -e "${GREEN}[✔] Oura detected.${RESET}"
fi

# --- Step 2: Setup Directories ---

INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONFIG_DIR="$INSTALL_DIR/config"
CACHE_DIR="$INSTALL_DIR/cache"
MANIFEST="$CONFIG_DIR/scrolls_manifest.json"
CONFIG_YAML="$INSTALL_DIR/config.yaml"

# Create config dir
mkdir -p "$CONFIG_DIR"
mkdir -p "$CACHE_DIR"

# Create sample config.yaml if missing
if [ ! -f "$CONFIG_YAML" ]; then
    echo "Creating sample config.yaml..."
    cat << EOF > "$CONFIG_YAML"
driver: oura  # or ogmios, mithril
relays:
  - tcp://relays-new.cardano-mainnet.iohk.io:3001
registry_address: "UPDATE_once_built_addr1_YOUR_TOWN_SQUARE_ADDRESS_HERE"
cache_dir: "cache"
EOF
    echo -e "${GREEN}[✔] config.yaml created. Edit it with your settings.${RESET}"
fi

# Create manifest if missing (moved to scrolls_manifest.json)
if [ ! -f "$MANIFEST" ]; then
    echo "Creating sample scrolls_manifest.json..."
    cat << EOF > "$MANIFEST"
{
    "registry_settings": {
        "registry_address": "UPDATE_once_built_addr1_YOUR_TOWN_SQUARE_ADDRESS_HERE",
        "listen_network": "mainnet"
    },
    "known_scrolls": {
        "The Cardano Bible": {
            "policy_id": "2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0",
            "start_slot": 115000450,
            "structure": "Book/Text",
            "description": "The Holy Bible on Cardano"
        },
        "BTC Whitepaper": {
            "policy_id": "8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1",
            "start_slot": 100000000,
            "structure": "Document/PDF",
            "description": "Satoshi's Vision"
        }
    }
}
EOF
    echo -e "${GREEN}[✔] scrolls_manifest.json created.${RESET}"
fi

# --- Step 3: Create 'scroll' Launcher ---

LAUNCHER_PATH="$INSTALL_DIR/scroll"

echo -e "#!/bin/bash\npython3 \"$INSTALL_DIR/src/main.py\" \"\$@\"" > "$LAUNCHER_PATH"
chmod +x "$LAUNCHER_PATH"

echo -e "${GREEN}[✔] Created launcher at: $LAUNCHER_PATH${RESET}"

# --- Step 4: Final Instructions ---

echo ""
echo "======================================"
echo -e "${GREEN}${BOLD}Installation Complete!${RESET}"
echo ""
echo "To use Ledger Scrolls, edit config.yaml, then run:"
echo -e "   ${YELLOW}./scroll help${RESET}"
echo ""
echo "PRO TIP: Add this directory to your PATH to run 'scroll' from anywhere."
echo -e "   ${BOLD}export PATH=\$PATH:$INSTALL_DIR${RESET}"
echo ""
