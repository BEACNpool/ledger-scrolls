# Ledger Scrolls + Ledger Book

**Preserve an original. Grow a record. Built by BEACN.**

Two independent products live in this app:

- **Ledger Scrolls** preserves finished files inside Cardano transactions. Read,
  reconstruct, check fingerprints, and recover original bytes.
- **Ledger Book** collects public entries around a person, project, or occasion.
  Its NFT provides a book identity that follows its ownership history.

Either works on its own. A new Book can optionally attach a Scroll's exact
pointer and fingerprint, giving readers a path between entries and an original.
The shared app, saved shelf, and BEACN branding connect them without making one
a requirement of the other.

## Use the products

| Product | Start here | Purpose |
|---|---|---|
| Ledger Scrolls | [Library](https://beacnpool.github.io/ledger-scrolls/index.html) | Read and check preserved originals |
| Ledger Scrolls | [Preserve a file](https://beacnpool.github.io/ledger-scrolls/calculator.html) | Prepare locally, review cost, publish with a wallet |
| Ledger Book | [Open a book](https://beacnpool.github.io/ledger-scrolls/ledger-book.html) | Find a book and read its entries |
| Ledger Book | [Create a book](https://beacnpool.github.io/ledger-scrolls/ledger-book.html?create=1) | Personal book, project log, or event guestbook |
| Both | [Guide](https://beacnpool.github.io/ledger-scrolls/media.html) | Independent uses, optional connection, costs and limits |

Existing mainnet Books, Scroll pointers, and public URLs remain compatible.
The actual records live on-chain. Links, bookmarks and the app help find them;
browser storage is not their canonical record.

## Connect them when useful

After publishing or reading a Scroll, choose **Create a Book about this Scroll**.
The new Book NFT can carry its transaction/output pointer and decoded SHA-256 in
mint metadata. Sharing the Book gives readers access to that exact original.

An attachment is optional and cannot be changed after minting. Book entries do
not imply endorsement or acceptance of a work. Names are self-declared; input
addresses attribute transactions, not verified human identities. Book starters
suggest names only: every Book remains public, with the same entry rules.

[First principles and brand architecture](docs/PRODUCT.md) ·
[Book attachment extension](registry/spec/book-subject-v1.md)

## What is checked

The reader reconstructs bytes and computes SHA-256 locally. When a fingerprint is
available, it shows its source and compares the bytes; mismatch blocks rendering.
Without a declared fingerprint, the file remains explicitly unverified. A hash
computed from the same downloaded bytes is not an independent commitment.

The reader relies on provider data for chain facts. It does not verify consensus
or block inclusion proofs. A hash match establishes consistency, not authorship,
factual truth, or independent evidence that the provider reported Cardano
accurately. Use independent providers or a node for stronger chain verification.

Book policy checks reconstruct the native script and compare its hash to the
policy ID. Supply one is required explicitly. Uniqueness becomes final only once
the verified mint policy expires. Keeper-payment checks use returned ownership
history; missing or ambiguous history is unresolved, not green.

HTML renders in a script-disabled sandbox with network access blocked. Downloaded
original bytes are unchanged. External images/fonts in a work may therefore be
absent in its safe reader view.

## Permanence and cost

Content is public. A pointer is not a privacy mechanism. Availability depends on
Cardano, retained transaction history, accessible providers and working decoders.
There is no unconditional promise of forever.

Publishing costs network fees and, for locked storage, irrecoverably locked ADA.
Large files need multiple transactions and wallet approvals. Guest entries pay
an anchor to the book's keeper plus a network fee. Minimum ADA accompanying a
Book NFT stays with its holder. The application charges no platform fee.

The publishing tool estimates cost from the prepared bytes and refreshes network
parameters when connected. Review the actual transaction in the wallet. Paid
entries are not spam-proof, and a blockchain record is not automatically legal
proof of identity or ownership.

## Storage formats and compatibility

| Format | Storage | Role |
|---|---|---|
| Standard Scroll | A file in an always-fail UTxO datum | Compact files |
| Chain Scroll | Metadata pages named by a locked manifest | Larger files |
| Legacy CIP-25 pages | Original page NFTs and manifest metadata | Historical reading |
| Ledger Book v2 | NFT under a signature + expiry native policy | Guestbook identity |
| Book entries | Transaction metadata label 22031 and keeper payment | Public guest entries |

Original URLs, metadata labels and minted originals remain readable. New browser
Book links can use `policy.0xASSETHEX` to distinguish raw name bytes from legacy
ASCII names. A Book subject is an optional backward-compatible metadata field;
it does not change the underlying mint policy or entry protocol.

- [Registry wire format](registry/spec/format.md)
- [Chain Scroll wire format](registry/spec/manifest-chain-v2.md)
- [Book v1](registry/spec/ledger-book-v1.md) · [Book v2](registry/spec/ledger-book-v2.md)
- [Book subject v1](registry/spec/book-subject-v1.md)
- [Publisher channels](registry/spec/publisher-channel-v1.md)
- [Countersigned scrolls](registry/spec/countersigned-scroll-v1.md)
- [Inventory and receipts](docs/SCROLL_INVENTORY.md)

## Reconstruct independently

The repo includes a dependency-free Python reader, reconstruction tooling,
conformance vectors, specs, and an on-chain reference reader.

```bash
python3 viewers/koios-cli/read_scroll.py --list
python3 conformance/run_conformance.py
node conformance/run_conformance.mjs
python3 conformance/check_schemas.py
```

For larger reconstruction tasks, install `koios-viewer/requirements.txt` in a
virtual environment and use its `lsview` CLI. Read [Build a Reader](docs/BUILD_A_READER.md)
and [Your First Scroll](docs/YOUR_FIRST_SCROLL.md) before using minting scripts.
Never put keys into the repository or publish them with build artifacts.

## Development

The browser pages remain standalone HTML/CSS/JavaScript. There is no runtime
framework or CDN dependency. Serve the repository with any static HTTP server.
Shared navigation and styling are generated at edit time:

```bash
python3 scripts/sync_nav.py
python3 scripts/sync_nav.py --check
node scripts/check_inline_js.mjs
node scripts/check_frozen_files.mjs
```

The CI workflow includes protocol/schema tests, Python readers, syntax checks,
cost-model parity, navigation parity, mirror lists, and frozen on-chain artwork.
[Browser regression instructions](docs/UNIFIED_VALIDATION.md) cover synthetic
wallets, exact token change, policy verification and the combined publishing flow.

Device-local drafts and saved shelves do not sync between devices or mirrors.
The existing publishing vault remains available; download receipts and drafts
before clearing browser data.

The new Book attachment extension has synthetic transaction coverage; it has not
received a new mainnet acceptance mint. An independently operated second browser
mirror and long-history pagination remain infrastructure follow-ups. No private
key, production-node change or new chain transaction was needed for this rebuild.

MIT · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)
