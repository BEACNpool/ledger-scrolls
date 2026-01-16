#!/bin/bash

echo "📜 Ledger Scrolls Installer"
echo "======================================"

# Check Python
if command -v python3 > /dev/null; then
  echo "[✔] Python 3 detected."
else
  echo "[!] Python 3 not found. Install it first."
  exit 1
fi

# Check Oura
if command -v oura > /dev/null; then
  echo "[✔] Oura blockchain driver detected."
else
  echo "[!] 'oura' binary not found in PATH."
  echo "Install option:"
  echo "If you have Rust/Cargo installed, run: cargo install oura"
  echo "Or download a release from: https://github.com/txpipe/oura/releases"
  read -p "Continue anyway? (The script will fail without it later) [y/N] " -n 1 -r
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Install deps
pip3 install -r requirements.txt

# Create launcher
cat > scroll << EOF
#!/usr/bin/env bash
cd "\$(dirname "\$0")"
python3 src/main.py "\$@"
EOF
chmod +x scroll
echo "[✔] Created launcher at: \$(pwd)/scroll"

# Create config if not exists
if [ ! -f config.yaml ]; then
  cat > config.yaml << EOF
driver: oura
relays:
  - Tcp:relays-new.cardano-mainnet.iohk.io:3001
blockfrost_key: ""  # Optional for hash lookup
registry_address: "UPDATE_once_built_addr1_YOUR_TOWN_SQUARE_ADDRESS_HERE"
EOF
fi

echo "======================================"
echo "Installation Complete!"
echo "To use, run: ./scroll help"
echo "PRO TIP: Add to PATH: export PATH=\$PATH:\$(pwd)"
