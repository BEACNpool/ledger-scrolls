from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict

KOIOS = "https://api.koios.rest/api/v1"


def _get_json(url: str, timeout: int = 30) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_json(url: str, payload: Dict[str, Any], timeout: int = 30) -> Any:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def koios_post(path: str, payload: Dict[str, Any], timeout: int = 30) -> Any:
    url = f"{KOIOS}/{path.lstrip('/')}"
    return _post_json(url, payload, timeout=timeout)


def koios_get(path: str, timeout: int = 30) -> Any:
    url = f"{KOIOS}/{path.lstrip('/')}"
    return _get_json(url, timeout=timeout)


def _normalize_block_row(row: Dict[str, Any]) -> Dict[str, Any]:
    height = row.get("block_height") or row.get("height")
    slot = row.get("abs_slot") or row.get("absolute_slot")
    block_hash = row.get("hash") or row.get("block_hash")
    if height is None or slot is None or block_hash is None:
        raise RuntimeError(f"Unexpected block row: {row}")
    return {"height": int(height), "slot": int(slot), "hash": str(block_hash)}


def block_info_by_height(height: int) -> Dict[str, Any]:
    rows = koios_get(f"blocks?block_height=eq.{height}")
    if not rows:
        raise RuntimeError("blocks query returned empty")
    return _normalize_block_row(rows[0])


def block_info_by_hash(block_hash: str) -> Dict[str, Any]:
    rows = koios_get(f"blocks?hash=eq.{urllib.parse.quote(block_hash)}")
    if not rows:
        raise RuntimeError("blocks hash query returned empty")
    return _normalize_block_row(rows[0])


def tx_point(tx_hash: str) -> Dict[str, Any]:
    rows = koios_post("tx_info", {"_tx_hashes": [tx_hash]})
    if not rows:
        raise RuntimeError("tx_info returned empty")
    row = rows[0]
    return {
        "slot": int(row["absolute_slot"]),
        "hash": str(row["block_hash"]),
        "height": int(row["block_height"]),
    }


def prev_point_from_height(height: int) -> Dict[str, Any]:
    return block_info_by_height(height - 1)


def prev_point_from_tx(tx_hash: str) -> Dict[str, Any]:
    manifest = tx_point(tx_hash)
    return prev_point_from_height(manifest["height"])
