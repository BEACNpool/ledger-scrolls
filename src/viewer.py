#!/usr/bin/env python3
"""
Ledger Scrolls Viewer (Deprecated)
=================================

Note: This script is deprecated in favor of decentralized streaming in main.py (scroll read <name>).
It now only supports local JSON for legacy use. For new features, use the unified reader mode.
"""

import argparse
import binascii
import gzip
import json
import os
import sys
from pathlib import Path

def load_pages_from_local(directory: str) -> list[dict]:
    path = Path(directory)
    if not path.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")

    pages = []
    for file_path in sorted(path.glob("*.json")):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "i" in data and "payload" in data:
                pages.append(data)
            else:
                print(f"Skipping invalid file: {file_path.name}", file=sys.stderr)

    return pages

def concatenate_payload(pages: list[dict]) -> bytes:
    gz_bytes = bytearray()
    for page in sorted(pages, key=lambda p: int(p["i"])):
        for segment in page.get("payload", []):
            if "bytes" in segment:
                try:
                    gz_bytes.extend(binascii.unhexlify(segment["bytes"]))
                except binascii.Error as e:
                    raise ValueError(f"Invalid hex in page {page['i']}: {e}")
    return bytes(gz_bytes)

def decompress_and_verify(
    gz_data: bytes,
    manifest: dict | None = None,
) -> bytes:
    if manifest and "sha_gz" in manifest:
        import hashlib
        actual = hashlib.sha256(gz_data).hexdigest()
        if actual != manifest["sha_gz"]:
            raise ValueError(f"GZIP hash mismatch! Expected: {manifest['sha_gz']} Got: {actual}")

    try:
        raw_data = gzip.decompress(gz_data)
    except OSError as e:
        raise ValueError(f"GZIP decompression failed: {e}")

    if manifest and "sha_raw" in manifest:
        import hashlib
        actual_raw = hashlib.sha256(raw_data).hexdigest()
        if actual_raw != manifest["sha_raw"]:
            raise ValueError(f"Raw hash mismatch! Expected: {manifest['sha_raw']} Got: {actual_raw}")

    return raw_data

def save_output(data: bytes, output_path: str) -> None:
    path = Path(output_path)
    if path.suffix.lower() in (".html", ".htm", ".txt", ".md", ".json"):
        mode = "w"
        encoding = "utf-8"
        content = data.decode("utf-8", errors="replace")
    else:
        mode = "wb"
        encoding = None
        content = data

    with open(path, mode, encoding=encoding) as f:
        f.write(content)

    print(f"Successfully reconstructed to: {path.absolute()}")

def main():
    parser = argparse.ArgumentParser(description="Ledger Scrolls Viewer (Deprecated - Use main.py for decentralized recon)")
    parser.add_argument(
        "--local-json",
        type=str,
        required=True,
        help="Directory containing *.json files",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        help="Path to manifest.json for hash verification",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reconstructed.html",
        help="Output file path (default: reconstructed.html)",
    )

    args = parser.parse_args()

    manifest = None
    if args.manifest:
        with open(args.manifest, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    try:
        print(f"Loading local pages from: {args.local_json}")
        pages = load_pages_from_local(args.local_json)

        if not pages:
            print("No valid pages found.", file=sys.stderr)
            return 1

        print(f"Found {len(pages)} pages.")

        gz_stream = concatenate_payload(pages)
        print(f"Concatenated gzip stream: {len(gz_stream):,} bytes")

        raw_content = decompress_and_verify(gz_stream, manifest)
        print(f"Decompressed content: {len(raw_content):,} bytes")

        save_output(raw_content, args.output)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
