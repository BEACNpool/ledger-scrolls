# FAQ — every question, answered straight

## The basics

**What is Ledger Scrolls, in one sentence?**
The free, open-source reader and writer for immutable, forever media — files
stored byte-for-byte inside the Cardano blockchain, rebuilt and hash-verified
by anyone, deletable by no one.

**Is this an NFT project?**
No. A modern scroll mints **zero tokens** — the file rides in plain
transactions, sealed by one unspendable manifest. (The very first scrolls in
2026 used NFT pages; they're still readable, but nobody mints that way now.)

**What can I store?** Anything with bytes: text, HTML, images, PDF, audio,
video, datasets. Best practices per type: [CREATING_SCROLLS.md](CREATING_SCROLLS.md).

**What does it cost?** Network fees, once — roughly **0.06 ADA per KB**,
plus ~1.5 ADA locked forever with the manifest. A manifesto costs a coffee;
a 5 MB video ≈ 380 ADA. Exact quote before you sign: the
[cost calculator](https://beacnpool.github.io/ledger-scrolls/calculator.html).
No subscription, no renewal, no pinning bill, ever.

## Trust

**Why should I trust BEACN?**
You shouldn't — that's the design. Readers recompute SHA-256 against the
on-chain commitment on every read; a wrong byte renders nothing. The spec,
the reader, and the conformance tests are public; the reader and the spec
are *themselves stored on the chain* ([the-reader](../examples/the-reader/),
[the-spec](../examples/the-spec/)). If BEACN disappears tomorrow, nothing
about any scroll changes.

**Who controls a scroll after minting?**
No one — not the author, not BEACN, not Cardano's founders. The manifest
sits at an address whose spending script always fails. There is no admin key
anywhere in the design.

**Is "forever" real?**
As long as any copy of the Cardano chain exists, every scroll survives —
the same replicated history that secures the money secures the media.
"Permanent" here means: bound to the survival of the ledger itself, which is
the strongest guarantee any digital object has ever had.

**What about the data source — isn't that a middleman?**
A reader needs *some* window onto the chain, and you choose yours: your own
node, any Koios-compatible endpoint, a
[two-minute self-hosted mirror](../tools/cors-mirror/), or Blockfrost with
your own key. A source can refuse to serve you; it can never fool you —
hashes are checked locally. Full trust ladder: [ARCHITECTURE.md](ARCHITECTURE.md).

## The obvious objections

**Why not IPFS?**
IPFS guarantees integrity, not existence. A CID of unpinned bytes is a
fingerprint of a ghost — verifiable forever, readable never. Pinning is a
subscription; a scroll is a purchase. And "anchor + hash on IPFS" still uses
the chain — it's ledger *plus* a second system with a landlord.

**Why not Arweave?**
Arweave is honest one-time-fee storage and we respect it. Ledger Scrolls
puts bytes on **Cardano** specifically: the chain people already run nodes
for, with no separate token, no separate network to bet on, and media
sitting in the same history as the governance and money it may need to
outlive. Different bet; pick yours.

**Isn't this blockchain bloat?**
Cardano charges per byte precisely so users pay for what the network
carries. A scroll pays full freight at protocol prices — that's not abuse,
that's the fee market doing its job. And the format is deliberately frugal:
gzip first, ~0.06 ADA/KB, nothing minted.

**Energy?** Cardano is proof-of-stake. A scroll's marginal energy cost is a
few ordinary transactions.

**Can someone put something horrible on-chain?**
Permissionless systems can carry awful things; that's true of paper, the
internet, and every ledger. Ledger Scrolls readers render nothing by
default, verify everything, sandbox HTML, and fetch only what a user
explicitly points at. We publish norms (no private data, no secrets, consent,
restraint — [the five rules](YOUR_FIRST_SCROLL.md)) and we don't index
anything we haven't chosen to catalog. The protocol can't censor; the
catalogs can curate.

**What about the right to be forgotten / GDPR?**
Exactly why the rules say **never inscribe personal data** — yours or
anyone else's. Permanence is a one-way door; publish only what should
survive you.

**Can I delete my scroll?** No. Read that again before minting. Rehearse on
testnet; the mistakes are free there.

## Practical

**How do I read a scroll right now?**
[The Library](https://beacnpool.github.io/ledger-scrolls/) in any browser —
or [reader.html](../reader.html) from a USB stick — or two `curl` commands
([BUILD_A_READER.md](BUILD_A_READER.md)).

**How do I write one?**
[YOUR_FIRST_SCROLL.md](YOUR_FIRST_SCROLL.md) — ten minutes, a funded
wallet, and a file you've thought hard about.

**How do I publish under a byline nobody can fake?**
A [publisher channel](../registry/spec/publisher-channel-v1.md): a minting
policy only your key can write under. Readers follow the policy ID the way
they once followed a handle — no platform can suspend, seize, or imitate it.

**I found a bug / want to add my scroll to the catalog.**
PRs welcome: [CONTRIBUTING.md](../CONTRIBUTING.md). Registry entries need a
pointer and a `sha256`, nothing else.

**Who pays for the website?**
Nobody has to. GitHub Pages serves static files; every page works from a
local copy of the repo; the scrolls live on-chain. The site is a lens, not
a home.
