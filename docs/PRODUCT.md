# Ledger Scrolls + Ledger Book — the BEACN ecosystem

Two independent products share a home, visual language, and open infrastructure.
Neither is a feature of the other. A Scroll preserves a finished original;
a Book accumulates entries over time. They connect when a Book needs a fixed
reference, and each is complete without that connection.

## First principles: two different jobs

| | Ledger Scrolls | Ledger Book |
|---|---|---|
| Job | Preserve and recover an exact file | Collect public entries over time |
| Core object | A fixed original with a stable pointer | An NFT book with a stable identity |
| Examples | Letter, document, artwork, release | Personal book, project log, event guestbook |
| Main actions | Read, check, download, preserve | Open, create, read, add an entry |
| What changes | A revision is a separately published work | New entries join the record; earlier entries stay |
| Standalone | No Book or NFT is required for locked file storage | No Scroll is required |
| Optional connection | Become a new Book's attached reference | Name a Scroll in the Book's mint metadata |

The first audience is Cardano creators and communities who already use wallets.
Scrolls serves someone who needs the original version after a website changes.
Book serves someone who wants a public record of contributions around a person,
project or occasion. A wedding guest should not have to learn cryptocurrency
merely to leave a message; wallet friction remains a real adoption cost.

## Brand architecture

**Ledger Scrolls** and **Ledger Book** are the product names. **BEACN** is the
shared maker and ecosystem signature, not a third product users must learn.
Keep both names in the main navigation and use the full name in page titles.

- Scrolls: cool blue, a scroll mark, fixed originals, archival reading.
- Book: warm amber, a book mark, accumulating entries, personal participation.
- Shared: dark surfaces, serif headings, clear controls, BEACN's existing badge,
  accessible focus states, the same saved shelf, and inspectable evidence.
- Use “guestbook” for that Book use case, not as a replacement product name.
- Say “Create a Book about this Scroll” for the optional bridge. Never imply that
  publishing a Scroll requires a Book or that a Book is incomplete without one.

Book starters set a suggested name only; they do not change the on-chain format,
permissions, entry visibility, or moderation rules. A project log is public and
accepts protocol-conforming entries; it is not a private or owner-only notebook.

## Independent and connected journeys

1. **Scrolls alone:** choose a file or compose text, review exact bytes and cost,
   publish through a wallet, then share a pointer and recover the original.
2. **Book alone:** name a book, review ownership and cost, mint through a wallet,
   share its link, and collect wallet-attributed public entries.
3. **Together:** after reading or publishing a Scroll, create a Book with its
   exact transaction/output pointer and SHA-256 in the mint metadata. Readers
   can move from the Book's entries to that original and back.

The optional attachment is immutable once the Book is minted. Existing Books
are not modified by selecting a new file in this app. An entry is not a
countersignature, endorsement, acceptance of terms, or identity proof.

## What the technology buys

Scrolls stores original bytes in Cardano data, rather than at a URL named by a
token. Book gives the record an identity that follows its NFT between wallets;
its entries and optional attachment do not depend on this website's database.
Formats, reconstruction tools, and content commitments are open, so another
implementation can read the same records.

These properties suit compact public records that matter. Large files need more
transactions, fees, and wallet approvals. Paid entries add friction and do not
make spam impossible or a statement meaningful. Shared infrastructure does not
erase the distinct purpose or cost of either product.

## The trust contract

| Evidence | What it establishes | What it does not establish |
|---|---|---|
| Locally computed SHA-256 | A fingerprint of the bytes just recovered | An independent commitment or chain inclusion |
| Fingerprint match | Recovered bytes match the specified commitment | That the author is known or the contents are true |
| Fingerprint in a shared link | Consistency with the link the reader received | Independent evidence that the fingerprint was published on-chain |
| Book attachment | The provider-returned mint metadata names that work and hash | Endorsement by every guest or authenticity of the human author |
| Reconstructed native policy hash | The script matches the requested policy ID | Independent evidence of current supply |
| Supply one + verified expired policy | Given correct chain data, minting cannot increase that supply | Uniqueness while the minting window remains open |
| Entry input address | The first input address in the returned transaction | A verified individual or sole signer |
| Keeper payment check | The transaction paid the keeper established at its block | A check when transfer ordering/history is unresolved |

The browser uses an indexer. It does not verify block headers, consensus, or a
transaction inclusion proof. A provider can omit or fabricate data that is
internally consistent. A fingerprint pinned through an independent channel helps
protect the file contents; it does not turn this reader into a light client.
Use independently operated providers or a node for stronger chain verification.

Content is public. Pointer obscurity is not privacy. Long-term availability depends
on Cardano, retained history, accessible data providers, and someone preserving a
working decoder. “Forever” is an intention, not an unconditional guarantee.

HTML works render in a sandbox with scripts, forms, and network requests blocked.
This may suppress remotely loaded images or fonts; the original downloadable bytes
are unchanged. A verified hash never grants code permission to execute.

## This implementation

- Shared BEACN navigation with distinct Ledger Scrolls and Ledger Book destinations.
- A library-first home, live registry titles, searchable media groups, progressive
  metadata loading, readable errors and retries, and a device-local saved shelf shared by both products, plus saved books on Book’s opening screen.
- A local text composer with draft restoration and download, using the same file
  preparation and wallet publishing engine as uploaded files.
- Portable work and book receipts; explicit canonical links for raw Book asset
  names; an attached work opens through the existing reader and checks the Book
  mint attachment before rendering.
- Backward-compatible optional Book `subject` metadata; existing Book URLs,
  identities, entries, Scroll formats and minted originals remain readable.
- Bounds on network CBOR, strict hex and manifest checks, gzip limits, exact decoded
  sizes, native-policy hashing, evidence-aware history states, fresh expiry reads,
  wallet-network checks, keeper refresh before signing, signed-size/fee guards,
  and token-preserving change.

Older bookmarks and publishing receipts in the existing “My Scrolls” vault remain
available on Publish. Shared saved-shelf bookmarks and composer drafts are local to
the browser origin. They do not synchronize between devices or different mirrors.
Download receipts/drafts before changing device or clearing site data.

## Boundaries and next decisions

The mainnet minting path is inherited; the new attachment extension has synthetic
wallet and byte-encoding coverage. No new mainnet mint or entry was performed as
part of this rebuild. Real wallet acceptance of the updated release remains a
separate validation step.

There is still one configured browser-capable Koios mirror. Direct reads and
provider outages are shown honestly. A second independently operated mirror and
a better long-history index are worthwhile infrastructure work, not guarantees
that this interface can manufacture. Reads reaching the current scan limits are
partial; ambiguous same-block keeper changes remain unresolved.

Do not add a token, trading marketplace, general social feed, or new storage format
before these products earn repeat usage. The first product test is concrete:
can creators independently preserve a Scroll or open a Book and bring someone
back without personally explaining the interface? Test the optional combined
journey separately. Track completed publishing, successful reads, actual entries,
and repeat use with consenting users. A redesign alone
cannot establish demand or a business model.

## Compatibility and operation

The public entry points remain `index.html`, `calculator.html`, and
`ledger-book.html`. Shared styles are generated from `scripts/workspace.css` by
`scripts/sync_nav.py`; the pages remain standalone at runtime. Existing minted
mirrors are guarded by `scripts/check_frozen_files.mjs`.

See [the attachment extension](../registry/spec/book-subject-v1.md) and
[the Book v2 protocol](../registry/spec/ledger-book-v2.md). This document describes
the unified implementation, superseding older marketing claims in historical
project material and already-minted works.
