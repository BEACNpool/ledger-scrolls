from __future__ import annotations

import gzip
import hashlib
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .cip25 import Cip25Manifest, Cip25Page, sort_pages


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@dataclass
class ReconstructedFile:
    filename: str
    content_type: Optional[str]
    codec: Optional[str]
    raw_bytes: bytes
    sha256: str


def reconstruct_pages(pages: List[Cip25Page]) -> bytes:
    ordered = sort_pages(pages)
    out = bytearray()
    for p in ordered:
        for seg in p.payload_segments:
            out.extend(seg)
    return bytes(out)


def maybe_gunzip(b: bytes, codec: Optional[str]) -> Tuple[bytes, Optional[str]]:
    if codec is None:
        if len(b) >= 2 and b[0] == 0x1F and b[1] == 0x8B:
            return gzip.decompress(b), "gzip"
        return b, None
    if codec.lower() == "gzip":
        return gzip.decompress(b), "gzip"
    return b, codec


def reconstruct_cip25(
    pages: List[Cip25Page],
    manifest: Optional[Cip25Manifest],
    out_name: str,
) -> ReconstructedFile:
    gz_bytes = reconstruct_pages(pages)

    codec = manifest.codec if manifest else None
    content_type = manifest.content_type if manifest else None

    decoded, codec_used = maybe_gunzip(gz_bytes, codec)

    if manifest and manifest.sha256_gz:
        if sha256_hex(gz_bytes) != manifest.sha256_gz.lower():
            raise ValueError("Integrity check failed: gzip sha256 mismatch")
    if manifest and manifest.sha256:
        if sha256_hex(decoded) != manifest.sha256.lower():
            raise ValueError("Integrity check failed: decoded sha256 mismatch")

    return ReconstructedFile(
        filename=out_name,
        content_type=content_type,
        codec=codec_used,
        raw_bytes=decoded,
        sha256=sha256_hex(decoded),
    )
