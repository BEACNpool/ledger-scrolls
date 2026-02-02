from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict


BLOCKFROST_MAINNET = "https://cardano-mainnet.blockfrost.io/api/v0"


@dataclass(frozen=True)
class BlockfrostPoint:
    slot: int
    block_hash: str


def _request(path: str, project_id: str, base_url: str = BLOCKFROST_MAINNET) -> Dict[str, Any]:
    url = f"{base_url}{path}"
    req = urllib.request.Request(url, headers={"project_id": project_id})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def resolve_point_from_tx(tx_hash: str, project_id: str | None = None) -> BlockfrostPoint:
    key = project_id or os.getenv("BLOCKFROST_PROJECT_ID")
    if not key:
        raise ValueError("Blockfrost project_id missing. Set BLOCKFROST_PROJECT_ID or pass --blockfrost-key.")

    tx = _request(f"/txs/{tx_hash}", key)
    block_hash = tx.get("block")
    slot = tx.get("slot")

    if block_hash is None or slot is None:
        raise ValueError("Blockfrost tx response missing block or slot")

    return BlockfrostPoint(slot=int(slot), block_hash=str(block_hash))
