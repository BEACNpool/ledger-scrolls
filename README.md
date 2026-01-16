
# Ledger Scrolls 📜

> "A library that cannot burn."

**Ledger Scrolls** is an open-source protocol and tool for publishing and reading immutable data on Cardano.  
It enables lightweight "edge nodes" to discover and reconstruct scrolls without full nodes or central APIs.

## Ethos & Vision

Preserve knowledge in a decentralized way.  
Creators publish scrolls as metadata chunks; viewers stream via P2P/light clients.  
Overhauled for reliability: multiple drivers, caching, easy setup.

## Quick Start

1. Clone & Install (Python 3 required):

```bash
git clone https://github.com/BEACNpool/ledger-scrolls.git
cd ledger-scrolls
pip install -r requirements.txt
chmod +x install.sh
./install.sh          # Installs dependencies + creates config.yaml if missing
```

2. Configure `config.yaml` (choose driver, relays, registry address, etc.)

3. Run:

```bash
./scroll registry               # Discover new beacons / registrations
./scroll list                   # List saved scrolls
./scroll read "The Cardano Bible"  # Reconstruct from stream/cache → HTML
```

## Protocol Specification

See [PROTOCOL.md](PROTOCOL.md) for full details about:
- Beacon registration format
- Metadata chunk structure
- Reconstruction rules

## Architecture Overview

See [ARCHITECTURE.md](ARCHITECTURE.md) for component diagram and flow explanation.

## Supported Drivers

| Driver    | Type              | Reliability | Setup Difficulty | Notes                              |
|-----------|-------------------|-------------|------------------|------------------------------------|
| **Oura**  | P2P streaming     | ★★★★        | ★★               | Default, native Cardano relay      |
| **Ogmios**| WebSocket queries | ★★★★        | ★                | Fast filtering, easy local node    |
| **Mithril**| Snapshots        | ★★★★★       | ★★★              | Historical access (coming soon)    |

Current config example (`config.yaml`):

```yaml
driver: oura          # or ogmios (mithril coming soon)
relays:
  - tcp://relays-new.cardano-mainnet.iohk.io:3001
registry_address: "addr1...your_town_square_beacon_address_here..."
cache_dir: "cache"    # Where streamed metadata is saved locally
```

## Features

- **Decentralized discovery** via beacon registrations on Cardano
- **Local caching** of streamed metadata chunks (resumable & offline reconstruction)
- **Driver fallback** — automatically tries secondary driver if primary fails
- **Integrated reconstruction** — collects chunks → concatenates → gzip decompress → saves HTML/website
- **One-command install** via improved `install.sh`
- **No Blockfrost** or centralized APIs required

## Currently Minted & Reconstructible Scrolls

- **The Cardano Bible**  
  Policy ID: `2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0`

- **Bitcoin Whitepaper**  
  Policy ID: `8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1`

## Contributing

PRs are very welcome!  
Especially helpful areas right now:

- Full Mithril driver implementation
- Better error recovery & multi-driver parallel streaming
- GUI viewer / browser extension
- More example scrolls & documentation

License: MIT

Maintained with ❤️ by [@BEACNpool](https://x.com/BEACNpool)
```
