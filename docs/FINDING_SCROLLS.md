# Finding a Scroll — the lookup keys explained

Every scroll in the [inventory](SCROLL_INVENTORY.md) lists several
identifiers. They are **not interchangeable** — each answers a different
question. This page explains what each one is, when to use it, and where you
paste it.

**The one-line mental model:**

> A **pointer** finds *one file*. A **policy ID** finds *a whole catalog, a
> byline, or a page-set*. A **$handle** finds *someone's library*. A
> **tx hash** finds *a transaction*. A **SHA-256** doesn't find anything —
> it *proves* what you found.

Everything below pastes into one place: the reader bar on
**[the Main Viewer](https://beacnpool.github.io/ledger-scrolls/)**. It
auto-detects which kind of key you gave it.

---

## Pointer — `txHash#ix`  ·  finds one file

The primary key. A pointer is a Cardano **UTxO reference**: a 64-character
transaction hash, a `#`, and an output index (almost always `#0`).

It points at a scroll's **manifest** (Chain Scroll) or its **locked datum**
(Standard Scroll). Hand a pointer to the reader and it rebuilds *that one
file* from the chain and verifies its hash before showing a byte.

- **Looks like:** `b6d9e70a751398fae0dc86580ce256802e6aea9ae0978b8c92b88b50a536962b#0`
- **Use it to:** open and verify a specific scroll.
- **Paste it into:** the reader bar, or share a deep link `…/#s=<name>`.
- **Pointer kinds** (declared in the registry): `manifest-chain-v2` (Chain
  Scroll), `utxo-inline-datum-bytes-v1` (Standard Scroll).

## $handle — `$name`  ·  finds someone's library

An [ADA Handle](https://adahandle.com) used as a front door. The reader
resolves the handle to its wallet, finds the newest **Registry Head** NFT in
that wallet, and opens the whole catalog it lists. This is the human-friendly
way to share a library — the live example is **`$beacn`**, BEACN's public shelf.

- **Looks like:** `$beacn`
- **Use it to:** open a person's or project's whole library by name.
- **Requires:** the handle and a Registry Head NFT in the **same wallet**
  (same stake key) — move either and the door stops resolving.
- Details: [`registry/spec/registry-nft-v2.md`](../registry/spec/registry-nft-v2.md).

## Policy ID — 56 hex  ·  finds a catalog, a byline, or a page-set

A **minting policy**. The reader tries three meanings, in order:

1. **A library** — if Registry Head NFTs exist under the policy, the reader
   opens the **latest catalog** (highest `Version`, scroll list from mint-tx
   metadata label `22027`). The BEACN library policy is
   `8d6d38b3967028a15fc0e401b53c73a75ac654affc3f817c750c8b80`.
2. **A publisher channel** — a policy used as a permanent, unforgeable
   byline. Only the key holder can ever publish under it; the reader opens the
   channel's **feed**. Example: BEACN Leaks
   (`5f569d01614c42003131c40b46d0b58c351a718907645c96d6da5415`).
3. **A legacy CIP-25 page-set** — the original scrolls (the Bible, both
   Constitutions, First Video, FIRST WORDS) are stored as **NFT pages**, all
   minted under one policy. The policy groups every page of that one file.

- **Looks like:** `38fbd56d7de6eb9df88599b5b102304df4c817aee53e4fb9c59cbed2`
- **Use it to:** open a library, follow a publisher, or rebuild a page-set.
- **Also works in:** the [BEACN Leaks player](https://beacnpool.github.io/ledger-scrolls/leaks.html)
  (`leaks.html#policy=<id>`), and channel deep links `…/#p=<id>`.

## Registry NFT — `policy.ASSET`  ·  pins one catalog version

A specific Registry Head, named exactly. Where a bare policy ID always opens
the *latest* catalog, `policy.ASSET` opens *that* version forever — mint-tx
metadata is immutable, so even a superseded (or burned) head keeps resolving.

- **Looks like:** `8d6d38b3967028a15fc0e401b53c73a75ac654affc3f817c750c8b80.LS_REGISTRY_V6`
- **Use it to:** pin a catalog snapshot, or cite exactly what a library said
  at a point in time. (Registry Head NFTs even carry this string in their
  `Ledger Scrolls Pointer` trait.)
- **Bonus:** any NFT whose metadata carries an `app` pointer (tx + ix) also
  opens here — the NFT becomes a paste-able address for an on-chain page.

## TX hash — 64 hex, no `#ix`  ·  finds a transaction

Just the transaction-hash half of a pointer, with the output index dropped.
In the reader it opens a registry list directly from a head's **mint tx**
(label `22027`). On a block explorer it identifies **one transaction** — a
mint, a manifest tx, or a page tx. It is **not a complete scroll pointer**:
add `#0` to make it one.

- **Looks like:** `955c6d2aa84b1d1d09a8228cb13616cfc4f6e08454d26671fff4eab163341500`
- **Use it to:** open a registry by its mint tx, or look up any transaction
  on an explorer (cexplorer.io, cardanoscan.io, pool.pm).
- **Note:** a Chain Scroll's *page* txs are separate hashes from its
  *manifest* pointer — the manifest lists them.

## Asset fingerprint — `asset1…`  ·  finds an NFT by its explorer name

The CIP-14 fingerprint explorers like pool.pm display for an asset. The
reader resolves it to `policy.ASSET` and continues from there — so a
fingerprint of a Registry Head opens the catalog, and a fingerprint of an
`app`-pointer NFT opens its page.

- **Looks like:** `asset1t0hms536krzq87cjken2d820ak98kamtmlm54d`
- **Use it to:** paste straight from an explorer without hunting for the
  policy id and asset name.

## SHA-256 — 64 hex  ·  proves, doesn't find

Not a locator — a **fingerprint of the bytes**. Every scroll commits to the
SHA-256 of its finished file. The reader recomputes it locally after
reconstruction and renders **only if it matches**. You verify *with* a hash;
you don't search *by* one (though you can grep a receipt to confirm you have
the right file).

- **Looks like:** `8bd5c906744197d94a7252f2607f671037b426eea18a05fa39330a85145b06e7`
- **Use it to:** confirm bytes are authentic and unaltered.
- **Careful:** it's the same shape as a tx hash. A tx hash finds; a SHA-256 proves.

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
| **$handle** | `$name` | a wallet's library (newest Registry Head) | reader bar |
| **Policy ID** | 56 hex | latest catalog, a channel feed, or a page-set | reader bar / leaks player |
| **Registry NFT** | `56hex.NAME` | one pinned catalog version | reader bar |
| **TX hash** | 64 hex | a registry mint tx / any transaction | reader bar / explorer |
| **Fingerprint** | `asset1…` | an NFT (→ catalog or app page) | reader bar |
| **SHA-256** | 64 hex | *nothing — it verifies* | local hash check |
| **Lock address** | `addr1w…` | the manifest vault (unindexed) | explorer / advanced |

**Rule of thumb:** to *read a specific scroll*, you want its **pointer**. To
*open someone's library*, you want their **$handle** (or policy ID). To
*follow a publisher*, you want their **policy ID**. Everything else is for
inspection or proof.

Full per-scroll values: **[SCROLL_INVENTORY.md](SCROLL_INVENTORY.md)**.
Machine-readable: **[card-catalog.csv](../examples/card-catalog/card-catalog.csv)**.
Registry resolution in normative detail:
**[registry/spec/registry-nft-v2.md](../registry/spec/registry-nft-v2.md)**.
