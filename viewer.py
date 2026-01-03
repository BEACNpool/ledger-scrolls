#!/usr/bin/env python3
"""
Ledger Scrolls Viewer - Open Source Standard

A minimal, open-source viewer for reconstructing immutable Ledger Scrolls
from Cardano NFT metadata using the Ledger Scrolls standard.

This tool fetches assets under a policy, reads the manifest and page NFTs,
verifies checksums, and reconstructs the full ledger into an HTML file.

As an open-source project, it's designed for community contributions — fork it on GitHub to add features like GUIs, custom networks, or minting tools. Together, we can evolve this into a timeless, decentralized standard for preserving any knowledge on the blockchain.

MIT License - Contributions welcome!
"""

import gzip
import hashlib
import json
import os
import time
import re
import requests
from pathlib import Path

# Default known proof-of-concept policy
DEFAULT_POLICY = "2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0"

MAGIC_LINES = [
    "Collecting scroll fragments from the chain…",
    "Unsealing policy sigils…",
    "Indexing minted pages…",
    "Stitching fragments together…",
    "Verifying checksum seals…",
    "Inflating the eternal scroll…",
    "The Ledger Scroll is revealed."
]

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def hex_to_bytes(hex_str: str) -> bytes:
    return bytes.fromhex(hex_str)

def hex_to_utf8(hex_str: str) -> str:
    try:
        return hex_to_bytes(hex_str).decode("utf-8")
    except:
        return ""

def extract_metadata(asset_json: dict) -> dict:
    for key in ["onchain_metadata", "onchain_metadata_standard"]:
        meta = asset_json.get(key)
        if isinstance(meta, dict) and meta:
            return meta
    std = asset_json.get("onchain_metadata_standard")
    if isinstance(std, dict) and std.get("metadata"):
        return std["metadata"]
    raise ValueError("No valid on-chain metadata found")

def payload_to_bytes(payload) -> bytes:
    out = bytearray()
    for item in payload:
        if isinstance(item, dict) and "bytes" in item:
            out.extend(hex_to_bytes(item["bytes"]))
    return bytes(out)

def get_json(session: requests.Session, url: str, headers: dict, params: dict = None):
    if params:
        query = requests.compat.urlencode(params)
        url += ('?' + query) if query else ''
    while True:
        r = session.get(url, headers=headers, timeout=60)
        if r.status_code == 429:
            print("Rate limited — waiting 10 seconds...")
            time.sleep(10)
            continue
        r.raise_for_status()
        return r.json()

def main():
    print("\n" + "=" * 50)
    print("     Welcome to Ledger Scrolls Viewer")
    print("=" * 50 + "\n")
    print("This open-source application views immutable data scrolls stored on the Cardano blockchain.")
    print("It queries NFT metadata under a policy ID, verifies structure via the manifest,")
    print("and reconstructs the full, timeless scroll from compressed fragments.\n")
    print("As a community-driven open-source standard, this tool is free for anyone to use, modify, or extend.")
    print("Fork it on GitHub: https://github.com/BEACNpool/ledger-scrolls\n")
    print("Let's begin...\n")

    print("First, enter the Policy ID of the Ledger Scrolls collection.")
    print("(This unique ID groups all NFTs containing the scroll data fragments.)")
    policy = input(f"Policy ID [{DEFAULT_POLICY}]: ").strip()
    if not policy:
        policy = DEFAULT_POLICY

    print("\nNext, enter your Blockfrost API key to query blockchain data.")
    print("Blockfrost is an independent, excellent service we leverage for fast queries.")
    print("They are not affiliated with Ledger Scrolls, but their generous free tier (with Google OAuth signup)")
    print("makes this open-source tool accessible to everyone.")
    print("Get your free key at: https://blockfrost.io")
    api_key = input("Blockfrost API Key (mainnet): ").strip()
    if not api_key:
        print("\nError: API key is required.")
        return

    script_dir = Path(__file__).resolve().parent
    output_file = script_dir / "ledger_scroll.html"
    print(f"\nThe reconstructed scroll will be saved next to this script:")
    print(f"{output_file}\n")
    print("Reconstructing your eternal scroll now...\n")

    base_url = "https://cardano-mainnet.blockfrost.io/api/v0"
    headers = {"project_id": api_key}
    session = requests.Session()

    try:
        print(MAGIC_LINES[0])
        units = []
        page = 1
        while True:
            batch = get_json(session, f"{base_url}/assets/policy/{policy}", headers, {"count": 100, "page": page})
            if not batch:
                break
            units.extend([item["asset"] for item in batch])
            page += 1

        if not units:
            print("No assets found under this policy.")
            return

        print(f"{MAGIC_LINES[2]} Found {len(units)} assets.")

        print(MAGIC_LINES[1])
        pages = []
        manifest = None

        for i, unit in enumerate(units, 1):
            print(f"Fetching asset {i}/{len(units)}...", end="\r")
            asset_data = get_json(session, f"{base_url}/assets/{unit}", headers)
            asset_name_hex = asset_data.get("asset_name", "")
            asset_name = hex_to_utf8(asset_name_hex)

            if not asset_name:
                continue

            meta = extract_metadata(asset_data)

            if "MANIFEST" in asset_name:
                manifest = meta
            elif re.match(r".*_P\d{4}$", asset_name):  # Matches any prefix ending _P#### (e.g., BIBLE_P0001)
                index = int(meta.get("i", 0))
                pages.append((index, meta.get("payload", [])))

            time.sleep(0.1)

        if not manifest:
            print("\nError: No manifest asset found (look for one containing 'MANIFEST').")
            return

        pages.sort(key=lambda x: x[0])

        print(f"\n{MAGIC_LINES[3]} Assembling {len(pages)} pages...")

        gz_data = bytearray()
        for _, payload in pages:
            gz_data.extend(payload_to_bytes(payload))

        expected_sha_gz = manifest.get("sha_gz", "").lower()
        if expected_sha_gz and sha256_hex(gz_data) != expected_sha_gz:
            print("Warning: GZ checksum mismatch — possible incomplete data.")

        print(MAGIC_LINES[5])

        html_bytes = gzip.decompress(gz_data)

        expected_sha_html = manifest.get("sha_html", "").lower()
        if expected_sha_html and sha256_hex(html_bytes) != expected_sha_html:
            print("Warning: HTML checksum mismatch.")

        output_file.write_bytes(html_bytes)

        print(f"\n{MAGIC_LINES[6]}")
        print(f"Scroll successfully reconstructed!")
        print(f"Location: {output_file}")
        print("\nDouble-click 'ledger_scroll.html' to view it in your browser.")
        print("\nThank you for using this open-source tool. Share your improvements on GitHub!")

        input("\nPress Enter to close this window...")

    except Exception as e:
        print(f"\nError: {e}")
        input("\nPress Enter to close...")

if __name__ == "__main__":
    main()