#!/usr/bin/env python3
"""
Ledger Scrolls Viewer - Open Source Standard

Reconstruct immutable "Ledger Scrolls" stored as Cardano NFT metadata (CIP-25 / 721),
queried via Blockfrost.

Works with payload styles:
  - payload: ["0xABCD...", "0x....", ...]
  - payload: ["ABCD...", "....", ...]
  - payload: [{"bytes":"0xABCD..."}, {"bytes":"ABCD..."} , ...]

Usage:
  export BLOCKFROST_PROJECT_ID="mainnet...."
  ./viewer.py --policy <56-hex-policy> --debug

MIT License
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

from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


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


def safe_print(msg: str) -> None:
    print(msg, flush=True)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hex_to_bytes(hex_str: str) -> bytes:
    hs = (hex_str or "").strip()
    if hs.startswith(("0x", "0X")):
        hs = hs[2:]
    hs = re.sub(r"\s+", "", hs)
    if not hs:
        return b""
    # fromhex requires even length
    if len(hs) % 2 == 1:
        hs = "0" + hs
    return bytes.fromhex(hs)


def hex_to_utf8(hex_str: str) -> str:
    try:
        return hex_to_bytes(hex_str).decode("utf-8")
    except Exception:
        return ""


def extract_metadata(asset_json: dict) -> dict:
    """
    Blockfrost assets/{asset} typically returns:
      - onchain_metadata: dict
      - onchain_metadata_standard: sometimes present
    Prefer onchain_metadata.
    """
    meta = asset_json.get("onchain_metadata")
    if isinstance(meta, dict) and meta:
        return meta

    std = asset_json.get("onchain_metadata_standard")
    if isinstance(std, dict) and std:
        if isinstance(std.get("metadata"), dict) and std["metadata"]:
            return std["metadata"]
        return std

    raise ValueError("No valid on-chain metadata found in asset response")


def payload_to_bytes(payload: Any) -> bytes:
    """
    Supports payload styles:
      - [{"bytes":"0x...."}, {"bytes":"...."}]
      - ["0x....", "...."]
    """
    out = bytearray()
    if payload is None:
        return b""
    if not isinstance(payload, list):
        raise ValueError(f"payload is not a list (got {type(payload).__name__})")

    for item in payload:
        if isinstance(item, dict) and isinstance(item.get("bytes"), str):
            out.extend(hex_to_bytes(item["bytes"]))
        elif isinstance(item, str):
            out.extend(hex_to_bytes(item))
        else:
            raise ValueError(f"Unsupported payload element: {repr(item)[:160]}")
    return bytes(out)


def http_get_json(url: str, headers: Dict[str, str], params: Optional[Dict[str, Any]] = None, debug: bool = False) -> Any:
    if params:
        # manual querystring to avoid extra deps
        qs = "&".join([f"{k}={params[k]}" for k in params])
        url = f"{url}?{qs}"

    backoff = 2
    while True:
        req = Request(url, headers=headers, method="GET")
        try:
            with urlopen(req, timeout=60) as resp:
                raw = resp.read()
                return json.loads(raw.decode("utf-8"))
        except HTTPError as e:
            if e.code == 429:
                if debug:
                    safe_print(f"[debug] 429 rate limit; sleeping {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)
                continue
            raise
        except URLError:
            # transient network hiccup
            if debug:
                safe_print(f"[debug] network error; sleeping {backoff}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
            continue


def list_policy_assets(base_url: str, headers: dict, policy: str, debug: bool = False) -> List[str]:
    units: List[str] = []
    page = 1
    while True:
        batch = http_get_json(
            f"{base_url}/assets/policy/{policy}",
            headers=headers,
            params={"count": 100, "page": page},
            debug=debug,
        )
        if not batch:
            break
        units.extend([item["asset"] for item in batch if "asset" in item])
        page += 1
    return units


def is_manifest(meta: dict, asset_name: str) -> bool:
    if isinstance(meta, dict):
        if meta.get("role") == "manifest":
            return True
        if isinstance(meta.get("pages"), list) and meta["pages"]:
            return True
    return "MANIFEST" in (asset_name or "")


def is_page(meta: dict, asset_name: str) -> bool:
    if isinstance(meta, dict) and meta.get("role") == "page":
        return True
    if re.match(r".*_P\d{4}$", asset_name or ""):
        return True
    if isinstance(meta, dict) and isinstance(meta.get("payload"), list) and meta["payload"]:
        return True
    return False


def choose_page_order(manifest_meta: dict, pages_by_name: Dict[str, dict]) -> List[str]:
    if isinstance(manifest_meta.get("pages"), list) and manifest_meta["pages"]:
        return [p for p in manifest_meta["pages"] if p in pages_by_name]

    sortable: List[Tuple[int, str]] = []
    for name, meta in pages_by_name.items():
        try:
            idx = int(meta.get("i", 0))
        except Exception:
            idx = 0
        sortable.append((idx, name))
    sortable.sort(key=lambda x: x[0])
    return [name for _, name in sortable]


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


def main() -> int:
    ap = argparse.ArgumentParser(description="Ledger Scrolls Viewer (Blockfrost, CIP-25/721)")
    ap.add_argument("--policy", default="", help="Policy ID (56 hex). If omitted, you’ll be prompted.")
    ap.add_argument("--blockfrost", default="", help="Blockfrost project_id (or env BLOCKFROST_PROJECT_ID).")
    ap.add_argument("--out", default="", help="Output filename (default: ledger_scroll_<policy>.html)")
    ap.add_argument("--no-gunzip", action="store_true", help="Do not gunzip even if bytes look like gzip")
    ap.add_argument("--debug", action="store_true", help="Verbose debug output")
    args = ap.parse_args()

    safe_print("\n" + "=" * 58)
    safe_print("                 Ledger Scrolls Viewer")
    safe_print("=" * 58 + "\n")

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

    api_key = (args.blockfrost or os.getenv("BLOCKFROST_PROJECT_ID", "")).strip()
    if not api_key:
        safe_print("\nEnter your Blockfrost API key (mainnet).")
        api_key = input("Blockfrost project_id: ").strip()
    if not api_key:
        safe_print("\nError: Blockfrost key required.")
        return 2

    script_dir = Path(__file__).resolve().parent
    out_path = Path(args.out) if args.out else (script_dir / f"ledger_scroll_{policy[:10]}.html")

    base_url = "https://cardano-mainnet.blockfrost.io/api/v0"
    headers = {"project_id": api_key, "user-agent": "ledger-scrolls-viewer/1.1"}

    safe_print(f"\nPolicy: {policy}")
    safe_print("Scanning assets…")
    units = list_policy_assets(base_url, headers, policy, debug=args.debug)
    safe_print(f"Found {len(units)} assets under policy.")

    manifest_meta: Optional[dict] = None
    manifest_asset_name: Optional[str] = None
    pages_by_name: Dict[str, dict] = {}

    for i, unit in enumerate(units, 1):
        if args.debug:
            safe_print(f"[debug] asset {i}/{len(units)}: {unit}")
        asset_data = http_get_json(f"{base_url}/assets/{unit}", headers=headers, debug=args.debug)
        asset_name = hex_to_utf8(asset_data.get("asset_name", ""))  # usually plain hex, no 0x
        if not asset_name:
            continue

        try:
            meta = extract_metadata(asset_data)
        except Exception:
            continue

        if manifest_meta is None and is_manifest(meta, asset_name):
            manifest_meta = meta
            manifest_asset_name = asset_name
            if args.debug:
                safe_print(f"[debug] manifest candidate: {asset_name}")
            continue

        if is_page(meta, asset_name):
            pages_by_name[asset_name] = meta

        time.sleep(0.02)

    if not manifest_meta:
        safe_print("\nError: no manifest found (expected role=manifest or pages[]).")
        return 1
    if not pages_by_name:
        safe_print("\nError: no pages found.")
        return 1

    page_names = choose_page_order(manifest_meta, pages_by_name)
    if not page_names:
        safe_print("\nError: could not determine page order.")
        return 1

    safe_print(f"\nManifest: {manifest_asset_name or '(unknown)'}")
    safe_print(f"Pages discovered: {len(pages_by_name)}")
    safe_print(f"Pages to assemble: {len(page_names)}\n")

    assembled = bytearray()
    per_page_sizes: List[Tuple[str, int]] = []

    for pn in page_names:
        meta = pages_by_name[pn]
        page_bytes = payload_to_bytes(meta.get("payload", []))
        per_page_sizes.append((pn, len(page_bytes)))

        page_sha = pick_hash(meta, ["sha", "sha256", "sha_gz", "sha_page"])
        if page_sha:
            verify_optional(f"page {pn}", page_bytes, page_sha)

        assembled.extend(page_bytes)

    blob = bytes(assembled)

    if args.debug:
        safe_print("Per-page byte sizes:")
        for pn, sz in per_page_sizes:
            safe_print(f"  {pn}: {sz} bytes")
        safe_print(f"\nTOTAL assembled bytes: {len(blob)}")
        safe_print(f"[debug] first 8 bytes: {blob[:8].hex() if blob else '(empty)'}")

    if len(blob) == 0:
        safe_print("\nERROR: assembled 0 bytes. Payload decoding failed or payload was empty.")
        return 1

    expected_gz = pick_hash(manifest_meta, ["sha_gz", "sha_gzip", "sha_compressed", "sha"])
    if expected_gz:
        safe_print(MAGIC_LINES[4])
        verify_optional("assembled (compressed)", blob, expected_gz)

    looks_gzip = len(blob) >= 2 and blob[0] == 0x1F and blob[1] == 0x8B
    if looks_gzip and not args.no_gunzip:
        safe_print("GZIP detected — decompressing…" if args.debug else MAGIC_LINES[5])
        out_bytes = gzip.decompress(blob)
    else:
        out_bytes = blob

    expected_raw = pick_hash(manifest_meta, ["sha_raw", "sha_html", "sha_uncompressed"])
    if expected_raw:
        verify_optional("assembled (uncompressed)", out_bytes, expected_raw)

    # If user didn’t specify --out, try to keep it .html when it looks like html
    if not args.out:
        head = out_bytes[:512].lower()
        if b"<!doctype html" in head or b"<html" in head or b"<body" in head:
            out_path = out_path.with_suffix(".html")
        else:
            out_path = out_path.with_suffix(".bin")

    out_path.write_bytes(out_bytes)

    safe_print(f"\n{MAGIC_LINES[6]}")
    safe_print(f"WROTE: {out_path} ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
