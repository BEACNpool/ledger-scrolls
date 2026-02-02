from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .blockfrost import resolve_point_from_tx


DEFAULT_CATALOG = Path(__file__).resolve().parent.parent / "examples" / "scrolls.json"


@dataclass
class CatalogEntry:
    id: str
    data: Dict[str, Any]


def load_catalog(path: Optional[str] = None) -> Dict[str, CatalogEntry]:
    src = Path(path) if path else DEFAULT_CATALOG
    with open(src, "r", encoding="utf-8") as f:
        raw = json.load(f)

    entries: Dict[str, CatalogEntry] = {}
    for item in raw.get("scrolls", []):
        sid = item.get("id")
        if not sid:
            continue
        entries[str(sid)] = CatalogEntry(id=str(sid), data=item)

    return entries


def save_catalog(entries: Dict[str, CatalogEntry], path: Optional[str] = None) -> None:
    src = Path(path) if path else DEFAULT_CATALOG
    payload = {"scrolls": [e.data for e in entries.values()]}
    with open(src, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False)
        f.write("\n")


def refresh_catalog(path: Optional[str] = None, blockfrost_key: Optional[str] = None) -> Dict[str, CatalogEntry]:
    entries = load_catalog(path)

    for entry in entries.values():
        data = entry.data
        tx_hash = data.get("tx_hash") or data.get("manifest_tx")
        if not tx_hash:
            continue

        try:
            point = resolve_point_from_tx(tx_hash, blockfrost_key)
        except Exception:
            continue

        data["block_slot"] = int(point.slot)
        data["block_hash"] = point.block_hash

    save_catalog(entries, path)
    return entries
