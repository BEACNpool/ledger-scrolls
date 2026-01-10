#!/usr/bin/env python3
"""
Ledger Scrolls Viewer (local JSON) — supports:
  1) gzip-pages-v1 (manifest + page_*.json chunks)
  2) single-file-v1 (one asset containing payload chunks, e.g. image/png)

This viewer is intentionally "vanilla":
- No Blockfrost required
- Reads the metadata JSON you already generated for minting (cardano-cli / CNTools style)

Author: BEACN / Ledger Scrolls ethos — simple, inspectable, reproducible.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clean_hex(s: str) -> str:
    hs = (s or "").strip()
    if hs.startswith(("0x", "0X")):
        hs = hs[2:]
    hs = re.sub(r"\s+", "", hs)
    if hs and (len(hs) % 2 != 0):
        raise ValueError(f"Hex string has odd length: {len(hs)}")
    if hs and not HEX_RE.match(hs):
        raise ValueError("Hex string contains non-hex characters")
    return hs


def decode_segment(seg: Any) -> bytes:
    """
    Segment formats supported:
      - {"bytes": "<hex>"}           (recommended / matches cardano-cli JSON bytestring pattern)
      - {"b64": "<base64>"}          (optional convenience)
      - "<hex>"                      (bare string)
    """
    if isinstance(seg, dict):
        if "bytes" in seg:
            hs = _clean_hex(str(seg["bytes"]))
            return bytes.fromhex(hs) if hs else b""
        if "b64" in seg:
            return base64.b64decode(seg["b64"])
        raise ValueError(f"Unknown segment dict keys: {list(seg.keys())}")

    if isinstance(seg, str):
        hs = _clean_hex(seg)
        return bytes.fromhex(hs) if hs else b""

    raise ValueError(f"Unsupported segment type: {type(seg)}")


def join_payload(payload: Any) -> bytes:
    if payload is None:
        return b""
    if not isinstance(payload, list):
        raise ValueError("payload must be a list")
    out = bytearray()
    for seg in payload:
        out.extend(decode_segment(seg))
    return bytes(out)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_asset_obj(doc: Dict[str, Any], policy_id: str, asset_name: str) -> Dict[str, Any]:
    # CIP-25 structure: {"721": { "<policy>": { "<asset>": { ... }}}}
    if "721" not in doc:
        raise KeyError("Missing top-level '721' key (not CIP-25 metadata?)")

    p = doc["721"].get(policy_id)
    if p is None:
        raise KeyError(f"Policy not found in metadata JSON: {policy_id}")

    a = p.get(asset_name)
    if a is None:
        raise KeyError(f"Asset not found in policy {policy_id}: {asset_name}")

    if not isinstance(a, dict):
        raise TypeError("Asset object is not a dict")

    return a


def maybe_decode_codec(data: bytes, codec: str) -> bytes:
    c = (codec or "raw").lower()
    if c in ("raw", "none"):
        return data
    if c in ("gzip", "gz"):
        return gzip.decompress(data)
    raise ValueError(f"Unsupported codec: {codec}")


def reconstruct_single_file(asset_obj: Dict[str, Any]) -> Tuple[bytes, Dict[str, Any]]:
    payload = asset_obj.get("payload")
    raw = join_payload(payload)

    codec = asset_obj.get("codec", asset_obj.get("encoding", "raw"))
    data = maybe_decode_codec(raw, codec)

    # optional SHA validation
    expected_sha = (asset_obj.get("sha") or "").strip().lower()
    if expected_sha:
        got = sha256_hex(data)
        if got != expected_sha:
            raise ValueError(f"SHA mismatch: expected {expected_sha} got {got}")

    return data, asset_obj


def manifest_page_list(manifest_obj: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    Supports two manifest styles:

    A) Explicit list:
       pages: [ {"policy":"<pid>", "asset":"PAGE_0001"}, ... ]

    B) Pattern:
       pagePolicy: "<pid>" (or "policy")
       pagePrefix: "BIBLE_P"
       count: 119
       start: 1 (default)
       pad: 4 (default)
       pattern: "{prefix}{i:04d}" (optional)
    """
    if isinstance(manifest_obj.get("pages"), list):
        out: List[Tuple[str, str]] = []
        for it in manifest_obj["pages"]:
            if not isinstance(it, dict):
                raise ValueError("manifest pages[] entries must be objects")
            pid = it.get("policy") or it.get("policyId") or it.get("pid")
            an = it.get("asset") or it.get("assetName") or it.get("name")
            if not pid or not an:
                raise ValueError("manifest pages[] must contain policy + asset")
            out.append((str(pid), str(an)))
        return out

    pid = manifest_obj.get("pagePolicy") or manifest_obj.get("policy") or manifest_obj.get("policyId")
    prefix = manifest_obj.get("pagePrefix") or manifest_obj.get("assetPrefix") or manifest_obj.get("prefix")
    count = manifest_obj.get("count") or manifest_obj.get("n")
    start = int(manifest_obj.get("start", 1))
    pad = int(manifest_obj.get("pad", 4))
    pattern = manifest_obj.get("pattern")  # optional python format

    if not pid or not prefix or not count:
        raise ValueError("manifest missing pages[] or (policy/prefix/count)")

    out = []
    for i in range(start, start + int(count)):
        if pattern:
            an = pattern.format(prefix=prefix, i=i, pad=pad)
        else:
            an = f"{prefix}{i:0{pad}d}"
        out.append((str(pid), str(an)))
    return out


def load_folder_index(folder: Path) -> List[Dict[str, Any]]:
    """
    Loads all *.json in a folder (non-recursive) as separate CIP-25 docs.
    """
    docs = []
    for p in sorted(folder.glob("*.json")):
        try:
            d = load_json(p)
            if isinstance(d, dict) and "721" in d:
                docs.append(d)
        except Exception:
            # ignore files that aren't valid JSON/CIP-25
            continue
    if not docs:
        raise FileNotFoundError(f"No CIP-25 JSON files found in folder: {folder}")
    return docs


def find_asset_in_docs(docs: List[Dict[str, Any]], policy_id: str, asset_name: str) -> Dict[str, Any]:
    last_err: Optional[Exception] = None
    for d in docs:
        try:
            return find_asset_obj(d, policy_id, asset_name)
        except Exception as e:
            last_err = e
    raise KeyError(f"Asset not found across docs: {policy_id} / {asset_name} ({last_err})")


def reconstruct_from_manifest(docs: List[Dict[str, Any]], policy_id: str, manifest_asset: str) -> Tuple[bytes, Dict[str, Any]]:
    manifest = find_asset_in_docs(docs, policy_id, manifest_asset)

    # manifest itself may be stored as payload bytes (recommended),
    # OR may be "plain JSON fields". We support both.
    if "payload" in manifest:
        raw_manifest_bytes = join_payload(manifest["payload"])
        codec = manifest.get("codec", manifest.get("encoding", "raw"))
        manifest_bytes = maybe_decode_codec(raw_manifest_bytes, codec)
        try:
            manifest_data = json.loads(manifest_bytes.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Manifest payload did not decode as JSON: {e}")
    else:
        manifest_data = manifest

    pages = manifest_page_list(manifest_data)

    assembled = bytearray()
    for (pid, an) in pages:
        page_obj = find_asset_in_docs(docs, pid, an)
        raw_page = join_payload(page_obj.get("payload"))
        page_codec = page_obj.get("codec", page_obj.get("encoding", "raw"))
        page_bytes = maybe_decode_codec(raw_page, page_codec)
        assembled.extend(page_bytes)

    # If the manifest declares a codec for the full assembled blob, respect it
    full_codec = manifest_data.get("contentCodec") or manifest_data.get("codec") or manifest_data.get("assembledCodec")
    if full_codec:
        final = maybe_decode_codec(bytes(assembled), str(full_codec))
    else:
        final = bytes(assembled)

    expected_sha = (manifest_data.get("sha") or "").strip().lower()
    if expected_sha:
        got = sha256_hex(final)
        if got != expected_sha:
            raise ValueError(f"SHA mismatch: expected {expected_sha} got {got}")

    return final, manifest_data


def guess_extension(media_type: str) -> str:
    mt = (media_type or "").lower().strip()
    if mt == "image/png":
        return ".png"
    if mt in ("image/jpeg", "image/jpg"):
        return ".jpg"
    if mt in ("text/html", "application/xhtml+xml"):
        return ".html"
    if mt == "text/plain":
        return ".txt"
    if mt == "application/pdf":
        return ".pdf"
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Ledger Scrolls viewer (local CIP-25 JSON).")
    ap.add_argument("--input", required=True, help="Path to a metadata JSON file OR a folder containing *.json")
    ap.add_argument("--policy", required=True, help="Policy ID (hex)")
    ap.add_argument("--asset", required=True, help="Asset name for single-file mode (e.g., HOSKY_SCROLL_001) OR manifest asset name")
    ap.add_argument("--mode", choices=["auto", "single", "manifest"], default="auto",
                    help="auto=detect role/spec, single=reconstruct one asset, manifest=reconstruct via manifest+pages")
    ap.add_argument("--out", default="", help="Output file path. If omitted, uses asset name + extension in current dir.")
    ap.add_argument("--stdout", action="store_true", help="Write bytes to stdout (useful for piping).")
    args = ap.parse_args()

    inp = Path(args.input).expanduser().resolve()
    if inp.is_dir():
        docs = load_folder_index(inp)
    else:
        d = load_json(inp)
        if not (isinstance(d, dict) and "721" in d):
            raise ValueError("Input JSON is not CIP-25 (missing top-level '721')")
        docs = [d]

    policy = args.policy
    asset = args.asset

    if args.mode == "manifest":
        data, meta = reconstruct_from_manifest(docs, policy, asset)
        media_type = meta.get("mediaType") or meta.get("contentType") or "application/octet-stream"
        role = meta.get("role", "manifest")
    else:
        aobj = find_asset_in_docs(docs, policy, asset)
        role = (aobj.get("role") or "").lower().strip()
        spec = (aobj.get("spec") or "").lower().strip()

        if args.mode == "single" or (args.mode == "auto" and (role in ("file", "cover") or "single" in spec)):
            data, meta = reconstruct_single_file(aobj)
            media_type = meta.get("mediaType") or meta.get("contentType") or "application/octet-stream"
        else:
            # fall back to manifest reconstruction (asset is the manifest name)
            data, meta = reconstruct_from_manifest(docs, policy, asset)
            media_type = meta.get("mediaType") or meta.get("contentType") or "application/octet-stream"
            role = meta.get("role", "manifest")

    if args.stdout:
        sys.stdout.buffer.write(data)
        return 0

    out = args.out.strip()
    if not out:
        ext = guess_extension(str(media_type))
        out = f"{asset}{ext or '.bin'}"

    out_path = Path(out).expanduser().resolve()
    out_path.write_bytes(data)

    print(f"[ok] role={role} bytes={len(data)} mediaType={media_type}")
    print(f"[ok] wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
