# Ledger Scrolls 📜

**"A library that cannot burn."**
*Unfindable by bots. Verifiable by anyone. Deletable by no one.*

Ledger Scrolls is the free, open-source **reader and writer for immutable,
forever media**. That is the whole job — one job. It puts files **inside the
Cardano blockchain itself** — not a
link to a file, not a hash of a file kept somewhere else. The actual bytes,
inside transactions, on a ledger replicated by thousands of independent
computers around the world.

Once a scroll is written:

- **No one can edit it.** Not the author, not BEACN, not anyone.
- **No one can delete it.** There is no takedown, no admin key, no delete button.
- **Anyone can read it.** No account, no permission, no fee to read.
- **Everyone can verify it.** The bytes are checked against a SHA-256
  fingerprint on every read. Readers don't trust — they check.
- **No crawler can find it.** A scroll has no URL — it exists as fragments
  spread across transactions, and only becomes a file again when someone
  holding the pointer reassembles it. Search engines, scrapers, and
  content-ID systems see nothing; anyone you hand the pointer sees
  everything. Hidden from the web's machinery, not from people — the
  chain itself is radically public.

That combination has never existed before. Books burn. Servers go dark.
Links rot. Platforms moderate, archives get edited, companies fold. A
Ledger Scroll survives as long as the Cardano chain survives — and it cost
a few dollars, once.

If you're an artist, a journalist, a witness, or someone with words that
must outlive the platforms — this is for you.

---

## Why on-chain? — the economics of forever

The first reaction is always the price: *"dollars for kilobytes? My cloud
drive stores a terabyte for that."* That's comparing a headstone engraving
to a Post-it note. Nobody engraves their vacation photos in granite — you
engrave the few kilobytes you want read after you're gone.

**Per gigabyte, on-chain is absurd. Per *guarantee*, it's the cheapest
notary, archive, and courier-to-the-future ever built.** The honest
comparison isn't object storage — it's the notary (~$15 to witness a
signature, proves nothing about content), the provisional patent (~$300),
the safe-deposit box ($50 *a year, forever*), the archival service (alive
only as long as the archivist). Against those, a few dollars **once** is a
bargain — and none of them can prove *what*, *when*, and *who* the way a
chain can.

What the money actually buys:

- **Zero counterparty.** Every cloud file has a landlord. Eleven nines of
  durability measure disk failure — they are *zero* nines against a lapsed
  credit card, a policy change, an acquisition, a subpoena, or your own
  death. A scroll has no account, no invoice, no admin key, and no one to
  comply.
- **Forever, immutable.** Cloud durability is a promise from a company.
  Chain durability is a property of the system. Promises have expiration
  dates; companies just don't publish them.
- **A timestamp that is proof, not metadata.** "Last modified" is a database
  field an admin can edit. A block height is a fact thousands of independent
  machines will swear to. The cloud can *assert* when — only a chain can
  *prove* it.
- **Cryptographic authorship.** Scrolls arrive signed by their author's own
  keys — an unforgeable byline. In the deepfake era, *"I provably published
  exactly these words, on exactly this date, from this key"* is not a
  gimmick; it's a defense.
- **A complement, not a replacement.** Cloud storage answers *"where do I
  put 10 terabytes?"* Ledger Scrolls answers *"how do I make 10 kilobytes
  unkillable?"* Different questions. Mocking one for failing at the other
  cuts both ways — try hosting something on a cloud drive that its
  trust-and-safety team dislikes.

## What belongs in a scroll

The value is highest where the adversary is **time, power, or your own
counterparty — never volume.** That's the test. Some things that pass it:

**Truth vs. power**
- Whistleblowing and source material no host or ISP can take down
  (see [BEACN Leaks](leaks.html))
- The *last copy* — preserving what was already published before it gets
  stealth-edited, retracted, or memory-holed
- Witness testimony and evidence fingerprints, timestamped before anyone
  can question the chain of custody
- Warrant canaries — signed, dated, unforgeable, and their *absence* is
  detectable

**Priority & authorship**
- Prior-art / defensive publication — timestamp an invention for a few
  dollars, strong enough to invalidate a later patent claim
- Scientific pre-registration — you can't p-hack a hypothesis you can't edit
- Art provenance — the artist signs the work and a statement at creation;
  settles authenticity fights decades later

**Outliving institutions**
- Credentials that survive their issuer — schools close, registries burn,
  the chain doesn't
- Estate letters and time capsules — readable in forty years with no
  company, subscription, or executor surviving the trip
- Memorials and guestbooks that don't die with a funeral home's website
  (see [Ledger Book](https://beacnpool.github.io/ledger-scrolls/ledger-book.html))

**Integrity anchors**
- Software release hashes and signing keys, published where a compromised
  website can't rewrite them
- Public promises — platforms, pledges, terms-of-service — quotable back
  *verbatim*, with date, when someone claims they never said it
- Two-party agreements with both signatures cryptographic and the document
  impossible to "lose" (countersigned scrolls, label `22026`)

---

## 📚 The full catalog

Every scroll BEACNpool has written, with all its keys (pointer, policy,
asset, hashes) in one browsable list: **[BEACNpool's Library →](BEACNpool's%20Library/README.md)**

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
| [Main Viewer](https://beacnpool.github.io/ledger-scrolls/) | Read & verify any scroll — browse and verify any scroll, channel, or registry |
| [Build a Reader](https://beacnpool.github.io/ledger-scrolls/build-a-reader/) | Everything to build your own reader in an afternoon — the minimal reference reader itself is minted on-chain |
| [Mint a Scroll](https://beacnpool.github.io/ledger-scrolls/calculator.html) | The one-stop shop: drop any file → what forever costs — and small files mint right there from your browser wallet, no node, no CLI |
| [Media Types](https://beacnpool.github.io/ledger-scrolls/media.html) | What can live forever — every media type that works, prep tips, live proof scrolls, prices |
| [BEACN Leaks player](https://beacnpool.github.io/ledger-scrolls/leaks.html) | Publisher-channel player — point at a policy ID; this site hosts nothing |

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
| **Standard Scroll** | Whole file in one locked UTxO datum | Small treasures ≤ ~14 KB: messages, poems, icons. Strongest guarantee Cardano can give. |
| **Chain Scroll** | File split across plain tx metadata, anchored by a manifest | Everything else: books, images, PDFs, audio, video. ~0.06 ADA/KB, nothing locked per page. |
| **Original NFT pages** | one NFT per page (2026, the first scrolls) | Reading the historical scrolls (Bible, Constitutions). New scrolls use the Chain Scroll format. |

Specs: [Protocol v1](docs/PROTOCOL_V1_PROPOSAL.md) ·
[Chain Scroll wire format](registry/spec/manifest-chain-v2.md) ·
[Standard Scrolls](docs/STANDARD_SCROLLS.md) ·
[Original NFT pages](docs/LEGACY_SCROLLS.md)

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
protocol that survives its creators. **[docs/BUILD_A_READER.md](docs/BUILD_A_READER.md)**
is the complete guide to writing your own reader; the [conformance suite](conformance/)
ships test vectors so your thirty lines and ours can prove they agree:
`python3 conformance/run_conformance.py` or `node conformance/run_conformance.mjs`.

And the minimal reader — **[examples/the-reader/reader.html](examples/the-reader/reader.html)**, one dependency-free
file that speaks the open Koios API (any endpoint you choose) or Blockfrost
with your own key — **is itself minted on Cardano as a scroll**
(`9a564165ebdc4e0c4a2e1163b5cf9355604ecb8e163b425d834570e5b9007de2#0`,
receipts in [examples/the-reader/](examples/the-reader/)). The library holds
its own pair of glasses: even if every website disappears, a working reader
can be rebuilt from the chain it reads — which then reads every other
scroll, including itself.

---

## Write your own scroll

**No node? No command line?** Small files (≤ ~14 KB encoded) mint **in one
click from a browser wallet** — Eternl, Lace, Typhon, Vespr — on the
**[Mint a Scroll](https://beacnpool.github.io/ledger-scrolls/calculator.html)**
page. The transaction is built locally in auditable page JS, your wallet signs
and submits it, and the page reconstructs the scroll from the chain and checks
both SHA-256s before declaring success. Nothing to install, no API key, no
custody — if you can send ADA, you can write forever.

For bigger files (Chain Scrolls) use the CLI toolkit —
**[docs/YOUR_FIRST_SCROLL.md](docs/YOUR_FIRST_SCROLL.md)** is the 10-minute
quickstart. The short version:

```bash
# Small file (≤ ~14 KB gzipped) → Standard Scroll:
./scripts/mint-standard-scroll.sh yourfile payment.skey payment.addr

# Anything larger → Chain Scroll:
python3 tools/lschain/prepare.py yourfile --out build/   # hashes, splits, prices it
tools/lschain/mint.sh build/ payment.skey payment.addr   # mints pages + manifest
```

### The five rules of the scroll

1. **Permanent means permanent.** No edit, no delete. Never inscribe
   secrets, private data, or words you may regret.
2. **Rehearse on testnet.** Same bytes, free mistakes — run the full
   pipeline on the Preview testnet before spending mainnet ADA.
3. **Hash before, verify after.** Record your file's SHA-256 before minting;
   reconstruct from chain and compare before telling the world.
4. **Keep receipts.** Transaction hashes are how civilization finds your
   scroll again.
5. **Self-contained files only.** Anything that phones home — external
   images, fonts, scripts — is a future broken promise. Inline everything.

Which media types work, with live proof scrolls and prices:
**[media.html](https://beacnpool.github.io/ledger-scrolls/media.html)**.
Media-specific best practices (text, images, HTML, PDF, audio, video, data):
**[docs/CREATING_SCROLLS.md](docs/CREATING_SCROLLS.md)**. Every skeptic's
question, answered straight: **[docs/FAQ.md](docs/FAQ.md)**.

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

## Agree on it, on-chain (countersigned scrolls)

Two parties, one document: mint the terms as a scroll, then each party
**countersigns** with a small transaction naming the scroll and its hash —
a signing platform's audit trail with no platform. Exact bytes, signer
keys, block timestamps, ordering: reconstructible forever from any Cardano
node. The mint page emits the acceptance JSON pre-filled. Spec:
[registry/spec/countersigned-scroll-v1.md](registry/spec/countersigned-scroll-v1.md).

---

## The family — apps built on the scrolls

The same primitives (bytes in transactions, metadata labels, wallet signatures)
power more than a library:

- **✒️ [Ledger Book](https://beacnpool.github.io/ledger-scrolls/ledger-book.html)** —
  guestbooks that live inside Cardano **as NFTs**. Mint your book (~0.21 ADA),
  share the link; every signature is a real transaction — a name, a message,
  and the signer's own wallet keys — bound to the book NFT forever and
  traveling with it to any wallet (label `22031`). Books are found by
  **$handle**, address, or `policy.Name` pointer. The ~1 ADA isn't a fee to a
  platform — the anchor goes to the **book's keeper**, and the price is a
  filter: dozens of signatures that meant something, not thousands of posts
  that didn't. Open protocol, MIT:
  [registry/spec/ledger-book-v1.md](registry/spec/ledger-book-v1.md).
- **♟️ [Ledger Chess](https://beacnpool.github.io/ledger-scrolls/ledger-chess.html)** —
  a chess arcade whose deterministic referee engine is itself minted on-chain;
  beat it and etch your victory into Cardano forever (label `22030`).

---

## Repository map

```
ledger-scrolls/
├── index.html              # THE LIBRARY — the app, one dependency-free file (source = deployment)
├── reader.html             # retired stub → build-a-reader/ (the minted reader lives in examples/the-reader/)
├── build-a-reader/         # BUILD YOUR OWN READER — the one-stop guide page
├── calculator.html / leaks.html / media.html   # site pages (Pages serves repo root)
├── ledger-book.html        # LEDGER BOOK — guestbooks as NFTs (spec: registry/spec/ledger-book-v1.md)
├── ledger-chess.html       # LEDGER CHESS — the on-chain arcade + victory leaderboard
├── docs/                   # All guides — start at docs/README.md
│   └── history/            # Past audits & design reviews
├── registry/               # Registry + protocol specs, JSON schemas, examples, tooling
├── conformance/            # Protocol test vectors + Python/Node runners
├── tools/lschain/          # Chain Scroll writer (prepare / mint)
├── tools/cors-mirror/      # deploy-your-own Koios CORS mirror (~25 lines)
├── scripts/                # Standard Scroll minting & verification
├── viewers/koios-cli/      # Zero-dependency Python readers
├── koios-viewer/           # Full Python viewer/reconstructor (lsview)
├── templates/              # Datum + policy templates (incl. the always-fail script)
├── examples/               # Every live scroll: exact source + receipts.json
└── media/                  # Assets used by the standalone viewers
```

The viewer obeys the same ethos as the scrolls it reads: one dependency-free
HTML file — save it to a USB stick and it still works. How the layers fit
(and which ones are allowed to die): **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

---

## Philosophy

- **Open standard** — specified, tested, forkable; implementable by strangers
- **Permissionless** — no account, no gatekeeper; anyone with a few ADA publishes
- **Non-custodial** — no admin key anywhere in the design
- **Non-indexed** — deterministic pointers, not search
- **Local-first** — viewer and verifier run offline from disk
- **Permanently locked** — the strongest scrolls sit where no one can ever spend them
- **Complement, not replacement** — clouds hold your terabytes; the chain
  holds your testimony

BEACN is a librarian, not a landlord — and unlike your cloud drive, this
library *has* no landlord. If BEACN disappears tomorrow, every scroll
survives: the data is on a public chain, the spec is public, and the
protocol can be rebuilt from the spec alone.

*Mint deliberately. The library cannot burn — and it cannot forget.*

---

## Contributing & security

[CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) ·
[MIT License](LICENSE)

Maintained with ❤️ by [@BEACNpool](https://x.com/BEACNpool)
