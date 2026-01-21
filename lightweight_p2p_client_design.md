# Lightweight Ledger Scrolls P2P Client Design
## "Minimal Query, Maximum Sovereignty"

### Core Concept
A lightweight client (~10MB) that connects directly to Cardano P2P network to fetch ONLY the data needed for a specific scroll, then disconnects.

---

## Architecture

```
User Input: Scroll Pointer
  ↓
Determine Query Type:
  - Standard Scroll: UTxO at address
  - Legacy Scroll: NFT metadata by policy
  ↓
Connect to Cardano P2P Node (port 6000)
  ↓
Use Mini-Protocol to Request Data:
  - Chain-Sync from specific slot
  - Block-Fetch for known blocks
  ↓
Parse CBOR Response Locally
  ↓
Extract Scroll Data
  ↓
Disconnect
  ↓
Reconstruct Scroll File
```

---

## Implementation Strategy

### Phase 1: Block-Fetch Mode (Easiest)
**For scrolls where we know the exact block:**

```python
class LightweightP2PClient:
    def __init__(self, relay_host, relay_port=6000):
        self.relay = (relay_host, relay_port)
    
    def fetch_block_by_hash(self, block_hash):
        """
        Connect via Ouroboros protocol
        Request specific block
        Return parsed CBOR
        """
        # 1. TCP connection
        # 2. Handshake (protocol version negotiation)
        # 3. Send BlockFetch request
        # 4. Receive block CBOR
        # 5. Disconnect
        pass
    
    def extract_utxo_from_block(self, block, tx_hash, output_index):
        """
        Parse block CBOR
        Find transaction
        Extract UTxO datum
        """
        pass
```

**Requirements:**
- Know block hash (can derive from tx hash + blockchain explorers)
- Implement Ouroboros handshake
- Parse CBOR blocks
- Extract specific transaction outputs

**Data transferred:** ~2-5MB per block (much better than 150GB!)

### Phase 2: Chain-Sync Range Query
**For scrolls where we know approximate slot:**

```python
def query_scroll_by_slot_range(self, start_slot, end_slot, policy_id=None):
    """
    Connect to P2P network
    Request chain-sync from start_slot to end_slot
    Filter for:
      - UTxOs at specific address
      - NFTs with specific policy
    Extract relevant data
    Disconnect
    """
    pass
```

**Data transferred:** Depends on slot range, could be 10-100MB for a few epochs

### Phase 3: Smart Caching
**For repeated queries:**

```python
# Local cache structure
cache/
  blocks/
    <block_hash>.cbor
  utxos/
    <tx_hash>_<index>.json
  nfts/
    <policy_id>/
      <asset_name>.json
```

Once fetched, data is cached locally. Never re-download.

---

## Protocol Implementation Needs

### 1. Ouroboros Handshake
```
Client → Node: MsgProposeVersions
Node → Client: MsgAcceptVersion
```

### 2. Mini-Protocol Multiplexing
```
Multiplexed Connection:
  - Protocol 2: Chain-Sync
  - Protocol 3: Block-Fetch  
  - Protocol 5: Tx-Submission (not needed)
```

### 3. CBOR Encoding/Decoding
All Cardano data is CBOR-encoded. Must implement:
- Block structure parsing
- Transaction parsing
- Datum extraction
- Metadata extraction

---

## Challenges & Solutions

### Challenge 1: "How do I know which block to fetch?"

**Solution:**
- For Standard Scrolls: Use tx hash to determine block
- Can query a block explorer API ONCE to get block hash
- Or maintain a small index of "known scroll locations"
- Or query Blockfrost ONCE to get slot, then use P2P

**Hybrid approach:**
```python
# First time: Use Blockfrost to find slot
slot = blockfrost.get_tx_slot(tx_hash)

# Every time after: Use P2P to fetch block at that slot
block = p2p_client.fetch_block_at_slot(slot)
```

### Challenge 2: "Ouroboros protocol is complex"

**Solution:**
- Start with Python `pycardano` library (has some protocol code)
- Use `cardano-sync` as reference implementation
- Build minimal subset - don't need full node features
- Focus ONLY on read operations

### Challenge 3: "CBOR parsing is hard"

**Solution:**
- Use `cbor2` library (already required)
- Reference `cardano-cli` source for structure
- Build incrementally: blocks → txs → outputs → datums

---

## Proof of Concept Roadmap

### Week 1: Connection + Handshake
- [ ] Establish TCP connection to relay
- [ ] Implement Ouroboros handshake
- [ ] Verify protocol version negotiation works

### Week 2: Block Fetch
- [ ] Implement BlockFetch mini-protocol
- [ ] Request block by hash
- [ ] Receive and save raw CBOR

### Week 3: CBOR Parsing
- [ ] Parse block structure
- [ ] Extract transactions
- [ ] Extract UTxO outputs
- [ ] Extract inline datums

### Week 4: Integration
- [ ] Integrate with existing viewer
- [ ] Add P2P mode alongside Blockfrost
- [ ] Handle errors gracefully
- [ ] Cache fetched data

### Week 5: Legacy Scrolls
- [ ] Implement NFT metadata extraction
- [ ] Handle multi-block queries
- [ ] Parse CIP-25 metadata

### Week 6: Polish
- [ ] Connection pooling (try multiple relays)
- [ ] Better error messages
- [ ] Performance optimization
- [ ] Documentation

---

## Estimated Resource Usage

**Lightweight P2P Client:**
- Software size: ~10-15MB
- Memory: ~50-100MB during query
- Disk cache: Grows with usage (~1MB per scroll)
- Network: 2-10MB per Standard Scroll query
- Network: 10-100MB per Legacy Scroll (depends on pages)

**vs. Full Node:**
- Software: ~500MB
- Memory: ~4-8GB
- Disk: ~150GB
- Network: Must sync entire chain

---

## The Honest Assessment

### What This Achieves:
✅ No full node required
✅ No always-running daemon
✅ Direct P2P access (no API)
✅ Permissionless (connect to any public relay)
✅ ~10MB software, ~100MB RAM
✅ Query in seconds, not hours

### What This Doesn't Solve:
❌ Still need to know WHERE to look (slot/block)
❌ Still download some blockchain data (2-100MB per query)
❌ Complex implementation (mini-protocols + CBOR)
❌ Not as fast as API (API is optimized)

### When This Makes Sense:
- ✅ Privacy-focused users
- ✅ API services are down
- ✅ Want to verify data independently
- ✅ Building for censorship resistance

### When API Makes More Sense:
- ✅ Casual users
- ✅ Speed priority
- ✅ Mobile apps (battery/bandwidth)
- ✅ Quick demos

---

## Recommendation

**Build BOTH modes:**

```python
class ScrollViewer:
    def __init__(self):
        self.mode = None  # Set by user
    
    def fetch_scroll(self, pointer):
        if self.mode == "blockfrost":
            return self._fetch_via_api(pointer)
        elif self.mode == "p2p_lightweight":
            return self._fetch_via_p2p(pointer)
        elif self.mode == "local_node":
            return self._fetch_via_cli(pointer)
```

**User chooses based on their priorities:**
- Speed → Blockfrost
- Privacy → P2P Lightweight
- Sovereignty → Local Node

---

## Next Steps

To build this, I need to:

1. **Study existing implementations:**
   - `pycardano` mini-protocol code
   - `cardano-wallet` light mode
   - `Oura` (lightweight chain follower)

2. **Build minimal prototype:**
   - Connect to relay
   - Fetch ONE block
   - Parse it manually
   - Prove concept works

3. **Expand to full viewer:**
   - Handle all scroll types
   - Error handling
   - Multiple relay fallback
   - Cache management

**Time estimate:** 4-6 weeks for full implementation
**Complexity:** High (protocol-level programming)
**Benefit:** True permissionless access without full node

---

## Alternative: Use Existing Lightweight Tools

**Mithril** (Cardano's official light client):
- Snapshot-based verification
- Much lighter than full sync
- Could use Mithril snapshots + light queries
- Official Cardano project

**This might be easier than building from scratch!**

Would you like me to:
A) Build the P2P prototype (4-6 weeks)
B) Integrate with Mithril instead (1-2 weeks)
C) Keep current design (Blockfrost + Local Node options)

---

## Conclusion

Your vision is **technically possible** and **philosophically sound**. It requires significant protocol-level work but would create a truly unique tool:

**"The lightest Cardano client that can read scrolls without intermediaries"**

This would be a major contribution to Cardano's decentralization goals.

Ready to build it? 🚀
