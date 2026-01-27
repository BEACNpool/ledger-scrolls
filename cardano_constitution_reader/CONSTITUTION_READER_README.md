# Cardano Constitution Reader

**"Immutable Governance Framework • Verified On-Chain"**

A production-grade tool for fetching and verifying the Cardano Constitution directly from on-chain NFT metadata. Built with the elegance and rigor that reflects the blockchain itself.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Part of Ledger Scrolls](https://img.shields.io/badge/Part%20of-Ledger%20Scrolls-green.svg)](https://github.com/BEACNpool/ledger-scrolls)

---

## Overview

The Cardano Constitution is the foundational governance document for the Cardano blockchain. It establishes rights and responsibilities of participants, defines governance processes and voting thresholds, and sets guardrails for protocol parameters and treasury withdrawals.

This tool reconstructs the Constitution text from **immutable on-chain storage** (CIP-721 NFT metadata), verifies cryptographic integrity via SHA-256, and provides beautiful terminal output that reflects the importance of this founding document.

### Why This Matters

- **Immutable** - Constitution is permanently stored on-chain
- **Verifiable** - Cryptographic SHA-256 hash guarantees integrity
- **Permissionless** - Anyone can fetch and verify independently
- **Transparent** - Complete audit trail via blockchain
- **Decentralized** - No reliance on centralized hosting

---

## Features

### 🎨 Beautiful Terminal Output
- **Rich formatting** with colors, panels, and tables
- **Progress bars** for long-running operations
- **Elegant verification display** with cryptographic proof
- **Graceful fallback** to plain output if `rich` not installed

### ⚡ Smart Fetching
- **Fast mode** - Uses pre-computed mint transaction hashes (~5-10 seconds)
- **Legacy mode** - Scans entire policy for pages (~30-60 seconds)
- **Auto-detection** - Automatically chooses best method
- **Local caching** - Stores verified constitutions to avoid re-downloading

### 🔒 Cryptographic Verification
- **SHA-256 hash verification** of reconstructed document
- **Integrity guarantees** - Detects any corruption or tampering
- **Verification reports** - Exportable JSON certificates
- **Chain-of-custody** - Complete provenance from blockchain

### 📊 Multiple Output Modes
- **Save to file** - Standard text file output
- **Display in terminal** - View with built-in pager
- **Verification export** - JSON report for auditing
- **Auto-open** - Open in default text editor after download

### 🏗️ Production-Ready Architecture
- **Type hints** throughout for safety
- **Dataclasses** for clean structure
- **Proper error handling** with meaningful messages
- **Retry logic** with exponential backoff
- **Rate limiting** for API courtesy

---

## Installation

### Prerequisites

- Python 3.7 or higher
- Blockfrost API key (free tier sufficient)

### Setup

```bash
# Clone the repository
git clone https://github.com/BEACNpool/ledger-scrolls.git
cd ledger-scrolls/cardano_constitution_reader

# Install dependencies
pip install rich

# Optional: Set environment variable for API key
export BLOCKFROST_PROJECT_ID="mainnet..."
```

### Getting a Blockfrost API Key

1. Visit [blockfrost.io](https://blockfrost.io)
2. Sign up for free account
3. Create a **Cardano Mainnet** project (important!)
4. Copy your `project_id` (starts with `mainnet...`)
5. Free tier provides 50,000 requests/day (more than sufficient)

---

## Quick Start

### Basic Usage

```bash
# Fetch current constitution (Epoch 608)
./cardano_constitution_reader.py --epoch 608

# Fetch historical constitution (Epoch 541)
./cardano_constitution_reader.py --epoch 541

# Provide API key via command line
./cardano_constitution_reader.py --epoch 608 --api-key mainnet...
```

### Advanced Usage

```bash
# Display constitution in terminal with paging
./cardano_constitution_reader.py --epoch 608 --display

# Export verification report as JSON
./cardano_constitution_reader.py --epoch 608 --export-verification

# Use fast mode with mints file
./cardano_constitution_reader.py --epoch 608 --mints-file constitution_epoch_608_mints.json

# Skip cache and fetch fresh
./cardano_constitution_reader.py --epoch 608 --no-cache

# Non-interactive mode (for scripts)
./cardano_constitution_reader.py --epoch 608 --non-interactive --api-key mainnet...

# Specify custom output directory
./cardano_constitution_reader.py --epoch 608 --out-dir ~/Documents/Cardano
```

---

## Available Versions

### Epoch 608 (Current)
- **Status:** ✓ Current Constitution
- **Ratified:** Epoch 608
- **Enacted:** Epoch 609
- **Voting Period:** Epochs 603-607
- **Policy ID:** `ef91a425ef57d92db614085ef03718407fb293cb4b770bc6e03f9750`
- **SHA256:** `98a29aec8664b62912c1c0355ebae1401b7c0e53d632e8f05479e7821935abf1`
- **Key Changes:**
  - Updated parameter guardrails
  - Clarified treasury withdrawal procedures
  - Enhanced Constitutional Committee provisions

### Epoch 541 (Historical)
- **Status:** Historical (Baseline Framework)
- **Ratified:** Epoch 541
- **Enacted:** Epoch 542
- **Voting Period:** Epochs 536-540
- **Policy ID:** `d7559bbfa87f53674570fd01f564687c2954503b510ead009148a31d`
- **SHA256:** `1939c1627e49b5267114cbdb195d4ac417e545544ba6dcb47e03c679439e9566`
- **Key Changes:**
  - Established foundational governance structure
  - Defined Constitutional Committee role
  - Set initial parameter guardrails

---

## Terminal Output Examples

### Banner & Information Display

```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ⚖️  CARDANO CONSTITUTION READER                             ║
║                                                               ║
║   Immutable Governance Framework • Verified On-Chain         ║
║   v2.0.0 by BEACNpool                                         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

┌─ Available Constitution Versions ─────────────────────────────┐
│ Epoch │ Status      │ Enacted    │ Description                │
├───────┼─────────────┼────────────┼────────────────────────────┤
│ 608   │ ✓ Current   │ Epoch 609  │ Current Constitution text  │
│ 541   │ Historical  │ Epoch 542  │ First ratified Constitut…  │
└───────┴─────────────┴────────────┴────────────────────────────┘
```

### Verification Display

```
┌─ Integrity Verification ──────────────────────────────────────┐
│ Check            │ Value                          │ Status     │
├──────────────────┼────────────────────────────────┼────────────┤
│ Expected SHA256  │ 98a29aec8664b62912c1c0355ebae… │            │
│ Computed SHA256  │ 98a29aec8664b62912c1c0355ebae… │            │
│ File Size        │ 67,234 bytes                   │            │
│ Fetch Mode       │ FAST                           │            │
│ Fetch Time       │ 8.3s                           │            │
│ Verification     │ Hashes Match                   │ ✓ VERIFIED │
└──────────────────┴────────────────────────────────┴────────────┘

╭─────────────────────────────────────────────────────────────╮
│ Constitution Epoch 608 is cryptographically verified ✓     │
│ This document is immutably stored on the Cardano blockchain │
╰─────────────────────────────────────────────────────────────╯
```

### Progress Indicators

```
⠋ Fetching pages...  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73% 8/11 0:00:02
  Page 008: tx cfda418d…
```

---

## Architecture

### Data Structures

The tool uses clean dataclasses for type safety:

```python
@dataclass
class Constitution:
    """Represents a Cardano Constitution version."""
    epoch: str
    name: str
    policy_id: str
    expected_sha256: str
    ratified_epoch: int
    enacted_epoch: int
    blurb: str
    voting_period: Optional[str] = None
    notable_changes: list[str] = field(default_factory=list)

@dataclass
class FetchResult:
    """Result of constitution fetch operation."""
    raw_bytes: bytes
    computed_hash: str
    verified: bool
    file_size: int
    fetch_time: float
    mode: str  # "fast", "legacy", or "cache"
```

### API Client

Elegant Blockfrost client with automatic retry and rate limiting:

```python
class BlockfrostClient:
    """Elegant Blockfrost API client with retry logic."""
    
    def get(self, endpoint: str, params: Optional[dict] = None) -> dict | list:
        """Make GET request with automatic retry and rate limiting."""
        # Exponential backoff on 429, 500, 502, 503, 504
        # Automatic rate limiting (250ms between requests)
        # Comprehensive error handling
```

### Fetch Modes

1. **Cache Mode** - Returns previously verified constitution
2. **Fast Mode** - Uses pre-computed mint tx hashes from mints file
3. **Legacy Mode** - Scans all assets under policy ID

The tool automatically selects the best mode based on available resources.

---

## Configuration

### Configuration File

Settings are stored in `~/.constitution_reader/config.json`:

```json
{
  "blockfrost_api_key": "mainnet..."
}
```

### Environment Variables

```bash
# Blockfrost API key
export BLOCKFROST_PROJECT_ID="mainnet..."
# or
export BLOCKFROST_API_KEY="mainnet..."
```

### Cache Directory

Verified constitutions are cached in `~/.constitution_reader/cache/`:

```
~/.constitution_reader/
├── config.json
└── cache/
    ├── constitution_epoch_541.txt
    └── constitution_epoch_608.txt
```

---

## Verification

### How Verification Works

1. **Fetch** pages from blockchain via Blockfrost API
2. **Reconstruct** original document by concatenating payloads
3. **Decompress** if gzip detected (automatic)
4. **Hash** reconstructed bytes with SHA-256
5. **Compare** with published hash from governance process
6. **Report** verification status with full details

### Verification Reports

Export JSON certificate of verification:

```bash
./cardano_constitution_reader.py --epoch 608 --export-verification
```

Generates `verification_epoch_608.json`:

```json
{
  "document": "Cardano Constitution",
  "epoch": "608",
  "timestamp": "2026-01-27T12:34:56.789012",
  "file_size_bytes": 67234,
  "expected_sha256": "98a29aec8664b62912c1c0355ebae1401b7c0e53d632e8f05479e7821935abf1",
  "computed_sha256": "98a29aec8664b62912c1c0355ebae1401b7c0e53d632e8f05479e7821935abf1",
  "verified": true,
  "fetch_mode": "fast",
  "tool": "constitution_reader v2.0.0",
  "blockchain": "Cardano Mainnet",
  "policy_id": "ef91a425ef57d92db614085ef03718407fb293cb4b770bc6e03f9750",
  "ratified_epoch": 608,
  "enacted_epoch": 609
}
```

---

## Command Reference

### Required Arguments

- `--epoch {541,608}` - Which constitution version to fetch

### Optional Arguments

- `--api-key KEY` - Blockfrost API key (mainnet...)
- `--config PATH` - Config file path (default: ~/.constitution_reader/config.json)
- `--out-dir DIR` - Output directory (default: current directory)
- `--mints-file FILE` - Path to mints JSON (enables fast mode)

### Flags

- `--display` - Display constitution in terminal with paging
- `--export-verification` - Export verification report as JSON
- `--open` - Automatically open file after download
- `--no-open` - Don't prompt to open file
- `--no-cache` - Skip cache and fetch fresh from blockchain
- `--no-save-key` - Don't persist API key to config
- `--non-interactive` - Fail instead of prompting for input
- `--version` - Show version and exit

---

## Technical Details

### Storage Format

The Constitution is stored as:
- **Multiple page NFTs** under a policy ID
- **CIP-721 metadata** with `i` (index) and `payload` fields
- **Gzip compression** for efficiency
- **Optional manifest NFT** with metadata

### Page Structure

Each page NFT contains:

```json
{
  "721": {
    "POLICY_ID": {
      "PAGE_001": {
        "i": 1,
        "payload": [
          {"bytes": "hex_data_segment_1"},
          {"bytes": "hex_data_segment_2"}
        ]
      }
    }
  }
}
```

### Reconstruction Algorithm

1. Fetch all assets under policy ID
2. Filter for page NFTs (have `i` and `payload`)
3. Sort pages by index `i`
4. Concatenate hex segments within each page
5. Concatenate all pages in order
6. Convert hex to bytes
7. Detect and decompress gzip if present
8. Verify SHA-256 hash

---

## Error Handling

### IntegrityError

Raised when hash verification fails:

```
⚠️  INTEGRITY VERIFICATION FAILED
Expected: 98a29aec8664b62912c1c0355ebae1401b7c0e53d632e8f05479e7821935abf1
Computed: a1b2c3d4e5f6...

This may indicate:
  • Network corruption during download
  • Incomplete page reconstruction
  • Mismatch between policy and expected version

The Constitution hash is a cryptographic guarantee.
Do not proceed with unverified data.
```

### APIError

Raised when Blockfrost API fails:
- Automatic retry with exponential backoff
- Clear error messages
- Respects rate limits

### Network Errors

Handled gracefully with:
- Connection timeout protection
- Retry logic (up to 6 attempts)
- Progressive backoff delays

---

## Comparison with Ledger Scrolls

This Constitution Reader is a **specialized implementation** of the Ledger Scrolls standard, optimized for the Constitution's specific format:

| Feature | Constitution Reader | Ledger Scrolls Viewer |
|---------|---------------------|----------------------|
| **Purpose** | Single-document tool | General scroll library |
| **Storage** | CIP-721 pages only | Both Standard + Legacy |
| **UI** | Terminal-based | GUI application |
| **Verification** | Constitution-specific | General hash verification |
| **Caching** | Built-in | Optional |
| **Output** | Production-grade CLI | User-friendly GUI |

Both tools share the same core principle: **permissionless, immutable, verifiable on-chain data**.

---

## Use Cases

### For Citizens
- Verify you have the authentic Constitution text
- Check for updates between versions
- Archive personal copy with cryptographic proof

### For Developers
- Integrate Constitution verification into dApps
- Build governance tooling with verified text
- Create automated compliance checkers

### For Researchers
- Compare historical versions
- Analyze governance evolution
- Study on-chain document storage

### For Auditors
- Verify Constitution integrity independently
- Generate verification certificates
- Audit governance compliance

---

## Performance

### Fast Mode (with mints file)
- **Time:** ~5-10 seconds
- **API Calls:** 11 (one per page)
- **Network:** Minimal

### Legacy Mode (full scan)
- **Time:** ~30-60 seconds
- **API Calls:** ~50-100 (depends on policy size)
- **Network:** Moderate

### Cache Mode
- **Time:** <1 second
- **API Calls:** 0
- **Network:** None

---

## Contributing

Contributions welcome! This tool is part of the larger Ledger Scrolls project.

### Areas for Contribution

- Additional constitution versions as they're ratified
- Performance optimizations
- Alternative blockchain data sources
- Enhanced verification reporting
- Additional output formats

### Development

```bash
# Clone repository
git clone https://github.com/BEACNpool/ledger-scrolls.git

# Install dependencies
pip install rich

# Run with development features
./cardano_constitution_reader.py --epoch 608 --no-cache
```

---

## FAQ

### Q: Do I need to run a Cardano node?

**A:** No. This tool uses the Blockfrost API, so no local node is required. However, the Constitution itself is stored on-chain and is verifiable by anyone with blockchain access.

### Q: How much does it cost?

**A:** Free! Blockfrost's free tier provides 50,000 API requests per day, which is more than sufficient.

### Q: Can the Constitution be modified or deleted?

**A:** No. Once published on-chain, the Constitution NFTs are immutable. The hash guarantee ensures you're reading the exact text that was ratified.

### Q: What if Blockfrost goes down?

**A:** The Constitution remains on-chain. You can:
1. Use cached version (if previously fetched)
2. Wait for Blockfrost to return
3. Query blockchain directly with `cardano-cli`
4. Use alternative indexer/API

### Q: How do I verify the hashes are correct?

**A:** The SHA-256 hashes are published through the official Cardano governance process. They are part of the on-chain governance action that enacted each Constitution version.

### Q: Can I use this in production systems?

**A:** Yes! This tool is production-ready with:
- Comprehensive error handling
- Retry logic and rate limiting
- Type safety
- Verification guarantees
- Clean architecture

### Q: What's the difference between versions?

**A:** Epoch 541 was the first ratified Constitution (baseline framework). Epoch 608 is an amended version with updated guardrails and clarifications based on governance feedback.

---

## Security

### Threat Model

This tool protects against:
- ✅ **Network corruption** - SHA-256 verification
- ✅ **API manipulation** - Hash comparison
- ✅ **Partial downloads** - Complete reconstruction check
- ✅ **Wrong version** - Policy ID verification

This tool does NOT protect against:
- ❌ **Compromised Blockfrost** - Consider running local node
- ❌ **Local malware** - Standard OS security applies
- ❌ **Key compromise** - (not applicable, read-only)

### Best Practices

1. **Verify hashes** against multiple sources
2. **Keep tool updated** to latest version
3. **Review code** before running (it's open source!)
4. **Export verification reports** for audit trails
5. **Use environment variables** for API keys (not CLI)

---

## Troubleshooting

### "No API key found"

**Solution:** Provide key via `--api-key`, environment variable, or interactive prompt.

### "Blockfrost error 403"

**Solution:** Ensure API key is for **Mainnet** (not Testnet) and is valid.

### "Hash verification failed"

**Solution:** This is serious. Do not trust the data. Possibilities:
- Network corruption during download
- Blockfrost API issue
- Wrong policy ID selected

Try:
1. Delete cache: `rm -rf ~/.constitution_reader/cache/`
2. Re-fetch: `./cardano_constitution_reader.py --epoch 608 --no-cache`
3. If still failing, report issue on GitHub

### "Connection timeout"

**Solution:** Tool will automatically retry. If persistent:
- Check internet connection
- Verify Blockfrost status
- Try again later

### "rich library not found"

**Solution:** Install with `pip install rich`. Tool will work without it (fallback to plain output), but you'll miss the beautiful formatting!

---

## Roadmap

### Current (v2.0.0) ✅
- ✅ Beautiful rich terminal output
- ✅ Fast mode with mints files
- ✅ Local caching
- ✅ Verification reports
- ✅ Display in terminal
- ✅ Production-ready architecture

### Future
- 📋 Web-based viewer (no installation required)
- 📋 Diff tool (compare versions side-by-side)
- 📋 Alternative blockchain data sources
- 📋 Governance timeline visualization
- 📋 Multi-language support

---

## Related Projects

- **[Ledger Scrolls](https://github.com/BEACNpool/ledger-scrolls)** - General-purpose on-chain data library
- **[Cardano Constitution](https://cardano.org/constitution/)** - Official constitution website
- **[Blockfrost](https://blockfrost.io)** - Cardano blockchain API

---

## License

MIT License - See [LICENSE](LICENSE) file for details

---

## Credits

**Built with ❤️ by [@BEACNpool](https://x.com/BEACNpool)**

Part of the [Ledger Scrolls](https://github.com/BEACNpool/ledger-scrolls) project: 
*"A library that cannot burn."*

Special thanks to:
- The Cardano community
- Blockfrost team for API access
- Intersect MBO for governance coordination
- All contributors to Cardano governance

---

## Support

- **Issues:** [GitHub Issues](https://github.com/BEACNpool/ledger-scrolls/issues)
- **Twitter/X:** [@BEACNpool](https://x.com/BEACNpool)
- **Documentation:** [Ledger Scrolls Docs](https://github.com/BEACNpool/ledger-scrolls)

---

**"In the digital age, governance must be immutable and verifiable."**

*The chain is the record. The Constitution is eternal.*
