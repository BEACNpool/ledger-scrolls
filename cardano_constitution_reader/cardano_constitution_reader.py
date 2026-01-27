#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
import time
import zlib
import subprocess
import socket
import re
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
          𝐂 𝐀 𝐑 𝐃 𝐀 𝐍 𝐎  𝐂 𝐎  𝐒 𝐓 𝐈 𝐓 𝐔 𝐓 𝐈 𝐎 𝐍  𝐑 𝐄 𝐀 𝐃 𝐄 𝐑
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

# ---------------------------
# FAST MODE (mints file) helpers
# ---------------------------

HEX64_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


def _looks_like_txhash(s: str) -> bool:
    return isinstance(s, str) and bool(HEX64_RE.match(s.strip()))


def extract_page_payload_any_asset(policy_id: str, metadata_list: list) -> tuple[int, str] | None:
    """
    Extract the first {i,payload} found under the given policy_id in a CIP-721 label.
    This avoids needing the exact asset name key when we already know the page's mint tx.
    Returns (page_index_i, payload_hex_string).
    """
    for m in metadata_list:
        if str(m.get("label")) != "721":
            continue

        meta = m.get("json_metadata", {}) or {}
        policy_bucket = meta.get(policy_id)
        if not isinstance(policy_bucket, dict):
            continue

        for _asset_key, page_data in policy_bucket.items():
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
                    elif isinstance(p, dict) and isinstance(p.get("bytes"), str):
                        hex_parts.append(p["bytes"].replace("0x", "").strip())
            elif isinstance(payload, str):
                hex_parts.append(payload.replace("0x", "").strip())

            full_hex = "".join(hex_parts).strip()
            if not full_hex:
                continue

            try:
                page_index = int(i)
            except Exception:
                continue

            return (page_index, full_hex)

    return None


def load_mints_file(path: Path) -> tuple[str | None, dict[int, str]]:
    """
    Tolerant parser for constitution_epoch_XXX_mints.json produced by discover_constitution_mints.py.
    Returns (manifest_tx_or_None, {page_index: page_mint_tx}).
    """
    obj = json.loads(path.read_text(encoding="utf-8"))
    manifest_tx = None
    pages: dict[int, str] = {}

    def walk(x):
        nonlocal manifest_tx, pages
        if isinstance(x, dict):
            # manifest keys (try a few common variants)
            for k in ("manifest_mint_tx", "manifest_tx", "manifestMintTx", "manifestTx", "manifest_mint"):
                v = x.get(k)
                if _looks_like_txhash(v):
                    manifest_tx = v.strip()

            # common list form: {"pages":[{"page":1,"tx":"..."}, ...]}
            if isinstance(x.get("pages"), list):
                for item in x["pages"]:
                    if isinstance(item, dict):
                        p = item.get("page") or item.get("i") or item.get("index")
                        tx = item.get("tx") or item.get("tx_hash") or item.get("txhash")
                        if p is not None and tx and _looks_like_txhash(tx):
                            try:
                                pages[int(p)] = tx.strip()
                            except Exception:
                                pass

            # common map form: {"PAGE001":{"tx_hash":"...","i":1}, ...}
            for k, v in x.items():
                m = re.search(r"PAGE\s*0*(\d+)", str(k), re.IGNORECASE)
                if m and isinstance(v, dict):
                    pnum = int(m.group(1))
                    tx = v.get("tx") or v.get("tx_hash") or v.get("txhash")
                    if tx and _looks_like_txhash(tx):
                        pages[pnum] = tx.strip()

                walk(v)

        elif isinstance(x, list):
            for item in x:
                walk(item)

    walk(obj)

    return manifest_tx, pages


def fetch_constitution_bytes_fast(policy_id: str, project_id: str, page_mint_txs: dict[int, str]) -> bytes:
    """
    Fast path: use known mint tx hashes (from mints file) to fetch tx metadata directly.
    """
    if not page_mint_txs:
        raise Exception("Fast mode requested but no page tx hashes were found in the mints file.")

    pages: list[tuple[int, str]] = []
    ordered_pages = sorted(page_mint_txs.keys())

    print(f"  Fast mode: fetching metadata for {len(ordered_pages)} page txs...", flush=True)

    for idx, page_i in enumerate(ordered_pages, start=1):
        tx = page_mint_txs[page_i]
        print(f"  Page {page_i:03d} ({idx}/{len(ordered_pages)}): tx {tx[:8]}…", flush=True)

        metadata_list = api_get(f"txs/{tx}/metadata", project_id)
        if not isinstance(metadata_list, list):
            raise Exception(f"Unexpected metadata response for tx {tx}")

        extracted = extract_page_payload_any_asset(policy_id, metadata_list)
        if not extracted:
            raise Exception(f"Could not find 721 payload in tx {tx} for page {page_i}")

        i_found, payload_hex = extracted
        pages.append((i_found, payload_hex))

    pages.sort(key=lambda x: x[0])
    total_hex = "".join(h for _, h in pages)

    try:
        data = bytes.fromhex(total_hex)
    except ValueError:
        raise Exception("Reconstruction failed: payload hex was invalid.") from None

    if data[:2] == b"\x1f\x8b":
        print("  Detected gzip compression – decompressing...", flush=True)
        try:
            data = zlib.decompress(data, 16 + zlib.MAX_WBITS)
        except zlib.error:
            raise Exception("Gzip decompression failed (data corrupted or not actually gzip).") from None

    return data


# ---------------------------
# config + http helpers
# ---------------------------

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


def http_get_json(url: str, headers: dict, timeout: int = 20) -> dict | list:
    req = Request(url, headers=headers, method="GET")
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)


def api_get(endpoint: str, project_id: str, params: dict | None = None, *, max_retries: int = 6) -> dict | list:
    qs = f"?{urlencode(params)}" if params else ""
    url = f"{BASE_URL}/{endpoint}{qs}"
    headers = {"project_id": project_id}

    backoff = 0.75
    for attempt in range(1, max_retries + 1):
        try:
            data = http_get_json(url, headers=headers, timeout=20)
            time.sleep(0.25)  # be gentle on free tier
            return data

        except HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="ignore")
            except Exception:
                pass

            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                sleep_s = backoff * (2 ** (attempt - 1))
                print(
                    f"  Blockfrost HTTP {e.code} (attempt {attempt}/{max_retries}) – retrying in {sleep_s:.1f}s...",
                    flush=True
                )
                time.sleep(sleep_s)
                continue

            raise Exception(f"Blockfrost error {e.code}: {body or e.reason}") from None

        except (URLError, socket.timeout, TimeoutError) as e:
            if attempt < max_retries:
                sleep_s = backoff * (2 ** (attempt - 1))
                print(
                    f"  Network/timeout error (attempt {attempt}/{max_retries}) – retrying in {sleep_s:.1f}s...",
                    flush=True
                )
                time.sleep(sleep_s)
                continue
            raise Exception(f"Network/timeout error: {e}") from None

    raise Exception("Failed after retries (unexpected).")


# ---------------------------
# legacy (scan policy) helpers
# ---------------------------

def try_decode_asset_name(asset_name_hex: str) -> str:
    try:
        return bytes.fromhex(asset_name_hex).decode("utf-8", errors="ignore")
    except Exception:
        return asset_name_hex


def is_manifest_asset(asset_name_hex: str) -> bool:
    name = try_decode_asset_name(asset_name_hex).upper()
    if "MANIFEST" in name and "PAGE" not in name:
        return True
    if name.endswith("_MANIFEST"):
        return True
    return False


def extract_payload_hex_from_721(policy_id: str, asset_name_hex: str, metadata_list: list) -> tuple[int, str] | None:
    key_utf8 = try_decode_asset_name(asset_name_hex)
    key_hex_fallback = asset_name_hex

    for m in metadata_list:
        if str(m.get("label")) != "721":
            continue
        meta = m.get("json_metadata", {}) or {}
        if policy_id not in meta:
            continue

        asset_dict = meta.get(policy_id, {}) or {}
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
            hex_parts.append(payload.replace("0x", "").strip())

        if not hex_parts:
            continue

        full_hex = "".join(hex_parts).strip()
        if not full_hex:
            continue

        try:
            page_index = int(i)
        except Exception:
            continue

        return (page_index, full_hex)

    return None


def fetch_constitution_bytes(policy_id: str, project_id: str) -> bytes:
    print("  Querying assets under policy (paginated)...", flush=True)
    all_assets: list[dict] = []
    page = 1

    while True:
        assets_page = api_get(f"assets/policy/{policy_id}", project_id, {"page": page, "count": 100})
        if not isinstance(assets_page, list):
            raise Exception("Unexpected API response while listing assets.")

        print(f"  Page {page}... ({len(assets_page)} items)", flush=True)
        if not assets_page:
            break

        all_assets.extend(assets_page)
        if len(assets_page) < 100:
            break
        page += 1

    print(f"  Total assets under policy: {len(all_assets)}", flush=True)
    print("  Reconstructing pages (this can take ~10–60s on free tier)...", flush=True)

    pages: list[tuple[int, str]] = []
    total = len(all_assets)

    for idx, asset_info in enumerate(all_assets, start=1):
        if asset_info.get("quantity") != "1":
            continue

        asset = asset_info.get("asset")
        if not asset or len(asset) <= 56:
            continue

        asset_name_hex = asset[56:]
        if is_manifest_asset(asset_name_hex):
            continue

        pretty_name = try_decode_asset_name(asset_name_hex).strip()
        pretty_name = pretty_name if pretty_name else asset_name_hex
        print(f"  Processing asset {idx}/{total}: {pretty_name}", flush=True)

        tx_hash = None
        details = api_get(f"assets/{asset}", project_id)
        if isinstance(details, dict):
            tx_hash = details.get("initial_mint_tx_hash")

        if not tx_hash:
            history = api_get(f"assets/{asset}/history", project_id, {"order": "asc", "count": 50})
            if isinstance(history, list):
                for e in history:
                    if e.get("action") == "minted" and e.get("tx_hash"):
                        tx_hash = e["tx_hash"]
                        break

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

    if data[:2] == b"\x1f\x8b":
        print("  Detected gzip compression – decompressing...", flush=True)
        try:
            data = zlib.decompress(data, 16 + zlib.MAX_WBITS)
        except zlib.error:
            raise Exception("Gzip decompression failed (data corrupted or not actually gzip).") from None

    return data


# ---------------------------
# OS helpers
# ---------------------------

def is_wsl() -> bool:
    if os.getenv("WSL_DISTRO_NAME") or os.getenv("WSL_INTEROP"):
        return True
    try:
        with open("/proc/sys/kernel/osrelease", "r", encoding="utf-8") as f:
            s = f.read().lower()
        return ("microsoft" in s) or ("wsl" in s)
    except Exception:
        return False


def wsl_to_windows_path(path: Path) -> str | None:
    try:
        out = subprocess.check_output(["wslpath", "-w", str(path)], text=True).strip()
        return out or None
    except Exception:
        return None


def open_text_file(path: Path) -> None:
    try:
        if is_wsl():
            win_path = wsl_to_windows_path(path)
            if win_path:
                if win_path.startswith("\\\\"):
                    subprocess.Popen(["explorer.exe", win_path])
                else:
                    subprocess.Popen(["notepad.exe", win_path])
                return
            subprocess.Popen(["explorer.exe", "."])
            return

        if sys.platform.startswith("win"):
            subprocess.Popen(["notepad.exe", str(path)])
            return

        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
            return

        subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        print(f"Could not automatically open the file. It's located here:\n  {path}", flush=True)


def resolve_api_key(args, config: dict) -> str | None:
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
    parser.add_argument("--mints-file", help="Path to constitution_epoch_XXX_mints.json (enables fast mode).")
    args = parser.parse_args()

    print("\n" + BANNER + "\n")
    print(ABOUT + "\n")

    config_path = Path(args.config).expanduser()
    config = load_config(config_path)

    api_key = resolve_api_key(args, config)

    if not api_key:
        if args.non_interactive:
            print("Error: Missing API key. Provide --api-key or set BLOCKFROST_PROJECT_ID.")
            sys.exit(1)
        print("No API key found (CLI/env/config).")
        print("A Blockfrost key is required to query the on-chain metadata.")
        print('Get a free key at https://blockfrost.io (sign up → create a Cardano MAINNET project → copy the project_id starting with "mainnet").')
        print("Note: Free tier is typically sufficient; this script rate-limits and paginates requests.")
        api_key = input("Paste your Blockfrost Mainnet API key (mainnet...): ").strip()

    if not api_key.startswith("mainnet"):
        print("Error: Blockfrost key should start with 'mainnet...'.")
        sys.exit(1)

    if (not args.no_save_key) and (config.get("blockfrost_api_key") != api_key):
        config["blockfrost_api_key"] = api_key
        save_config(config_path, config)
        print(f"API key saved to: {config_path}", flush=True)

    epoch = args.epoch
    if not epoch:
        if args.non_interactive:
            print("Error: Missing --epoch (541 or 608).")
            sys.exit(1)
        print("\nAvailable versions:")
        for k in sorted(CONSTITUTIONS.keys(), key=lambda x: int(x), reverse=True):
            v = CONSTITUTIONS[k]
            extra = f" (ratified {v['ratified_epoch']}, enacted {v['enacted_epoch']})"
            print(f"  {k} → {v['name']}{extra}")
            print(f"      - {v['blurb']}")
        epoch = input("\nEnter epoch number (541 or 608): ").strip()

    if epoch not in CONSTITUTIONS:
        print("Invalid epoch. Use 541 or 608.")
        sys.exit(1)

    conf = CONSTITUTIONS[epoch]
    print(f"\nFetching: {conf['name']}", flush=True)
    print(f"Policy: {conf['policy_id']}", flush=True)

    try:
        # ---- FAST MODE selection ----
        mints_file: Path | None = None
        if args.mints_file:
            mints_file = Path(args.mints_file).expanduser()
        else:
            # auto-detect next to script
            candidate = Path(__file__).resolve().parent / f"constitution_epoch_{epoch}_mints.json"
            if candidate.exists():
                mints_file = candidate

        if mints_file and mints_file.exists():
            print(f"  Using mints file: {mints_file}", flush=True)
            manifest_tx, page_map = load_mints_file(mints_file)
            if manifest_tx:
                print(f"  Manifest mint tx: {manifest_tx}", flush=True)
            raw_bytes = fetch_constitution_bytes_fast(conf["policy_id"], api_key, page_map)
        else:
            raw_bytes = fetch_constitution_bytes(conf["policy_id"], api_key)

        computed_hash = hashlib.sha256(raw_bytes).hexdigest()
        print(f"\nComputed SHA256: {computed_hash}", flush=True)

        if computed_hash == conf["expected_sha256"]:
            print("✓ Integrity verified – matches published hash", flush=True)
        else:
            print("⚠ Hash mismatch! Possible reconstruction issue.", flush=True)
            print(f"Expected: {conf['expected_sha256']}", flush=True)
            sys.exit(1)

        filename = f"Cardano_Constitution_Epoch_{epoch}.txt"
        out_dir = Path(args.out_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = (out_dir / filename).resolve()
        out_path.write_bytes(raw_bytes)

        print("\nSuccessfully saved immutable document:", flush=True)
        print(f"  → {out_path}", flush=True)
        print(f"  Size: {len(raw_bytes):,} bytes", flush=True)
        print(f"  SHA256: {computed_hash}", flush=True)

        print("\nTip: open it later with:", flush=True)
        if is_wsl():
            win_path = wsl_to_windows_path(out_path)
            if win_path:
                print(f'  notepad.exe "{win_path}"', flush=True)
            else:
                print("  explorer.exe .", flush=True)
        elif sys.platform.startswith("win"):
            print(f'  notepad "{out_path}"', flush=True)
        elif sys.platform == "darwin":
            print(f'  open "{out_path}"', flush=True)
        else:
            print(f'  xdg-open "{out_path}"', flush=True)

        if not args.no_open:
            choice = "y" if args.open else (input("\nOpen the file now? (Y/n): ").strip().lower() or "y")
            if choice.startswith("y"):
                open_text_file(out_path)

    except Exception as e:
        print(f"\nError: {e}", flush=True)
        sys.exit(1)

    print("\n" + "═" * 60, flush=True)


if __name__ == "__main__":
    main()
