#!/bin/bash

# --- Styling ---
BOLD="\033[1m"
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[1;33m"
RESET="\033[0m"

echo -e "${BOLD}📜 Ledger Scrolls Installer${RESET}"
echo "======================================"

# --- Step 1: Check Dependencies ---

# 1. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[X] Python 3 is missing.${RESET}"
    echo "    Please install Python 3 to continue."
    exit 1
fi
echo -e "${GREEN}[✔] Python 3 detected.${RESET}"

# 2. Check for Oura (The Blockchain Connector)
if ! command -v oura &> /dev/null; then
    echo -e "${YELLOW}[!] 'oura' binary not found in PATH.${RESET}"
    echo "    Ledger Scrolls requires 'oura' to connect to Cardano."
    echo ""
    echo -e "    ${BOLD}Install option:${RESET}"
    echo "    If you have Rust/Cargo installed, run: ${YELLOW}cargo install oura${RESET}"
    echo "    Or download a release from: https://github.com/txpipe/oura/releases"
    echo ""
    read -p "    Continue anyway? (The script will fail without it later) [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}[✔] Oura blockchain driver detected.${RESET}"
fi

# --- Step 2: Setup Directories ---

# Get the directory where this install script is running
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONFIG_DIR="$INSTALL_DIR/config"
MANIFEST="$CONFIG_DIR/manifest.json"

# Create config directory if missing
if [ ! -d "$CONFIG_DIR" ]; then
    echo "    Creating config directory..."
    mkdir -p "$CONFIG_DIR"
fi

# --- Step 3: Create the 'scroll' Launcher ---

LAUNCHER_PATH="$INSTALL_DIR/scroll"

echo -e "#!/bin/bash\npython3 \"$INSTALL_DIR/main.py\" \"\$@\"" > "$LAUNCHER_PATH"
chmod +x "$LAUNCHER_PATH"

echo -e "${GREEN}[✔] Created launcher at: $LAUNCHER_PATH${RESET}"

# --- Step 4: Final Instructions ---

echo ""
echo "======================================"
echo -e "${GREEN}${BOLD}Installation Complete!${RESET}"
echo ""
echo "To use Ledger Scrolls, you can now run:"
echo -e "   ${YELLOW}./scroll help${RESET}"
echo ""
echo "PRO TIP: Add this directory to your PATH to run 'scroll' from anywhere."
echo -e "   ${BOLD}export PATH=\$PATH:$INSTALL_DIR${RESET}"
echo ""
