# BEACN archive lookup

`lookup.py` lists every Ledger Scroll and every NFT that BEACN minted (22 scrolls and 69 mints) and gets any of
them straight from Cardano through the free public Koios API. It needs Python 3.8 or newer and nothing else.
Rebuilding scrolls also uses the open `lsview` reader in [`koios-viewer/`](../koios-viewer/).

| Command | What it does |
|---|---|
| `python3 archive/lookup.py` | Menu: choose a group and an item, see its command, and fetch it if you like |
| `python3 archive/lookup.py --list` | Every item and its id |
| `python3 archive/lookup.py <id>` | Show one item and the command to paste |
| `python3 archive/lookup.py get <id> [--out DIR]` | Fetch it now |

- **Mints:** the tool reads the NFT's own minting metadata and decodes its on-chain image, plus its playable
  program when it has one. Nothing is downloaded from anywhere but Koios.
- **Scrolls:** the tool runs `lsview`, which rebuilds the file page by page and checks it against the hash
  recorded on chain. Install the reader once:
  `cd koios-viewer && python3 -m venv .venv && . .venv/bin/activate && pip install -e . && cd ..`
- [`catalog.json`](catalog.json) was generated from the chain on 15 September 2026. Set `KOIOS_BASE` to use any
  other Koios-compatible endpoint.

Everything here is also readable in a browser, with an in-browser hash check, in the
[BEACN legacy archive](https://beacnpool.github.io/ABCDE/pool/#library).
