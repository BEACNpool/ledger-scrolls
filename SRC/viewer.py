import os
import json
import zlib
import hashlib
import subprocess
import requests
import time  # for rate limit delay
from typing import Dict, List, Any, Tuple, Optional

# ── Defaults from README ─────────────────────────────────────────────────────
DEFAULT_REGISTRY = {
    "address": "addr1q9x84f458uyf3k23sr7qfalg3mw2hl0nvv4navps2r7vq69esnxrheg9tfpr8sdyfzpr8jch5p538xjynz78lql9wm6qpl6qxy",
    "policy_id": "895cbbe0e284b60660ed681e389329483d5ca94677cbb583f3124062",
    "asset_name_hex": "4c535f5245474953545259",  # LS_REGISTRY
}

DEFAULT_SCROLLS = [
    {
        "id": "bible",
        "title": "Bible (HTML, gzip compressed)",
        "policy_id": "2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0",
        "manifest_tx_hash": "cfda418ddc84888ac39116ffba691a4f90b3232f4c2633cd56f102cfebda0ee4",
        "manifest_asset_name": "BIBLE_MANIFEST",  # Plain text
        "codec": "gzip",
        "content_type": "text/html",
        "pages_prefix": "BIBLE_P",
        "pages_total": 237,
        "seg": 32,
    },
    {
        "id": "bitcoin",
        "title": "Bitcoin Whitepaper",
        "policy_id": "8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1",
        "manifest_tx_hash": "2575347068f77b21cfe8d9c23d9082a68bfe4ef7ba7a96608af90515acbe228f",
        "manifest_asset_name": "BTCWP_MANIFEST",  # Plain text
        "codec": "none",
        "content_type": "text/plain",
    },
    # ── Example inline PNG scroll ───────────────────────────────────────────
    {
        "id": "hosky_example",
        "title": "Hosky PNG (inline datum)",
        "kind": "inline_png",
        "script_address": "addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn",
        "locked_txin": "728660515c6d9842d9f0ffd273f2b487a4070fd9f4bd5455a42e3a56880389be#0",
        "content_type": "image/png",
    }
]

BLOCKFROST_BASE = "https://cardano-mainnet.blockfrost.io/api/v0"


def get_cardano_socket() -> str:
    path = os.environ.get("CARDANO_NODE_SOCKET_PATH")
    if not path or not os.path.exists(path):
        raise RuntimeError(
            "CARDANO_NODE_SOCKET_PATH not set or invalid.\n"
            "Example: export CARDANO_NODE_SOCKET_PATH=/opt/cardano/cnode/sockets/node.socket"
        )
    return path


def cardano_cli(*args: str, json_output: bool = False) -> Any:
    socket = get_cardano_socket()
    cmd = ["cardano-cli", *args, "--mainnet", "--socket-path", socket]
    if json_output:
        cmd += ["--output-json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"cardano-cli error: {result.stderr.strip()}")
    return json.loads(result.stdout) if json_output else result.stdout


def fetch_registry_datum(custom_registry: Optional[Dict] = None) -> Dict:
    reg = custom_registry or DEFAULT_REGISTRY
    utxos = cardano_cli("utxo", "--address", reg["address"], json_output=True)
    target_asset = f"{reg['policy_id']}.{reg['asset_name_hex']}"
    for tx_in, info in utxos.items():
        assets = info.get("value", {})
        if target_asset in assets:
            datum = info.get("inline-datum") or info.get("inlineDatum")
            if datum and "bytes" in datum:
                compressed = bytes.fromhex(datum["bytes"])
                decompressed = zlib.decompress(compressed)
                return json.loads(decompressed)
    raise LookupError("Registry NFT UTxO with inline datum not found")


def get_scrolls(use_registry: bool = True, custom_registry: Optional[Dict] = None) -> List[Dict]:
    if not use_registry:
        return DEFAULT_SCROLLS.copy()
    try:
        data = fetch_registry_datum(custom_registry)
        scrolls = data.get("scrolls", [])
        return scrolls if scrolls else DEFAULT_SCROLLS.copy()
    except Exception as e:
        print(f"Registry fetch failed: {e}\n→ Using demo scrolls")
        return DEFAULT_SCROLLS.copy()


def fetch_tx_metadata_blockfrost(tx_hash: str, bf_key: str) -> Dict:
    url = f"{BLOCKFROST_BASE}/txs/{tx_hash}/metadata"
    headers = {"project_id": bf_key}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    metadata_list = r.json()
    return {item["label"]: item.get("json_metadata", {}) for item in metadata_list}


def fetch_policy_assets_blockfrost(policy_id: str, bf_key: str) -> List[Dict]:
    url = f"{BLOCKFROST_BASE}/assets/policy/{policy_id}"
    headers = {"project_id": bf_key}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def fetch_asset_blockfrost(asset_id: str, bf_key: str) -> Dict:
    url = f"{BLOCKFROST_BASE}/assets/{asset_id}"
    headers = {"project_id": bf_key}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def fetch_manifest(scroll: Dict, use_blockfrost: bool = True, bf_key: Optional[str] = None) -> Dict:
    if scroll.get("kind") == "inline_png":
        return {}  # manifest not used/needed

    tx_hash = scroll.get("manifest_tx_hash")
    if not tx_hash:
        raise ValueError(f"No manifest_tx_hash for {scroll.get('title', 'unknown')}")

    if not use_blockfrost or not bf_key:
        raise NotImplementedError("Pure local manifest fetch not implemented yet – use Blockfrost")

    metadata_dict = fetch_tx_metadata_blockfrost(tx_hash, bf_key)
    nft_data = metadata_dict.get("721", {})
    policy_data = nft_data.get(scroll["policy_id"], {})

    manifest_name = scroll.get("manifest_asset_name")
    if not manifest_name:
        raise ValueError("manifest_asset_name not defined for this scroll")

    manifest_data = policy_data.get(manifest_name, {})

    if not manifest_data:
        raise ValueError(
            f"Manifest not found in 721 metadata under "
            f"{scroll['policy_id']}/{manifest_name} (tx: {tx_hash})"
        )

    return manifest_data


def fetch_inline_datum_png(script_address: str, locked_txin: str) -> bytes:
    """
    Returns raw PNG bytes stored in inline datum at a script address UTxO.
    locked_txin format: "<txhash>#<ix>"
    """
    utxos = cardano_cli("utxo", "--address", script_address, json_output=True)

    if locked_txin not in utxos:
        raise LookupError(f"Locked UTxO not found: {locked_txin} at address {script_address}")

    info = utxos[locked_txin]
    datum = info.get("inlineDatum") or info.get("inline-datum") or info.get("inline_datum")
    if not datum or "bytes" not in datum:
        raise ValueError("No inline datum bytes found on that UTxO")

    return bytes.fromhex(datum["bytes"])


def reconstruct(scroll: Dict, manifest: Dict, bf_key: Optional[str] = None) -> Tuple[bytes, str]:
    kind = scroll.get("kind", "classic")

    if kind == "inline_png":
        if "script_address" not in scroll or "locked_txin" not in scroll:
            raise ValueError("inline_png scroll missing script_address or locked_txin")
        data = fetch_inline_datum_png(scroll["script_address"], scroll["locked_txin"])
        content_type = scroll.get("content_type", "image/png")
        return data, content_type

    # ── Classic multi-asset segmented reconstruction ────────────────────────
    if not bf_key:
        raise ValueError("Blockfrost key required for classic reconstruction")

    codec = scroll.get("codec", manifest.get("codec", "none"))
    content_type = scroll.get("content_type", manifest.get("content_type", "application/octet-stream"))

    full_data = bytearray()

    pages = manifest.get("pages", [])

    # Bible case: no explicit list → dynamically fetch from policy assets
    if not pages and "pages_prefix" in scroll and "pages_total" in scroll:
        print("Fetching all assets under policy for Bible...")
        all_assets = fetch_policy_assets_blockfrost(scroll["policy_id"], bf_key)
        prefix = scroll["pages_prefix"]
        filtered_assets = [a for a in all_assets if a["asset_name"].startswith(prefix)]
        filtered_assets = sorted(filtered_assets, key=lambda x: int(x["asset_name"].split('P')[-1]))
        if len(filtered_assets) != scroll["pages_total"]:
            raise ValueError(f"Expected {scroll['pages_total']} pages, found {len(filtered_assets)}")
        pages = filtered_assets

    if pages and isinstance(pages[0], str):
        pages = [{"asset_name": p, "mint_tx_hash": scroll["manifest_tx_hash"]} for p in pages]

    if not pages:
        raise ValueError("No pages defined in manifest")

    for page_idx, page_info in enumerate(pages, 1):
        if isinstance(page_info, dict):
            asset_name = page_info.get("asset_name")
            mint_tx = page_info.get("mint_tx_hash")
        else:
            asset_name = page_info
            mint_tx = scroll["manifest_tx_hash"]

        if not asset_name:
            raise ValueError(f"Invalid page entry at index {page_idx}: {page_info}")

        # For Bible: fetch mint tx if missing
        if mint_tx is None and scroll.get("id") == "bible":
            asset_hex = asset_name.encode('utf-8').hex().upper()
            asset_id = scroll["policy_id"] + asset_hex
            asset_data = fetch_asset_blockfrost(asset_id, bf_key)
            mint_tx = asset_data.get("mint_tx_hash")
            if not mint_tx:
                raise ValueError(f"Mint tx not found for Bible page '{asset_name}'")
            page_info["mint_tx_hash"] = mint_tx

        policy_id = scroll["policy_id"]
        metadata_dict = fetch_tx_metadata_blockfrost(mint_tx, bf_key)
        page_data = metadata_dict.get("721", {}).get(policy_id, {}).get(asset_name, {})

        if not page_data:
            raise ValueError(f"Page metadata not found for '{asset_name}' (tx: {mint_tx})")

        segments = page_data.get("payload", [])
        if not segments:
            raise ValueError(f"No payload segments for page '{asset_name}'")

        page_bytes = b""
        for seg_idx, seg in enumerate(segments):
            if not isinstance(seg, str) or not seg.strip():
                continue
            seg_clean = ''.join(c for c in seg.strip().removeprefix("0x") if c in '0123456789abcdefABCDEF')
            if not seg_clean or len(seg_clean) % 2 != 0:
                continue
            try:
                page_bytes += bytes.fromhex(seg_clean)
            except ValueError as hex_err:
                raise ValueError(f"Invalid hex in segment {seg_idx} of '{asset_name}': {hex_err}")

        if page_sha := page_data.get("sha"):
            calculated = hashlib.sha256(page_bytes).hexdigest()
            if calculated != page_sha:
                raise ValueError(f"Page hash mismatch for '{asset_name}'")

        full_data.extend(page_bytes)
        time.sleep(0.2)

    data = bytes(full_data)

    if codec == "gzip":
        try:
            data = zlib.decompress(data)
        except zlib.error as e:
            raise ValueError(f"Gzip decompression failed: {e}")

    if full_sha := manifest.get("sha_gz") or manifest.get("sha") or manifest.get("sha256"):
        calculated = hashlib.sha256(data).hexdigest()
        if calculated != full_sha:
            raise ValueError(f"Final hash mismatch (expected {full_sha}, got {calculated})")

    return data, content_type


if __name__ == "__main__":
    print("Available demo scrolls:")
    for s in get_scrolls(use_registry=False):
        print(f" • {s['title']}")