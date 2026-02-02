from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..cbor_helpers import normalize_asset_key, normalize_policy_key

CIP25_LABEL = 721


@dataclass
class Cip25Asset:
    policy_id: str
    asset_name: str
    fields: Dict[str, Any]


@dataclass
class Cip25Page:
    asset: Cip25Asset
    index: Optional[int]
    total: Optional[int]
    payload_segments: List[bytes]


@dataclass
class Cip25Manifest:
    asset: Cip25Asset
    codec: Optional[str]
    content_type: Optional[str]
    total_pages: Optional[int]
    sha256: Optional[str]
    sha256_gz: Optional[str]


def _as_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8")
        except Exception:
            return v.hex()
    return str(v)


def _as_int(v: Any) -> Optional[int]:
    if isinstance(v, int):
        return int(v)
    if isinstance(v, str) and v.isdigit():
        return int(v)
    return None


def extract_cip25_assets(metadata_721: Any, wanted_policy_hex: str) -> List[Cip25Asset]:
    wanted_policy_hex = wanted_policy_hex.lower()
    out: List[Cip25Asset] = []

    if not isinstance(metadata_721, dict):
        return out

    for pk, pv in metadata_721.items():
        policy_hex = normalize_policy_key(pk)
        if policy_hex is None:
            continue
        if policy_hex.lower() != wanted_policy_hex:
            continue
        if not isinstance(pv, dict):
            continue

        for ak, av in pv.items():
            asset_name = normalize_asset_key(ak)
            fields = {str(k): v for k, v in av.items()} if isinstance(av, dict) else {"value": av}
            out.append(Cip25Asset(policy_id=policy_hex, asset_name=asset_name, fields=fields))

    return out


def classify_assets(assets: List[Cip25Asset], manifest_asset: str | None) -> Tuple[List[Cip25Page], Optional[Cip25Manifest]]:
    pages: List[Cip25Page] = []
    manifest: Optional[Cip25Manifest] = None

    for a in assets:
        is_manifest = False
        if manifest_asset and a.asset_name == manifest_asset:
            is_manifest = True
        elif manifest_asset is None:
            if any(k in a.fields for k in ("codec", "content_type", "content-type", "sha256", "sha", "sha256_gz", "sha_gz")):
                is_manifest = True

        if is_manifest:
            codec = _as_str(a.fields.get("codec"))
            content_type = _as_str(a.fields.get("content_type") or a.fields.get("content-type"))
            total_pages = _as_int(a.fields.get("n") or a.fields.get("pages") or a.fields.get("total_pages"))
            sha256 = _as_str(a.fields.get("sha256") or a.fields.get("sha"))
            sha256_gz = _as_str(a.fields.get("sha256_gz") or a.fields.get("sha_gz"))
            manifest = Cip25Manifest(
                asset=a,
                codec=codec,
                content_type=content_type,
                total_pages=total_pages,
                sha256=sha256,
                sha256_gz=sha256_gz,
            )
            continue

        idx = _as_int(a.fields.get("i") or a.fields.get("index") or a.fields.get("page"))
        total = _as_int(a.fields.get("n") or a.fields.get("total") or a.fields.get("pages"))

        payload = a.fields.get("payload") or a.fields.get("segments") or a.fields.get("seg")
        segs: List[bytes] = []

        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, bytes):
                    segs.append(bytes(item))
                elif isinstance(item, str):
                    try:
                        segs.append(bytes.fromhex(item))
                    except Exception:
                        pass
        elif isinstance(payload, str):
            try:
                segs.append(bytes.fromhex(payload))
            except Exception:
                pass

        pages.append(Cip25Page(asset=a, index=idx, total=total, payload_segments=segs))

    return pages, manifest


def sort_pages(pages: List[Cip25Page]) -> List[Cip25Page]:
    def key(p: Cip25Page):
        if p.index is not None:
            return (0, p.index)
        return (1, p.asset.asset_name)
    return sorted(pages, key=key)
