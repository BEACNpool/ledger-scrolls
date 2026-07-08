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


def read_cbor_len(buf: bytes, pos: int, ai: int):
    if ai < 24:
        return ai, pos
    widths = {24: 1, 25: 2, 26: 4, 27: 8}
    w = widths[ai]
    return int.from_bytes(buf[pos : pos + w], "big"), pos + w


def decode_cbor_bytestring_at(raw: bytes, pos: int = 0) -> tuple[bytes, int]:
    """Decode a CBOR byte string (definite or indefinite length) at pos."""

    mt, ai = raw[pos] >> 5, raw[pos] & 0x1F
    pos += 1
    if mt != 2:
        raise ValueError("not a CBOR byte string")
    if ai == 31:
        out = bytearray()
        while raw[pos] != 0xFF:
            cmt, cai = raw[pos] >> 5, raw[pos] & 0x1F
            if cmt != 2 or cai == 31:
                raise ValueError("invalid chunk")
            clen, pos = read_cbor_len(raw, pos + 1, cai)
            out.extend(raw[pos : pos + clen])
            pos += clen
        return bytes(out), pos + 1
    blen, pos = read_cbor_len(raw, pos, ai)
    return raw[pos : pos + blen], pos + blen


def decode_cbor_bytestring(raw: bytes) -> bytes:
    """Decode standard scroll datum bytes.

    Supports bare CBOR bytes and Plutus constructor-0/tag-121 with one bytes
    field, which is what cardano-cli emits for {"constructor":0,"fields":[...]}.
    """

    if raw[:2] == b"\xd8\x79":
        pos = 2
        if raw[pos] != 0x9F:
            raise ValueError("expected indefinite constructor field array")
        decoded, pos = decode_cbor_bytestring_at(raw, pos + 1)
        if raw[pos] != 0xFF:
            raise ValueError("expected constructor array break")
        return decoded

    return decode_cbor_bytestring_at(raw, 0)[0]


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


def decode_cbor(raw: bytes, pos: int = 0):
    """Minimal generic CBOR decoder (uint/nint/bytes/text/array/tag) for
    LS-CHAIN manifests. Returns (value, next_pos); tags -> ("tag", n, value)."""

    def read_len(ai, p):
        if ai < 24:
            return ai, p
        w = {24: 1, 25: 2, 26: 4, 27: 8}[ai]
        return int.from_bytes(raw[p : p + w], "big"), p + w

    mt, ai = raw[pos] >> 5, raw[pos] & 0x1F
    if mt == 0:
        return read_len(ai, pos + 1)
    if mt == 1:
        n, p = read_len(ai, pos + 1)
        return -1 - n, p
    if mt in (2, 3):
        n, p = read_len(ai, pos + 1)
        v = raw[p : p + n]
        return (v if mt == 2 else v.decode("utf-8")), p + n
    if mt == 4:
        n, p = read_len(ai, pos + 1)
        out = []
        for _ in range(n):
            v, p = decode_cbor(raw, p)
            out.append(v)
        return out, p
    if mt == 6:
        n, p = read_len(ai, pos + 1)
        v, p = decode_cbor(raw, p)
        return ("tag", n, v), p
    raise ValueError(f"unsupported CBOR major type {mt}")


def reconstruct_chain(manifest_hex: str, pages_by_tx: dict, manifests_by_ptr: dict | None = None):
    """Reconstruct a scroll from its head manifest, following `next` pointers
    (field 7: Constr 0 [] = end, Constr 1 [txHash, ix] = continuation).
    manifests_by_ptr maps "txhash#ix" -> manifest hex for continuation parts."""
    info = None
    hashes = []
    cur = manifest_hex
    parts = 0
    while True:
        m, _ = decode_cbor(bytes.fromhex(cur))
        assert m[0] == "tag" and m[1] == 121, "manifest must be Constr 0"
        f = m[2]
        parts += 1
        if info is None:
            info = {
                "version": f[0], "contentType": f[1].decode(), "codec": f[2].decode(),
                "sizeDecoded": f[3], "sha256Decoded": f[4].hex(), "sha256Encoded": f[5].hex(),
            }
        else:
            assert (f[0] == info["version"] and f[1].decode() == info["contentType"]
                    and f[4].hex() == info["sha256Decoded"]), "continuation file fields mismatch"
        hashes.extend(h.hex() for h in f[6])
        nxt = f[7] if len(f) > 7 else None
        if isinstance(nxt, tuple) and nxt[0] == "tag" and nxt[1] == 122 and nxt[2]:
            key = f"{nxt[2][0].hex()}#{nxt[2][1]}"
            assert manifests_by_ptr and key in manifests_by_ptr, f"continuation manifest missing: {key}"
            cur = manifests_by_ptr[key]
            assert parts <= 32, "manifest chain too long"
        else:
            break
    info["pageTxHashes"] = hashes
    info["parts"] = parts
    encoded = bytearray()
    for tx in info["pageTxHashes"]:
        page = pages_by_tx[tx]["22025"]
        payload = b"".join(bytes.fromhex(clean_segment(s)) for s in page["p"])
        assert sha256_hex(payload) == clean_segment(page["sha"]), "page sha mismatch"
        encoded.extend(payload)
    encoded = bytes(encoded)
    decoded = gzip.decompress(encoded) if info["codec"] == "gzip" else encoded
    return info, encoded, decoded


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

    print("== ls-chain v2 ==")
    for v in vectors.get("chain", []):
        mhex = (ROOT / v["manifest"]).read_text().strip()
        pages = json.loads((ROOT / v["pages"]).read_text())
        conts = {ptr: (ROOT / path).read_text().strip()
                 for ptr, path in (v.get("manifests") or {}).items()}
        info, encoded, decoded = reconstruct_chain(mhex, pages, conts)
        check(f"{v['manifest']} fields", info["contentType"] == v["contentType"]
              and info["codec"] == v["codec"] and len(info["pageTxHashes"]) == v["pageCount"]
              and info["parts"] == v.get("parts", 1))
        check(f"{v['manifest']} encoded sha256", sha256_hex(encoded) == v["encodedSha256"]
              and info["sha256Encoded"] == v["encodedSha256"])
        check(f"{v['manifest']} decoded sha256", sha256_hex(decoded) == v["reconstructedSha256"]
              and info["sha256Decoded"] == v["reconstructedSha256"]
              and len(decoded) == info["sizeDecoded"])

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
