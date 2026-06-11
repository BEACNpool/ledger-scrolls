#!/usr/bin/env python3
"""Ledger Scrolls conformance runner (Python, stdlib only).

Runs the shared fixture corpus in conformance/manifest.json. The same
fixtures are exercised by run_conformance.mjs so the JS and Python
implementations stay byte-compatible.

Usage:
    python3 conformance/run_conformance.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

FAILURES: list[str] = []
PASSES = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASSES
    if ok:
        PASSES += 1
        print(f"  PASS  {label}")
    else:
        FAILURES.append(label)
        print(f"  FAIL  {label}  {detail}")


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical_json_bytes(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def decode_cbor_bytestring(raw: bytes) -> bytes:
    """Decode a CBOR byte string (definite or indefinite length)."""

    def read_len(buf: bytes, pos: int, ai: int):
        if ai < 24:
            return ai, pos
        widths = {24: 1, 25: 2, 26: 4, 27: 8}
        w = widths[ai]
        return int.from_bytes(buf[pos : pos + w], "big"), pos + w

    mt, ai = raw[0] >> 5, raw[0] & 0x1F
    if mt != 2:
        raise ValueError("not a CBOR byte string")
    if ai == 31:
        out = bytearray()
        pos = 1
        while raw[pos] != 0xFF:
            cmt, cai = raw[pos] >> 5, raw[pos] & 0x1F
            if cmt != 2 or cai == 31:
                raise ValueError("invalid chunk")
            clen, pos = read_len(raw, pos + 1, cai)
            out.extend(raw[pos : pos + clen])
            pos += clen
        return bytes(out)
    blen, pos = read_len(raw, 1, ai)
    return raw[pos : pos + blen]


def clean_segment(seg) -> str:
    # Segments appear as plain hex strings or as {"bytes": "<hex>"} objects
    if isinstance(seg, dict):
        seg = seg.get("bytes") or seg.get("seg") or ""
    seg = str(seg).strip()
    return seg[2:] if seg.lower().startswith("0x") else seg


def reconstruct_cip25_pages(metadata_721: dict, policy_id: str) -> bytes:
    policy_meta = metadata_721["721"][policy_id]
    pages = []
    for asset_name, meta in policy_meta.items():
        if meta.get("role") == "manifest" or "MANIFEST" in asset_name.upper():
            continue
        if "payload" not in meta or "i" not in meta:
            continue
        pages.append((int(meta["i"]), meta["payload"]))
    pages.sort(key=lambda p: p[0])
    hex_blob = "".join(clean_segment(s) for _, payload in pages for s in payload)
    raw = bytes.fromhex(hex_blob)
    if raw[:2] == b"\x1f\x8b":
        return gzip.decompress(raw), raw
    return raw, raw


POINTER_RULES = {
    "utxo-inline-datum-bytes-v1": {
        "txHash": re.compile(r"^[0-9a-fA-F]{64}$"),
        "txIx": int,
    },
    "cip25-pages-v1": {
        "policyId": re.compile(r"^[0-9a-fA-F]{56}$"),
    },
    "url": {
        "url": str,
    },
    # Deprecated aliases readers may still accept
    "utxo-locked-bytes": {
        "txin": re.compile(r"^[0-9a-fA-F]{64}#[0-9]+$"),
    },
    "asset-manifest": {
        "policyId": str,
        "assetName": str,
    },
}


def pointer_is_valid(pointer) -> bool:
    if not isinstance(pointer, dict):
        return False
    rules = POINTER_RULES.get(pointer.get("kind"))
    if rules is None:
        return False
    for field, rule in rules.items():
        value = pointer.get(field)
        if value is None:
            return False
        if isinstance(rule, re.Pattern):
            if not isinstance(value, str) or not rule.match(value):
                return False
        elif not isinstance(value, rule):
            return False
    return True


def main() -> int:
    manifest = json.loads((ROOT / "manifest.json").read_text())
    vectors = manifest["vectors"]

    print("== payload vectors ==")
    for v in vectors["payloads"]:
        data = (ROOT / v["file"]).read_bytes()
        check(f"{v['file']} sha256", sha256_hex(data) == v["sha256"])
        if v.get("codec") == "gzip":
            check(
                f"{v['file']} gunzip sha256",
                sha256_hex(gzip.decompress(data)) == v["decodedSha256"],
            )

    print("== standard scroll datums ==")
    for v in vectors["datums"]:
        raw = bytes.fromhex((ROOT / v["file"]).read_text().strip())
        decoded = decode_cbor_bytestring(raw)
        check(f"{v['file']} decoded sha256", sha256_hex(decoded) == v["decodedSha256"])

    print("== cip25 page reconstruction ==")
    for v in vectors["cip25"]:
        meta = json.loads((ROOT / v["file"]).read_text())
        decoded, gz_raw = reconstruct_cip25_pages(meta, v["policyId"])
        check(f"{v['file']} reconstructed sha256", sha256_hex(decoded) == v["reconstructedSha256"])
        check(f"{v['file']} gzip sha256", sha256_hex(gz_raw) == v["gzipSha256"])

    print("== pointers ==")
    valid_dir = ROOT / vectors["pointers"]["validDir"]
    for f in sorted(valid_dir.glob("*.json")):
        check(f"valid pointer accepted: {f.name}", pointer_is_valid(json.loads(f.read_text())))
    invalid_dir = ROOT / vectors["pointers"]["invalidDir"]
    for f in sorted(invalid_dir.glob("*.json")):
        check(f"invalid pointer rejected: {f.name}", not pointer_is_valid(json.loads(f.read_text())))

    print("== registry canonical hashing ==")
    for v in vectors["registry"]:
        obj = json.loads((ROOT / v["file"]).read_text())
        check(
            f"{v['file']} canonical sha256",
            sha256_hex(canonical_json_bytes(obj)) == v["canonicalSha256"],
        )

    print()
    print(f"{PASSES} passed, {len(FAILURES)} failed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
