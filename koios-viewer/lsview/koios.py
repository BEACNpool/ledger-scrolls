from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

KOIOS = "https://api.koios.rest/api/v1"


class KoiosError(RuntimeError):
    pass


def _get_json(url: str, timeout: int = 30) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_json(url: str, payload: Dict[str, Any], timeout: int = 30) -> Any:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def koios_post(path: str, payload: Dict[str, Any], timeout: int = 30) -> Any:
    url = f"{KOIOS}/{path.lstrip('/')}"
    return _post_json(url, payload, timeout=timeout)


def koios_get(path: str, timeout: int = 30) -> Any:
    url = f"{KOIOS}/{path.lstrip('/')}"
    return _get_json(url, timeout=timeout)


# --- Existing helpers (used by older code; kept for compatibility) ---

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


# --- Koios: scroll primitives (Koios-first viewer path) ---


def utxo_info(txin: str) -> Dict[str, Any]:
    """Return the Koios utxo_info row for a txin (<txhash>#<ix>)."""
    rows = koios_post("utxo_info", {"_utxo_refs": [txin]})
    if not rows:
        raise KoiosError(f"UTxO not found: {txin}")
    return rows[0]


def get_inline_datum_hex_from_utxo_info_row(row: Dict[str, Any]) -> str:
    datum = row.get("inline_datum") or {}
    # Koios typically returns { "bytes": "<hex>" }
    b = datum.get("bytes")
    if not b:
        raise KoiosError("No inline datum bytes found")
    return str(b)


def policy_asset_list(policy_id: str) -> List[Dict[str, Any]]:
    return koios_post("policy_asset_list", {"_policy_id": policy_id}) or []


def asset_info(policy_id: str, asset_name_hex: str) -> Dict[str, Any]:
    rows = koios_post("asset_info", {"_asset_list": [[policy_id, asset_name_hex]]})
    if not rows:
        raise KoiosError(f"asset_info empty for {policy_id}.{asset_name_hex}")
    return rows[0]


def tx_metadata(tx_hashes: List[str]) -> Dict[str, Any]:
    rows = koios_post("tx_metadata", {"_tx_hashes": tx_hashes}) or []
    out: Dict[str, Any] = {}
    for row in rows:
        tx = row.get("tx_hash")
        if tx:
            out[str(tx)] = row.get("metadata")
    return out


def with_retries(fn, *, retries: int = 5, backoff: float = 0.6):
    last: Exception | None = None
    for i in range(retries):
        try:
            return fn()
        except Exception as exc:
            last = exc
            if i >= retries - 1:
                break
            time.sleep(backoff * (2**i))
    raise KoiosError(str(last))
