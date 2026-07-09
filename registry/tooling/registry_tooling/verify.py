import argparse
import hashlib
import json
import os
from typing import Any, Dict, Optional, Tuple

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .hashutil import canonical_json_bytes


KOIOS_BASE = os.environ.get("LSR_KOIOS_BASE", "https://api.koios.rest/api/v1")


class RegistryError(RuntimeError):
    pass


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_head_signature(head: Dict[str, Any], trusted_key: Optional[str] = None) -> str:
    """Verify a registry-v1 Ed25519 envelope; return the authenticated key id.

    v0 heads remain readable when no trust key is requested. Supplying a trust
    key is fail-closed: an unsigned head is then rejected.
    """
    signature = head.get("signature")
    signer = head.get("signer")
    if not signature or not isinstance(signer, dict) or not signer.get("keyId"):
        if trusted_key:
            raise RegistryError("Trusted-key mode requires a signed registry-v1 head")
        return "unsigned-v0"
    key_id = str(signer["keyId"]).lower()
    if trusted_key and key_id != trusted_key.lower():
        raise RegistryError("Registry head signer does not match the pinned key")
    try:
        pub = bytes.fromhex(key_id)
        sig = bytes.fromhex(str(signature))
        if len(pub) != 32 or len(sig) != 64:
            raise ValueError("wrong Ed25519 key/signature length")
        unsigned = dict(head)
        del unsigned["signature"]
        Ed25519PublicKey.from_public_bytes(pub).verify(sig, canonical_json_bytes(unsigned))
    except (ValueError, InvalidSignature) as exc:
        raise RegistryError("Invalid registry head signature") from exc
    return key_id


def rotation_allows(previous_head: Dict[str, Any], next_head: Dict[str, Any]) -> bool:
    """Return whether a signed successor uses the same or an authorized next key."""
    prev = previous_head.get("signer") or {}
    nxt = next_head.get("signer") or {}
    current = str(prev.get("keyId") or "").lower()
    candidate = str(nxt.get("keyId") or "").lower()
    allowed = {current, *(str(k).lower() for k in (prev.get("nextKeys") or []))}
    return bool(candidate and candidate in allowed)


def load_json(path: str) -> Any:
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def _decode_cbor_bytestring(raw: bytes) -> bytes:
    """Minimal CBOR decoder for byte strings (definite or indefinite length).

    Standard Scroll / registry datums are CBOR byte strings whose chunks are
    each <= 64 bytes (see registry/spec/cardano-utxo-datum.md). Returns the
    input unchanged when it is not a CBOR byte string.
    """

    def read_len(buf: bytes, pos: int, ai: int) -> Tuple[int, int]:
        if ai < 24:
            return ai, pos
        widths = {24: 1, 25: 2, 26: 4, 27: 8}
        w = widths.get(ai)
        if w is None or pos + w > len(buf):
            raise ValueError("unsupported CBOR length")
        return int.from_bytes(buf[pos : pos + w], "big"), pos + w

    if not raw:
        return raw
    mt, ai = raw[0] >> 5, raw[0] & 0x1F
    if mt != 2:
        return raw
    try:
        if ai == 31:  # indefinite-length byte string
            out = bytearray()
            pos = 1
            while pos < len(raw) and raw[pos] != 0xFF:
                cmt, cai = raw[pos] >> 5, raw[pos] & 0x1F
                if cmt != 2 or cai == 31:
                    raise ValueError("invalid chunk in indefinite byte string")
                clen, pos = read_len(raw, pos + 1, cai)
                out.extend(raw[pos : pos + clen])
                pos += clen
            return bytes(out)
        blen, pos = read_len(raw, 1, ai)
        return raw[pos : pos + blen]
    except ValueError:
        return raw


def read_bytes_from_url(url: str, base_dir: Optional[str] = None) -> bytes:
    """Fetch bytes for pointer kind=url.

    Supports:
    - http(s) URLs
    - local relative paths when url starts with ./ or ../ (resolved relative to base_dir)
    """
    if url.startswith("http://") or url.startswith("https://"):
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.content

    if url.startswith("./") or url.startswith("../") or (not "://" in url and not url.startswith("/")):
        if not base_dir:
            raise RegistryError("Relative url pointer requires base_dir")
        path = os.path.normpath(os.path.join(base_dir, url))
        with open(path, "rb") as f:
            return f.read()

    if url.startswith("file://"):
        path = url[len("file://") :]
        with open(path, "rb") as f:
            return f.read()

    raise RegistryError(f"Unsupported url pointer: {url}")


def read_bytes_from_utxo_inline_datum(tx_hash: str, tx_ix: int) -> bytes:
    """Resolve a utxo-inline-datum-bytes-v1 pointer via Koios.

    _extended is required: without it Koios omits inline_datum.
    """
    r = requests.post(
        f"{KOIOS_BASE}/utxo_info",
        json={"_utxo_refs": [f"{tx_hash}#{tx_ix}"], "_extended": True},
        timeout=30,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows:
        raise RegistryError(f"UTxO not found: {tx_hash}#{tx_ix}")
    datum_hex = (rows[0].get("inline_datum") or {}).get("bytes")
    if not datum_hex:
        raise RegistryError(f"UTxO has no inline datum: {tx_hash}#{tx_ix}")
    return _decode_cbor_bytestring(bytes.fromhex(datum_hex))


def normalize_pointer(pointer: Dict[str, Any]) -> Dict[str, Any]:
    """Map deprecated legacy pointer kinds onto canonical v0 kinds."""
    kind = pointer.get("kind")
    if kind == "utxo-locked-bytes":
        txin = str(pointer.get("txin") or "")
        tx_hash, _, tx_ix = txin.partition("#")
        return {
            "kind": "utxo-inline-datum-bytes-v1",
            "txHash": tx_hash,
            "txIx": int(tx_ix or 0),
        }
    if kind == "asset-manifest":
        return {
            "kind": "cip25-pages-v1",
            "policyId": pointer.get("policyId"),
            "manifestAsset": pointer.get("assetName"),
        }
    return pointer


def fetch_bytes_from_pointer(pointer: Dict[str, Any], *, base_dir: Optional[str]) -> bytes:
    pointer = normalize_pointer(pointer)
    kind = pointer.get("kind")

    if kind == "url":
        return read_bytes_from_url(pointer["url"], base_dir=base_dir)

    if kind == "utxo-inline-datum-bytes-v1":
        tx_hash = pointer.get("txHash")
        tx_ix = pointer.get("txIx")
        if not tx_hash or tx_ix is None:
            raise RegistryError("utxo-inline-datum-bytes-v1 pointer requires txHash and txIx")
        return read_bytes_from_utxo_inline_datum(str(tx_hash), int(tx_ix))

    if kind == "cip25-pages-v1":
        raise RegistryError(
            "Pointer kind 'cip25-pages-v1' is not implemented in reference tooling yet. "
            "Use koios-viewer (lsview reconstruct-cip25) for paged scrolls."
        )

    raise RegistryError(f"Unknown pointer kind: {kind}")


def load_registry_list_from_head(head: Dict[str, Any], *, head_path: str) -> Tuple[Dict[str, Any], str]:
    pointer = head.get("registryList")
    if not isinstance(pointer, dict):
        raise RegistryError("head.registryList must be a pointer object")

    base_dir = os.path.dirname(os.path.abspath(head_path))
    raw = fetch_bytes_from_pointer(pointer, base_dir=base_dir)

    # v0 list is JSON
    lst = json.loads(raw.decode("utf-8"))
    return lst, base_dir


def find_entry(registry_list: Dict[str, Any], name: str) -> Dict[str, Any]:
    entries = registry_list.get("entries")
    if not isinstance(entries, list):
        raise RegistryError("registry list missing entries[]")

    for e in entries:
        if isinstance(e, dict) and e.get("name") == name:
            return e
    raise RegistryError(f"name not found: {name}")


def verify_name(head_path: str, name: str, trusted_key: Optional[str] = None) -> None:
    head = load_json(head_path)
    signer_status = verify_head_signature(head, trusted_key)

    # Optional: show deterministic head hash (canonical JSON)
    head_hash = sha256_hex(canonical_json_bytes(head))

    reg_list, base_dir = load_registry_list_from_head(head, head_path=head_path)

    entry = find_entry(reg_list, name)

    pointer = entry.get("pointer")
    if not isinstance(pointer, dict):
        raise RegistryError("entry.pointer must be a pointer object")

    expected = entry.get("sha256")
    if not isinstance(expected, str) or not expected:
        raise RegistryError("entry.sha256 missing")

    data = fetch_bytes_from_pointer(pointer, base_dir=base_dir)
    got = sha256_hex(data)

    ok = got.lower() == expected.lower()

    print(json.dumps({
        "headHash": head_hash,
        "headSigner": signer_status,
        "name": name,
        "contentType": entry.get("contentType"),
        "bytesSha256": got,
        "expectedSha256": expected,
        "ok": ok
    }, indent=2))

    if not ok:
        raise SystemExit(2)


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify Ledger Scrolls Registry resolution (v0/v1)")
    ap.add_argument("--head", required=True, help="Path to registry head JSON")
    ap.add_argument("--name", required=True, help="Entry name to resolve")
    ap.add_argument("--trusted-key", help="Pinned 32-byte Ed25519 public key hex; rejects unsigned/other signers")
    args = ap.parse_args()

    verify_name(args.head, args.name, args.trusted_key)


if __name__ == "__main__":
    main()
