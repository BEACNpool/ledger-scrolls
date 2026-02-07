import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import requests

from .hashutil import canonical_json_bytes


class RegistryError(RuntimeError):
    pass


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: str) -> Any:
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


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


def fetch_bytes_from_pointer(pointer: Dict[str, Any], *, base_dir: Optional[str]) -> bytes:
    kind = pointer.get("kind")
    if kind == "url":
        return read_bytes_from_url(pointer["url"], base_dir=base_dir)

    # Cardano pointer kinds are specified but require a chain indexer/provider.
    if kind == "utxo-locked-bytes":
        txin = pointer.get("txin")
        raise RegistryError(
            "Pointer kind 'utxo-locked-bytes' is not implemented in reference tooling yet. "
            f"Need Cardano provider to resolve txin={txin}."
        )

    if kind == "asset-manifest":
        policy_id = pointer.get("policyId")
        asset_name = pointer.get("assetName")
        raise RegistryError(
            "Pointer kind 'asset-manifest' is not implemented in reference tooling yet. "
            f"Need Cardano provider to fetch manifest for policyId={policy_id} assetName={asset_name}."
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


def verify_name(head_path: str, name: str) -> None:
    head = load_json(head_path)

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
        "name": name,
        "contentType": entry.get("contentType"),
        "bytesSha256": got,
        "expectedSha256": expected,
        "ok": ok
    }, indent=2))

    if not ok:
        raise SystemExit(2)


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify Ledger Scrolls Registry resolution (v0)")
    ap.add_argument("--head", required=True, help="Path to registry head JSON")
    ap.add_argument("--name", required=True, help="Entry name to resolve")
    args = ap.parse_args()

    verify_name(args.head, args.name)


if __name__ == "__main__":
    main()
