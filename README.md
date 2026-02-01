# Ledger Scrolls 📜
https://beacnpool.github.io/ledger-scrolls/
**"A Library That Cannot Burn"**

[![Version](https://img.shields.io/badge/version-2.1.0-gold)](https://github.com/BEACNpool/ledger-scrolls)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Cardano](https://img.shields.io/badge/blockchain-Cardano-blue)](https://cardano.org)
[![Community](https://img.shields.io/badge/built%20for-the%20people-green)](https://beacnpool.org)

---

## What is Ledger Scrolls?

Ledger Scrolls is an **open-source system** for inscribing permanent, immutable documents on the Cardano blockchain. Once written, a scroll can never be deleted, modified, or censored by anyone — not governments, not corporations, not even us.

**This is knowledge preservation for the people, by the people.**

> *"In the digital age, true knowledge must be unstoppable."*

---

## 🌟 Why Ledger Scrolls?

- **Permanent** — Your words outlive servers, companies, and even you
- **Immutable** — No one can alter what you've written
- **Censorship-Resistant** — No authority can remove it
- **Verifiable** — Cryptographic hashes prove authenticity
- **Open Source** — The tools belong to everyone
- **Low Cost** — Cardano's efficiency means affordable permanence

---

## 📚 Two Types of Scrolls

### Standard Scrolls (LS-LOCK v1)
**Best for: Small files up to ~16KB**

A single locked UTxO containing your content. Simple, elegant, and truly permanent — the UTxO can never be spent because it's locked by an always-fail script.

```
┌─────────────────────────────────────┐
│  LOCKED UTxO                        │
│  ├─ Address: always-fail script     │
│  ├─ Value: 2+ ADA (locked forever)  │
│  └─ Datum: Your content (inline)    │
└─────────────────────────────────────┘
```

### Legacy Scrolls (LS-PAGES v1)  
**Best for: Large files, multi-page documents**

Multiple CIP-25 NFTs under a time-locked policy, each containing a page of your content. The pages are concatenated to reconstruct the full document.

```
┌─────────────────────────────────────┐
│  POLICY (time-locked)               │
│  ├─ NFT #0: { i: 0, payload: [...]} │
│  ├─ NFT #1: { i: 1, payload: [...]} │
│  ├─ NFT #2: { i: 2, payload: [...]} │
│  └─ ...                             │
└─────────────────────────────────────┘
```

---

## 🚀 Quick Start

### View Existing Scrolls

1. Open `index.html` in your browser
2. Click ⚙️ Settings → Enter your [Blockfrost API key](https://blockfrost.io) (or use Koios for free)
3. Click "Connect to Cardano"
4. Browse the library!

### Create Your Own Scroll

**Option 1: Use Our Scripts**
```bash
# Clone the repo
git clone https://github.com/BEACNpool/ledger-scrolls.git
cd ledger-scrolls

# For a Standard Scroll (small file)
./scripts/mint-standard-scroll.sh your-file.txt

# For a Legacy Scroll (large file)
./scripts/mint-legacy-scroll.sh large-document.pdf
```

**Option 2: Follow the Guides**
- 📖 [Standard Scroll Guide](docs/STANDARD_SCROLLS.md)
- 📖 [Legacy Scroll Guide](docs/LEGACY_SCROLLS.md)
- 📖 [Getting Started](docs/GETTING_STARTED.md)

---

## 🏛️ Example Scrolls (Minted January 2026)

These scrolls were minted by BEACN Pool and serve as reference examples:

| Scroll | Type | TX Hash | Description |
|--------|------|---------|-------------|
| 📜 **The Genesis Scroll** | Standard | [`a19f64fb...`](https://cardanoscan.io/transaction/a19f64fba94abdc37b50012d5d602c75a1ca73c82520ae030fc6b4e82274ceb2) | The founding manifesto |
| 💜 **FIRST WORDS** | Legacy (4 NFTs) | [`cb0a2087...`](https://cardanoscan.io/transaction/cb0a2087c4ed1fd16dc3707e716e1a868cf4772b7340f4db7205a8344796dfae) | Seven meditations on existence |
| 🔮 **The Architect's Scroll** | Standard | [`076d6800...`](https://cardanoscan.io/transaction/076d6800d8ccafbaa31c32a6e23eecfc84f7d1e35c31a9128ec53736d5395747) | Hidden tribute (locked forever) |

See the [`examples/`](examples/) directory for complete implementation details.

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/GETTING_STARTED.md) | Prerequisites and setup |
| [Standard Scrolls](docs/STANDARD_SCROLLS.md) | How to mint Standard Scrolls |
| [Legacy Scrolls](docs/LEGACY_SCROLLS.md) | How to mint Legacy Scrolls |
| [Viewer Guide](docs/VIEWER.md) | Using the web viewer |
| [Technical Specs](docs/TECHNICAL.md) | Protocol specifications |
| [Examples](docs/EXAMPLES.md) | Detailed walkthrough of our minted scrolls |

---

## 🛠️ Repository Structure

```
ledger-scrolls/
├── index.html              # Web viewer application
├── css/                    # Viewer styles
├── js/                     # Viewer logic
│   ├── app.js              # Main application
│   ├── scrolls.js          # Scroll definitions
│   ├── blockchain.js       # API clients
│   └── reconstruct.js      # Reconstruction engine
├── scripts/                # Minting tools
│   ├── mint-standard-scroll.sh
│   ├── mint-legacy-scroll.sh
│   └── verify-scroll.sh
├── templates/              # Ready-to-use templates
│   ├── standard-scroll/    # Standard Scroll template
│   └── legacy-scroll/      # Legacy Scroll template
├── examples/               # Reference implementations
│   ├── genesis-scroll/
│   ├── first-words/
│   └── architects-scroll/
├── docs/                   # Documentation
└── mint/                   # Legacy minting scripts
```

---

## 🤝 Contributing

Ledger Scrolls is built for the community. Contributions are welcome!

- 🐛 **Found a bug?** [Open an issue](https://github.com/BEACNpool/ledger-scrolls/issues)
- 💡 **Have an idea?** [Start a discussion](https://github.com/BEACNpool/ledger-scrolls/discussions)
- 🔧 **Want to contribute?** See [CONTRIBUTING.md](CONTRIBUTING.md)

### Ways to Help

- Add support for new content types
- Improve the viewer UI
- Write better documentation
- Create tutorials
- Translate to other languages
- Mint your own scrolls and share them!

---

## 🔐 Security

- **Locked UTxOs are permanent** — Think before you mint
- **Private keys never leave your machine** — All signing is local
- **Verify hashes** — Always check SHA256 for important documents
- **Content is public** — Anyone can read what you inscribe

See [SECURITY.md](SECURITY.md) for security considerations.

---

## 📜 License

MIT License — Free to use, modify, and distribute. See [LICENSE](LICENSE).

---

## 🙏 Credits

**Built by [BEACN Pool](https://beacnpool.org)** — A Chicago-based single pool operator committed to decentralization and empowering everyday stakers.

**Viewer architecture & documentation crafted by Claude** (Anthropic) — January 2026

### Special Thanks

- The **Cardano community** — for believing in decentralization
- **Blockfrost** & **Koios** — for accessible blockchain APIs
- Everyone who preserves knowledge for future generations

---

## 🌟 The BEACN Ethos

> *"We believe the tools of permanence should belong to everyone — not just the technically elite, not just the wealthy, but anyone with something worth preserving."*

Ledger Scrolls is free, open-source, and built for the people of Cardano. If you find it valuable, consider [delegating to BEACN Pool](https://beacnpool.org) — or just go mint something amazing.

**The chain is the library. The scrolls are eternal.**

---

<details>
<summary>🔮 For the curious...</summary>

```
↑ ↑ ↓ ↓ ← → ← → B A
```

*30 lives. Infinite knowledge.*

</details>
