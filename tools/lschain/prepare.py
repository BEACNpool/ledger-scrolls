#!/usr/bin/env python3
"""LS-CHAIN v2 writer, step 1: prepare a file for minting (stdlib only).

Splits the (optionally gzipped) file into page metadata JSON files for
cardano-cli, plus a plan.json with every hash a verifier needs.

Packing: each page is a self-send carrying label-22025 metadata. Metadata
byte-strings are ≤64 B (ledger rule); max tx size is typically 16_384 B.
Default is to auto-fill each page near the limit (minus a safety margin) so
you pay fewer fixed per-tx fees and need fewer wallet signatures — without
changing the wire format or using any off-chain host.

Usage:
    python3 prepare.py <file> --content-type text/html [--codec auto|gzip|none] [--out workdir]
    python3 prepare.py <file> --content-type video/mp4 --segments-per-page auto

Then mint with mint.sh.

Spec: registry/spec/manifest-chain-v2.md
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import sys
import urllib.error
import urllib.request

METADATA_LABEL = "22025"
SEGMENT_BYTES = 64
# Legacy conservative default (still valid). Prefer --segments-per-page auto.
LEGACY_SEGMENTS_PER_PAGE = 190
DEFAULT_MAX_TX_SIZE = 16384
# Leave room for address/fee CBOR width, multi-input, and wallet re-wrapping.
TX_SAFETY_MARGIN = 400
FEE_A = 44          # lovelace per byte
FEE_B = 155381      # lovelace fixed


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def deterministic_gzip(data: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(data)
    return buf.getvalue()


def _cbor_uint_len(n: int) -> int:
    if n < 24:
        return 1
    if n < 256:
        return 2
    if n < 65536:
        return 3
    if n < 2**32:
        return 5
    return 9


def _cbor_bytes_len(n: int) -> int:
    return _cbor_uint_len(n) + n


def estimate_page_tx_bytes(segs: int, n_pages: int = 999, with_sha: bool = True) -> int:
    """Conservative CBOR size of a 1-in/1-out page tx with label-22025 aux data.

    Matches the model used by calculator.html so browser + CLI pack the same.
    """
    # Inner metadata map: i, n, p, [sha], v  (text keys)
    inner = _cbor_uint_len(4 + (1 if with_sha else 0))  # map header
    inner += 2 + _cbor_uint_len(1)                      # "i" + small int
    inner += 2 + _cbor_uint_len(max(n_pages, 1))        # "n"
    inner += 2 + _cbor_uint_len(segs)                   # "p" + array hdr
    inner += segs * _cbor_bytes_len(SEGMENT_BYTES)      # full 64 B segments
    if with_sha:
        inner += 4 + _cbor_bytes_len(32)                # "sha" + 32 B
    inner += 2 + _cbor_uint_len(2)                      # "v" = 2
    # outer {22025: inner}
    outer = _cbor_uint_len(1) + _cbor_uint_len(22025) + inner
    # tag 259 {0: metadata}
    aux = 3 + _cbor_uint_len(1) + _cbor_uint_len(0) + outer
    # body: inputs(1), outputs(1), fee, aux data hash — pad for variance
    body = 120
    wit = 110  # one vkey witness + margin
    # [body, wit, true, aux]
    return 1 + body + wit + 1 + aux


def max_segments_per_page(
    max_tx_size: int = DEFAULT_MAX_TX_SIZE,
    safety: int = TX_SAFETY_MARGIN,
    with_sha: bool = True,
) -> int:
    budget = max(1024, max_tx_size - safety)
    lo, hi, best = 1, 400, LEGACY_SEGMENTS_PER_PAGE
    while lo <= hi:
        mid = (lo + hi) // 2
        if estimate_page_tx_bytes(mid, with_sha=with_sha) <= budget:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def fetch_max_tx_size(network: str = "mainnet") -> int:
    """Best-effort live max_tx_size from Koios; falls back to 16384."""
    bases = {
        "mainnet": [
            "https://koios.beacn.workers.dev/api/v1",
            "https://api.koios.rest/api/v1",
        ],
        "preview": [
            "https://koios.beacn.workers.dev/preview/api/v1",
            "https://preview.koios.rest/api/v1",
        ],
    }.get(network, [])
    for base in bases:
        url = f"{base}/epoch_params?order=epoch_no.desc&limit=1"
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                rows = json.loads(r.read().decode())
            if rows and rows[0].get("max_tx_size"):
                return int(rows[0]["max_tx_size"])
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError, json.JSONDecodeError):
            continue
    return DEFAULT_MAX_TX_SIZE


def resolve_segments_per_page(spec: str, max_tx_size: int) -> int:
    spec = (spec or "auto").strip().lower()
    if spec in ("auto", "max", "0"):
        return max_segments_per_page(max_tx_size)
    n = int(spec)
    if n < 1:
        sys.exit("--segments-per-page must be ≥ 1 or 'auto'")
    est = estimate_page_tx_bytes(n)
    if est > max_tx_size - 64:
        sys.exit(
            f"--segments-per-page {n} ≈ {est} B tx, over max_tx_size {max_tx_size}; "
            f"try auto (max safe = {max_segments_per_page(max_tx_size)})"
        )
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description="Prepare a file for LS-CHAIN v2 minting")
    ap.add_argument("file", help="Source file")
    ap.add_argument("--content-type", required=True, help="MIME type, e.g. text/html")
    ap.add_argument("--codec", choices=["auto", "gzip", "none"], default="auto")
    ap.add_argument("--out", default="lschain-work", help="Output work directory")
    ap.add_argument(
        "--segments-per-page",
        default="auto",
        help="Segments (64B each) per page tx, or 'auto' to fill near max_tx_size "
        f"(legacy conservative default was {LEGACY_SEGMENTS_PER_PAGE})",
    )
    ap.add_argument(
        "--max-tx-size",
        type=int,
        default=0,
        help="Ledger max_tx_size (bytes). 0 = fetch live or use 16384",
    )
    ap.add_argument(
        "--network",
        choices=["mainnet", "preview"],
        default="mainnet",
        help="Network for live epoch_params when --max-tx-size is 0",
    )
    ap.add_argument(
        "--safety-margin",
        type=int,
        default=TX_SAFETY_MARGIN,
        help=f"Bytes kept free under max_tx_size (default {TX_SAFETY_MARGIN})",
    )
    args = ap.parse_args()

    max_tx = args.max_tx_size or fetch_max_tx_size(args.network)
    if (args.segments_per_page or "auto").strip().lower() in ("auto", "max", "0"):
        segments_per_page = max_segments_per_page(max_tx, safety=args.safety_margin)
    else:
        segments_per_page = resolve_segments_per_page(str(args.segments_per_page), max_tx)

    with open(args.file, "rb") as f:
        decoded = f.read()

    codec = args.codec
    if codec == "auto":
        gz = deterministic_gzip(decoded)
        codec = "gzip" if len(gz) < len(decoded) else "none"
    encoded = deterministic_gzip(decoded) if codec == "gzip" else decoded

    page_size = SEGMENT_BYTES * segments_per_page
    pages = [encoded[i : i + page_size] for i in range(0, len(encoded), page_size)]
    n = len(pages)
    if n == 0:
        sys.exit("empty file")

    os.makedirs(args.out, exist_ok=True)
    page_shas = []
    for idx, payload in enumerate(pages, start=1):
        segs = [payload[j : j + SEGMENT_BYTES] for j in range(0, len(payload), SEGMENT_BYTES)]
        page_shas.append(sha256_hex(payload))
        meta = {
            METADATA_LABEL: {
                "v": 2,
                "i": idx,
                "n": n,
                "sha": "0x" + page_shas[-1],
                "p": ["0x" + s.hex() for s in segs],
            }
        }
        with open(os.path.join(args.out, f"page-{idx:04d}.json"), "w") as f:
            json.dump(meta, f, separators=(",", ":"))

    tx_est = estimate_page_tx_bytes(segments_per_page, n_pages=n)
    fee_lovelace = FEE_A * tx_est + FEE_B
    fee_ada = fee_lovelace / 1e6
    total_fees = fee_ada * n
    plan = {
        "format": "ls-chain-v2-plan",
        "sourceFile": os.path.basename(args.file),
        "contentType": args.content_type,
        "codec": codec,
        "sizeDecoded": len(decoded),
        "sizeEncoded": len(encoded),
        "sha256Decoded": sha256_hex(decoded),
        "sha256Encoded": sha256_hex(encoded),
        "pages": n,
        "segmentBytes": SEGMENT_BYTES,
        "segmentsPerPage": segments_per_page,
        "pagePayloadBytes": page_size,
        "maxTxSize": max_tx,
        "safetyMargin": args.safety_margin,
        "estimatedPageTxBytes": tx_est,
        "estimatedFeePerPageAda": round(fee_ada, 6),
        "pageSha256": page_shas,
        "metadataLabel": int(METADATA_LABEL),
    }
    with open(os.path.join(args.out, "plan.json"), "w") as f:
        json.dump(plan, f, indent=2)
        f.write("\n")

    density = (page_size / tx_est) if tx_est else 0
    print(f"file: {args.file}")
    print(f"decoded: {len(decoded)} bytes  sha256: {plan['sha256Decoded']}")
    print(f"encoded ({codec}): {len(encoded)} bytes  sha256: {plan['sha256Encoded']}")
    print(
        f"packing: {segments_per_page} segs × {SEGMENT_BYTES} B = {page_size} B/page "
        f"(max_tx={max_tx}, safety={args.safety_margin}, est tx≈{tx_est} B, "
        f"payload density≈{100*density:.1f}%)"
    )
    print(
        f"pages: {n}  (~{fee_ada:.3f} ADA fee each, ~{total_fees:.2f} ADA pages total + seal)"
    )
    print(f"work dir: {args.out}/  (page-NNNN.json + plan.json)")


if __name__ == "__main__":
    main()
