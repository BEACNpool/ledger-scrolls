#!/usr/bin/env python3
"""LS-CHAIN v2 writer, step 1: prepare a file for minting (stdlib only).

Splits the (optionally gzipped) file into page metadata JSON files for
cardano-cli, plus a plan.json with every hash a verifier needs.

Usage:
    python3 prepare.py <file> --content-type text/html [--codec auto|gzip|none] [--out workdir]

Then mint with mint.sh, which submits the page transactions, builds the
manifest datum from the recorded tx hashes (make_manifest.py), and locks it
at the always-fail script address.

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

METADATA_LABEL = "22025"
SEGMENT_BYTES = 64
SEGMENTS_PER_PAGE = 190  # 12,160-byte page payload; tx stays well under 16 KB


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def deterministic_gzip(data: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(data)
    return buf.getvalue()


def main() -> None:
    ap = argparse.ArgumentParser(description="Prepare a file for LS-CHAIN v2 minting")
    ap.add_argument("file", help="Source file")
    ap.add_argument("--content-type", required=True, help="MIME type, e.g. text/html")
    ap.add_argument("--codec", choices=["auto", "gzip", "none"], default="auto")
    ap.add_argument("--out", default="lschain-work", help="Output work directory")
    args = ap.parse_args()

    with open(args.file, "rb") as f:
        decoded = f.read()

    codec = args.codec
    if codec == "auto":
        gz = deterministic_gzip(decoded)
        codec = "gzip" if len(gz) < len(decoded) else "none"
    encoded = deterministic_gzip(decoded) if codec == "gzip" else decoded

    page_size = SEGMENT_BYTES * SEGMENTS_PER_PAGE
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
        "segmentsPerPage": SEGMENTS_PER_PAGE,
        "pageSha256": page_shas,
        "metadataLabel": int(METADATA_LABEL),
    }
    with open(os.path.join(args.out, "plan.json"), "w") as f:
        json.dump(plan, f, indent=2)
        f.write("\n")

    est_fee_per_page = 0.155381 + 0.000044 * 14000
    print(f"file: {args.file}")
    print(f"decoded: {len(decoded)} bytes  sha256: {plan['sha256Decoded']}")
    print(f"encoded ({codec}): {len(encoded)} bytes  sha256: {plan['sha256Encoded']}")
    print(f"pages: {n}  (~{est_fee_per_page:.2f} ADA fee each, estimate)")
    print(f"work dir: {args.out}/  (page-NNNN.json + plan.json)")


if __name__ == "__main__":
    main()
