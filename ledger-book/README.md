# Ledger Book

An independent product in the BEACN ecosystem, alongside [Ledger Scrolls](../README.md).
Create a personal book, project log, or event guestbook. A Book NFT identifies
the ongoing record; public entries are collected across its ownership history.
A Scroll attachment is optional. Both products share navigation and a local saved shelf.

The optional [Book subject](../registry/spec/book-subject-v1.md) records an
original work pointer and SHA-256 in the NFT's mint metadata. It is not a browser
bookmark and does not disappear when this website changes. Entries remain guest
messages, not countersigned acceptance of that work.

Existing Books use [v1 compatibility](../registry/spec/ledger-book-v1.md) or
[v2 native policies](../registry/spec/ledger-book-v2.md). New Book minting uses v2:
a wallet signature and an expiry slot. Supply can still change before expiry;
readers check explicit supply, reconstruct the policy hash, and report whether
its minting window has closed.

An entry pays a minimum-output anchor to the keeper plus a network fee. A typed
name is self-declared; the transaction's input address is not verified human
identity. Readers only mark keeper payment when the history establishes the
keeper at that entry's block. Partial scans and ambiguous transfers stay visible.

Read for free without a wallet. Publishing and guest entries require a wallet
transaction. Content is public, and access depends on Cardano and retained history.
A paid entry does not make spam impossible or its contents true.

[Open the app](https://beacnpool.github.io/ledger-scrolls/ledger-book.html) ·
[Product and trust model](../docs/PRODUCT.md) ·
[Validation](../docs/UNIFIED_VALIDATION.md)

The legacy URL remains stable because existing NFTs refer to it. New canonical
links explicitly mark raw asset bytes with `policy.0xASSETHEX`; existing
`policy.Name` links retain their interpretation. No new mainnet acceptance mint
was performed for the subject extension during this rebuild.
