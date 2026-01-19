import os
import json
import zlib
import hashlib
import subprocess
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
        "codec": "gzip",
        "content_type": "text/html",
    },
    {
        "id": "bitcoin",
        "title": "Bitcoin Whitepaper",
        "policy_id": "8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1",
        "manifest_tx_hash": "2575347068f77b21cfe8d9c23d9082a68bfe4ef7ba7a96608af90515acbe228f",
        "codec": "none",
        "content_type": "text/plain",
    },
]

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
            datum = info.get("inline-datum")
            if datum and "bytes" in datum:
                compressed = bytes.fromhex(datum["bytes"])
                try:
                    decompressed = zlib.decompress(compressed)
                    return json.loads(decompressed)
                except Exception as e:
                    raise ValueError(f"Failed to decompress/gunzip registry datum: {e}")

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


def fetch_manifest(scroll: Dict, use_blockfrost: bool = False, bf_key: Optional[str] = None) -> Dict:
    tx_hash = scroll.get("manifest_tx_hash")
    if not tx_hash:
        raise ValueError(f"No manifest_tx_hash for scroll: {scroll.get('title')}")

    if use_blockfrost and bf_key:
        # Simple Blockfrost fallback – you can expand this
        url = f"https://cardano-mainnet.blockfrost.io/api/v0/txs/{tx_hash}/metadata"
        headers = {"project_id": bf_key}
        import requests
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        metadata = r.json()
    else:
        # Try to get tx metadata via cardano-cli (limited – needs tx view or extension)
        # For many cases you'll need Ogmios / Blockfrost here in practice
        tx_view = cardano_cli("transaction", "view", "--tx-file", tx_hash)  # placeholder
        # Real implementation usually needs Ogmios query or Blockfrost
        raise NotImplementedError("Local manifest fetch via cardano-cli only is limited → use Blockfrost fallback or Ogmios")

    # Typical 721 metadata structure – adapt to actual on-chain format
    label_721 = next((v for k,v in metadata if k in ("721", "721")), {})
    policy_data = label_721.get(scroll["policy_id"], {})
    manifest_name = scroll.get("manifest_asset_name_hex", "manifest")
    manifest_data = policy_data.get(manifest_name, {})

    return manifest_data


def reconstruct(scroll: Dict, manifest: Dict) -> Tuple[bytes, str]:
    pages_order = manifest.get("pages", [])           # list of asset_name_hex
    codec = scroll.get("codec", manifest.get("codec", "none"))
    content_type = scroll.get("content_type", manifest.get("content_type", "application/octet-stream"))

    full_data = bytearray()

    for page_idx, asset_hex in enumerate(pages_order, 1):
        # TODO: Implement page fetch (similar to manifest)
        # You will need:
        # 1. asset's mint tx hash (from manifest or separate registry field)
        # 2. fetch metadata of that tx
        # 3. extract payload segments
        # 4. concat segments → verify sha per page
        raise NotImplementedError("Page fetching & segment concatenation – coming next")

    data = bytes(full_data)

    if codec == "gzip":
        data = zlib.decompress(data)

    # Optional full hash verification
    if full_sha := manifest.get("sha256"):
        if hashlib.sha256(data).hexdigest() != full_sha:
            raise ValueError("Final document hash mismatch")

    return data, content_type


# Quick test helper
if __name__ == "__main__":
    print("Available demo scrolls:")
    for s in get_scrolls(use_registry=False):
        print(f"  • {s['title']}")
