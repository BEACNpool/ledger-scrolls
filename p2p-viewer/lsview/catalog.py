from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


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
