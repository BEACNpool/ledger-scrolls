# Ledger Scrolls: a work and its people

Ledger Scrolls preserves public works and gives people a place to leave entries
beside them. Scrolls are the fixed original; Ledger Book is the guestbook around
that original. They are two parts of one publishing workflow.

## Start with the job

Someone publishes a work that matters. Later, a reader needs the exact version,
even if its original website has changed. Other people may want to mark the
occasion, leave a response, or support its keeper. The work should stay fixed;
responses should accumulate without rewriting it.

The first audience is Cardano creators and communities publishing releases,
statements, letters, or project milestones. They already understand wallets.
Personal guestbooks remain supported, but a wedding guest should not need to
learn cryptocurrency merely to leave a message. That friction is real.

The primary journey is:

1. **Publish a work:** choose a file or compose text locally, inspect its storage
   plan and estimated cost, then approve the transaction(s) in a wallet.
2. **Read the original:** reconstruct its bytes, inspect the fingerprint and its
   source, download the file and a portable receipt.
3. **Attach a guestbook:** create a Book NFT whose mint metadata contains the
   work's exact transaction/output pointer and SHA-256 fingerprint.
4. **Share the book:** readers can open the referenced original and inspect the
   public entries alongside it. Saving a work or book bookmarks it on this device.

No NFT is required just to preserve a file. A standalone guestbook is still valid.
The guestbook attachment is optional and immutable once minted. An entry in that
book is not a countersignature, endorsement, acceptance of terms, or identity proof.

## What the technology buys

The original bytes are stored in Cardano data, rather than at a URL named by a
token. The formats, reconstruction tools, and content commitments are open.
Readers can recover files through another implementation or provider. The book's
identity is independent of its current wallet, and its attachment does not depend
on browser storage or this website.

These properties are valuable for compact, public, important works. They do not
make blockchains efficient bulk storage. Large files require many transactions,
fees, and wallet approvals. A paid guest entry also takes more effort than a web
comment. Price does not make spam impossible or a statement meaningful.

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

- One navigation: Library, Publish, Guestbooks, How it works.
- A library-first home, live registry titles, searchable media groups, progressive
  metadata loading, readable errors and retries, and a device-local saved shelf.
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
available on Publish. New saved-shelf bookmarks and composer drafts are local to
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
before this workflow earns repeat usage. The first product test is concrete:
can several creators publish a real work, share its book, and bring a reader back
without personally explaining the interface? Track completed publishing, successful
reads, actual entries, and repeat use with consenting users. A redesign alone
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
