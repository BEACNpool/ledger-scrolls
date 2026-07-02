# Ledger Scrolls 📜

**"A library that cannot burn."**

Ledger Scrolls is the free, open-source **reader and writer for immutable,
forever media**. It puts files **inside the Cardano blockchain itself** — not a
link to a file, not a hash of a file kept somewhere else. The actual bytes,
inside transactions, on a ledger replicated by thousands of independent
computers around the world.

Once a scroll is written:

- **No one can edit it.** Not the author, not BEACN, not anyone.
- **No one can delete it.** There is no takedown, no admin key, no delete button.
- **Anyone can read it.** No account, no permission, no fee to read.
- **Everyone can verify it.** The bytes are checked against a SHA-256
  fingerprint on every read. Readers don't trust — they check.

That combination has never existed before. Books burn. Servers go dark.
Links rot. Platforms moderate, archives get edited, companies fold. A
Ledger Scroll survives as long as the Cardano chain survives — and it cost
a few dollars, once.

If you're an artist, a journalist, a witness, or someone with words that
must outlive the platforms — this is for you.

---

## Read a scroll right now (30 seconds, nothing to install)

Open **[The Library](https://beacnpool.github.io/ledger-scrolls/)** — a
single self-contained HTML page. Pick a scroll. Watch the trust log as your
browser queries the chain, reassembles the bytes, verifies the hash, and
only then renders. Nothing is hosted; everything is proven.

Live on mainnet today: a freedom-of-speech manifesto, both Cardano
Constitutions, the complete Bible (237 pages), the Bitcoin whitepaper, a
video, and the protocol's own tutorial — stored as a scroll, by the
technology it teaches. Full list with hashes and receipts:
**[docs/SCROLL_INVENTORY.md](docs/SCROLL_INVENTORY.md)**.

| Site | What it is |
|---|---|
| [The Library](https://beacnpool.github.io/ledger-scrolls/) | Main viewer — browse and verify any scroll, channel, or registry |
| [Create a Scroll](https://beacnpool.github.io/ledger-scrolls/create.html) | The friendly how-to: costs, estimator, full workflow |
| [BEACN Leaks player](https://beacnpool.github.io/ledger-scrolls/leaks.html) | Publisher-channel player — point at a policy ID; this site hosts nothing |
| [Ledger Docket](https://beacnpool.github.io/ledger-scrolls/legal.html) | Legal-records terminal — pull a recorded instrument by document number |
| [Constitution](https://beacnpool.github.io/ledger-scrolls/constitution.html) · [Bible](https://beacnpool.github.io/ledger-scrolls/bible.html) · [First Video](https://beacnpool.github.io/ledger-scrolls/first-video.html) · [Latest](https://beacnpool.github.io/ledger-scrolls/latest.html) · [Testnet PoC](https://beacnpool.github.io/ledger-scrolls/preview.html) | Standalone viewers |

---

## How it works (the whole idea in one diagram)

```
 POINTER            MANIFEST                 PAGES                YOUR FILE
 one tx id   ──▶    locked on-chain    ──▶   plain txs      ──▶  concat → gunzip
 (share it          forever: type,           carrying the        → sha256 ✓
  as a QR)          hashes, page list        actual bytes        verified, rendered
```

Everything starts from a **pointer** — a single transaction id. It leads to
a **manifest**: a tiny record locked inside an *unspendable* Cardano UTxO
(an "always-fail" script address — an unbreakable vault every node carries
forever). The manifest declares what the file is, lists the exact
transactions holding its pages, and commits to the SHA-256 of the finished
file. A viewer fetches, reassembles, and **proves** the result before
showing you a single byte.

No indexer. No search. No trust. One pointer, a handful of deterministic
queries, and arithmetic.

**The golden rule: a viewer never shows you bytes it could not verify.**

### The three formats

| Format | How bytes live | Use it for |
|---|---|---|
| **Standard Scroll** (LS-LOCK) | Whole file in one locked UTxO datum | Small treasures ≤ ~14 KB: messages, poems, icons. Strongest guarantee Cardano can give. |
| **Chain Scroll** (LS-CHAIN v2) | File split across plain tx metadata, anchored by a manifest | Everything else: books, images, PDFs, audio, video. ~0.06 ADA/KB, nothing locked per page. |
| **Legacy Pages** (LS-PAGES) | CIP-25 NFTs carrying pages | Reading the historical scrolls (Bible, Constitutions). New scrolls use LS-CHAIN. |

Specs: [Protocol v1](docs/PROTOCOL_V1_PROPOSAL.md) ·
[LS-CHAIN v2](registry/spec/manifest-chain-v2.md) ·
[Standard Scrolls](docs/STANDARD_SCROLLS.md) ·
[Legacy Pages](docs/LEGACY_SCROLLS.md)

---

## Verify with your own hands (don't trust us — that's the point)

The entire protocol is two queries against any Cardano indexer. Free,
keyless, thirty lines of any language:

```bash
# 1. Fetch a manifest datum (content type, codec, hashes, page tx list):
curl -X POST https://api.koios.rest/api/v1/utxo_info \
  -H 'Content-Type: application/json' \
  -d '{"_utxo_refs":["<manifest-txhash>#0"], "_extended":true}'

# 2. Fetch the pages it names (label 22025 holds the payload segments):
curl -X POST https://api.koios.rest/api/v1/tx_metadata \
  -H 'Content-Type: application/json' \
  -d '{"_tx_hashes":["<page-tx-1>","<page-tx-2>"]}'

# Concatenate, gunzip, sha256sum — done.
```

Or use the tools in this repo:

```bash
# Zero dependencies, plain Python:
python3 viewers/koios-cli/read_scroll.py --list

# Full reconstructor:
cd koios-viewer
python3 -m lsview reconstruct-chain --txin <MANIFEST_TX>#0 --out scroll.html
sha256sum scroll.html   # must match the manifest's declared hash
```

A protocol simple enough to re-implement from its spec in an afternoon is a
protocol that survives its creators. The [conformance suite](conformance/)
ships test vectors so your thirty lines and ours can prove they agree:
`python3 conformance/run_conformance.py` or `node conformance/run_conformance.mjs`.

---

## Write your own scroll

**[docs/YOUR_FIRST_SCROLL.md](docs/YOUR_FIRST_SCROLL.md)** is the 10-minute
quickstart. The short version:

```bash
# Small file (≤ ~14 KB gzipped) → Standard Scroll:
./scripts/mint-standard-scroll.sh yourfile payment.skey payment.addr

# Anything larger → LS-CHAIN v2:
python3 tools/lschain/prepare.py yourfile --out build/   # hashes, splits, prices it
tools/lschain/mint.sh build/ payment.skey payment.addr   # mints pages + manifest
```

### The five rules of the scroll

1. **Permanent means permanent.** No edit, no delete. Never inscribe
   secrets, private data, or words you may regret.
2. **Rehearse on testnet.** Same bytes, free mistakes —
   [docs/PREVIEW_TESTNET_POC.md](docs/PREVIEW_TESTNET_POC.md).
3. **Hash before, verify after.** Record your file's SHA-256 before minting;
   reconstruct from chain and compare before telling the world.
4. **Keep receipts.** Transaction hashes are how civilization finds your
   scroll again.
5. **Self-contained files only.** Anything that phones home — external
   images, fonts, scripts — is a future broken promise. Inline everything.

Media-specific best practices (text, images, HTML, PDF, audio, video, data):
**[docs/CREATING_SCROLLS.md](docs/CREATING_SCROLLS.md)**.

---

## Publish under an unforgeable byline

A **publisher channel** is a Cardano minting policy used as a permanent
byline: only the holder of one key can ever publish under that policy ID.
No platform can suspend it, impersonate it, or reassign it. Readers follow
a policy ID the way they once followed a handle — except no authority on
Earth can post to it but you.

The first channel is **BEACN Leaks**
(`5f569d01614c42003131c40b46d0b58c351a718907645c96d6da5415`) — its founding
manifesto is [live on mainnet](examples/beacn-leaks-000/). Spec:
[registry/spec/publisher-channel-v1.md](registry/spec/publisher-channel-v1.md).

Discovery is handled by the **registry** — an on-chain directory (a "DNS
for scrolls") that is forkable by design: run your own, or PR an entry into
BEACN's public one. Spec and schemas: [registry/](registry/).

---

## Repository map

```
ledger-scrolls/
├── index.html              # THE LIBRARY — the app, one dependency-free file (source = deployment)
├── create.html / leaks.html / legal.html / …   # standalone site pages (GitHub Pages serves this repo root)
├── docs/                   # All guides — start at docs/README.md
│   └── history/            # Past audits & design reviews
├── registry/               # Registry + protocol specs, JSON schemas, examples, tooling
├── conformance/            # Protocol test vectors + Python/Node runners
├── tools/lschain/          # LS-CHAIN v2 writer (prepare / mint)
├── scripts/                # Standard Scroll minting & verification
├── viewers/koios-cli/      # Zero-dependency Python readers
├── koios-viewer/           # Full Python viewer/reconstructor (lsview)
├── templates/              # Datum + policy templates (incl. the always-fail script)
├── examples/               # Every live scroll: exact source + receipts.json
└── media/                  # Assets used by the standalone viewers
```

The viewer obeys the same ethos as the scrolls it reads: one dependency-free
HTML file — save it to a USB stick and it still works.

---

## Philosophy

- **Open standard** — specified, tested, forkable; implementable by strangers
- **Permissionless** — no account, no gatekeeper; anyone with a few ADA publishes
- **Non-custodial** — no admin key anywhere in the design
- **Non-indexed** — deterministic pointers, not search
- **Local-first** — viewer and verifier run offline from disk
- **Permanently locked** — the strongest scrolls sit where no one can ever spend them

BEACN is a librarian, not a landlord. If BEACN disappears tomorrow, every
scroll survives: the data is on a public chain, the spec is public, and the
protocol can be rebuilt from the spec alone.

*Mint deliberately. The library cannot burn — and it cannot forget.*

---

## Contributing & security

[CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) ·
[MIT License](LICENSE)

Maintained with ❤️ by [@BEACNpool](https://x.com/BEACNpool)
