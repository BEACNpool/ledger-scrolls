from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

BLOCKFROST_MAINNET = "https://cardano-mainnet.blockfrost.io/api/v0"


@dataclass(frozen=True)
class BlockfrostPoint:
    slot: int
    block_hash: str


def _request(path: str, project_id: str, base_url: str = BLOCKFROST_MAINNET) -> Any:
    url = f"{base_url}{path}"
    req = urllib.request.Request(url, headers={"project_id": project_id})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _key(project_id: Optional[str] = None) -> str:
    key = project_id or os.getenv("BLOCKFROST_PROJECT_ID")
    if not key:
        raise ValueError("Blockfrost project_id missing. Set BLOCKFROST_PROJECT_ID or pass --blockfrost-key.")
    return key


def resolve_point_from_tx(tx_hash: str, project_id: str | None = None) -> BlockfrostPoint:
    key = _key(project_id)
    tx = _request(f"/txs/{tx_hash}", key)
    block_hash = tx.get("block")
    slot = tx.get("slot")

    if block_hash is None or slot is None:
        raise ValueError("Blockfrost tx response missing block or slot")

    return BlockfrostPoint(slot=int(slot), block_hash=str(block_hash))


def tx_utxos(tx_hash: str, project_id: str | None = None) -> Dict[str, Any]:
    """Fetch tx UTxOs. Used as a fallback for inline datum discovery."""
    key = _key(project_id)
    return _request(f"/txs/{tx_hash}/utxos", key)


def script_datum_cbor(datum_hash: str, project_id: str | None = None) -> str:
    """Fetch datum CBOR (hex) by datum hash."""
    key = _key(project_id)
    # Blockfrost has /scripts/datum/{datum_hash}/cbor returning { cbor: ".." }
    obj = _request(f"/scripts/datum/{datum_hash}/cbor", key)
    cbor_hex = obj.get("cbor")
    if not cbor_hex:
        raise ValueError("Blockfrost datum cbor missing")
    return str(cbor_hex)


def get_output_inline_datum_hex(tx_hash: str, tx_ix: int, project_id: str | None = None) -> str:
    """Best-effort: return inline datum CBOR hex for a given tx output index."""
    utx = tx_utxos(tx_hash, project_id)
    outputs: List[Dict[str, Any]] = utx.get("outputs") or []
    if tx_ix >= len(outputs):
        raise ValueError("tx output index out of range")

    out = outputs[tx_ix]

    # Different Blockfrost versions expose either inline_datum or datum_hash.
    inline = out.get("inline_datum")
    if inline:
        return str(inline)

    datum_hash = out.get("data_hash") or out.get("datum_hash")
    if datum_hash:
        return script_datum_cbor(str(datum_hash), project_id)

    raise ValueError("No inline datum found for output")
