# Ledger Scrolls 📜

> "A library that cannot burn."

**Ledger Scrolls** is an open-source protocol and tool for publishing and reading immutable data on Cardano. It enables lightweight "edge nodes" to discover and reconstruct scrolls without full nodes or central APIs.

## Ethos & Vision

Preserve knowledge in a decentralized way. Creators publish scrolls as metadata chunks; viewers stream via P2P/light clients. Overhauled for reliability: multiple drivers, caching, easy setup.

## Quick Start (Fixed for Oura v2)

1. Clone & Install (Python 3 required):
   ```
   git clone https://github.com/BEACNpool/ledger-scrolls.git
   cd ledger-scrolls
   pip install -r requirements.txt  # Adds ogmios-python, requests
   chmod +x install.sh
   ./install.sh
   ```

2. Run (use Oura driver by default; switch in config.yaml):
   ```
   scroll registry  # Discover new beacons
   scroll list      # List saved
   scroll read "The Cardano Bible"  # Reconstruct
   ```

## Protocol Spec

See PROTOCOL.md for Beacon JSON, registration, reconstruction.

## Architecture

See ARCHITECTURE.md for diagram.

## Drivers

- **Oura**: P2P streaming (unfiltered + Python filter for 777).
- **Ogmios**: WebSocket queries (easy slot/policy filtering).
- **Mithril**: Snapshot-based historical access (subprocess to client binary).

Config in `config.yaml`:
```
driver: ogmios  # or oura, mithril
relays:
  - Tcp:relays-new.cardano-mainnet.iohk.io:3001
blockfrost_key: ""  # Optional for hash lookup
registry_address: "UPDATE_once_built_addr1_YOUR_TOWN_SQUARE_ADDRESS_HERE"
```

## Contributing

PRs welcome! See ARCHITECTURE.md for extensions.

License: MIT  
Maintained by @BEACNpool.org
