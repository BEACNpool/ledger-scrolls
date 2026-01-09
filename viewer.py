#!/usr/bin/env python3
"""
Ledger Scrolls Viewer - Open Source Standard

A minimal, open-source viewer for reconstructing immutable Ledger Scrolls
from Cardano NFT metadata using the Ledger Scrolls standard.

This tool queries assets under a policy (via Blockfrost), finds the manifest + page NFTs,
stitches fragments together, optionally verifies checksums (when provided), and reconstructs
the full scroll (typically HTML) from compressed fragments.

MIT License - Contributions welcome!
"""

import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# Handy presets (you can add more)
DEFAULT_POLICIES = {
    "BTC Whitepaper (BTCWP)": "8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1",
    "On-chain Bible (legacy)": "2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0",
}

MAGIC_LINES = [
    "Collecting scroll fragments from the chain…",
    "Unsealing policy sigils…",
    "Indexing minted pages…",
    "Stitching fragments together…",
    "Verifying checksum seals…",
    "Inflating the eternal scroll…",
    "The Ledger Scroll is revealed.",
]


# ---------- small utilities ----------

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def hex_to_bytes(hex_str: str) -> bytes:
    return bytes.fromhex(hex_str)

def hex_to_utf8(hex_str: str) -> str:
    try:
        return hex_to_bytes(hex_str).decode("utf-8")
    except Exception:
        return ""

def safe_print(msg: str) -> None:
    print(msg, flush=True)

def extract_metadata(asset_json: dict) -> dict:
    """
    Blockfrost assets/{asset} typically returns:
      - onchain_metadata: dict (CIP-25 per-asset metadata)
      - onchain_metadata_standard: sometimes present
    We prefer onchain_metadata.
    """
    meta = asset_json.get("onchain_metadata")
    if isinstance(meta, dict) and meta:
        return meta

    std = asset_json.get("onchain_metadata_standard")
    if isinstance(std, dict) and std:
        # Some variants store metadata under "metadata"
        if isinstance(std.get("metadata"), dict) and std["metadata"]:
            return std["metadata"]
        # Or already looks like a metadata dict
        return std

    raise ValueError("No valid on-chain metadata found in asset response")

def payload_to_bytes(payload: Any) -> bytes:
    """
    Supports payload styles:
      1) Detailed schema list: [{"bytes":"ABCD..."}, {"bytes":"..."}]
      2) Simple list: ["ABCD...", "...."]
    """
    out = bytearray()
    if payload is None:
        return b""

    if not isinstance(payload, list):
        raise ValueError(f"payload is not a list (got {type(payload).__name__})")

    for item in payload:
        if isinstance(item, dict) and "bytes" in item and isinstance(item["bytes"], str):
            out.extend(hex_to_bytes(item["bytes"]))
        elif isinstance(item, str):
            out.extend(hex_to_bytes(item))
        else:
            raise ValueError(f"Unsupported payload element: {repr(item)[:120]}")
    return bytes(out)

def get_json(session: requests.Session, url: str, headers: dict, params: dict = None) -> Any:
    """
    Simple resilient GET with rate-limit backoff.
    """
    backoff = 2
    while True:
        r = session.get(url, headers=headers, params=params, timeout=60)
        if r.status_code == 429:
            safe_print(f"Rate limited — sleeping {backoff}s…")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
            continue
        r.raise_for_status()
        return r.json()


# ---------- chain scanning + selection ----------

def list_policy_assets(session: requests.Session, base_url: str, headers: dict, policy: str) -> List[str]:
    units: List[str] = []
    page = 1
    while True:
        batch = get_json(
            session,
            f"{base_url}/assets/policy/{policy}",
            headers,
            params={"count": 100, "page": page},
        )
        if not batch:
            break
        # each item has {"asset": "<policy><assetnamehex>"}
        units.extend([item["asset"] for item in batch if "asset" in item])
        page += 1
    return units

def is_manifest(meta: dict, asset_name: str) -> bool:
    # Strong signal: role=manifest OR pages list
    if isinstance(meta, dict):
        if meta.get("role") == "manifest":
            return True
        if isinstance(meta.get("pages"), list) and meta["pages"]:
            return True

    # Fallback: name contains MANIFEST
    return "MANIFEST" in (asset_name or "")

def is_page(meta: dict, asset_name: str) -> bool:
    if isinstance(meta, dict) and meta.get("role") == "page":
        return True
    # Common naming convention: *_P0001, BTCWP_P0001, BIBLE_P0123 etc.
    if re.match(r".*_P\d{4}$", asset_name or ""):
        return True
    # Fallback: if it has payload, it's probably a page
    if isinstance(meta, dict) and isinstance(meta.get("payload"), list) and meta["payload"]:
        return True
    return False

def choose_page_order(manifest_meta: dict, pages_by_name: Dict[str, dict]) -> List[str]:
    """
    Preferred ordering:
      - manifest.pages list (explicit)
    Fallback:
      - sort by meta.i (page index)
    """
    if isinstance(manifest_meta, dict) and isinstance(manifest_meta.get("pages"), list) and manifest_meta["pages"]:
        # Use explicit list; keep only ones we actually have
        return [p for p in manifest_meta["pages"] if p in pages_by_name]

    # fallback: sort by i
    sortable: List[Tuple[int, str]] = []
    for name, meta in pages_by_name.items():
        i = meta.get("i")
        try:
            idx = int(i)
        except Exception:
            idx = 0
        sortable.append((idx, name))
    sortable.sort(key=lambda x: x[0])
    return [name for _, name in sortable]


# ---------- checksum helpers (optional) ----------

def pick_hash(meta: dict, keys: List[str]) -> Optional[str]:
    for k in keys:
        v = meta.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
    return None

def verify_optional(label: str, data: bytes, expected_hex: Optional[str]) -> None:
    if not expected_hex:
        return
    got = sha256_hex(data)
    if got != expected_hex.lower():
        safe_print(f"⚠️  Warning: {label} checksum mismatch")
        safe_print(f"    expected: {expected_hex}")
        safe_print(f"    got     : {got}")
    else:
        safe_print(f"✅ {label} checksum OK")


# ---------- main ----------

def main() -> int:
    ap = argparse.ArgumentParser(description="Ledger Scrolls Viewer (Blockfrost, CIP-25/721)")
    ap.add_argument("--policy", default="", help="Policy ID (hex). If omitted, you’ll be prompted.")
    ap.add_argument("--blockfrost", default="", help="Blockfrost project_id (mainnet). Or set env BLOCKFROST_PROJECT_ID.")
    ap.add_argument("--out", default="", help="Output filename (default: ledger_scroll_<policy>.html or .bin)")
    ap.add_argument("--no-gunzip", action="store_true", help="Do not gunzip even if the bytes look like gzip")
    args = ap.parse_args()

    safe_print("\n" + "=" * 58)
    safe_print("                 Ledger Scrolls Viewer")
    safe_print("=" * 58 + "\n")
    safe_print("This open-source app reconstructs immutable scrolls stored as NFT metadata on Cardano.\n")

    # Policy selection
    policy = (args.policy or "").strip()
    if not policy:
        safe_print("Choose a default policy or paste your own:\n")
        names = list(DEFAULT_POLICIES.keys())
        for i, name in enumerate(names, 1):
            safe_print(f"  {i}) {name}: {DEFAULT_POLICIES[name]}")
        safe_print("  0) Enter a custom policy\n")
        choice = input("Select [1]: ").strip() or "1"
        if choice == "0":
            policy = input("Policy ID: ").strip()
        else:
            try:
                idx = int(choice) - 1
                policy = DEFAULT_POLICIES[names[idx]]
            except Exception:
                policy = DEFAULT_POLICIES[names[0]]

    if not re.fullmatch(r"[0-9a-fA-F]{56}", policy):
        safe_print("\nError: policy id should be 56 hex chars.")
        return 2

    # Blockfrost key
    api_key = (args.blockfrost or os.getenv("BLOCKFROST_PROJECT_ID", "")).strip()
    if not api_key:
        safe_print("\nEnter your Blockfrost API key (mainnet).")
        safe_print("Get one at: https://blockfrost.io\n")
        api_key = input("Blockfrost project_id: ").strip()
    if not api_key:
        safe_print("\nError: API key is required.")
        return 2

    script_dir = Path(__file__).resolve().parent
    out_path = Path(args.out) if args.out else (script_dir / f"ledger_scroll_{policy[:10]}.html")

    safe_print(f"\nPolicy: {policy}")
    safe_print(f"Output: {out_path}\n")
    safe_print("Reconstructing your eternal scroll now…\n")

    base_url = "https://cardano-mainnet.blockfrost.io/api/v0"
    headers = {"project_id": api_key, "user-agent": "ledger-scrolls-viewer/1.0"}
    session = requests.Session()

    try:
        safe_print(MAGIC_LINES[0])
        units = list_policy_assets(session, base_url, headers, policy)
        if not units:
            safe_print("No assets found under this policy.")
            return 1
        safe_print(f"{MAGIC_LINES[2]} Found {len(units)} assets.")

        safe_print(MAGIC_LINES[1])

        manifest_meta: Optional[dict] = None
        manifest_asset_name: Optional[str] = None

        pages_by_name: Dict[str, dict] = {}

        # Fetch each asset and classify
        for i, unit in enumerate(units, 1):
            safe_print(f"Fetching asset {i}/{len(units)}…",)
            asset_data = get_json(session, f"{base_url}/assets/{unit}", headers)
            asset_name_hex = asset_data.get("asset_name", "")
            asset_name = hex_to_utf8(asset_name_hex)
            if not asset_name:
                continue

            try:
                meta = extract_metadata(asset_data)
            except Exception:
                continue

            if manifest_meta is None and is_manifest(meta, asset_name):
                manifest_meta = meta
                manifest_asset_name = asset_name
                continue

            if is_page(meta, asset_name):
                pages_by_name[asset_name] = meta

            time.sleep(0.05)

        if not manifest_meta:
            safe_print("\nError: No manifest found.")
            safe_print("Hint: manifest metadata should include role='manifest' or a pages[] list.")
            return 1

        if not pages_by_name:
            safe_print("\nError: No pages found.")
            safe_print("Hint: pages typically have role='page' or names like *_P0001 and include payload[].")
            return 1

        # Determine page order
        page_names = choose_page_order(manifest_meta, pages_by_name)
        if not page_names:
            safe_print("\nError: Could not determine page order (manifest.pages empty and page indices missing).")
            return 1

        safe_print(f"\nManifest: {manifest_asset_name or '(unknown)'}")
        safe_print(f"{MAGIC_LINES[3]} Assembling {len(page_names)} pages…")

        # Build gz (or raw) bytes by concatenating page payloads
        assembled = bytearray()

        for pn in page_names:
            meta = pages_by_name[pn]
            payload = meta.get("payload", [])
            page_bytes = payload_to_bytes(payload)

            # Optional per-page sha
            page_sha = pick_hash(meta, ["sha", "sha256", "sha_gz", "sha_page"])
            if page_sha:
                verify_optional(f"page {pn}", page_bytes, page_sha)

            assembled.extend(page_bytes)

        blob = bytes(assembled)

        # Optional full gzip/raw sha from manifest (supports multiple key spellings)
        safe_print(MAGIC_LINES[4])
        expected_gz = pick_hash(manifest_meta, ["sha_gz", "sha_gzip", "sha_compressed", "sha"])
        if expected_gz:
            verify_optional("assembled (compressed)", blob, expected_gz)

        # Decide whether to gunzip
        looks_gzip = len(blob) >= 2 and blob[0] == 0x1F and blob[1] == 0x8B
        if looks_gzip and not args.no_gunzip:
            safe_print(MAGIC_LINES[5])
            out_bytes = gzip.decompress(blob)
        else:
            out_bytes = blob

        # Optional raw/uncompressed sha if available
        expected_raw = pick_hash(manifest_meta, ["sha_raw", "sha_html", "sha_uncompressed"])
        if expected_raw:
            verify_optional("assembled (uncompressed)", out_bytes, expected_raw)

        # Choose default extension if user didn’t specify --out
        if not args.out:
            # If it looks like HTML, use .html
            head = out_bytes[:512].lower()
            if b"<html" in head or b"<!doctype html" in head or b"<body" in head:
                out_path = out_path.with_suffix(".html")
            else:
                out_path = out_path.with_suffix(".bin")

        out_path.write_bytes(out_bytes)

        safe_print(f"\n{MAGIC_LINES[6]}")
        safe_print("Scroll successfully reconstructed!")
        safe_print(f"Location: {out_path}")
        if out_path.suffix.lower() == ".html":
            safe_print("\nOpen it in your browser to view the scroll.")
        else:
            safe_print("\nOutput is not obviously HTML; saved as .bin")

        return 0

    except KeyboardInterrupt:
        safe_print("\nCancelled.")
        return 130
    except Exception as e:
        safe_print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
