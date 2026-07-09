# Ledger Book v1 — an open protocol for on-chain guestbooks (`ledger-book-v1`)

Status: ACTIVE (first book: `$beacn`, July 2026) · License: MIT

Every Cardano wallet is a guestbook. A **book** is identified by an address (or an
ADA Handle that resolves to one). A **signature** is a transaction that pays a
minimal anchor output to the book's address and carries the entry in transaction
metadata. No server, no database, no registry: the book *is* the chain, and any
conforming reader can display any book.

## Signature transaction

A conforming signature transaction:

1. **Pays an anchor output to the book address.** RECOMMENDED amount: the
   protocol min-UTxO for that output (~1 ADA at 2026 parameters) — the cheapest
   a permanent signature can be. Larger amounts are valid (a bigger tip to the
   book's owner).
2. **Carries metadata under label `22031`:**

```json
{ "22031": {
    "b": "ledger-book-v1",
    "n": "<name — string, ≤64 bytes UTF-8, required>",
    "m": [ "<message line ≤64 bytes>", "…" ]
} }
```

- `b` — protocol id, MUST be `"ledger-book-v1"`.
- `n` — the signer's display name. Free-form; ≤64 bytes (ledger string limit). Required.
- `m` — OPTIONAL message as an array of strings, each ≤64 bytes (UTF-8 split on
  codepoint boundaries). Readers join the array with no separator.
  RECOMMENDED total ≤192 bytes; readers MUST tolerate more.
- Unknown extra fields MUST be ignored by readers (forward compatibility).

## Reading a book

1. Resolve the book reference:
   - `addr1…` — use as-is.
   - `$handle` — ADA Handle policy
     `f0ff48bbb7bbe9d59a40f1ce90e9e9d0ff5002ec48f232b49ca0fb9a`; look up asset
     `000de140 + hex(name)` (CIP-68) first, then `hex(name)` (legacy); the book
     address is the address currently holding the handle NFT.
2. Enumerate transactions involving the address (e.g. Koios `POST /address_txs`).
3. Fetch their metadata (e.g. Koios `POST /tx_metadata`, batched); keep entries
   whose label `22031` parses per the schema above.
4. Render newest-first (or oldest-first — reader's choice). Escape ALL user
   content; render text only, never markup or clickable links from entries.

## Attribution & trust

- **Authorship is cryptographic**: the signature tx is signed by the author's own
  wallet keys. Readers SHOULD display the first input's payment address (or its
  $handle/stake key) alongside the free-form name — names can claim anything;
  the signing address cannot.
- **Anything can be written.** There is no moderation and no deletion — that is
  the point. Readers MUST HTML-escape entries and SHOULD state clearly that
  content is user-generated and permanent.
- **Moving a handle moves the book.** A `$handle` book is the address currently
  holding the handle; signatures anchor to the address they paid. If the handle
  moves wallets, the old signatures remain with the old address (viewable by
  `addr1…`), and new signatures follow the handle. Address-referenced books are
  immune to this.

## Book NFTs — mintable books

A book MAY be represented by an NFT so it can be owned, displayed, and moved:

- Mint 1 asset under a **sig-type native script policy** keyed to the minter's
  payment key hash (`policyId = blake2b224(0x00 ‖ script_cbor)`, where
  `script_cbor = [0, keyhash]`).
- CIP-25 (label 721) metadata SHOULD include `Type: "Ledger Book"` and
  `protocol: "ledger-book-v1"`, plus a human name and a reader deep link in
  `description`.
- The book's address is **wherever the NFT currently lives**: readers resolve
  `policy.AssetName` via the asset's holding address (same mechanics as $handle
  books). Moving the NFT moves the book; old signatures stay with the old
  address, new ones follow the NFT.
- **$handle front door**: when resolving a `$handle`, readers SHOULD check the
  holder's stake account for a Ledger Book NFT (CIP-25 `Type: "Ledger Book"`);
  if present, open THAT NFT's book (canonical, follows the NFT) and fall back
  to the handle wallet's address book otherwise. Multiple book NFTs: pick
  deterministically (lowest policy+name) or offer a choice.
- Reference minter: `ledger-book.html` → "Mint a Ledger Book" (in-browser,
  CIP-30; the only cost is the network fee — the min-UTxO travels with the NFT
  into the minter's own wallet).

## Hosting a book

There is nothing to deploy. Share a link to any conforming reader with your
reference, e.g.:

```
https://beacnpool.github.io/ledger-scrolls/ledger-book.html?book=$yourhandle
https://beacnpool.github.io/ledger-scrolls/ledger-book.html?book=addr1…
```

Anchors are paid to *you*. The reference reader (`ledger-book.html`, one
self-contained file, MIT) can be copied, restyled, embedded, or mirrored
anywhere — every copy reads the same books, because the books live on-chain.

## Relationship to Ledger Chess claims (label 22030)

Ledger Chess victory claims use the sibling label `22030` with a different,
replay-verifiable schema. The two protocols share tooling but never mix:
readers select strictly by label + protocol id.
