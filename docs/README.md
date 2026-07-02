# Ledger Scrolls Documentation

Start at the top and stop when you know enough. Every path below is real —
each guide is backed by scrolls live on mainnet today.

## 🌱 Start here (no experience needed)

| Read this | To learn |
|---|---|
| [YOUR_FIRST_SCROLL.md](YOUR_FIRST_SCROLL.md) | The 10-minute path from "I have a file" to "it's on-chain, verified, forever" |
| [Create a Scroll (web guide)](https://beacnpool.github.io/ledger-scrolls/create.html) | The friendly browser version: costs, an interactive estimator, the full workflow |
| [Cost Calculator](https://beacnpool.github.io/ledger-scrolls/calculator.html) | Drop a file in your browser → one price to make it permanent, exact hashes, metadata builder |
| [VIEWERS.md](VIEWERS.md) | The ways to read scrolls — browser, CLI, Python |
| [BUILD_A_READER.md](BUILD_A_READER.md) | Write your own reader — the whole protocol is two queries and a hash |

## ✍️ Creating scrolls

| Read this | To learn |
|---|---|
| [CREATING_SCROLLS.md](CREATING_SCROLLS.md) | Best practices for every media type: text, images, HTML, PDF, audio, video, data |
| [GETTING_STARTED.md](GETTING_STARTED.md) | Environment setup: cardano-cli, node access, wallet |
| [PREVIEW_TESTNET_POC.md](PREVIEW_TESTNET_POC.md) | Rehearse the whole pipeline on testnet — the mistakes are free |
| [CREATING_LEGAL_RECORDS.md](CREATING_LEGAL_RECORDS.md) | Signature-controlled legal dockets with numbered document tokens |

## 📖 Reading & verifying

| Read this | To learn |
|---|---|
| [KOIOS_CLI.md](KOIOS_CLI.md) | Zero-dependency verification with plain Python |
| [EXAMPLES.md](EXAMPLES.md) | The gallery — every live scroll's story, with links to source + receipts |
| [SCROLL_INVENTORY.md](SCROLL_INVENTORY.md) | Every live scroll: pointers, hashes, policy IDs, proof walkthrough |

## 🔬 The protocol (for implementers)

| Read this | To learn |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | How the stack fits together — and which layers are allowed to die |
| [PROTOCOL_V1_PROPOSAL.md](PROTOCOL_V1_PROPOSAL.md) | The normative spec: pointer kinds, encoding, verification, failure semantics |
| [STANDARD_SCROLLS.md](STANDARD_SCROLLS.md) | Standard Scrolls: one file in one locked UTxO datum (small files, strongest guarantee) |
| [../registry/spec/manifest-chain-v2.md](../registry/spec/manifest-chain-v2.md) | Chain Scrolls: any size, bare metadata pages + manifest (the standard write format) |
| [LEGACY_SCROLLS.md](LEGACY_SCROLLS.md) | Original NFT pages (how the historical scrolls are read) |
| [../registry/spec/publisher-channel-v1.md](../registry/spec/publisher-channel-v1.md) | Publisher channels: a minting policy as an unforgeable byline |
| [../registry/](../registry/) | Registry spec, pointer schemas, tooling |
| [../conformance/](../conformance/) | Test vectors — run `python3 conformance/run_conformance.py` or `node conformance/run_conformance.mjs` |

## 🗄️ Project history

Design reviews and audits that shaped the protocol live in
[history/](history/). Prior-art implementations (the 2026 React app, the
experimental P2P viewer) were removed from the working tree in July 2026 and
remain in git history.
