# Ledger Scrolls 📜

> **"A library that cannot burn."**

**Ledger Scrolls** is an open-source protocol and reference implementation for publishing and reading permissionless, immutable data on the Cardano blockchain.

We are building the **Smart Edge Node**: a tool that allows anyone to preserve human knowledge without relying on centralized APIs, cloud servers, or massive hardware requirements.

---

## 📜 The Ethos
The intent is supposed to be permanent; but links rot, servers crash, and history is rewritten or censored. Blockchains solve this, but accessing that data usually requires:
1.  **Massive Hardware:** Storing hundreds of GB of history (Full Node).
2.  **Centralized Gatekeepers:** Relying on APIs (like Blockfrost or Google) that can cut you off.

**Ledger Scrolls changes this.**

By combining **Cardano's deterministic eUTxO architecture** with the lightweight **Beacon Protocol**, we allow low-power devices to act as independent librarians. They don't need to index the whole world—they only need to know *where* to look.

### The Mission
* **Permissionless:** No one can stop you from publishing a Scroll.
* **Immutable:** Once on-chain, the data is permanent.
* **Decentralized:** The reader connects directly to the P2P network. No middleman.
* **Efficient:** "Start Slot" indexing allows instant syncing on consumer hardware.

---

## 🚀 Quick Start
Read the **BTC Whitepaper** or **The Bible** directly from the blockchain in seconds.

**Mac/Linux:**
```bash
# 1. Download & Install (Requires Python 3 & Docker/Oura)
git clone [https://github.com/BEACNpool/ledger-scrolls.git](https://github.com/BEACNpool/ledger-scrolls.git)
cd ledger-scrolls
chmod +x install.sh && ./install.sh

# 2. Run
./scroll read --policy <POLICY_ID> --slot <SLOT>

```

---

## 📡 The Beacon Protocol (How it Works)

Ledger Scrolls is not a platform; it is a standard. It relies on a "Town Square" model to connect Creators and Viewers.

### 1. For Creators (The Writers)

You want to publish a book, a manifesto, or a document.

1. **Mint:** You mint your data as NFTs or transactions on Cardano.
2. **Beacon:** You send a single transaction (~0.17 ADA) to the **Ledger Scrolls Registry Address** (or simply share your address publicly).
3. **Metadata (Label 777):** You attach a simple JSON tag to this transaction:

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

```

* **PolicyID:** The unique ID of your content.
* **StartSlot:** The exact moment in time your content was created. This tells nodes exactly when to start listening, **skipping years of irrelevant blockchain history**.

### 2. For Viewers (The Readers)

You don't need to trust a website. You run a Ledger Scroll Node.

* **Public Mode:** Your node watches the "Town Square" for new registrations.
* **Private Mode:** You point your node at a specific address or Policy ID to read private/unlisted scrolls.

---

## 🛠 piLedgerScrolls: The Smart Edge Node

This repository contains the software for **piLedgerScrolls**, designed to run on low-power hardware.

### Hardware Requirements

* **Minimum:** Any PC/Mac with Python 3 and Internet.
* **Recommended (The "Edge Node"):** Raspberry Pi 5 (8GB RAM).
* **Optional AI:** Raspberry Pi AI HAT+ (Hailo-10H).
* *Note: If no AI chip is detected, the software automatically falls back to CPU-based text reconstruction.*



### How it runs

1. **Oura (The Eyes):** Connects to the Cardano P2P network to stream live blocks.
2. **The Filter:** Ignores 99.9% of chain traffic, capturing only transactions matching known Ledger Scroll Policy IDs or Protocols (Label 674/777).
3. **Hailo AI / CPU (The Brain):** The raw blockchain data is stitched together and formatted into human-readable text.

---

## 📖 Usage Guide

Once installed, use the `scroll` command to interact with the blockchain.

### 1. Read a Private Scroll (Direct Mode)

Read data from any Policy ID or Address without registering it first. Perfect for testing or private storage.

```bash
./scroll read --policy <POLICY_ID> --slot <START_SLOT>
# OR
./scroll read --address <WALLET_ADDR> --slot <START_SLOT>

```

### 2. Watch the Town Square (Discovery Mode)

Listen to the registry for new public projects.

```bash
./scroll registry

```

### 3. List & Read Saved Scrolls

View projects you have discovered or saved locally.

```bash
./scroll list
./scroll read "The Cardano Bible"

```

---

## 🤝 Contributing

Ledger Scrolls is an open protocol.

* **Developers:** Submit PRs to improve the `oura` driver or AI parsing logic.
* **Creators:** Mint your own Ledger Scrolls and register them on-chain.

Maintained by **[BEACN] Stake Pool**.
*Because the truth shouldn't require an API key.*

```

```
