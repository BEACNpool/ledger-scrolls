# Creating Your Own Ledger Scrolls — Best Practices by Media Type

A practical how-to for publishing immutable media on Cardano. This guide is
organized by *what you're publishing*; the format mechanics live in
[STANDARD_SCROLLS.md](STANDARD_SCROLLS.md) (single locked UTxO) and
[LEGACY_SCROLLS.md](LEGACY_SCROLLS.md) (CIP-25 pages), and the normative
rules in [PROTOCOL_V1_PROPOSAL.md](PROTOCOL_V1_PROPOSAL.md).

Every recommendation here is backed by a scroll that is live on mainnet
today — the worked examples are real, with receipts.

---

## Before You Mint: The Five Rules

1. **Permanent and public means exactly that.** No edit, no delete, no
   takedown. Never include secrets, private keys, personal data, or anything
   you may regret. Assume every future human and bot can read it.
2. **Rehearse on testnet first.** Run the full pipeline on the Preview
   testnet (see [PREVIEW_TESTNET_POC.md](PREVIEW_TESTNET_POC.md)) before
   spending mainnet ADA. The bytes are the same; the mistakes are free.
3. **Hash before, verify after.** Record the SHA-256 of your original file
   *before* minting. After minting, reconstruct the scroll from chain with a
   viewer and confirm the hash matches **before you announce anything**:

   ```bash
   sha256sum myfile.png                      # before
   cd koios-viewer
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python3 -m lsview reconstruct-utxo --txin TXHASH#0 --out check.png
   sha256sum check.png                       # must be identical
   ```

4. **Keep receipts.** Save tx hashes, the lock address or policy ID, the
   content hash, file size, codec, and the exact commands you ran. Put them
   in a `receipts.json` next to your source file. Your scroll is only as
   findable as its pointer.
5. **Self-contained files only.** A scroll is reconstructed as bytes and
   rendered offline. Anything that references the outside world (external
   images, fonts, CSS, CDNs, IPFS links) will be broken or untrustworthy
   forever. Inline everything.

---

## Choosing a Format

```
                 ┌─ ≤ ~9 KB raw, or ≤ ~14 KB after gzip ─▶  STANDARD SCROLL
 your file ──────┤                                           (one locked UTxO,
                 │                                            simplest, strongest)
                 └─ anything larger ───────────────────────▶  LEGACY SCROLL
                                                              (CIP-25 pages + manifest)
```

| | Standard (LS-LOCK) | Legacy (LS-PAGES) |
|---|---|---|
| Capacity | ~14 KB compressed | Practical/economic limit, not a single-UTxO limit (1 tx per page) |
| Permanence | Strongest: UTxO at always-fail script can never be spent | Metadata is immutable; policy must be time-locked; park page NFTs for trust and discoverability |
| Cost | One tx; min-UTxO ADA locked forever (~4–7.5 ADA observed for 1–3 KB datums) | One tx fee (~0.2 ADA) + one min-UTxO NFT per page |
| Wallet-visible | No | Yes (NFTs) |
| Reconstruction | 1 query | Policy scan + page concat |

When in doubt: **gzip your file and check the size.** If it fits in one
inline datum, use a Standard Scroll — it is the strongest guarantee this
protocol offers (immutability Class A with no custody conditions).

---

## Universal Preparation Steps

These apply to every media type below.

```bash
FILE=mywork.png

# 1. Record the original hash — this is your permanent commitment
sha256sum "$FILE"

# 2. If compressing, use DETERMINISTIC gzip (no timestamp, no filename)
#    so anyone can reproduce your encoded bytes from the source file
gzip -n -9 -c "$FILE" > "$FILE.gz"
sha256sum "$FILE.gz"        # record this too (the encoded hash)

# 3. Compare sizes — only ship the gzip if it actually helps
stat -c '%s' "$FILE" "$FILE.gz"
```

**Codec rule:** declare `codec: "gzip"` or `codec: "none"` explicitly in
your registry entry / viewer config. Don't rely on readers sniffing magic
bytes. And don't gzip formats that are already compressed (PNG, JPEG, MP4,
PDF mostly) — you add overhead for ~0 gain.

**Content type rule:** declare the real MIME type. Viewers render by
declared type: text as text, images/video natively, HTML in a locked-down
sandbox. Lying about the type just breaks rendering.

---

## Plain Text — messages, poetry, manifestos, licenses

*Live examples: The Architect's Scroll (3 KB), Genesis Scroll (1 KB).*

The ideal Standard Scroll. Text is small, gzips ~3:1, and renders everywhere
forever with zero format risk.

- **Format:** Standard Scroll
- **content_type:** `text/plain; charset=utf-8`
- **codec:** `none` under ~8 KB (keep it trivially readable); `gzip` above
- **Prep:** UTF-8 encode. Normalize line endings to `\n`. Strip trailing
  whitespace. Run `file` and `iconv -f utf-8 -t utf-8` to confirm clean UTF-8
  — a stray Latin-1 byte is immortalized otherwise.

```bash
./scripts/mint-standard-scroll.sh message.txt payment.skey payment.addr
```

Plain text is the *archival gold standard*. If your content can be plain
text (or Markdown), prefer it over HTML/PDF: it has no parser ambiguity, no
rendering dependencies, and the smallest cost.

## Markdown & Source Code

Same as plain text. Use `text/markdown` or `text/plain`. Tabs vs spaces,
trailing newline — whatever you mint is what history gets, so format first.

## Images — PNG, JPEG, SVG, GIF

*Live example: Hosky PNG — 1.3 KB PNG in a single inline datum, lock
address `addr1w8qvv…0svn`, sha256 `798e3296…642f`.*

- **content_type:** `image/png`, `image/jpeg`, `image/svg+xml`, `image/gif`
- **codec:** `none` for PNG/JPEG/GIF (already compressed); `gzip` for SVG
  (XML text, compresses ~4:1)
- **Format:** Standard if the *optimized* file fits; Pages otherwise

**Best practices:**

- **Optimize before minting — every byte is ADA.**
  - PNG: `oxipng -o max` or `pngcrush`; reduce to indexed color if the art
    allows (the Hosky PNG is a 100×100 4-bit-palette file — 1.3 KB).
  - JPEG: re-encode at quality 80–85, strip EXIF (`jpegtran -copy none` or
    `exiftool -all=`). **Check EXIF before minting** — GPS coordinates in a
    photo become permanent public record.
  - SVG: minify (`svgo`), then gzip. Ensure it contains **no scripts and no
    external references** — sandboxed viewers will strip/block them anyway.
- Pick dimensions for the purpose. An icon or pixel-art piece at 512×512 is
  a Standard Scroll; a full-resolution photograph is a Pages scroll —
  consider whether a 14 KB "archival thumbnail" Standard Scroll plus a
  full-size Pages scroll serves readers better than one huge artifact.

## Documents — HTML

*Live examples: the Bible (4.68 MB HTML → 1.28 MB gzip → 237 pages,
sha256 `b226867…c5dc5`), Bitcoin whitepaper (3 pages).*

HTML is the best choice for *formatted* long-form documents, with three hard
rules:

1. **Fully self-contained.** Inline all CSS in `<style>`, embed any images
   as `data:` URIs, no webfonts, no CDN links. Test by opening the file with
   networking disabled.
2. **No JavaScript.** Compliant viewers render scrolls in a fully sandboxed
   iframe — scripts will never run. A document that needs JS to display is
   broken by design here.
3. **Declare the charset** (`<meta charset="utf-8">`) and use
   `content_type: text/html`.

- **codec:** always `gzip` (HTML compresses 3–4:1)
- **Format:** almost always Pages (HTML documents are rarely under 14 KB);
  hash the original *and* the gzip, and put both in the manifest like the
  Bible does (`sha_html` + `sha_gz`)

## Documents — PDF

- **content_type:** `application/pdf`
- **codec:** usually `none` (PDF streams are already deflated; verify with
  the size check — some old PDFs do gzip well)
- **Format:** Pages, almost always

**Best practices:** linearize and shrink first
(`qpdf --linearize --object-streams=generate in.pdf out.pdf`, or Ghostscript
`-dPDFSETTINGS=/ebook`); strip metadata you don't want public
(`exiftool -all= file.pdf` — author names and tool paths hide in PDF
metadata). Prefer PDF/A if you're producing the file yourself — it's the
self-contained archival profile. If the source is text, seriously consider
minting plain text or HTML *instead of* (or alongside) the PDF: PDF is the
hardest of these formats to parse in 50 years.

## JSON & Datasets

- **content_type:** `application/json` (or `text/csv`)
- **codec:** `gzip`
- **Format:** by size, same thresholds

**Best practices:** canonicalize before hashing/minting (sorted keys, no
insignificant whitespace — see the canonical-JSON rule in the protocol
spec §4.1) so independent re-creations of the data hash identically.
Include a `schema` or self-describing header row; data without column
meaning is noise in 20 years.

## Audio — speech, music

- **content_type:** `audio/mpeg` (MP3) or `audio/ogg; codecs=opus`
- **codec:** `none` (audio codecs already compress)
- **Format:** Pages

**Best practices:** Opus at 24–32 kbps mono is excellent for speech (~1.4
MB per 10 minutes ≈ 75 pages); MP3 128 kbps for music compatibility. Cost
scales linearly with duration — a 3-minute song at 128 kbps is ~2.9 MB ≈
150 pages ≈ 150 transactions. Trim silence, normalize loudness, and ask
whether an excerpt serves the archival goal.

## Video

*Live example: BEACN Commercial — 175-page MP4 under policy
`38fbd56…bed2`, manifest `CM_MANIFEST`, sha256 `aebd63a…5814`.*

The most expensive medium. The live 175-page commercial proves it works —
and that it's a deliberate, sponsored undertaking, not a casual upload.

- **content_type:** `video/mp4`
- **codec:** `none`
- **Format:** Pages only

**Best practices:**

- H.264 in MP4 for maximum future decodability (`-movflags +faststart`),
  e.g. `ffmpeg -i in.mov -c:v libx264 -crf 28 -preset veryslow -vf scale=-2:480 -c:a aac -b:a 64k out.mp4`.
- Budget first: pages ≈ `ceil(bytes / 5408)`; at ~0.2 ADA fee + ~1.2 ADA
  min-UTxO per page NFT, a 5 MB clip ≈ 925 pages ≈ **1,300 ADA**. Downscale
  resolution, duration, and bitrate until the number is one you accept.
- Mint a Standard Scroll "poster" (title card image or text description +
  hash) pointing at the video's policy, so the work is discoverable even by
  readers who won't reconstruct 900 pages.

---

## Minting a Legacy (Pages) Scroll — the checklist

The full walkthrough is in [LEGACY_SCROLLS.md](LEGACY_SCROLLS.md); these are
the practices that distinguish a scroll that reconstructs cleanly in 2046
from one that needs forensics (all learned from scrolls live today):

1. **Segments: 32 bytes (64 hex chars) max** — the ledger caps metadata
   strings at 64 bytes. **Pages: ~169 segments (~5.4 KB)** keeps each mint
   tx safely under the 16 KB limit. Validate each tx with
   [`mint/validate_tx_size.sh`](../mint/validate_tx_size.sh) before signing.
2. **Page metadata MUST have:** integer `i` (page index, 1-based), `payload`
   (array of hex segment strings), `role: "page"`, and ideally `n` (total)
   and `sha` (page hash). Use **plain hex strings** for segments. `0x`
   prefixes and nested object segments both exist on chain and current
   conformance accepts them, but they caused compatibility bugs in older
   readers; don't add avoidable variance.
3. **Mint a manifest NFT** with `role: "manifest"`, an asset name ending in
   `_MANIFEST`, and (v1 form): `ct`, `codec`, an explicit `pages` array of
   asset names in order, `sha256` of the decoded file, and `sha256_enc` of
   the encoded stream. The Bible's manifest is the model — its declared
   `sha_html` is how this repo independently verified the reconstruction.
4. **Time-lock the policy** (`"type": "before"` slot in the policy script)
   and let it expire after minting — that's what makes the page set closed
   and the scroll's content fixed.
5. **Park the page NFTs in a dedicated address.** Moving pages doesn't
   destroy the metadata, and policy-scanning readers can still reconstruct
   them. But parking them avoids confusing naive/custodial workflows, keeps
   provenance easy to inspect, and preserves user trust. (Strongest option:
   lock page tokens at the always-fail script address too.)
6. Name assets `<NAME>_P0001 … <NAME>_P0237` + `<NAME>_MANIFEST` —
   zero-padded, so lexical order equals page order.

---

## After Minting: Publish the Pointer

A scroll nobody can find is not preserved. Do all three:

1. **Verify from chain** (rule 3 above) — web viewer or `lsview`.
2. **Write the registry entry** (canonical pointer kinds — see
   [registry/spec/format.md](../registry/spec/format.md)):

   ```json
   {
     "name": "my-scroll",
     "pointer": { "kind": "utxo-inline-datum-bytes-v1", "txHash": "…", "txIx": 0 },
     "contentType": "image/png",
     "sha256": "…",
     "description": "…"
   }
   ```

   For pages: `{ "kind": "cip25-pages-v1", "policyId": "…", "manifestAsset": "…_MANIFEST" }`.
   The `sha256` field is **required** — an entry without it can never show
   "verified" in any viewer.
3. **Open a PR** adding your entry to this repo (and/or publish your own
   registry head — the registry is forkable by design), including your
   receipts: mint tx hashes, policy ID or lock address, hashes, size, codec.

---

## Quick Reference

| Media | content_type | codec | Format | Key prep |
|---|---|---|---|---|
| Text / Markdown | `text/plain; charset=utf-8` / `text/markdown` | none (gzip if >8 KB) | Standard | UTF-8, `\n` endings |
| PNG / JPEG / GIF | `image/png` etc. | none | Standard if optimized ≤14 KB | optimize, **strip EXIF** |
| SVG | `image/svg+xml` | gzip | Standard | minify, no scripts/external refs |
| HTML doc | `text/html` | gzip | Pages (usually) | self-contained, **no JS**, charset meta |
| PDF | `application/pdf` | none | Pages | linearize/shrink, strip metadata |
| JSON / CSV | `application/json` / `text/csv` | gzip | by size | canonicalize before hashing |
| Audio | `audio/ogg; codecs=opus` / `audio/mpeg` | none | Pages | Opus 24–32 kbps speech |
| Video | `video/mp4` | none | Pages | H.264 CRF 26–30, budget pages first |

**Cost rules of thumb (mainnet):** Standard ≈ 0.2 ADA fee + 2–15 ADA locked
forever (scales with datum size). Pages ≈ (0.2 ADA fee + ~1.2 ADA min-UTxO)
× `ceil(encoded_bytes / 5408)` pages.

*Mint deliberately. The library cannot burn — and it cannot forget.*
