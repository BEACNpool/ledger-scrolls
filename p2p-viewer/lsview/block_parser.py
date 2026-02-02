from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .cbor_helpers import safe_cbor_loads


@dataclass
class ParsedTx:
    index: int
    metadata: Dict[int, Any]


@dataclass
class ParsedBlock:
    era: Optional[int]
    txs: List[ParsedTx]


def _extract_metadata_map(aux: Any) -> Dict[int, Any]:
    if aux is None:
        return {}

    if isinstance(aux, (bytes, bytearray)):
        try:
            aux = safe_cbor_loads(bytes(aux))
        except Exception:
            return {}

    if isinstance(aux, list) and aux:
        maybe_meta = aux[0]
        if isinstance(maybe_meta, dict):
            return {int(k): v for k, v in maybe_meta.items() if isinstance(k, int)}
        return {}

    if isinstance(aux, dict):
        return {int(k): v for k, v in aux.items() if isinstance(k, int)}

    return {}


def parse_block(block_body_cbor: bytes) -> ParsedBlock:
    obj = safe_cbor_loads(block_body_cbor)

    era = None
    block = None
    if isinstance(obj, list) and obj:
        if isinstance(obj[0], int):
            era = obj[0]
            block = obj[1] if len(obj) > 1 else None
        else:
            block = obj

    if block is None:
        raise ValueError("unrecognized block structure")

    tx_bodies = []
    aux_map = {}

    if isinstance(block, list) and len(block) >= 2:
        if isinstance(block[1], list):
            tx_bodies = block[1]
        if len(block) >= 4 and isinstance(block[3], dict):
            aux_map = block[3]
        elif len(block) >= 3 and isinstance(block[2], dict):
            aux_map = block[2]

    txs: List[ParsedTx] = []
    for i in range(len(tx_bodies)):
        md = _extract_metadata_map(aux_map.get(i) if isinstance(aux_map, dict) else None)
        txs.append(ParsedTx(index=i, metadata=md))

    return ParsedBlock(era=era, txs=txs)


def iter_label(block: ParsedBlock, label: int) -> List[Any]:
    out = []
    for tx in block.txs:
        if label in tx.metadata:
            out.append(tx.metadata[label])
    return out
