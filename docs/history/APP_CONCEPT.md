# The Library — Main App Concept (v3, from first principles)

2026-06-11. This document defines what the Ledger Scrolls main app *is*
before a single pixel is styled. The app at the site root implements this.

## First principles

Start from what Ledger Scrolls believes, and let the app fall out of it:

1. **Verify, don't trust.** Bytes render only after a local SHA-256 check
   against an on-chain commitment. Verification status is always visible,
   never implied.
2. **The site hosts nothing.** The page is a lens, not a source. The
   reader's own browser queries the chain, reconstructs, and verifies.
   Every request made on the reader's behalf is shown as it happens.
3. **The viewer must be as durable as the scrolls.** A reader for
   permanent documents that depends on 251 npm packages, a build pipeline,
   and a bundle hash is a contradiction. The app is therefore **one
   self-contained HTML file**: no libraries, no CDN, no build step —
   native `fetch`, WebCrypto, `DecompressionStream`, and an inline CBOR
   decoder. View-source is the documentation. Save it to a USB stick and
   it still works. One day it can be minted as a scroll itself.
4. **Open protocol, not a platform.** The library is not BEACN's list. The
   catalog loads from the **on-chain registry head**; any pointer — a
   txin, a policy ID, a channel — can be opened directly. BEACN's content
   is the demonstration, not the boundary.
5. **Reader sovereignty.** The reader chooses the data source (Koios
   direct by default, fallback endpoints visible, custom endpoint
   supported) and sees the trust profile of whatever they chose. Hidden
   trust assumptions are bugs.
6. **A library that cannot burn.** The experience is an archive's reading
   room, not a dapp demo: catalog, document, provenance, receipt.

## What the app does (three verbs)

**READ.** The catalog loads from the live on-chain registry
(head `a9c56fb3…bad9#0`, reader-overridable), merged with a built-in
bootstrap shelf of known scrolls. Each entry: title, storage form
(LS-LOCK / LS-CHAIN / LS-PAGES), content type, verification commitment.
Selecting a scroll runs the resolution pipeline in the open: step tracker
(POINT → FETCH → REBUILD → VERIFY → RENDER), live trust log of every
request, then — only if verified — a sandboxed render with the hash
receipt and a download of the original bytes.

**POINT.** A universal resolver bar. Paste anything:
- `txHash#ix` → inline-datum scroll (LS-LOCK) or LS-CHAIN manifest —
  detected automatically from the datum;
- a 56-hex policy ID → publisher channel (issues listed from chain) or
  legacy CIP-25 pages — detected automatically;
- a registry head txin → browse that registry instead (trust anchor
  switching).
Deep links (`#s=<name>`, `#p=<pointer>`) make every document and pointer
shareable as a URL.

**UNDERSTAND.** The trust model is part of the interface: a permanent
source line (endpoint in use, proof model, verification scope), an
explainer of what was and wasn't trusted, and direct paths to write your
own (tools, tutorial scroll, publisher channels, the spec).

## What the app refuses to do

- Render unverified bytes as if they were verified (mismatch = no render).
- Execute scroll content (HTML renders only in a fully sandboxed iframe).
- Require BEACN infrastructure (worker endpoints are visible fallbacks,
  never the default).
- Hide a failure (every error surfaces in the trust log with the endpoint
  that produced it).

## Style (decided after the above)

The reading room of an archive that has survived every fire: dark
charcoal walls, parchment documents, brass-plaque typography. Serif
display for titles, monospace for receipts and hashes. No animation
framework — the only motion is state changing. Fast on a phone, legible
in a terminal-rendered screenshot, printable.

## Supersession

This replaces the React/Vite app (removed from the tree; preserved in git history)
and the dist-to-root deploy ritual. The root `index.html` is now source,
not build output. The standalone viewers (`bible.html`,
`constitution.html`, `first-video.html`, `leaks.html`) are unaffected.
