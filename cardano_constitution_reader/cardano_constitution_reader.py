#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
import time
import zlib
import subprocess
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_URL = "https://cardano-mainnet.blockfrost.io/api/v0"
DEFAULT_CONFIG_PATH = Path.home() / ".constitution_reader" / "config.json"

CONSTITUTIONS = {
    "608": {
        "name": "Cardano Constitution – Epoch 608 (current)",
        "policy_id": "ef91a425ef57d92db614085ef03718407fb293cb4b770bc6e03f9750",
        "expected_sha256": "98a29aec8664b62912c1c0355ebae1401b7c0e53d632e8f05479e7821935abf1",
        "ratified_epoch": 608,
        "enacted_epoch": 609,
        "blurb": "Current Constitution text (amended). Ratified at epoch 608 and enacted at epoch 609.",
    },
    "541": {
        "name": "Cardano Constitution – Epoch 541 (earlier ratification)",
        "policy_id": "d7559bbfa87f53674570fd01f564687c2954503b510ead009148a31d",
        "expected_sha256": "1939c1627e49b5267114cbdb195d4ac417e545544ba6dcb47e03c679439e9566",
        "ratified_epoch": 541,
        "enacted_epoch": 542,
        "blurb": "First ratified Constitution text (baseline governance framework). Ratified at epoch 541 and enacted at epoch 542.",
    },
}


BANNER = """
════════════════════════════════════════════════════════════
          𝐂 𝐀 𝐑 𝐃 𝐀 𝐍 𝐎  𝐂 𝐎 𝐍 𝐒 𝐓 𝐈 𝐓 𝐔 𝐓 𝐈 𝐎 𝐍  𝐑 𝐄 𝐀 𝐃 𝐄 𝐑
                Immutable On-Chain Governance Document
════════════════════════════════════════════════════════════
""".strip("\n")


ABOUT = (
    "The Cardano Constitution is the governance framework for the Cardano blockchain. "
    "It establishes rights and responsibilities of participants, defines governance processes "
    "and voting thresholds, and sets guardrails for protocol parameters and treasury withdrawals.\n"
    "\n"
    "This tool reconstructs the Constitution text from on-chain NFT page payloads (CIP-721 metadata) "
    "and verifies integrity with SHA-256."
)


def load_config(config_path: Path) -> dict:
    try:
        if config_path.exists():
            return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_config(config_path: Path, config: dict) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def http_get_json(url: str, headers: dict, timeout: int = 30) -> dict | list:
    req = Request(url, headers=headers, method="GET")
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)


def api_get(endpoint: str, project_id: str, params: dict | None = None, *, max_retries: int = 6) -> dict | list:
    qs = f"?{urlencode(params)}" if params else ""
    url = f"{BASE_URL}/{endpoint}{qs}"
    headers = {"project_id": project_id}

    backoff = 0.5
    for attempt in range(1, max_retries + 1):
        try:
            data = http_get_json(url, headers=headers)
            time.sleep(0.25)  # be gentle on free tier
            return data
        except HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="ignore")
            except Exception:
                pass

            # Rate limit or transient errors: retry with backoff
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                sleep_s = backoff * (2 ** (attempt - 1))
                print(f"  Blockfrost HTTP {e.code} (attempt {attempt}/{max_retries}) – retrying in {sleep_s:.1f}s...")
                time.sleep(sleep_s)
                continue

            raise Exception(f"Blockfrost error {e.code}: {body or e.reason}") from None
        except URLError as e:
            if attempt < max_retries:
                sleep_s = backoff * (2 ** (attempt - 1))
                print(f"  Network error (attempt {attempt}/{max_retries}) – retrying in {sleep_s:.1f}s...")
                time.sleep(sleep_s)
                continue
            raise Exception(f"Network error: {e}") from None

    raise Exception("Failed after retries (unexpected).")


def try_decode_asset_name(asset_name_hex: str) -> str:
    try:
        return bytes.fromhex(asset_name_hex).decode("utf-8", errors="ignore")
    except Exception:
        return asset_name_hex


def is_manifest_asset(asset_name_hex: str) -> bool:
    name = try_decode_asset_name(asset_name_hex).upper()
    # Keep simple and safe: skip obvious manifest-like assets
    if "MANIFEST" in name and "PAGE" not in name:
        return True
    if name.endswith("_MANIFEST"):
        return True
    return False


def extract_payload_hex_from_721(policy_id: str, asset_name_hex: str, metadata_list: list) -> tuple[int, str] | None:
    """
    Returns (page_index_i, payload_hex_string) if found, else None.
    """
    key_utf8 = try_decode_asset_name(asset_name_hex)
    key_hex_fallback = asset_name_hex

    for m in metadata_list:
        if str(m.get("label")) != "721":
            continue
        meta = m.get("json_metadata", {}) or {}
        if policy_id not in meta:
            continue

        asset_dict = meta.get(policy_id, {}) or {}

        # Some tools store the asset name as UTF-8, some as raw hex, some as dict keys with odd decoding.
        candidate_keys = [key_utf8, key_utf8.upper(), key_hex_fallback, key_hex_fallback.upper()]
        page_data = None
        for k in candidate_keys:
            if k in asset_dict:
                page_data = asset_dict[k]
                break
        if not isinstance(page_data, dict):
            continue

        if "i" not in page_data or "payload" not in page_data:
            continue

        i = page_data["i"]
        payload = page_data["payload"]

        hex_parts: list[str] = []

        if isinstance(payload, list):
            for p in payload:
                if isinstance(p, str):
                    hex_parts.append(p.replace("0x", "").strip())
                elif isinstance(p, dict) and "bytes" in p and isinstance(p["bytes"], str):
                    hex_parts.append(p["bytes"].replace("0x", "").strip())
        elif isinstance(payload, str):
            # Allow single-string payloads
            hex_parts.append(payload.replace("0x", "").strip())

        if not hex_parts:
            continue

        full_hex = "".join(hex_parts)
        if not full_hex:
            continue

        try:
            page_index = int(i)
        except Exception:
            continue

        return (page_index, full_hex)

    return None


def fetch_constitution_bytes(policy_id: str, project_id: str) -> bytes:
    print("  Querying assets under policy (paginated)...")
    all_assets: list[dict] = []
    page = 1

    while True:
        assets_page = api_get(f"assets/policy/{policy_id}", project_id, {"page": page, "count": 100})
        if not isinstance(assets_page, list):
            raise Exception("Unexpected API response while listing assets.")

        print(f"  Page {page}... ({len(assets_page)} items)")
        if not assets_page:
            break

        all_assets.extend(assets_page)
        if len(assets_page) < 100:
            break
        page += 1

    print(f"  Total assets under policy: {len(all_assets)}")

    pages: list[tuple[int, str]] = []

    for asset_info in all_assets:
        if asset_info.get("quantity") != "1":
            continue

        asset = asset_info.get("asset")
        if not asset or len(asset) <= 56:
            continue

        asset_name_hex = asset[56:]

        if is_manifest_asset(asset_name_hex):
            continue

        # Latest mint tx (prefer minted action)
        history = api_get(f"assets/{asset}/history", project_id, {"order": "desc", "count": 10})
        tx_hash = None
        if isinstance(history, list):
            for e in history:
                if e.get("action") == "minted" and e.get("tx_hash"):
                    tx_hash = e["tx_hash"]
                    break

        if not tx_hash:
            details = api_get(f"assets/{asset}", project_id)
            if isinstance(details, dict):
                tx_hash = details.get("initial_mint_tx_hash")

        if not tx_hash:
            continue

        metadata_list = api_get(f"txs/{tx_hash}/metadata", project_id)
        if not isinstance(metadata_list, list):
            continue

        extracted = extract_payload_hex_from_721(policy_id, asset_name_hex, metadata_list)
        if extracted:
            pages.append(extracted)

    if not pages:
        raise Exception("No valid page NFTs found under this policy.")

    pages.sort(key=lambda x: x[0])
    total_hex = "".join(h for _, h in pages)

    try:
        data = bytes.fromhex(total_hex)
    except ValueError:
        raise Exception("Reconstruction failed: payload hex was invalid.") from None

    # gzip magic bytes
    if data[:2] == b"\x1f\x8b":
        print("  Detected gzip compression – decompressing...")
        try:
            data = zlib.decompress(data, 16 + zlib.MAX_WBITS)
        except zlib.error:
            raise Exception("Gzip decompression failed (data corrupted or not actually gzip).") from None

    return data


def is_wsl() -> bool:
    """Detect if running inside WSL (Windows Subsystem for Linux)."""
    if os.getenv("WSL_DISTRO_NAME") or os.getenv("WSL_INTEROP"):
        return True
    try:
        with open("/proc/sys/kernel/osrelease", "r", encoding="utf-8") as f:
            s = f.read().lower()
        return ("microsoft" in s) or ("wsl" in s)
    except Exception:
        return False


def wsl_to_windows_path(path: Path) -> str | None:
    """Convert a Linux path to a Windows path when running under WSL."""
    try:
        out = subprocess.check_output(["wslpath", "-w", str(path)], text=True).strip()
        return out or None
    except Exception:
        return None


def open_text_file(path: Path) -> None:
    """Best-effort: open the file in a user-friendly way on the current OS."""
    try:
        if sys.platform.startswith("win"):
            subprocess.Popen(["notepad.exe", str(path)])
            return
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
            return
        subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        print(f"Could not automatically open the file. It's located here:\n  {path}")


def resolve_api_key(args, config: dict) -> str | None:
    # Priority: CLI -> env -> config
    if args.api_key:
        return args.api_key.strip()

    env_key = os.getenv("BLOCKFROST_PROJECT_ID") or os.getenv("BLOCKFROST_API_KEY")
    if env_key:
        return env_key.strip()

    saved = config.get("blockfrost_api_key")
    if saved:
        return str(saved).strip()

    return None


def main():
    parser = argparse.ArgumentParser(description="Fetch & verify Cardano Constitution from on-chain NFTs via Blockfrost.")
    parser.add_argument("--epoch", choices=sorted(CONSTITUTIONS.keys()), help="Which constitution version to fetch (541 or 608).")
    parser.add_argument("--api-key", help="Blockfrost Mainnet API key (or set env BLOCKFROST_PROJECT_ID).")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Config path (default: ~/.constitution_reader/config.json)")
    parser.add_argument("--out-dir", default=str(Path(__file__).resolve().parent), help="Where to save output files (default: alongside this script).")
    parser.add_argument("--no-save-key", action="store_true", help="Do not persist API key to config.")
    parser.add_argument("--non-interactive", action="store_true", help="Fail instead of prompting for missing values.")
    parser.add_argument("--open", action="store_true", help="Open the downloaded file after saving.")
    parser.add_argument("--no-open", action="store_true", help="Do not prompt to open the file.")
    args = parser.parse_args()

    print("\n" + BANNER + "\n")
    print(ABOUT + "\n")

    config_path = Path(args.config).expanduser()
    config = load_config(config_path)

    api_key = resolve_api_key(args, config)

    # Prompt for API key if missing
    if not api_key:
        if args.non_interactive:
            print("Error: Missing API key. Provide --api-key or set BLOCKFROST_PROJECT_ID.")
            sys.exit(1)
        print("No API key found (CLI/env/config).")
        print("A Blockfrost key is required to query the on-chain metadata.")
        print("Get a free key at https://blockfrost.io (sign up → create a Cardano MAINNET project → copy the project_id starting with \"mainnet\").")
        print("Note: The free tier is typically sufficient; this script rate-limits and paginates requests.")
        api_key = input("Paste your Blockfrost Mainnet API key (mainnet...): ").strip()

    if not api_key.startswith("mainnet"):
        print("Error: Blockfrost key should start with 'mainnet...'.")
        sys.exit(1)

    # Save key (unless disabled)
    if (not args.no_save_key) and (config.get("blockfrost_api_key") != api_key):
        config["blockfrost_api_key"] = api_key
        save_config(config_path, config)
        print(f"API key saved to: {config_path}")

    # Choose epoch
    epoch = args.epoch
    if not epoch:
        if args.non_interactive:
            print("Error: Missing --epoch (541 or 608).")
            sys.exit(1)
        print("\nAvailable versions:")
        for k in sorted(CONSTITUTIONS.keys(), key=lambda x: int(x), reverse=True):
            v = CONSTITUTIONS[k]
            rat = v.get("ratified_epoch")
            en = v.get("enacted_epoch")
            extra = f" (ratified {rat}, enacted {en})" if rat and en else ""
            print(f"  {k} → {v['name']}{extra}")
            if v.get("blurb"):
                print(f"      - {v['blurb']}")
        epoch = input("\nEnter epoch number (541 or 608): ").strip()

    if epoch not in CONSTITUTIONS:
        print("Invalid epoch. Use 541 or 608.")
        sys.exit(1)

    conf = CONSTITUTIONS[epoch]
    print(f"\nFetching: {conf['name']}")
    print(f"Policy: {conf['policy_id']}")

    try:
        raw_bytes = fetch_constitution_bytes(conf["policy_id"], api_key)

        computed_hash = hashlib.sha256(raw_bytes).hexdigest()
        print(f"\nComputed SHA256: {computed_hash}")

        if computed_hash == conf["expected_sha256"]:
            print("✓ Integrity verified – matches published hash")
        else:
            print("⚠ Hash mismatch! Possible reconstruction issue.")
            print(f"Expected: {conf['expected_sha256']}")
            sys.exit(1)

        filename = f"Cardano_Constitution_Epoch_{epoch}.txt"
        out_dir = Path(args.out_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = (out_dir / filename).resolve()
        out_path.write_bytes(raw_bytes)

        print("\nSuccessfully saved immutable document:")
        print(f"  → {out_path}")
        print(f"  Size: {len(raw_bytes):,} bytes")
        print(f"  SHA256: {computed_hash}")

        print("\nTip: open it later with:")
        if is_wsl():
            win_path = wsl_to_windows_path(out_path)
            if win_path:
                print(f'  notepad.exe "{win_path}"')
            else:
                print("  explorer.exe .")
        elif sys.platform.startswith("win"):
            print(f'  notepad "{out_path}"')
        elif sys.platform == "darwin":
            print(f'  open "{out_path}"')
        else:
            print(f'  xdg-open "{out_path}"')

        if not args.no_open:
            choice = "y" if args.open else (input("\nOpen the file now? (Y/n): ").strip().lower() or "y")
            if choice.startswith("y"):
                open_text_file(out_path)


    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

    print("\n" + "═" * 60)


if __name__ == "__main__":
    main()
