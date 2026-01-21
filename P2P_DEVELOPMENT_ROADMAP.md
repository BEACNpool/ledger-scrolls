# Ledger Scrolls P2P Lightweight Client - Development Roadmap

## Current Status: v1.0 - Three Mode Viewer ✅

The viewer now supports THREE connection modes:

### 1. ✅ Blockfrost API Mode (Production Ready)
- Fast, convenient
- Requires API key
- Best for casual users
- **Status: Fully functional**

### 2. ✅ Local Node Mode (Production Ready)  
- True sovereignty
- Requires cardano-cli
- Best for node operators
- **Status: Fully functional**

### 3. ⚠️ P2P Lightweight Mode (EXPERIMENTAL)
- Direct P2P protocol
- No full node needed
- No API dependency
- **Status: Under construction - UI ready, protocol not implemented**

---

## What's Been Implemented (v1.0)

✅ **GUI Framework**
- Three-mode radio button selection
- P2P configuration inputs (relay host, port)
- Experimental warning banner
- Debug logging system

✅ **Logging Infrastructure**
- All operations logged to `~/.ledger-scrolls/logs/viewer_YYYYMMDD_HHMMSS.log`
- Debug info visible in console
- Error tracking for troubleshooting

✅ **P2P Client Stub**
- `P2PLightweightClient` class created
- API compatibility layer
- Cache directory structure
- Informative error messages

✅ **Documentation**
- Technical design document
- Development roadmap
- Clear user warnings

---

## What Needs To Be Built (v2.0 - P2P Implementation)

### Phase 1: Foundation (Week 1-2) 🔨

**Goal:** Establish basic P2P connection

**Tasks:**
- [ ] Implement TCP connection to relay node
- [ ] Implement Ouroboros protocol handshake
- [ ] Version negotiation
- [ ] Connection pooling (try multiple relays if one fails)

**Deliverables:**
- Can connect to relay
- Can perform handshake
- Logs show successful connection

**Testing:**
```python
# Test connection
client = P2PLightweightClient(P2PConfig("73.209.68.102", 6000))
assert client.connect() == True
assert client.is_connected() == True
```

---

### Phase 2: Block Fetching (Week 3-4) 🧱

**Goal:** Request and receive specific blocks

**Tasks:**
- [ ] Implement block-fetch mini-protocol
- [ ] Request block by hash
- [ ] Request block by slot number
- [ ] Receive and cache raw CBOR blocks
- [ ] Handle errors gracefully

**Deliverables:**
- Can request specific blocks
- CBOR data saved to cache
- Error handling for missing blocks

**Testing:**
```python
# Fetch known block
block = client.fetch_block_by_slot(123456789)
assert block is not None
assert len(block) > 1000  # Has data
```

---

### Phase 3: CBOR Parsing (Week 5-6) 📦

**Goal:** Extract data from CBOR blocks

**Tasks:**
- [ ] Parse block CBOR structure
- [ ] Extract transactions from block
- [ ] Extract UTxO outputs
- [ ] Extract inline datums
- [ ] Extract transaction metadata (CIP-25)
- [ ] Handle different era formats (Byron, Shelley, Babbage)

**Deliverables:**
- Can parse blocks into Python objects
- Can find specific transaction by hash
- Can extract UTxO datum bytes

**Testing:**
```python
# Parse Hosky PNG block
block = client.fetch_block_by_slot(known_slot)
utxo = client.extract_utxo(block, hosky_tx_hash, 0)
assert utxo['inline_datum'] is not None
```

---

### Phase 4: Standard Scroll Support (Week 7) 📜

**Goal:** Reconstruct Standard Scrolls via P2P

**Tasks:**
- [ ] Implement UTxO query by address
- [ ] Extract datum from specific UTxO
- [ ] Integrate with existing scroll reconstructor
- [ ] Add progress reporting
- [ ] Cache strategy for standard scrolls

**Deliverables:**
- Hosky PNG loads via P2P
- Hash verification works
- File saves correctly

**Testing:**
```python
# Load Hosky via P2P
pointer = StandardScrollPointer(...)
file_bytes, content_type = reconstructor.reconstruct_standard_scroll(pointer)
assert hashlib.sha256(file_bytes).hexdigest() == expected_hash
```

---

### Phase 5: Legacy Scroll Support (Week 8-9) 🧾

**Goal:** Reconstruct Legacy Scrolls via P2P

**Tasks:**
- [ ] Query NFTs by policy ID
- [ ] Fetch minting transactions
- [ ] Extract CIP-25 metadata
- [ ] Handle multi-block queries
- [ ] Reconstruct page order
- [ ] Integrate with legacy reconstructor

**Deliverables:**
- Bible loads via P2P
- Bitcoin Whitepaper loads via P2P
- All legacy scrolls work

**Testing:**
```python
# Load Bible via P2P
pointer = LegacyScrollPointer(bible_policy_id, ...)
file_bytes, content_type = reconstructor.reconstruct_legacy_scroll(pointer)
assert len(file_bytes) > 4_000_000  # Bible is ~4.6MB
```

---

### Phase 6: Optimization & Polish (Week 10) ⚡

**Goal:** Make it fast and reliable

**Tasks:**
- [ ] Smart caching (don't re-download)
- [ ] Parallel block fetches
- [ ] Connection retry logic
- [ ] Better error messages
- [ ] Performance metrics
- [ ] Memory optimization

**Deliverables:**
- Loads scrolls in under 30 seconds
- Uses less than 100MB RAM
- Graceful fallback on errors
- Clear progress indicators

---

### Phase 7: Testing & Documentation (Week 11) 📚

**Goal:** Production-ready release

**Tasks:**
- [ ] Comprehensive test suite
- [ ] User documentation
- [ ] Developer API docs
- [ ] Video tutorial
- [ ] Known issues list
- [ ] Performance benchmarks

**Deliverables:**
- Full test coverage
- User guide
- Developer guide
- Release notes

---

### Phase 8: Advanced Features (Week 12+) 🚀

**Goal:** Beyond MVP

**Tasks:**
- [ ] Multi-relay discovery (find healthy relays)
- [ ] Mithril integration (faster sync)
- [ ] Chain-sync streaming (real-time updates)
- [ ] Batch queries (load multiple scrolls)
- [ ] Compression (reduce bandwidth)
- [ ] Metrics dashboard (show stats)

---

## Technical Implementation Details

### Libraries Needed

```python
# Already have
cbor2>=5.4.0  # CBOR encoding/decoding
requests>=2.28.0  # HTTP (for API mode)

# Will need to add
pycardano>=0.9.0  # Cardano primitives (optional)
```

### Key Files to Create

```
ledger-scrolls/
├── viewer.py (main GUI - already updated)
├── p2p/
│   ├── __init__.py
│   ├── connection.py      # TCP connection + handshake
│   ├── protocols.py       # Mini-protocol implementations
│   ├── block_fetch.py     # BlockFetch protocol
│   ├── chain_sync.py      # ChainSync protocol (future)
│   ├── cbor_parser.py     # Block/Tx CBOR parsing
│   └── cache.py           # Cache management
├── tests/
│   ├── test_connection.py
│   ├── test_block_fetch.py
│   ├── test_cbor_parser.py
│   └── test_integration.py
└── docs/
    ├── p2p_protocol.md
    └── development.md
```

### Cache Structure

```
~/.ledger-scrolls/
├── logs/
│   └── viewer_20260121_123456.log
├── p2p_cache/
│   ├── blocks/
│   │   ├── slot_123456789.cbor
│   │   └── hash_abc123.cbor
│   ├── transactions/
│   │   └── tx_def456.json
│   └── metadata/
│       └── policy_ghi789_asset_jkl012.json
└── config.json
```

---

## Testing Strategy

### Unit Tests
- Test each mini-protocol in isolation
- Mock network responses
- Test CBOR parsing with known blocks
- Test caching logic

### Integration Tests
- Connect to actual relay (yours: 73.209.68.102:6000)
- Fetch real blocks
- Parse real data
- Reconstruct known scrolls

### Performance Tests
- Measure query time
- Measure memory usage
- Measure cache effectiveness
- Compare to Blockfrost mode

### User Acceptance Tests
- Load all three demo scrolls
- Verify hashes match
- Check file sizes
- Ensure UI responsiveness

---

## Known Challenges & Solutions

### Challenge 1: Protocol Complexity
**Problem:** Ouroboros protocol is complex  
**Solution:** Start simple (block-fetch only), add features incrementally  
**Resources:** cardano-node source code, Oura implementation

### Challenge 2: CBOR Parsing
**Problem:** Block structure varies by era  
**Solution:** Focus on Babbage era first (current), add others later  
**Resources:** cardano-cli source, CDDL specs

### Challenge 3: Finding Blocks
**Problem:** Don't know which block has our data  
**Solution:** Hybrid approach - use Blockfrost ONCE to find slot, then P2P forever  
**Alternative:** Maintain scroll→slot index

### Challenge 4: Connection Reliability
**Problem:** Relays might be down or slow  
**Solution:** Multi-relay support, automatic failover  
**Resources:** Public relay list from topology updater

---

## Success Metrics

### MVP Success (End of Phase 5):
- ✅ Hosky PNG loads via P2P
- ✅ Bible loads via P2P  
- ✅ Bitcoin Whitepaper loads via P2P
- ✅ Hash verification passes
- ✅ Files save correctly
- ✅ Logs capture all errors

### Production Success (End of Phase 7):
- ✅ 95% query success rate
- ✅ Under 30 second load time
- ✅ Under 100MB memory usage
- ✅ Clear error messages
- ✅ User documentation complete
- ✅ 80%+ test coverage

### Long-term Success:
- ✅ 1000+ users using P2P mode
- ✅ Community relay network
- ✅ Featured in Cardano docs
- ✅ Other projects adopt standard

---

## Release Plan

### v1.0 (Current - January 2026)
- ✅ Blockfrost mode
- ✅ Local node mode
- ✅ P2P mode (UI only, not functional)
- ✅ All three demo scrolls work (via Blockfrost/Local)

### v1.1 (February 2026)
- ✅ Bug fixes
- ✅ Better error messages
- ✅ HTML auto-detection
- ✅ Performance improvements

### v2.0 (Target: March-April 2026)
- ✅ P2P mode fully functional
- ✅ Standard scrolls via P2P
- ✅ Basic caching
- ✅ Connection retry logic

### v2.1 (Target: May 2026)
- ✅ Legacy scrolls via P2P
- ✅ Multi-relay support
- ✅ Performance optimizations
- ✅ Comprehensive tests

### v3.0 (Target: June+ 2026)
- ✅ Mithril integration
- ✅ Advanced caching
- ✅ Batch operations
- ✅ Metrics dashboard

---

## How To Contribute

### If you want to help build P2P mode:

1. **Study the protocol:**
   - Read: https://hydra.iohk.io/build/16881919/download/1/network.pdf
   - Study: cardano-node source (Haskell)
   - Reference: Oura (Rust implementation)

2. **Start small:**
   - Pick one task from Phase 1-2
   - Write tests first
   - Implement feature
   - Submit PR

3. **Test on real relay:**
   - Use provided relay (73.209.68.102:6000)
   - Test with known scrolls
   - Report results

4. **Document everything:**
   - Code comments
   - API docs
   - User guides
   - Known issues

### Areas needing help:

- **Protocol implementation** (Haskell/Rust/Python experience)
- **CBOR parsing** (Binary format experience)
- **Testing** (Write comprehensive tests)
- **Documentation** (Explain how it works)
- **UI/UX** (Improve user experience)

---

## Timeline Summary

```
Week 1-2:   TCP connection + handshake
Week 3-4:   Block fetching
Week 5-6:   CBOR parsing
Week 7:     Standard scrolls
Week 8-9:   Legacy scrolls
Week 10:    Optimization
Week 11:    Testing & docs
Week 12+:   Advanced features

Total: ~3 months for full implementation
```

---

## Final Thoughts

This is an ambitious but achievable goal. The viewer is already set up with the UI and infrastructure. Now we need to implement the actual P2P protocol.

**The beauty of this approach:**
- Users can start using Blockfrost mode TODAY
- P2P mode develops in parallel
- No breaking changes
- Progressive enhancement

**The vision:**
A truly permissionless viewer that anyone can use to read scrolls, with multiple options based on their needs:
- Casual user → Blockfrost (fast)
- Privacy user → P2P Lightweight (no API)
- Power user → Local Node (full sovereignty)

All three modes read the same immutable scrolls. All three embody the Ledger Scrolls ethos.

**Let's build the future of decentralized data access!** 🚀📜

---

*Last updated: January 21, 2026*
*Status: Phase 0 Complete (UI + Infrastructure)*
*Next: Phase 1 (TCP Connection)*
