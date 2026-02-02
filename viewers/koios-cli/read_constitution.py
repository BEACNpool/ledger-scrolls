#!/usr/bin/env python3
"""
Ledger Scrolls: Zero-Dependency Constitution Reader

- Python 3 stdlib only
- Koios public REST API (no API key)
- Reads Cardano Constitution (Epoch 608 or 541)
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import time
import urllib.request
from typing import Any, Dict, Iterable, List, Tuple

KOIOS = "https://api.koios.rest/api/v1"

CONSTITUTIONS = {
    "608": {
        "name": "Cardano Constitution (Epoch 608)",
        "policy_id": "ef91a425ef57d92db614085ef03718407fb293cb4b770bc6e03f9750",
        "sha256": "98a29aec8664b62912c1c0355ebae1401b7c0e53d632e8f05479e7821935abf1",
        "pages": 11,
    },
    "541": {
        "name": "Cardano Constitution (Epoch 541)",
        "policy_id": "d7559bbfa87f53674570fd01f564687c2954503b510ead009148a31d",
        "sha256": "1939c1627e49b5267114cbdb195d4ac417e545544ba6dcb47e03c679439e9566",
        "pages": 7,
    },
}


class KoiosError(RuntimeError):
    pass


def _request_json(url: str, payload: Dict[str, Any] | None = None, timeout: int = 30) -> Any:
    if payload is None:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
    else:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def koios_post(path: str, payload: Dict[str, Any], retries: int = 5, backoff: float = 0.6) -> Any:
    url = f"{KOIOS}/{path.lstrip('/')}"
    for attempt in range(retries):
        try:
            return _request_json(url, payload=payload)
        except Exception as exc:
            if attempt >= retries - 1:
                raise KoiosError(str(exc)) from exc
            time.sleep(backoff * (2**attempt))
    raise KoiosError("unreachable")


def hex_to_ascii(hex_str: str) -> str:
    try:
        return bytes.fromhex(hex_str).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def batched(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def extract_cip721(meta: Any) -> Dict[str, Any] | None:
    if isinstance(meta, dict):
        if "721" in meta:
            return meta["721"]
        if 721 in meta:
            return meta[721]
        return None
    if isinstance(meta, list):
        for item in meta:
            if isinstance(item, dict) and str(item.get("label")) == "721":
                return item.get("json_metadata") or item.get("metadata") or item.get("value")
    return None


def fetch_policy_assets(policy_id: str) -> List[Dict[str, Any]]:
    return koios_post("policy_asset_list", {"_policy_id": policy_id}) or []


def fetch_asset_info(policy_id: str, asset_name: str) -> Dict[str, Any]:
    rows = koios_post("asset_info", {"_asset_list": [[policy_id, asset_name]]})
    if not rows:
        raise KoiosError(f"asset_info empty for {policy_id}.{asset_name}")
    return rows[0]


def fetch_tx_metadata(tx_hashes: List[str]) -> Dict[str, Any]:
    rows = koios_post("tx_metadata", {"_tx_hashes": tx_hashes}) or []
    out: Dict[str, Any] = {}
    for row in rows:
        tx = row.get("tx_hash")
        if tx:
            out[tx] = row.get("metadata")
    return out


def reconstruct(policy_id: str, expected_sha256: str, rate_limit: float = 0.2) -> Tuple[bytes, str]:
    assets = fetch_policy_assets(policy_id)
    if not assets:
        raise KoiosError("No assets returned for policy.")

    asset_info: Dict[str, Dict[str, Any]] = {}
    mint_txs: List[str] = []

    for a in assets:
        asset_name = a.get("asset_name")
        if not asset_name:
            continue
        info = fetch_asset_info(policy_id, asset_name)
        asset_ascii = info.get("asset_name_ascii") or hex_to_ascii(asset_name)
        mint_tx = info.get("minting_tx_hash")
        asset_info[asset_name] = {
            "ascii": asset_ascii,
            "mint_tx": mint_tx,
        }
        if mint_tx:
            mint_txs.append(mint_tx)
        time.sleep(rate_limit)

    mint_txs = sorted(set(mint_txs))

    tx_meta: Dict[str, Any] = {}
    for batch in batched(mint_txs, 5):
        tx_meta.update(fetch_tx_metadata(batch))
        time.sleep(rate_limit)

    pages: List[Tuple[int, List[str]]] = []

    for asset_name, info in asset_info.items():
        tx_hash = info.get("mint_tx")
        if not tx_hash:
            continue
        meta = tx_meta.get(tx_hash)
        cip721 = extract_cip721(meta)
        if not cip721:
            continue
        policy_meta = cip721.get(policy_id) if isinstance(cip721, dict) else None
        if not policy_meta:
            continue

        asset_ascii = info.get("ascii")
        asset_meta = policy_meta.get(asset_ascii)
        if not asset_meta:
            continue

        if "MANIFEST" in (asset_ascii or ""):
            continue

        if "payload" in asset_meta and "i" in asset_meta:
            try:
                idx = int(asset_meta["i"])
            except Exception:
                continue
            payload = asset_meta.get("payload") or []
            if isinstance(payload, list):
                pages.append((idx, payload))

    if not pages:
        raise KoiosError("No pages found in metadata.")

    pages.sort(key=lambda x: x[0])
    hex_blob = "".join("".join(seg for seg in payload) for _, payload in pages)
    raw = bytes.fromhex(hex_blob)

    if raw.startswith(b"\x1f\x8b"):
        raw = gzip.decompress(raw)

    sha = hashlib.sha256(raw).hexdigest()
    if expected_sha256 and sha.lower() != expected_sha256.lower():
        raise KoiosError(f"SHA-256 mismatch: got {sha} expected {expected_sha256}")

    return raw, sha


def main() -> None:
    parser = argparse.ArgumentParser(description="Read the Cardano Constitution (Koios, zero-deps)")
    parser.add_argument("epoch", nargs="?", default="608", help="Constitution epoch (608 or 541)")
    parser.add_argument("--save", action="store_true", help="Write full text to file")
    parser.add_argument("--verify", action="store_true", help="Verify hash only (no output)")
    parser.add_argument("--out", help="Output file (default: Cardano_Constitution_Epoch_<epoch>.txt)")
    args = parser.parse_args()

    if args.epoch not in CONSTITUTIONS:
        raise SystemExit("Supported epochs: 608, 541")

    info = CONSTITUTIONS[args.epoch]
    data, sha = reconstruct(info["policy_id"], info["sha256"])

    if args.verify:
        print(f"OK — SHA-256 matches: {sha}")
        return

    if args.save:
        out = args.out or f"Cardano_Constitution_Epoch_{args.epoch}.txt"
        with open(out, "wb") as f:
            f.write(data)
        print(f"Reconstructed: {out}")
        print(f"Bytes: {len(data)}")
        print(f"SHA-256: {sha}")
        return

    preview = data.decode("utf-8", errors="ignore").splitlines()[:30]
    print("\n".join(preview))
    print("\n---")
    print(f"Bytes: {len(data)}")
    print(f"SHA-256: {sha}")


if __name__ == "__main__":
    main()
