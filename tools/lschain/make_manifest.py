#!/usr/bin/env python3
"""LS-CHAIN v2 writer, step 2: build the manifest datum CBOR (stdlib only).

Reads plan.json + the ordered page tx hashes and emits the manifest as a
Plutus-Data CBOR file for `--tx-out-inline-datum-cbor-file`.

Manifest = Constr 0 [version, contentType, codec, sizeDecoded,
                     sha256Decoded, sha256Encoded, [pageTxHash...], next]
(Constructor i is CBOR tag 121+i; `next` none = Constr 0 [].)

Usage:
    python3 make_manifest.py plan.json page_txids.txt manifest.cbor
"""
from __future__ import annotations

import json
import struct
import sys


def cbor_uint(major: int, n: int) -> bytes:
    if n < 24:
        return bytes([(major << 5) | n])
    if n < 256:
        return bytes([(major << 5) | 24, n])
    if n < 65536:
        return bytes([(major << 5) | 25]) + struct.pack(">H", n)
    if n < 2**32:
        return bytes([(major << 5) | 26]) + struct.pack(">I", n)
    return bytes([(major << 5) | 27]) + struct.pack(">Q", n)


def enc_int(n: int) -> bytes:
    return cbor_uint(0, n) if n >= 0 else cbor_uint(1, -1 - n)


def enc_bytes(b: bytes) -> bytes:
    assert len(b) <= 64, "Plutus Data byte strings must be <= 64 bytes"
    return cbor_uint(2, len(b)) + b


def enc_list(items: list[bytes]) -> bytes:
    # Definite-length list of pre-encoded items
    return cbor_uint(4, len(items)) + b"".join(items)


def enc_constr(index: int, fields: list[bytes]) -> bytes:
    assert 0 <= index <= 6, "only compact constructor tags supported"
    return cbor_uint(6, 121 + index) + enc_list(fields)


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    plan_path, txids_path, out_path = sys.argv[1:4]

    with open(plan_path) as f:
        plan = json.load(f)
    with open(txids_path) as f:
        txids = [line.strip() for line in f if line.strip()]

    if len(txids) != plan["pages"]:
        sys.exit(f"plan expects {plan['pages']} pages, got {len(txids)} txids")
    for t in txids:
        if len(t) != 64 or any(c not in "0123456789abcdefABCDEF" for c in t):
            sys.exit(f"bad txid: {t}")

    manifest = enc_constr(0, [
        enc_int(2),
        enc_bytes(plan["contentType"].encode("utf-8")),
        enc_bytes(plan["codec"].encode("utf-8")),
        enc_int(plan["sizeDecoded"]),
        enc_bytes(bytes.fromhex(plan["sha256Decoded"])),
        enc_bytes(bytes.fromhex(plan["sha256Encoded"])),
        enc_list([enc_bytes(bytes.fromhex(t)) for t in txids]),
        enc_constr(0, []),  # next: none
    ])

    with open(out_path, "wb") as f:
        f.write(manifest)
    print(f"manifest datum: {out_path} ({len(manifest)} bytes, {len(txids)} pages)")


if __name__ == "__main__":
    main()
