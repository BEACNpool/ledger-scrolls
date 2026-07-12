#!/usr/bin/env python3
"""Regenerate fixtures/chain/vector-004-* — the multi-part (next-pointer)
manifest chain vector. Deterministic: same bytes on every run.

Shape under test (manifest-chain-v2 `next` field):
  head manifest  = Constr 0 [2, ct, codec, size, shaDec, shaEnc, [p1,p2], Constr 1 [tailTx, 0]]
  tail manifest  = Constr 0 [2, ct, codec, size, shaDec, shaEnc, [p3,p4], Constr 0 []]
Page tx hashes and the tail manifest's "tx hash" are synthetic
(sha256 of fixed labels) — the runner resolves the continuation from the
vector's `manifests` map, not the network.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "fixtures" / "chain"

SEG = 64
SEGS_PER_PAGE = 3          # tiny pages keep the fixture readable
PAGES = 4                  # 2 per manifest → 2 manifests
CT = "text/plain; charset=utf-8"
CODEC = "none"


def sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


# ── minimal CBOR encoders (definite lengths, matching calculator.html) ──
def enc_len(mt: int, n: int) -> bytes:
    if n < 24:
        return bytes([(mt << 5) | n])
    if n < 256:
        return bytes([(mt << 5) | 24, n])
    if n < 65536:
        return bytes([(mt << 5) | 25]) + n.to_bytes(2, "big")
    return bytes([(mt << 5) | 26]) + n.to_bytes(4, "big")


def c_uint(n: int) -> bytes:
    return enc_len(0, n)


def c_bytes(b: bytes) -> bytes:
    return enc_len(2, len(b)) + b


def c_array(items: list[bytes]) -> bytes:
    return enc_len(4, len(items)) + b"".join(items)


def c_tag(n: int) -> bytes:
    return enc_len(6, n)


def manifest_datum(ct: str, codec: str, size: int, sha_dec: bytes,
                   sha_enc: bytes, page_hashes: list[bytes],
                   next_ptr: tuple[bytes, int] | None) -> bytes:
    nxt = (c_tag(122) + c_array([c_bytes(next_ptr[0]), c_uint(next_ptr[1])])
           if next_ptr else c_tag(121) + c_array([]))
    fields = [c_uint(2), c_bytes(ct.encode()), c_bytes(codec.encode()),
              c_uint(size), c_bytes(sha_dec), c_bytes(sha_enc),
              c_array([c_bytes(h) for h in page_hashes]), nxt]
    return c_tag(121) + c_array(fields)


def main() -> None:
    payload = (b"Ledger Scrolls multi-part conformance vector 004. "
               b"Two sealed manifests linked by a `next` pointer must "
               b"reconstruct as one scroll. ").ljust(PAGES * SEGS_PER_PAGE * SEG, b".")
    page_size = SEGS_PER_PAGE * SEG
    page_payloads = [payload[i:i + page_size] for i in range(0, len(payload), page_size)]
    assert len(page_payloads) == PAGES

    page_tx = [sha256(f"vector-004-page-{i+1}".encode()) for i in range(PAGES)]
    tail_tx = sha256(b"vector-004-tail-manifest")

    pages_json = {}
    for i, (tx, pp) in enumerate(zip(page_tx, page_payloads), start=1):
        segs = [pp[o:o + SEG] for o in range(0, len(pp), SEG)]
        pages_json[tx.hex()] = {"22025": {
            "v": 2, "i": i, "n": PAGES,
            "sha": "0x" + hashlib.sha256(pp).hexdigest(),
            "p": ["0x" + s.hex() for s in segs],
        }}

    sha_all = sha256(payload)
    tail = manifest_datum(CT, CODEC, len(payload), sha_all, sha_all, page_tx[2:], None)
    head = manifest_datum(CT, CODEC, len(payload), sha_all, sha_all, page_tx[:2], (tail_tx, 0))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "vector-004-head.hex").write_text(head.hex() + "\n")
    (OUT / "vector-004-tail.hex").write_text(tail.hex() + "\n")
    (OUT / "vector-004-pages.json").write_text(json.dumps(pages_json, indent=2) + "\n")
    print("payload sha256:", sha_all.hex())
    print("tail ptr:      ", tail_tx.hex() + "#0")
    print("pages:", PAGES, "· parts: 2 · written to", OUT)


if __name__ == "__main__":
    main()
