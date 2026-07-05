# Finding a Scroll — the lookup keys explained

Every scroll in the [inventory](SCROLL_INVENTORY.md) lists several
identifiers. They are **not interchangeable** — each answers a different
question. This page explains what each one is, when to use it, and where you
paste it.

**The one-line mental model:**

> A **pointer** finds *one file*. A **policy ID** finds *a byline or a
> page-set*. A **tx hash** finds *a transaction*. A **registry head** finds
> *a whole catalog*. A **SHA-256** doesn't find anything — it *proves* what
> you found.

---

## Pointer — `txHash#ix`  ·  finds one file

The primary key. A pointer is a Cardano **UTxO reference**: a 64-character
transaction hash, a `#`, and an output index (almost always `#0`).

It points at a scroll's **manifest** (Chain Scroll) or its **locked datum**
(Standard Scroll). Hand a pointer to the reader and it rebuilds *that one
file* from the chain and verifies its hash before showing a byte.

- **Looks like:** `b6d9e70a751398fae0dc86580ce256802e6aea9ae0978b8c92b88b50a536962b#0`
- **Use it to:** open and verify a specific scroll.
- **Paste it into:** the Library reader bar → [beacnpool.github.io/ledger-scrolls](https://beacnpool.github.io/ledger-scrolls),
  or a deep link `…/#s=<name>`.
- **Pointer kinds** (declared in the registry): `manifest-chain-v2` (Chain
  Scroll), `utxo-inline-datum-bytes-v1` (Standard Scroll).

## Policy ID — 56 hex  ·  finds a byline OR a page-set

A **minting policy**. In Ledger Scrolls a policy ID means one of two things:

1. **A publisher channel** — a policy used as a permanent, unforgeable
   byline. Only the key holder can ever publish under it. Point the reader at
   the policy and it opens the channel's **feed** — every issue published to
   that byline, in order. Examples: BEACN Leaks
   (`5f569d01614c42003131c40b46d0b58c351a718907645c96d6da5415`), LEDGER_SCROLLS,
   the Ledger Docket.
2. **A legacy CIP-25 page-set** — the original scrolls (the Bible, both
   Constitutions, First Video, FIRST WORDS) are stored as **NFT pages**, all
   minted under one policy. The policy groups every page of that one file.

- **Looks like:** `38fbd56d7de6eb9df88599b5b102304df4c817aee53e4fb9c59cbed2`
- **Use it to:** open a channel feed, or reconstruct a legacy page-set.
- **Paste it into:** the reader bar (auto-detected), the
  [BEACN Leaks player](https://beacnpool.github.io/ledger-scrolls/leaks.html)
  (`leaks.html#policy=<id>`), or the [Ledger Docket](https://beacnpool.github.io/ledger-scrolls/legal.html).

## TX hash — 64 hex, no `#ix`  ·  finds a transaction

Just the transaction-hash half of a pointer, with the output index dropped.
On its own it identifies **one transaction** — useful on a block explorer to
inspect a mint, a manifest tx, or an individual page tx. It is **not a
complete scroll pointer**: add `#0` to make it one.

- **Looks like:** `ceced54b2bd462b1ed41864f2583309666010ce1fb96b9f3dc9968174d958bc9`
- **Use it to:** look up a transaction on any Cardano explorer
  (cexplorer.io, cardanoscan.io, pool.pm), or fetch page bytes directly.
- **Note:** a Chain Scroll's *page* txs are separate hashes from its
  *manifest* pointer — the manifest lists them.

## Registry head — a `txHash#ix`  ·  finds a whole catalog

A special pointer to a **registry** — the on-chain directory ("DNS for
scrolls") that maps names to pointers. Give the reader a registry head and it
**swaps the entire library** to that catalog's shelf. Registries are
forkable: anyone can publish their own head. See
[registry/](../registry/) and [resolution.md](../registry/spec/resolution.md).

- **Use it to:** load someone else's whole catalog, or your own fork.
- **Paste it into:** the reader's "registry head" anchor (About → Your trust
  anchors).

## SHA-256 — 64 hex  ·  proves, doesn't find

Not a locator — a **fingerprint**. Every scroll commits to the SHA-256 of its
finished bytes. The reader recomputes it locally after reconstruction and
renders **only if it matches**. You verify *with* a hash; you don't search
*by* one (though you can grep a receipt to confirm you have the right file).

- **Looks like:** `8bd5c906744197d94a7252f2607f671037b426eea18a05fa39330a85145b06e7`
- **Use it to:** confirm bytes are authentic and unaltered.

## Lock address — `addr1w…`  ·  the vault, not an index

The **always-fail script address** where Chain and Standard Scroll manifests
are locked forever (e.g. `addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn`).
Querying it lists every manifest UTxO parked there — but they aren't
individually named, so it's a vault you can inspect, not a searchable index.
Use the **pointer** to open a specific one.

---

## Quick comparison

| Key | Length / shape | Finds | Where you use it |
|---|---|---|---|
| **Pointer** | `64hex#ix` | one file | reader bar → rebuild + verify |
| **Policy ID** | 56 hex | a channel feed, or a legacy page-set | reader bar / leaks / docket |
| **TX hash** | 64 hex | one transaction | block explorer |
| **Registry head** | `64hex#ix` | a whole catalog | reader trust-anchor |
| **SHA-256** | 64 hex | *nothing — it verifies* | local hash check |
| **Lock address** | `addr1w…` | the manifest vault (unindexed) | explorer / advanced |

**Rule of thumb:** to *read a specific scroll*, you want its **pointer**. To
*follow a publisher*, you want their **policy ID**. Everything else is for
inspection or proof.

Full per-scroll values: **[SCROLL_INVENTORY.md](SCROLL_INVENTORY.md)**.
Machine-readable: **[card-catalog.csv](../examples/card-catalog/card-catalog.csv)**.
