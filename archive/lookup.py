#!/usr/bin/env python3
"""BEACN archive lookup: pick any Ledger Scroll or BEACN mint and get it straight from Cardano.

Nothing here talks to BEACN. Scrolls are rebuilt with the open `lsview` reader in
koios-viewer/, and NFT art is decoded from its own on-chain metadata through the free
public Koios API. Python 3.8+ standard library only.

    python3 archive/lookup.py                 # menu: pick an item, get the command
    python3 archive/lookup.py --list          # every item and its id
    python3 archive/lookup.py bible           # print the copy-paste command for one item
    python3 archive/lookup.py get beacn-sigil # fetch it now into the current folder
"""
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
KOIOS = os.environ.get("KOIOS_BASE", "https://api.koios.rest/api/v1").rstrip("/")
EXT = {"image/svg+xml": "svg", "image/png": "png", "image/webp": "webp", "image/avif": "avif", "image/gif": "gif",
       "image/jpeg": "jpg", "text/html": "html", "text/plain": "txt", "audio/wav": "wav", "audio/mpeg": "mp3"}


def load_catalog():
    with open(os.path.join(HERE, "catalog.json"), encoding="utf-8") as f:
        return json.load(f)


def command_for(item):
    return f"python3 archive/lookup.py get {item['id']}"


def koios_post(path, body):
    req = urllib.request.Request(f"{KOIOS}/{path}", data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", "accept": "application/json",
                                          "user-agent": "beacn-archive-lookup"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def decode_data_uri(uri):
    m = re.match(r"data:([^;,]+)((?:;[^;,]*)*),(.*)", uri, re.S)
    if not m:
        return None, None
    mime, params, payload = m.groups()
    raw = base64.b64decode(payload) if "base64" in params else urllib.parse.unquote_to_bytes(payload)
    return mime, raw


def joined(value):
    return "".join(value) if isinstance(value, list) else (value or "")


def save(path, data):
    with open(path, "wb") as f:
        f.write(data)
    print(f"  saved {path}  ({len(data):,} bytes, sha256 {hashlib.sha256(data).hexdigest()})")


def get_nft(item, outdir):
    rows = koios_post("asset_info", {"_asset_list": [[item["policy"], item["asset_hex"]]]})
    if not rows:
        sys.exit(f"Koios has no asset {item['policy']}.{item['asset_hex']}")
    a = rows[0]
    meta = (a.get("minting_tx_metadata") or {}).get("721") or {}
    per_policy = meta.get(item["policy"]) or {}
    md = per_policy.get(a.get("asset_name_ascii") or "") or per_policy.get(item["asset_hex"]) or {}
    print(f"{item['title']}  ·  {a.get('fingerprint')}  ·  minted in tx {a.get('minting_tx_hash')}")
    if md.get("description"):
        print("  " + joined(md["description"])[:200])
    saved = 0
    image = joined(md.get("image"))
    if image.startswith("data:"):
        mime, raw = decode_data_uri(image)
        if raw:
            save(os.path.join(outdir, f"{item['id']}.{EXT.get(mime, 'bin')}"), raw)
            saved += 1
    elif image:
        print(f"  image is stored off chain at {image}")
    for n, f in enumerate(md.get("files") or []):
        src = joined(f.get("src")) if isinstance(f, dict) else ""
        if src.startswith("data:"):
            mime, raw = decode_data_uri(src)
            if raw:
                suffix = f"-file{n + 1}" if n else "-program"
                save(os.path.join(outdir, f"{item['id']}{suffix}.{EXT.get((f.get('mediaType') or mime).split(';')[0], 'bin')}"), raw)
                saved += 1
    if not saved:
        print("  no on-chain image or file in this NFT's metadata")


def get_scroll(item, outdir):
    cmd = item["cmd"].split()
    exe = shutil.which("lsview")
    if exe:
        run = [exe] + cmd[1:]
    else:
        viewer = os.path.join(REPO, "koios-viewer")
        os.environ["PYTHONPATH"] = viewer + os.pathsep + os.environ.get("PYTHONPATH", "")
        probe = subprocess.run([sys.executable, "-c", "import lsview.cli"], env=os.environ, capture_output=True)
        if probe.returncode != 0:
            sys.exit("Rebuilding a scroll uses the open lsview reader. Install it once, from the repository root:\n\n"
                     "  cd koios-viewer && python3 -m venv .venv && . .venv/bin/activate && pip install -e . && cd ..\n\n"
                     f"then run again:  python3 archive/lookup.py get {item['id']}")
        run = [sys.executable, "-m", "lsview"] + cmd[1:]
    print(f"{item['title']}  ·  {item['pointer']}")
    out = run.index("--out")
    run[out + 1] = os.path.join(outdir, run[out + 1])
    code = subprocess.call(run, env=os.environ)
    if code:
        sys.exit(code)
    if item.get("chain_sha256"):
        print(f"  on-chain hash to match: {item['chain_sha256']}")


def show(item):
    print(f"\n{item['title']}")
    print(f"  {item['blurb']}" if item.get("blurb") else "", end="\n" if item.get("blurb") else "")
    if item["type"] == "scroll":
        print(f"  Ledger Scroll · {item['content']} · on chain {item['date']}")
    else:
        print(f"  NFT · {item['fingerprint']} · minted {item['date']}")
    print("\n  Copy and paste into a terminal at the root of this repository:\n")
    print(f"    {command_for(item)}\n")
    if item["type"] == "scroll":
        print(f"  Or run the open reader directly:  {item['cmd']}\n")


def menu(catalog):
    groups = [("Ledger Scrolls", [i for i in catalog["items"] if i["type"] == "scroll"]),
              ("BEACN mints", [i for i in catalog["items"] if i["type"] == "nft"])]
    while True:
        print("\nBEACN archive lookup: everything is read from Cardano through public Koios.\n")
        for n, (label, items) in enumerate(groups, 1):
            print(f"  {n}. {label} ({len(items)})")
        choice = input("\nPick a group (number, or q to quit): ").strip().lower()
        if choice in ("q", "quit", ""):
            return
        if not choice.isdigit() or not 1 <= int(choice) <= len(groups):
            continue
        label, items = groups[int(choice) - 1]
        print(f"\n{label}:")
        for n, item in enumerate(items, 1):
            print(f"  {n:>3}. {item['title']}  [{item['id']}]")
        pick = input("\nPick an item (number, or Enter to go back): ").strip()
        if not pick.isdigit() or not 1 <= int(pick) <= len(items):
            continue
        item = items[int(pick) - 1]
        show(item)
        if input("  Fetch it now into this folder? [y/N] ").strip().lower() == "y":
            (get_scroll if item["type"] == "scroll" else get_nft)(item, os.getcwd())


def main():
    ap = argparse.ArgumentParser(description="Pick any Ledger Scroll or BEACN mint and get it from Cardano.")
    ap.add_argument("action", nargs="?", help="an item id to show its command, or 'get'")
    ap.add_argument("item", nargs="?", help="item id (with 'get')")
    ap.add_argument("--list", action="store_true", help="list every item and its id")
    ap.add_argument("--out", default=".", help="folder to save into (default: current folder)")
    args = ap.parse_args()
    catalog = load_catalog()
    by_id = {i["id"]: i for i in catalog["items"]}
    if args.list:
        for i in catalog["items"]:
            print(f"{i['id']:40} {'scroll' if i['type'] == 'scroll' else 'nft':6} {i['title']}")
        return
    if args.action == "get":
        if args.item not in by_id:
            sys.exit(f"Unknown id {args.item!r}; run with --list to see every id.")
        item = by_id[args.item]
        os.makedirs(args.out, exist_ok=True)
        (get_scroll if item["type"] == "scroll" else get_nft)(item, args.out)
        return
    if args.action:
        if args.action not in by_id:
            sys.exit(f"Unknown id {args.action!r}; run with --list to see every id.")
        show(by_id[args.action])
        return
    if not sys.stdin.isatty():
        sys.exit("Run interactively for the menu, or use --list / <id> / get <id>.")
    menu(catalog)


if __name__ == "__main__":
    main()
