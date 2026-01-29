# Ledger Scrolls v2.0 📜

**"A Library That Cannot Burn"**

A next-generation, web-based viewer for immutable data stored on the Cardano blockchain.

![Ledger Scrolls](https://img.shields.io/badge/version-2.0.0-gold)
![License](https://img.shields.io/badge/license-MIT-blue)
![Cardano](https://img.shields.io/badge/blockchain-Cardano-blue)

---

## ✨ Features

- 🎨 **Beautiful Modern UI** — Glassmorphism design with smooth animations
- 🔗 **Multiple Backends** — Blockfrost API or Koios (free, no key required)
- 📜 **All Scroll Types** — Supports both Standard (locked UTxO) and Legacy (CIP-25 pages)
- 🔐 **Hash Verification** — Cryptographic proof of data integrity
- 🌙 **Multiple Themes** — Dark, Light, and Parchment themes
- 📱 **Responsive** — Works on desktop and mobile
- 🔧 **Custom Scrolls** — Load any scroll by entering its on-chain pointer
- 📋 **Activity Log** — Track all operations in real-time
- 🔮 **Hidden Secrets** — *The old ways still work...*

---

## 🚀 Quick Start

### Option 1: Open Directly

Simply open `index.html` in your browser!

```bash
# On Linux/Mac
xdg-open index.html  # or: open index.html

# On Windows
start index.html
```

### Option 2: Local Server (Recommended)

For full functionality, run a local server:

```bash
# Python 3
python3 -m http.server 8000

# Then open: http://localhost:8000
```

### Option 3: VS Code Live Server

Install the "Live Server" extension and click "Go Live"

---

## 🔑 Setup

### Blockfrost API (Recommended)

1. Get a free API key at [blockfrost.io](https://blockfrost.io)
2. Create a **Mainnet** project
3. Click ⚙️ Settings in the app
4. Enter your API key and click Save
5. Click "Connect to Cardano"

### Koios API (Free, No Key)

1. Click ⚙️ Settings
2. Select "Koios API" as the connection mode
3. Click "Connect to Cardano"

---

## 📚 Included Scrolls

| Scroll | Type | Description |
|--------|------|-------------|
| 🐕 **Hosky PNG** | Standard | The legendary Hosky meme, stored in a locked UTxO |
| 📖 **Holy Bible** | Legacy | Complete King James Bible (237 pages, 4.6MB) |
| ₿ **Bitcoin Whitepaper** | Legacy | Satoshi's original whitepaper |
| ⚖️ **Constitution E608** | Legacy | Current Cardano Constitution |
| 📜 **Constitution E541** | Legacy | Historical Cardano Constitution |
| 🔮 **???** | ??? | *Some knowledge is hidden...* |

---

## 🎮 Secrets

> *"The old ways still work."*

Legends speak of a hidden vault within the library, accessible only to those who remember the ancient code passed down by gamers for generations...

**Hint:** If you grew up in the 80s or 90s, you might know it. Contra players definitely do.

---

## 🏗️ Architecture

```
ledger-scrolls-v2/
├── index.html          # Main application
├── css/
│   └── styles.css      # All styling (themes, animations, vault styles)
├── js/
│   ├── app.js          # Main application logic + easter egg
│   ├── scrolls.js      # Scroll definitions + hidden scrolls
│   ├── blockchain.js   # Blockchain API clients
│   ├── reconstruct.js  # Scroll reconstruction engine
│   └── lib/
│       ├── pako.min.js # Gzip decompression
│       └── cbor.min.js # CBOR decoding
├── LICENSE
└── README.md
```

---

## 🔧 Adding New Scrolls

Edit `js/scrolls.js` to add new scrolls:

### Standard Scroll (Small files in locked UTxO)

```javascript
{
    id: 'my-scroll',
    title: 'My Scroll',
    description: 'Description here',
    icon: '🎨',
    category: 'images',
    type: SCROLL_TYPES.STANDARD,
    pointer: {
        lock_address: 'addr1...',
        lock_txin: 'txhash#0',
        content_type: 'image/png',
        codec: 'none',
        sha256: 'hash...'
    },
    metadata: { size: '~10KB' }
}
```

### Legacy Scroll (Large files in CIP-25 pages)

```javascript
{
    id: 'my-document',
    title: 'My Document',
    description: 'A large document',
    icon: '📄',
    category: 'documents',
    type: SCROLL_TYPES.LEGACY,
    pointer: {
        policy_id: 'abc123...',
        content_type: 'text/html',
        codec: 'gzip'
    },
    metadata: { pages: 50 }
}
```

---

## 🎨 Themes

Three built-in themes:

- 🌙 **Dark** — Deep blues with gold accents (default)
- ☀️ **Light** — Clean white interface
- 📜 **Parchment** — Warm sepia tones, like ancient scrolls

---

## 🔐 Security Notes

- **API keys are stored in localStorage** — Clear browser data to remove
- **Content is sandboxed** — HTML scrolls render in isolated iframes
- **Hash verification** — Always verify important documents
- **No server required** — Everything runs client-side

---

## 🛠️ Development

### Modifying the UI

Edit `css/styles.css` — Uses CSS custom properties for easy theming.

### Adding New Backends

Extend `js/blockchain.js` with a new client implementation.

### Custom Categories

Add categories in `js/scrolls.js`:

```javascript
const CATEGORIES = {
    // ...existing categories
    CUSTOM: { id: 'custom', name: 'Custom', icon: '⭐' }
};
```

---

## 📝 Technical Specifications

### Standard Scrolls (LS-LOCK v1)

- Stored in locked UTxO with inline datum
- `inlineDatum.bytes` contains hex-encoded file
- Requires CBOR decoding
- Optional gzip compression

### Legacy Scrolls (LS-PAGES v1)

- Multiple CIP-25 NFTs under one policy
- Each NFT has `i` (index) and `payload` fields
- Payloads concatenated and decompressed
- Supports burn/re-mint recovery

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.

---

## 🙏 Credits

Built with ❤️ by [@BEACNpool](https://x.com/BEACNpool)

Viewer architecture crafted by **Claude** (Anthropic) — January 2026

**Special Thanks:**
- Cardano community
- Blockfrost team
- All knowledge preservers
- Players of Contra (1987) 🎮

---

*"In the digital age, true knowledge must be unstoppable."*

**The chain is the library. The scrolls are eternal.**

---

<details>
<summary>🔮 For the curious...</summary>

```
↑ ↑ ↓ ↓ ← → ← → B A
```

*30 lives. Infinite knowledge.*

</details>
