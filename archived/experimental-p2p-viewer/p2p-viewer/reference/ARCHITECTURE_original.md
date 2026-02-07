# Cardano Relay Impersonator — Architecture & Strategy Guide
## Ledger Scrolls Project (@BEACNpool)

---

## The Core Idea: "Sync Deception"

You connect to a public Cardano relay via raw TCP, speak just enough of the Ouroboros mini-protocol to convince the relay you're another node that wants to sync from a specific point. You grab the exact block(s) you need, extract the transaction metadata (CIP-25 scroll pages), and disconnect. **No full node. No centralized API. Pure P2P.**

The relay never knows you're not a real node — you follow the protocol spec to the letter.

---

## Protocol Flow (Per Ouroboros Network Specification)

```
┌──────────────┐                           ┌──────────────┐
│  YOUR CLIENT │                           │ CARDANO RELAY│
│ (Impersonator)│                          │  (Port 3001) │
└──────┬───────┘                           └──────┬───────┘
       │                                          │
       │  ① TCP CONNECT                           │
       │─────────────────────────────────────────→│
       │                                          │
       │  ② MsgProposeVersions (Handshake)        │  Section 3.6
       │  [0, {14: [764824073, true, 0, false]}]  │  MUX Protocol 0
       │─────────────────────────────────────────→│
       │                                          │
       │  ③ MsgAcceptVersion                      │
       │  [1, 14, [764824073, false, 0, false]]   │
       │←─────────────────────────────────────────│
       │                                          │
       │  ④ MsgFindIntersect (ChainSync)          │  Section 3.7
       │  [4, [[slot, block_hash]]]               │  MUX Protocol 2
       │─────────────────────────────────────────→│
       │                                          │
       │  ⑤ MsgIntersectFound                     │
       │  [5, [slot, hash], [tip_slot, tip_hash]] │
       │←─────────────────────────────────────────│
       │                                          │
       │  ⑥ MsgRequestRange (BlockFetch)          │  Section 3.8
       │  [0, [slot, hash], [slot, hash]]         │  MUX Protocol 3
       │─────────────────────────────────────────→│
       │                                          │
       │  ⑦ MsgStartBatch                         │
       │  [2]                                     │
       │←─────────────────────────────────────────│
       │                                          │
       │  ⑧ MsgBlock (full block body!)           │
       │  [4, <CBOR block with metadata>]         │
       │←─────────────────────────────────────────│
       │                                          │
       │  ⑨ MsgBatchDone                          │
       │  [5]                                     │
       │←─────────────────────────────────────────│
       │                                          │
       │  ⑩ MsgClientDone + TCP CLOSE             │
       │─────────────────────────────────────────→│
       │                                          │
       ▼                                          ▼
  Parse block CBOR → Extract label 721 → Reconstruct scroll
```

---

## Wire Format: MUX Framing (Section 2.1, Table 2.1)

Every message on the TCP connection is wrapped in an 8-byte MUX header:

```
Byte 0-3:  Transmission Time  (uint32, monotonic µs clock)
Byte 4-5:  [M][Protocol ID]   (1 bit mode + 15 bits ID)
Byte 6-7:  Payload Length      (uint16)
Byte 8+:   CBOR Payload

Mode bit: 0 = initiator (us), 1 = responder (relay)

Protocol IDs (Table 3.14 — Node-to-Node):
  0  = Handshake
  2  = ChainSync
  3  = BlockFetch
  4  = TxSubmission (not needed)
  8  = KeepAlive
  10 = PeerSharing (not needed)
```

---

## Handshake Version Data (Section 3.6.5)

For NodeToNode v14 (current mainnet — mandatory since 2025.01.29):

```
CBOR: [0, {14: [764824073, true, 0, false]}]

versionTable = {
  14: [
    764824073,  ← networkMagic (mainnet)
    true,       ← diffusionMode (true = InitiatorOnly — we only consume)
    0,          ← peerSharing (0 = disabled — no gossip)
    false       ← query (false = real connection, not version probe)
  ]
}
```

**Why InitiatorOnly?** Per the spec, InitiatorOnly mode tells the relay we're a leaf node (like a wallet or explorer). The relay won't try to sync FROM us. This is exactly what we want.

---

## Deployment Options

### Option A: Python Application (Recommended — Start Here)

**`ouroboros_client.py`** is a complete, runnable implementation:

```python
import asyncio
from ouroboros_client import fetch_block_at_point

block = asyncio.run(fetch_block_at_point(
    slot=141017832,
    block_hash_hex="abc123...",  # 64 hex chars
    relay_host="backbone.cardano.iog.io",
))

if block:
    print(f"Era: {block.era_name}")
    print(f"Metadata entries: {len(block.tx_metadata)}")
```

**Advantages:**
- Full asyncio for concurrent protocol handling
- cbor2 library handles all CBOR edge cases
- No execution time limits
- Can run on BEACNpool server, any VPS, or locally
- Direct integration with viewer_v2.py P2P mode

**Dependencies:** `pip install cbor2` (that's it)

### Option B: Cloudflare Worker + Python Backend (Hybrid)

```
┌─────────────┐    REST/JSON     ┌──────────────┐    Ouroboros TCP    ┌──────────┐
│  CF Worker   │ ──────────────→ │ Python Proxy │ ─────────────────→ │  Relay   │
│  (Website)   │ ←────────────── │  (Your VPS)  │ ←───────────────── │  (P2P)   │
└─────────────┘                  └──────────────┘                    └──────────┘
     ↑ User                     Handles Ouroboros                  Cardano network
```

The Python backend does the hard protocol work and exposes a simple REST API:
```
GET /api/block?slot=141017832&hash=abc123...
→ Returns parsed block JSON with metadata
```

The CF Worker provides a nice web UI that calls this API.

### Option C: Pure Cloudflare Worker (Advanced — Theoretically Possible)

CF Workers support TCP via `connect()` since 2023:

```javascript
const socket = connect({ hostname: "relay.cardano.iog.io", port: 3001 });
const writer = socket.writable.getWriter();
const reader = socket.readable.getReader();

// Build MUX header + CBOR handshake...
await writer.write(muxSegment);
```

**Challenges:**
- 30-second execution limit (paid plan) — tight for full handshake + fetch
- CBOR encoding in JS is less mature (use `cbor-x` or `cbor-web`)
- No `asyncio`-style demuxer — manual stream management
- Binary protocol debugging is painful in Workers

**Verdict:** Possible for simple queries, but Python is 10x easier to develop and debug. Use Option B.

### Option D: Cloudflare Worker + Ogmios Bridge

If you have access to an Ogmios instance (which wraps Ouroboros in JSON-RPC over WebSocket):

```javascript
// CF Worker → Ogmios (WebSocket, much easier than raw TCP)
const ws = new WebSocket("wss://your-ogmios.example.com");
ws.send(JSON.stringify({
  jsonrpc: "2.0",
  method: "findIntersection",
  params: { points: [{ slot: 141017832, id: "abc123..." }] }
}));
```

**This is the easiest CF Worker path** — but requires running Ogmios somewhere, which requires a full cardano-node. Defeats the "no full node" goal.

---

## Integration with Ledger Scrolls viewer_v2.py

The `OuroborosClient` class replaces the `NotImplementedError` stub in viewer_v2.py's P2P mode:

```python
# In viewer_v2.py, replace the P2P connect_to_relay() stub:

from ouroboros_client import OuroborosClient, Point

class P2PConnection:
    async def connect_and_fetch(self, relay_host, relay_port, slot, block_hash):
        client = OuroborosClient(relay_host, relay_port)
        await client.connect()
        block = await client.snipe_block(slot, block_hash)
        await client.disconnect()
        return block
```

---

## Known Mainnet Relays

| Relay | Port | Operator |
|-------|------|----------|
| backbone.cardano.iog.io | 3001 | IOG |
| backbone.mainnet.emurgornd.com | 3001 | Emurgo |
| backbone.mainnet.cardanofoundation.org | 3001 | Cardano Foundation |
| Your own BEACNpool relay | 3001 | You |

**Pro tip:** Connect to YOUR OWN relay first. It's faster, more reliable, and you control the topology. Any SPO relay will work — the Ouroboros protocol is the same for all nodes.

---

## Security Considerations

1. **We're a legitimate protocol participant.** The Ouroboros spec explicitly supports "leaf nodes" (wallets, explorers) connecting in InitiatorOnly mode. We're following the spec.

2. **No state modification.** We only READ blocks — we never submit transactions or produce blocks.

3. **Clean disconnects.** We send proper protocol termination messages (MsgClientDone, MsgDone) before closing TCP.

4. **Relay can always refuse.** The handshake can be refused, blocks can be MsgNoBlocks. We handle all cases.

5. **Network magic validation.** The handshake validates both sides agree on the network (mainnet/testnet). You can't accidentally connect to the wrong network.

---

## What You Need to Fetch a Block

To use `snipe_block()`, you need two things:

1. **Slot number** — e.g., `141017832`
2. **Block header hash** — 32 bytes as hex, e.g., `abc123def456...` (64 chars)

You already have these from your Ledger Scrolls spreadsheets (tx_hash → slot via Blockfrost). The block header hash can be obtained from any block explorer (CardanoScan) or via a one-time Blockfrost query.

**Once you have the slot+hash, you never need Blockfrost again for that block.** That's the whole point — deterministic, API-free access.

---

## File: ouroboros_client.py — Quick Reference

| Function | Purpose |
|----------|---------|
| `fetch_block_at_point(slot, hash)` | One-shot: connect → fetch → disconnect |
| `OuroborosClient.connect()` | Perform N2N handshake |
| `OuroborosClient.snipe_block(slot, hash)` | Find intersection + fetch block |
| `OuroborosClient.find_intersect(points)` | ChainSync intersection |
| `OuroborosClient.fetch_block(point)` | BlockFetch single block |
| `OuroborosClient.fetch_block_range(from, to)` | BlockFetch range |
| `OuroborosClient.disconnect()` | Clean protocol shutdown |
| `parse_block(cbor)` | Extract metadata from raw block |
| `extract_cip25_metadata(block, policy)` | Get CIP-25 data for a policy |

---

*Built from the Ouroboros Network Specification. No hallucinated protocols. Substance over hype.*
