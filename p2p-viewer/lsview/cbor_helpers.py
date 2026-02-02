from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Optional

import cbor2


def blake2b_256(data: bytes) -> bytes:
    return hashlib.blake2b(data, digest_size=32).digest()


def safe_cbor_loads(b: bytes) -> Any:
    return cbor2.loads(b)


def try_decode_ascii(b: bytes) -> str:
    try:
        s = b.decode("utf-8")
        if all(32 <= ord(ch) <= 126 or ch in "\r\n\t" for ch in s):
            return s
        return b.hex()
    except Exception:
        return b.hex()


def normalize_policy_key(k: Any) -> Optional[str]:
    if isinstance(k, bytes):
        return k.hex()
    if isinstance(k, str):
        return k.lower()
    return None


def normalize_asset_key(k: Any) -> str:
    if isinstance(k, bytes):
        return try_decode_ascii(k)
    if isinstance(k, str):
        return k
    return str(k)


@dataclass(frozen=True)
class Point:
    slot: int
    block_hash: bytes  # 32 bytes

    def to_cbor(self) -> list:
        return [int(self.slot), self.block_hash]

    @staticmethod
    def from_hex(slot: int, block_hash_hex: str) -> "Point":
        bh = bytes.fromhex(block_hash_hex)
        if len(bh) != 32:
            raise ValueError(f"block_hash must be 32 bytes (64 hex chars). got len={len(bh)}")
        return Point(slot=int(slot), block_hash=bh)
