# Ledger Book ✒️

> Compatibility note: books minted before the v2 hardening remain readable.
> New books use `ledger-book-v2`: their native mint policy requires the
> minter's signature and expires one hour after construction, preventing later
> duplicate minting. Canonical identity uses policy id plus raw asset-name hex.
> See [the v2 specification](../registry/spec/ledger-book-v2.md).

**Guestbooks that live inside Cardano — as NFTs.**
*Sign something that outlives the light.*

Ledger Book is part of the [Ledger Scrolls](../README.md) family and lives in
this repository until the day it outgrows it. The app itself is one
dependency-free file at the repo root — **[ledger-book.html](../ledger-book.html)**
([live](https://beacnpool.github.io/ledger-scrolls/ledger-book.html)) — because
the link minted into every Book NFT's on-chain metadata points there, forever.
This folder is the product's home for everything else.

- **Protocol specs (MIT):** [v1 compatibility](../registry/spec/ledger-book-v1.md) · [v2 current](../registry/spec/ledger-book-v2.md)
- **Metadata label:** `22031` (signatures) · v2 book NFTs are CIP-25 under a signature + expiring-slot native policy
- **Live since:** 2026-07-09 — first book `BEACN_Book` (find it by searching **$beacn**),
  first signature *"First — Welcome to BEACN Book <3"*, both on mainnet forever.

---

## What it is

Your book is an **NFT**. Whoever holds the NFT holds the book. A signature is a
real Cardano transaction: the signer's name (≤64 bytes) and message (≤192 bytes)
in metadata label `22031`, bound to the book's `policy.AssetName` key — plus a
protocol-minimum anchor (~1 ADA) paid **to the book's current keeper**. Move the
NFT to any wallet and every signature travels with it: readers walk the NFT's
full ownership history and collect the entries wherever the book has lived.

Books are found three ways: **$handle**, **address**, or the **pointer**
(`policy.AssetName`). No account, no server, no database — any reader asks the
chain and lays out the pages fresh.

| act | cost | where the money goes |
|---|---|---|
| Mint a book | ~0.21 ADA | network fee (the ~1.2 min-UTxO rides with the NFT — still yours) |
| Sign a book | ~1.15 ADA | ~0.98 anchor **to the book's keeper** + ~0.17 network fee |

Nobody else profits. There is no platform to pay.

---

## Why a signature costs something

The obvious question: *comments are free on X and Facebook — why pay ~1 ADA?*
Backwards. **A comment is worthless because it's free.** Zero cost is why there
are billions, why most are bots, why the feed buries them in minutes, and why
nobody — including their authors — ever reads one again. Platforms optimize for
volume because comments are ad inventory: your words on their wall, sold by
them, deletable by them, gone when the platform folds.

A signature is different in kind:

- **The price is a filter, not a fee.** ~1 ADA is trivial as money and enormous
  as a signal: it selects for people who mean it. Cost creates ceremony;
  ceremony creates meaning. A book fills with dozens of signatures that meant
  something, not thousands of posts that didn't.
- **Spam is self-defeating — economically and forensically.** Spamming a feed
  is free; spamming a book costs ~1.15 ADA *per message*, and the anchor goes
  to the very person you're spamming — every unwanted message **pays the book's
  keeper**. And it's signed: each entry carries the spammer's own wallet
  address, on a public ledger, permanently. Spam that funds its victim and
  fingerprints its sender isn't spam anymore; it's a donation with a confession
  attached.
- **The anchor is a gift, not rent.** Signing pays the book's keeper — like
  bringing a bottle to the host. Nobody sells the wall.
- **You write for a different reader.** On a feed you talk to the room. In a
  book you write for whoever opens it in fifty years. That shift in imagined
  audience is why the messages carry more thought — the medium demands it.
- **It's provably you, forever.** Any troll can type any name under a post. A
  signature carries its author's wallet keys — unforgeable, uneditable,
  undeletable, even by the book's owner. That's what makes autograph economics
  real: a book signed by the right people becomes an heirloom *because*
  signatures are scarce, verifiable, and bound to the object.

**"Free comments are written for the algorithm. Signatures are written for the
future — and the future doesn't read feeds."**

## What belongs in a book

Same test as every scroll: the adversary is **time, power, or your own
counterparty — never volume**. Books where it shines:

- weddings, births, graduations — the guestbook that can't be lost in a move
- memorials — condolences that don't die with a funeral home's website
- milestones for projects, pools, DAOs — supporters' words bound to the era
- visitor books for places and events — provably *"I was there, then"*
- autograph books — collect signatures from people whose keys are known;
  the book itself becomes the asset

## Origin story

The first Ledger Book was minted, signed, and verified on **2026-07-09** — all
three firsts on camera, all on mainnet: mint tx `2f5324ba…`, first signature tx
`47be5be6…`. The brand film built from that footage lives with the product; the
day also produced the protocol's favorite line, found in the empty book state:

> *This page is blank. Someone has to be first — and first is forever.*
