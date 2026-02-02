from __future__ import annotations

import json
import urllib.request
from typing import Iterable, List, Tuple


def _load_json(source: str) -> dict:
    if source.startswith("http://") or source.startswith("https://"):
        with urllib.request.urlopen(source, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    with open(source, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_endpoints(items: Iterable[dict]) -> List[Tuple[str, int]]:
    out: List[Tuple[str, int]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        host = item.get("addr") or item.get("address") or item.get("host")
        port = item.get("port") or 3001
        if host:
            out.append((str(host), int(port)))
    return out


def load_topology(source: str) -> List[Tuple[str, int]]:
    """
    Load a Cardano topology JSON file/URL and return a list of (host, port).
    Supports common keys: Producers / AccessPoints.
    """
    data = _load_json(source)
    if not isinstance(data, dict):
        return []

    producers = data.get("Producers") or data.get("producers") or []
    access_points = data.get("AccessPoints") or data.get("accessPoints") or []

    out: List[Tuple[str, int]] = []
    out.extend(_extract_endpoints(producers))
    out.extend(_extract_endpoints(access_points))

    seen = set()
    uniq: List[Tuple[str, int]] = []
    for host, port in out:
        key = (host, int(port))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(key)

    return uniq
