#!/usr/bin/env python3
"""
Ledger Scrolls Viewer
=====================

Reconstructs immutable data scrolls stored as CIP-25 NFTs on Cardano.

Supports:
- Blockfrost API (mainnet/preview/preprod)
- Local JSON files (page_*.json format)
- Optional manifest verification (SHA256 of gzip & raw data)
- Manifestless mode (just sort pages by index and concatenate)

Usage examples:
    python src/viewer.py --blockfrost --policy $POLICY_ID --prefix MYSCROLL_P --output reconstructed.html
    python src/viewer.py --local-json ./pages/ --manifest manifest.json --output bible.html
"""

import argparse
import binascii
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None


def fetch_pages_from_blockfrost(
    policy_id: str,
    name_prefix: str,
    network: str = "mainnet",
    project_id: Optional[str] = None,
) -> List[Dict]:
    """Fetch all assets under a policy and extract page metadata via Blockfrost."""
    if not requests:
        raise ImportError("The 'requests' library is required for Blockfrost queries. Install with: pip install requests")

    api_key = project_id or os.getenv("BLOCKFROST_PROJECT_ID")
    if not api_key:
        raise ValueError(
            "Blockfrost project ID not found. Set --blockfrost-key or BLOCKFROST_PROJECT_ID environment variable."
        )

    base_url = f"https://cardano-{network}.blockfrost.io/api/v0"
    headers = {"project_id": api_key}

    pages = []
    page = 1

    while True:
        url = f"{base_url}/assets/policy/{policy_id}?page={page}&count=100"
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        assets = response.json()
        if not assets:
            break

        for asset in assets:
            asset_name = bytes.fromhex(asset["asset"]).decode("utf-8", errors="ignore")
            if not asset_name.startswith(name_prefix):
                continue

            # Get on-chain metadata (CIP-25)
            meta_url = f"{base_url}/assets/{asset['unit']}/metadata"
            meta_resp = requests.get(meta_url, headers=headers)
            meta_resp.raise_for_status()
            metadata = meta_resp.json()

            if "onchain_metadata" not in metadata:
                print(f"Warning: No onchain_metadata for {asset_name}", file=sys.stderr)
                continue

            page_data = metadata["onchain_metadata"]
            # Basic validation
            if "i" not in page_data or "payload" not in page_data:
                print(f"Warning: Invalid page format for {asset_name}", file=sys.stderr)
                continue

            pages.append(page_data)

        page += 1

    return pages


def load_pages_from_local(directory: str) -> List[Dict]:
    """Load page JSON files from a local directory (page_0001.json, etc.)."""
    path = Path(directory)
    if not path.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")

    pages = []
    for file_path in sorted(path.glob("page_*.json")):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "i" in data and "payload" in data:
                pages.append(data)
            else:
                print(f"Skipping invalid file: {file_path.name}", file=sys.stderr)

    return pages


def concatenate_payload(pages: List[Dict]) -> bytes:
    """Combine all payload hex segments into a single gzip byte stream."""
    gz_bytes = bytearray()

    for page in sorted(pages, key=lambda p: int(p["i"])):
        for segment in page.get("payload", []):
            if "bytes" not in segment:
                continue
            try:
                gz_bytes.extend(binascii.unhexlify(segment["bytes"]))
            except binascii.Error as e:
                raise ValueError(f"Invalid hex in page {page['i']}: {e}")

    return bytes(gz_bytes)


def decompress_and_verify(
    gz_data: bytes,
    manifest: Optional[Dict] = None,
) -> bytes:
    """Decompress gzip data and optionally verify hashes against manifest."""
    if manifest:
        if "sha_gz" in manifest:
            actual = hashlib.sha256(gz_data).hexdigest()
            if actual != manifest["sha_gz"]:
                raise ValueError(
                    f"GZIP hash mismatch!\nExpected: {manifest['sha_gz']}\nGot:      {actual}"
                )

    try:
        raw_data = gzip.decompress(gz_data)
    except OSError as e:
        raise ValueError(f"GZIP decompression failed: {e}")

    if manifest and "sha_raw" in manifest:
        actual_raw = hashlib.sha256(raw_data).hexdigest()
        if actual_raw != manifest["sha_raw"]:
            raise ValueError(
                f"Raw content hash mismatch!\nExpected: {manifest['sha_raw']}\nGot:      {actual_raw}"
            )

    return raw_data


def save_output(data: bytes, output_path: str) -> None:
    """Save reconstructed bytes to file, guessing extension if needed."""
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
    parser = argparse.ArgumentParser(description="Ledger Scrolls - Reconstruct immutable data from Cardano NFTs")
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--blockfrost",
        action="store_true",
        help="Fetch pages using Blockfrost API",
    )
    group.add_argument(
        "--local-json",
        type=str,
        help="Directory containing page_*.json files",
    )

    parser.add_argument(
        "--policy",
        type=str,
        help="Policy ID of the scroll (required with --blockfrost)",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="PAGE_",
        help="Asset name prefix for page NFTs (default: PAGE_)",
    )
    parser.add_argument(
        "--network",
        type=str,
        default="mainnet",
        choices=["mainnet", "preprod", "preview"],
        help="Cardano network for Blockfrost (default: mainnet)",
    )
    parser.add_argument(
        "--blockfrost-key",
        type=str,
        help="Blockfrost project ID (overrides env var)",
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

    # Load manifest if provided
    manifest = None
    if args.manifest:
        manifest_path = Path(args.manifest)
        if not manifest_path.is_file():
            parser.error(f"Manifest file not found: {args.manifest}")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    # Fetch/load pages
    try:
        if args.blockfrost:
            if not args.policy:
                parser.error("--policy is required when using --blockfrost")
            print(f"Querying Blockfrost ({args.network}) for policy {args.policy}...")
            pages = fetch_pages_from_blockfrost(
                args.policy,
                args.prefix,
                args.network,
                args.blockfrost_key,
            )
        else:
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
