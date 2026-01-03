[README.md](https://github.com/user-attachments/files/24418634/README.md)
# Ledger Scrolls Viewer

An open-source, minimal viewer for **Ledger Scrolls** — a proposed standard for storing immutable, timeless data on the Cardano blockchain using NFTs.

This is a lean, community-driven proof-of-concept designed to be forked, extended, and improved by anyone.

## Vision

Ledger Scrolls enables eternal, decentralized preservation of knowledge — any text, document, or structured data — split across NFTs with cryptographic integrity checks. It is neutral, open, and intended for any subject, faith, culture, or domain.

## Features

- Minimal dependencies (`requests` only)
- Asks only for Policy ID and Blockfrost API key
- Reconstructs the full scroll into `ledger_scroll.html` in the same folder
- Verifies SHA-256 checksums from manifest
- Works with any compliant Ledger Scrolls policy

## Installation & Usage

```bash
# 1. Clone the repo
git clone https://github.com/BEACNpool/ledger-scrolls.git
cd ledger-scrolls

# 2. Install dependency
pip install requests

# 3. Run the viewer
python viewer.py
