import os
import json
import zlib
import hashlib
import subprocess
import requests
from typing import Dict, List, Any, Tuple, Optional
from hexbytes import HexBytes

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
        "manifest_asset_name_hex": "4d414e4946455354",  # example hex for "MANIFEST" - adjust if known
        "codec": "gzip",
        "content_type": "text/html",
    },
    {
        "id": "bitcoin",
        "title": "Bitcoin Whitepaper",
        "policy_id": "8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1",
        "manifest_tx_hash": "2575347068f77b21cfe8d9c23d9082a68bfe4ef7ba7a96608af90515acbe228f",
        "manifest_asset_name_hex": "4d414e4946455354",  # adjust if known
        "codec": "none",
        "content_type": "text/plain",
    },
]

BLOCKFROST_BASE = "https://cardano-mainnet.blockfrost.io/api/v0"

def get_cardano_socket() -> str:
    path = os.environ.get("CARDANO_NODE_SOCKET_PATH")
    if not path or not os.path.exists(path):
        raise RuntimeError(
            "CARDANO_NODE_SOCKET_PATH not set or socket file not found.\n"
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
        raise RuntimeError(f"cardano-cli failed:\n{result.stderr.strip()}")
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
                try:
                    decompressed = zlib.decompress(compressed)
                    return json.loads(decompressed)
                except Exception as e:
                    raise ValueError(f"Failed to decompress registry datum: {e}")
    raise LookupError("Could not find registry NFT UTxO with inline datum")

def get_scrolls(use_registry: bool = True, custom_registry: Optional[Dict] = None) -> List[Dict]:
    if not use_registry:
        return DEFAULT_SCROLLS.copy()
    try:
        data = fetch_registry_datum(custom_registry)
        scrolls = data.get("scrolls", [])
        if not scrolls:
            print("Warning: registry empty → falling back to demo scrolls")
            return DEFAULT_SCROLLS.copy()
        return scrolls
    except Exception as e:
        print(f"Registry fetch failed: {e}\nUsing demo scrolls instead.")
        return DEFAULT_SCROLLS.copy()

def fetch_tx_metadata_blockfrost(tx_hash: str, bf_key: str) -> Dict:
    url = f"{BLOCKFROST_BASE}/txs/{tx_hash}/metadata"
    headers = {"project_id": bf_key}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()

def fetch_manifest(scroll: Dict, use_blockfrost: bool = True, bf_key: Optional[str] = None) -> Dict:
    tx_hash = scroll.get("manifest_tx_hash")
    if not tx_hash:
        raise ValueError(f"No manifest_tx_hash for scroll: {scroll.get('title')}")

    if not use_blockfrost or not bf_key:
        raise NotImplementedError("Local-only manifest fetch not yet implemented → enable Blockfrost")

    metadata_list = fetch_tx_metadata_blockfrost(tx_hash, bf_key)

    # Blockfrost returns array of {"label": "...", "json_metadata": {...}}
    metadata_dict = {item["label"]: item.get("json_metadata", {}) for item in metadata_list}

    nft_data = metadata_dict.get("721", {})
    policy_data = nft_data.get(scroll["policy_id"], {})
    manifest_name = scroll.get("manifest_asset_name_hex", "manifest")
    manifest_data = policy_data.get(manifest_name, {})

    if not manifest_data:
        raise ValueError(f"Manifest data not found under 721/{scroll['policy_id']}/{manifest_name}")

    return manifest_data

def fetch_page_metadata(page_tx_hash: str, bf_key: str) -> Dict:
    # Same as manifest - assumes page metadata is in mint tx's 721 label
    metadata_list = fetch_tx_metadata_blockfrost(page_tx_hash, bf_key)
    metadata_dict = {item["label"]: item.get("json_metadata", {}) for item in metadata_list}
    return metadata_dict.get("721", {})

def reconstruct(scroll: Dict, manifest: Dict, bf_key: Optional[str] = None) -> Tuple[bytes, str]:
    if not bf_key:
        raise ValueError("Blockfrost key required for page reconstruction")

    pages_order = manifest.get("pages", [])  # list of {"asset_name_hex": "...", "mint_tx_hash": "..."} or just hex strings
    codec = scroll.get("codec", manifest.get("codec", "none"))
    content_type = scroll.get("content_type", manifest.get("content_type", "application/octet-stream"))

    full_data = bytearray()

    for page in pages_order:
        # Flexible: page can be str (asset hex) or dict with mint_tx_hash
        if isinstance(page, str):
            asset_hex = page
            mint_tx = None  # would need lookup → fallback to Blockfrost asset endpoint later
        else:
            asset_hex = page.get("asset_name_hex")
            mint_tx = page.get("mint_tx_hash")

        if not asset_hex:
            raise ValueError("Invalid page format in manifest")

        if not mint_tx:
            raise NotImplementedError("Page mint tx hash missing - add to manifest or implement asset lookup")

        policy_id = scroll["policy_id"]
        page_metadata = fetch_page_metadata(mint_tx, bf_key)
        page_data = page_metadata.get(policy_id, {}).get(asset_hex, {})

        # Extract payload segments (assume list of hex strings)
        segments = page_data.get("payload", [])
        page_bytes = b"".join(bytes.fromhex(seg) for seg in segments if isinstance(seg, str))

        # Per-page hash verification
        if page_sha := page_data.get("sha"):
            if hashlib.sha256(page_bytes).hexdigest() != page_sha:
                raise ValueError(f"Page hash mismatch for {asset_hex}")

        full_data.extend(page_bytes)

    data = bytes(full_data)

    if codec == "gzip":
        try:
            data = zlib.decompress(data)
        except zlib.error as e:
            raise ValueError(f"Gzip decompression failed: {e}")

    # Full document verification
    if full_sha := manifest.get("sha") or manifest.get("sha256"):
        if hashlib.sha256(data).hexdigest() != full_sha:
            raise ValueError("Final document hash mismatch")

    return data, content_type

# Quick test helper
if __name__ == "__main__":
    print("Available demo scrolls:")
    for s in get_scrolls(use_registry=False):
        print(f" • {s['title']}")
