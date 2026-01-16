# Ledger Scrolls

> **"A library that cannot burn."**

**Ledger Scrolls** is an open-source protocol and hardware reference design for storing, indexing, and reading permissionless, immutable data on the Cardano blockchain.

We are building the **Smart Edge Node**: a device that allows anyone to preserve human knowledge without relying on centralized APIs, cloud servers, or massive hardware requirements.

---

## 📜 The Ethos
The intent is supposed to be permanent; but links rot, servers crash, and history can be rewritten or censored. Blockchains solve this, but accessing that data usually requires:
1.  **Massive Hardware:** Storing hundreds of GB of history (a Full Node).  Lots of RAM to index.  multiple dockers and containers need to talk to eachother.
2.  **Centralized Gatekeepers:** Relying on APIs (like Blockfrost or Google) that can cut you off.

**Ledger Scrolls changes this.**

By combining **Cardano's deterministic eUTxO architecture** with a lightweight **Beacon Protocol**, we allow low-power devices to act as independent librarians. They don't need to index the whole world—they only need to know *where* to look.

### The Mission
* **Permissionless:** No one can stop you from publishing a Scroll.
* **Immutable:** Once on-chain, the data is permanent.
* **Decentralized:** The reader connects directly to the P2P network. No middleman.
* **Efficient:** "Start Slot" indexing allows instant syncing on consumer hardware.

---

## 📡 The Beacon Protocol (How it Works)

Ledger Scrolls is not a platform; it is a standard. It relies on a "Town Square" model to connect Creators and Viewers.

### 1. For Creators (The Writers)
You want to publish a book, a manifesto, or a document (e.g., *The Bitcoin Whitepaper* or *The Bible*).
1.  **Mint:** You mint your data as NFTs/Tokens on Cardano.
2.  **Beacon:** Instead of building a complex website, you send a single transaction (~1.5 ADA) to the **Ledger Scrolls Registry Address**.
3.  **Metadata (Label 777):** You attach a simple JSON tag to this transaction:

```json
{
  "777": {
    "msg": [
      "LS:Register",
      "Project: The Cardano Bible",
      "PolicyID: 123abcde...",
      "StartSlot: 115000450",
      "Structure: Book/Text"
    ]
  }
}
PolicyID: The unique ID of your content.

StartSlot: The exact moment in time your content was created. This is the key to efficiency. It tells nodes exactly when to start listening, skipping years of irrelevant blockchain history.

2. For Viewers (The Readers)
You don't need to trust a website. You run a Ledger Scroll Node.

Your node watches the Registry Address.

When a new "Beacon" signal arrives, your node records the PolicyID and StartSlot.

It spins up a listener that jumps directly to that slot in history and reconstructs the document locally.

🛠 piLedgerScrolls: The Smart Edge Node
This repository contains the reference implementation for piLedgerScrolls, a dedicated hardware node designed to run the Ledger Scrolls protocol.

The "Cheapest AI Indexer"
We target specific hardware to prove that decentralization is affordable.

Compute: Raspberry Pi 5 (8GB RAM)

Intelligence: Raspberry Pi AI HAT+ (Hailo-10H 13 TOPS)

Storage: 256GB NVMe SSD (USB 3.0 Adapter)

How it runs
Oura (The Eyes): Connects to the Cardano P2P network via Oura (Rust) to stream live blocks.

The Filter: Ignores 99.9% of chain traffic, capturing only transactions matching known Ledger Scroll Policy IDs.

Hailo AI (The Brain): The raw blockchain data (often messy JSON/Hex) is passed to the local AI HAT. The LLM parses the structure and outputs clean, human-readable text.

Local Database: The result is stored locally for instant querying.

🚀 Getting Started
Prerequisites
A Raspberry Pi 5 setup with the AI HAT installed.

oura installed and in your system PATH (for P2P connection).

Python 3.10+

Installation
Bash

git clone [https://github.com/BEACNpool/ledger-scrolls.git](https://github.com/BEACNpool/ledger-scrolls.git)
cd ledger-scrolls
pip install -r requirements.txt
Configuration
Open config/manifest.json. You can manually add scrolls, or set your registry_address to listen for new ones automatically.

Usage
1. List Available Scrolls View what your node currently knows about.

Bash

python -m src.main list
2. Watch the Beacon (Discovery Mode) Listen to the "Town Square" for new project registrations.

Bash

python -m src.main registry
3. Read a Scroll Sync and display a specific project. This will jump to the StartSlot and begin indexing immediately.

Bash

python -m src.main read "The Cardano Bible"
🤝 Contributing
Ledger Scrolls is an open protocol.

Developers: Submit PRs to improve the oura driver or AI parsing logic.

Creators: Mint your own Ledger Scrolls and register them on-chain.

Maintained by [BEACN] Stake Pool Because the truth shouldn't require an API key.
