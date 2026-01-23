# Ledger Scrolls Viewer v2.0 - Setup & Usage Guide

## 📋 Table of Contents
- [Installation](#installation)
- [Making it Double-Clickable](#making-it-double-clickable)
- [New Features](#new-features)
- [Configuration](#configuration)
- [QR Code Support](#qr-code-support)
- [P2P Mode](#p2p-mode)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Installation

### Step 1: Install Python

**Required:** Python 3.7 or higher

**Check if you have Python:**
```bash
python3 --version
```

**If not installed:**
- **Windows:** Download from https://python.org
- **macOS:** Comes pre-installed, or `brew install python3`
- **Linux:** `sudo apt-get install python3 python3-pip`

### Step 2: Install Dependencies

**Required:**
```bash
pip install requests cbor2
```

**Optional (for QR code scanning):**
```bash
pip install opencv-python pyzbar
```

**Note:** QR code scanning is optional. The app works without it.

### Step 3: Download viewer_v2.py

Save the `viewer_v2.py` file to your computer.

---

## 🖱️ Making it Double-Clickable

The viewer can be run by double-clicking, but setup differs by platform.

### Windows

**Option 1: Create a Batch File**

1. Create a file called `run_viewer.bat` in the same folder as `viewer_v2.py`
2. Add this content:
```batch
@echo off
python viewer_v2.py
pause
```
3. Double-click `run_viewer.bat` to run

**Option 2: File Association**

1. Right-click `viewer_v2.py`
2. Open With → Choose another app
3. Select Python (or browse to `python.exe`)
4. Check "Always use this app"
5. Now you can double-click `viewer_v2.py`

**Option 3: Create Desktop Shortcut**

1. Right-click Desktop → New → Shortcut
2. Location: `python "C:\path\to\viewer_v2.py"`
3. Name it "Ledger Scrolls Viewer"
4. Change icon if desired
5. Double-click shortcut to run

### macOS

**Option 1: Make Executable (Recommended)**

1. Open Terminal in the folder containing `viewer_v2.py`
2. Run:
```bash
chmod +x viewer_v2.py
```
3. Right-click `viewer_v2.py` → Open With → Other
4. Select Python Launcher (or Terminal)
5. Check "Always Open With"
6. Now double-click `viewer_v2.py` to run

**Option 2: Create App Bundle**

1. Open Automator
2. Create new "Application"
3. Add "Run Shell Script" action
4. Enter:
```bash
cd /path/to/viewer
python3 viewer_v2.py
```
5. Save as "Ledger Scrolls Viewer.app"
6. Double-click the app to run

### Linux

**Make Executable:**

1. Open terminal in the folder
2. Run:
```bash
chmod +x viewer_v2.py
```
3. Double-click `viewer_v2.py` in file manager
4. Select "Run" or "Execute"

**Create Desktop Entry:**

1. Create `~/.local/share/applications/ledger-scrolls.desktop`
2. Add:
```ini
[Desktop Entry]
Type=Application
Name=Ledger Scrolls Viewer
Exec=python3 /path/to/viewer_v2.py
Icon=/path/to/icon.png
Terminal=false
Categories=Utility;
```
3. Now searchable from app menu

---

## 🆕 New Features

### 1. **Configurable Registries**

**What is a Registry?**
A Registry is an on-chain scroll containing a list of available scrolls and their pointers.

**Default Registry:**
- Loads automatically on startup
- Hosted by BEACNpool
- Public and free to use

**Custom Registries:**
You can use your own Registry or a private one:

1. Enter Registry address in "Registry Configuration"
2. Give it a name (optional)
3. Click "Load Registry"
4. Registry is saved for next time

**Use Cases for Custom Registries:**
- Private organizations with internal scrolls
- Community-curated collections
- Personal scroll libraries
- Testing new scrolls before publishing

### 2. **QR Code Scanner** 📷

**Requirements:**
```bash
pip install opencv-python pyzbar
```

**How to Use:**

1. Generate QR code containing Registry address or scroll pointer
2. Click "📷 Scan QR" button
3. Hold QR code to camera
4. Address is automatically filled in
5. Press Q to cancel

**QR Code Format:**

**Simple (just address):**
```
addr1q9x84f458uyf3k23sr7qfalg3mw2hl0nvv4navps2r7vq69esnxrheg9tfpr8sdyfzpr8jch5p538xjynz78lql9wm6qpl6qxy
```

**Advanced (JSON with metadata):**
```json
{
  "address": "addr1q9x84f...",
  "name": "My Custom Registry",
  "policy_id": "895cbbe...",
  "asset_hex": "4c535f52..."
}
```

**Use Cases:**
- Share Registries in person (conferences, meetups)
- Publish Registry QR on websites
- Print QR codes on documents/posters
- Easy mobile-to-desktop transfer

### 3. **P2P Lightweight "Sync Deception" Mode** ⚡

**Concept:**
Connect directly to a Cardano relay node, pretend you're syncing, query specific blocks/slots, then disconnect quickly.

**Benefits:**
- No API dependency (Blockfrost not needed)
- No full node sync required (~150GB saved)
- Query specific data on-demand
- True decentralization

**How it Works:**

```
┌─────────────────────────────────────────┐
│  Your Computer                          │
│  ┌────────────────────────────────┐    │
│  │  P2P Lightweight Client        │    │
│  │  "I want to sync!"             │    │
│  └────────────────────────────────┘    │
│              │                          │
│              │ 1. Handshake             │
│              ▼                          │
│  ┌────────────────────────────────┐    │
│  │  Cardano Relay                 │    │
│  │  "Sure, let me help you sync"  │    │
│  └────────────────────────────────┘    │
│              │                          │
│              │ 2. "Give me block 12345"│
│              ▼                          │
│  ┌────────────────────────────────┐    │
│  │  Relay sends specific block    │    │
│  └────────────────────────────────┘    │
│              │                          │
│              │ 3. Parse, extract data  │
│              │ 4. Disconnect           │
│              ▼                          │
│         [Done! 🎉]                      │
└─────────────────────────────────────────┘
```

**Status:** 🚧 Experimental - Protocol implementation in progress

**How to Use:**

1. Select "⚡ P2P Lightweight" mode
2. Enter relay IP address (e.g., `relays-new.cardano-mainnet.iohk.io`)
3. Enter port (default: `3001`)
4. Click "Test Connection"

**Finding Relay IPs:**

```bash
# Option 1: Use a public relay
# IOHK relays: relays-new.cardano-mainnet.iohk.io

# Option 2: Resolve DNS
nslookup relays-new.cardano-mainnet.iohk.io

# Option 3: Check topology
curl https://explorer.cardano.org/relays/topology.json
```

**Implementation Status:**

- ✅ UI ready
- ✅ Configuration management
- ✅ Connection framework
- 🚧 Ouroboros protocol handshake (in progress)
- 🚧 Block-fetch mini-protocol (in progress)
- 🚧 CBOR parsing (in progress)
- 🚧 Local-state-query (in progress)

**ETA:** 2-3 months for full implementation

**For Now:** Use Blockfrost or Local Node mode

---

## ⚙️ Configuration

### Connection Modes

**1. Blockfrost API (Recommended for most users)**

**Pros:**
- ✅ Easy setup (just API key)
- ✅ Fast queries
- ✅ No infrastructure needed

**Cons:**
- ⚠️ Requires third-party service
- ⚠️ Rate limits (50k/day free tier)

**Setup:**
1. Get free API key at https://blockfrost.io
2. Create **Mainnet** project (not Testnet!)
3. Paste `project_id` in viewer
4. Click "Save"

**2. Local Node (For node operators)**

**Pros:**
- ✅ No API dependency
- ✅ Unlimited queries
- ✅ Maximum privacy
- ✅ Benefits from location hints!

**Cons:**
- ⚠️ Requires running full node
- ⚠️ ~150GB disk space
- ⚠️ 2-3 days initial sync

**Setup:**
1. Install Cardano node: https://developers.cardano.org/docs/get-started/installing-cardano-node
2. Wait for full sync
3. Enter socket path (e.g., `/opt/cardano/cnode/sockets/node.socket`)
4. Click "Test & Save"

**3. P2P Lightweight (Experimental)**

See [P2P Mode](#p2p-mode) section above.

---

## 📷 QR Code Support

### Generating QR Codes

**For Registries:**

**Python:**
```python
import qrcode
import json

registry_data = {
    "address": "addr1q9x84f458...",
    "name": "My Registry",
    "policy_id": "895cbbe...",
    "asset_hex": "4c535f52..."
}

qr = qrcode.QRCode(version=1, box_size=10, border=4)
qr.add_data(json.dumps(registry_data))
qr.make(fit=True)

img = qr.make_image(fill_color="black", back_color="white")
img.save("registry_qr.png")
```

**Online Tool:**
- Go to https://qr.io or https://www.qr-code-generator.com
- Enter Registry address or JSON
- Download QR code image

**For Scroll Pointers:**

Same process, but use scroll pointer data:
```json
{
  "type": "utxo_datum_bytes_v1",
  "lock_address": "addr1w8qvvu...",
  "lock_txin": "728660515c6d9842...",
  "content_type": "image/png",
  "codec": "none"
}
```

### Scanning QR Codes

1. Click "📷 Scan QR" button
2. Camera window opens
3. Hold QR code to camera
4. Wait for green box around code
5. Data automatically fills form
6. Press Q to cancel

**Troubleshooting:**
- **Camera won't open:** Check permissions
- **QR not detected:** Ensure good lighting
- **Wrong data scanned:** QR might contain wrong format

---

## 🔍 P2P Mode (Technical Details)

### The "Sync Deception" Strategy

**The Problem:**
- Full nodes download entire chain (~150GB)
- APIs are centralized gatekeepers
- Light clients don't exist on Cardano

**The Solution:**
Connect as if syncing, but only request specific data.

### Implementation Plan

**Phase 1: Connection (✅ Done)**
- TCP socket to relay
- Configuration management
- Error handling

**Phase 2: Handshake (🚧 In Progress)**
- Implement Ouroboros node-to-node protocol
- Version negotiation
- Network magic verification

**Phase 3: Mini-Protocols (🚧 In Progress)**

**chain-sync:**
- Announce we're at genesis (slot 0)
- Relay offers us blocks
- We politely decline most of them

**block-fetch:**
- Request specific blocks by hash/slot
- Parse CBOR-encoded block data
- Extract transactions we need

**local-state-query:**
- Query UTxO set for specific address
- Get current tip
- Request protocol parameters

**Phase 4: Data Extraction (📋 Planned)**
- CBOR parsing (blocks, transactions, datums)
- Reconstruct scrolls from parsed data
- Cache frequently accessed blocks

**Phase 5: Optimization (📋 Planned)**
- Smart caching
- Parallel queries to multiple relays
- Minimize connection time

### Why This Works

Relays are designed to serve syncing nodes:
- They expect connections from nodes
- They don't know if you're "really" syncing
- Requesting specific blocks is normal behavior
- Disconnecting is fine (nodes crash/restart often)

**Legal/Ethical:**
- Using public relays as designed
- Not exploiting vulnerabilities
- Same data available via full node
- No different from SPO querying their own node

### Current Limitations

- Protocol not yet implemented
- No production-ready libraries for Python
- Testing requires access to relay
- CBOR parsing is complex

**For developers interested in helping:**
- See `/mnt/project/lightweight_p2p_client_design.md`
- Ouroboros spec: https://iohk.io/en/research/library/
- Join discussion on GitHub

---

## 🐛 Troubleshooting

### Common Issues

**1. "cbor2 library required"**
```bash
pip install cbor2
```

**2. "Camera not opening" (QR scanner)**
```bash
# Install camera libraries
pip install opencv-python pyzbar

# Check camera permissions (macOS/Linux)
# System Preferences → Security & Privacy → Camera

# Test camera
python3 -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

**3. "Registry failed to load"**
- Check internet connection
- Verify Blockfrost API key is valid
- Try "Refresh Registry" button
- Use Custom Scroll as workaround

**4. "cardano-cli not found" (Local Node mode)**
```bash
# Install Cardano node tools
# See: https://developers.cardano.org/docs/get-started/installing-cardano-node

# Verify installation
cardano-cli --version
```

**5. "P2P connection failed"**
- This is expected - protocol not yet implemented
- Use Blockfrost or Local Node mode
- Check back in 2-3 months for P2P support

**6. Script won't run (Permission denied)**
```bash
# Make executable
chmod +x viewer_v2.py

# Or run directly
python3 viewer_v2.py
```

**7. "tkinter not found"**
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# macOS (should be pre-installed)
# If missing, reinstall Python from python.org

# Windows (should be pre-installed)
# If missing, reinstall Python and check "tcl/tk" option
```

### Getting Help

**Check logs:**
```bash
# View latest log
ls -lt ~/.ledger-scrolls/logs/ | head -2
tail -100 ~/.ledger-scrolls/logs/viewer_*.log
```

**Report issues:**
- Include log file contents
- Describe what you were doing
- Include error messages
- Note your OS and Python version

---

## 📊 Performance Tips

### For Best Performance

**1. Use Location Hints**
- Legacy scrolls with hints: 6-12x faster
- Essential for Local Node mode
- Registry should include hints for all large scrolls

**2. Choose Right Connection Mode**
- **Small scrolls (<100 pages):** Any mode works
- **Large scrolls (100+ pages):** Use hints + any mode
- **No internet:** Local Node only
- **No infrastructure:** Blockfrost

**3. Registry Management**
- Cache Registry locally (done automatically)
- Refresh only when needed
- Use private Registry for frequently accessed scrolls

**4. Multiple Scrolls**
- Load one at a time
- Blockfrost rate limits apply
- Local Node has no limits

---

## 🔐 Security & Privacy

### Data Privacy

**Blockfrost Mode:**
- Your API key is sent to Blockfrost
- Your queries are logged by Blockfrost
- Scroll downloads are visible to Blockfrost
- Still better than traditional web hosting

**Local Node Mode:**
- No third parties involved
- Queries stay on your machine
- Maximum privacy
- Requires running full node

**P2P Mode (When Available):**
- Direct connection to relay
- No intermediaries
- Relay sees connection but not intent
- Near-maximum privacy

### API Key Security

**Blockfrost API Key:**
- Stored locally in `~/.ledger-scrolls/config.json`
- File permissions: Only your user can read
- Not transmitted except to Blockfrost
- Free tier is low-risk (no billing)

**Best Practices:**
- Don't share your API key
- Use free tier for testing
- Rotate keys periodically
- Monitor usage on Blockfrost dashboard

---

## 🎯 Advanced Usage

### Creating Your Own Registry

1. **Create Registry JSON:**
```json
{
  "spec": "ledger-scrolls-registry-v2",
  "version": 2,
  "updated": "2026-01-22T00:00:00Z",
  "scrolls": [
    {
      "id": "my-scroll-1",
      "title": "My First Scroll",
      "type": "utxo_datum_bytes_v1",
      "lock_address": "addr1...",
      "lock_txin": "txhash#0",
      "content_type": "image/png",
      "codec": "none"
    }
  ]
}
```

2. **Compress with gzip:**
```bash
gzip -c registry.json > registry.json.gz
```

3. **Convert to hex:**
```bash
xxd -p registry.json.gz | tr -d '\n' > registry.hex
```

4. **Create inline datum and lock on-chain** (see main README)

5. **Share Registry address** (via QR or text)

### Using Multiple Registries

The viewer saves your last-used Registry, but you can switch anytime:

1. Enter new Registry address
2. Click "Load Registry"
3. New scrolls appear in dropdown
4. Old Registry is replaced

To use multiple Registries:
- Load one, use its scrolls
- Load another, use its scrolls
- Repeat as needed

### Verifying Scroll Integrity

**For Standard Scrolls with SHA256:**
```bash
# After downloading
sha256sum ~/Downloads/LedgerScrolls/MyScroll.png

# Compare with scroll's sha256 field
# They should match exactly
```

**For Legacy Scrolls:**
- No built-in hash verification
- Trust comes from on-chain immutability
- Verify source (who published the scroll)

---

## 🚀 What's Next?

### Upcoming Features (v2.1)

- [ ] Local Registry caching (faster startup)
- [ ] Batch download multiple scrolls
- [ ] Export/import scroll collections
- [ ] Scroll preview before download
- [ ] Improved error messages
- [ ] Progress percentage indicators

### Long-term Roadmap (v3.0)

- [ ] P2P protocol fully implemented
- [ ] Web-based viewer (no installation)
- [ ] Mobile apps (iOS/Android)
- [ ] Decentralized registry discovery
- [ ] Smart contract-gated scrolls
- [ ] Mithril integration

---

## 📝 Summary

**Key Improvements in v2.0:**

1. ✅ **Configurable Registries** - Use any Registry, not just default
2. ✅ **QR Code Support** - Scan addresses/configs with camera
3. ✅ **Enhanced P2P Mode** - Enter relay IP/port (UI ready, protocol in progress)
4. ✅ **Better UX** - Clearer status messages, better error handling
5. ✅ **Improved docs** - Setup guides for all platforms

**Bottom Line:**
- Easy to set up
- Can run with double-click (after setup)
- Supports private/custom Registries
- QR scanning for easy sharing
- P2P mode foundation ready

---

**"The chain is the library. The Registry makes it discoverable. QR codes make it shareable."**
