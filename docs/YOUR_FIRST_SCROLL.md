# Your First Scroll — a 10-minute quickstart

So you want to put something on Cardano *forever*. This is the short path from
"I have a file" to "it's on-chain, verified, and anyone can read it." For the
deeper why-and-how, see [CREATING_SCROLLS.md](CREATING_SCROLLS.md).

A **scroll** is any file stored directly on the Cardano blockchain — no IPFS, no
server, no link that can rot. It is reconstructed byte-for-byte from chain data
and checked against a hash. If it verifies, it is exactly the file you minted.

---

## Before you spend a single ADA — three rules

1. **It is permanent and public.** No edit, no delete, no takedown. Never put in
   secrets, private keys, personal data, or anything you might regret.
2. **Hash before, verify after.** Record `sha256sum yourfile` before you mint,
   and reconstruct it from chain afterward — the hashes must match *before* you
   announce anything.
3. **Self-contained only.** No external images, fonts, CDNs, or IPFS links. A
   scroll is rendered offline; anything pointing outward is broken forever. Inline
   everything.

---

## Step 1 — Pick your format

```
  ≤ ~14 KB after gzip   ─▶  STANDARD SCROLL   (one locked UTxO; simplest, strongest)
  anything larger       ─▶  Chain Scroll       (bare metadata pages + manifest)
```

That's the whole decision. **Chain Scroll is the format for everything that
doesn't fit in a single datum** — documents, audio, video, datasets. It costs
~0.06 ADA/KB and locks nothing. (The older CIP-25 "pages" format still works and
is how legacy scrolls are read, but it costs ~6× more and locks ADA in an NFT per
page — don't reach for it for new scrolls.)

## Step 2 — Make the file as small as it can honestly be

On-chain storage is priced per byte, so shrinking the file *before* it touches
the chain is the entire optimization. Pick the right encoding, then declare it
honestly:

| Media | content_type | codec | Tips |
|---|---|---|---|
| Text / Markdown | `text/plain; charset=utf-8` | `gzip` if > ~8 KB, else `none` | UTF-8, `\n` line endings |
| Image (PNG/JPEG) | `image/png`, `image/jpeg` | `none` | optimize, **strip EXIF** |
| SVG | `image/svg+xml` | `gzip` | minify; no scripts/external refs |
| HTML document | `text/html` | `gzip` | self-contained, **no JavaScript** |
| Audio | `audio/ogg; codecs=opus` | `none` | **Opus** 24–32 kbps mono (speech), 64–96 kbps (music) |
| Video | `video/mp4` or `video/webm` | `none` | see below |
| Video **with sound** | `video/mp4` / `video/webm` | `none` | one file, both tracks — no separate audio scroll |

**`codec: gzip` only helps uncompressed data** (text, HTML, SVG, JSON). Media is
already compressed — gzipping an MP4/Opus/PNG buys nothing, so declare `none`.

**Video, specifically:**
- Maximum future-proof: H.264 + AAC in MP4 —
  `ffmpeg -i in.mov -c:v libx264 -crf 30 -preset veryslow -vf scale=-2:480 -c:a aac -b:a 64k -movflags +faststart out.mp4`
- Smallest bytes (~30–50% less, plays in modern browsers): AV1/VP9 + Opus in WebM —
  `ffmpeg -i in.mov -c:v libsvtav1 -crf 38 -preset 5 -vf scale=-2:480 -c:a libopus -b:a 64k out.webm`
- The real levers are **resolution, duration, and bitrate** — not the container.
  Avoid HEVC/H.265 (patent + spotty playback).

**Audio and video together is just one file** — a normal MP4 or WebM with both a
video and an audio track and a single `content_type`. The viewer plays picture
and sound from one `<video>` element. There is nothing extra to do.

## Step 3 — Rehearse on testnet (free)

The bytes are identical on testnet; the mistakes are free. Run the full pipeline
on the Preview testnet first — see [PREVIEW_TESTNET_POC.md](PREVIEW_TESTNET_POC.md).

## Step 4 — Mint it

**Standard Scroll (tiny files):**

```bash
cd scripts
./mint-standard-scroll.sh /path/to/yourfile /path/to/payment.skey /path/to/payment.addr
```

**Chain Scroll (everything larger):**

```bash
# Prepare: gzip-if-it-helps, hash, split into page payloads
python3 tools/lschain/prepare.py /path/to/yourfile --out build/

# Mint the page transactions, then build + lock the manifest datum
tools/lschain/mint.sh build/ /path/to/payment.skey /path/to/payment.addr
```

Keep every tx hash, the manifest txin (or lock address), the content hash, size,
and codec in a `receipts.json`. Your scroll is only as findable as its pointer.

## Step 5 — Verify from chain (do not skip)

```bash
cd koios-viewer
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Standard scroll
python3 -m lsview reconstruct-utxo  --txin <TXHASH>#0 --out check.bin
# Chain Scroll scroll
python3 -m lsview reconstruct-chain --txin <MANIFEST_TX>#0 --out check.bin

sha256sum check.bin    # must equal the hash you recorded in Step 1
```

Zero dependencies, no API key needed:
`python3 viewers/koios-cli/read_scroll.py --list`.

## Step 6 — Register and share

Make it discoverable — do all three:

1. **Add a registry entry** with your pointer and the (required) `sha256`:
   ```json
   { "name": "my-scroll",
     "pointer": { "kind": "manifest-chain-v2", "txHash": "<manifest tx>", "txIx": 0 },
     "contentType": "video/mp4",
     "sha256": "…",
     "description": "…" }
   ```
   Standard scrolls use `"kind": "utxo-inline-datum-bytes-v1"`. The registry is
   **forkable** — you can run your own head, or get listed in BEACN's public one.
2. **Open a PR** adding your entry (and your `receipts.json`) to this repo.
3. **Share it** on X with **#LedgerScrolls** and tag
   [@BEACNpool](https://x.com/BEACNpool).

---

## Stuck?

- **Worked examples with receipts:** [`examples/`](../examples/) — the
  `eternal-scroll-tutorial/` is itself an on-chain Chain Scroll scroll.
- **Full reference:** [CREATING_SCROLLS.md](CREATING_SCROLLS.md) ·
  [GETTING_STARTED.md](GETTING_STARTED.md) ·
  [Chain Scroll spec](../registry/spec/manifest-chain-v2.md)
- **Ask:** open a [GitHub Discussion](https://github.com/BEACNpool/ledger-scrolls/discussions).

*Mint deliberately. The library cannot burn — and it cannot forget.*
