from __future__ import annotations

import argparse
import asyncio
import logging

from .blockfrost import resolve_point_from_tx
from .cbor_helpers import Point, blake2b_256_hex, safe_cbor_loads
from .catalog import load_catalog, refresh_catalog
from .n2n_client import MAINNET_MAGIC, N2NConnection
from .chainsync import ChainSyncClient
from .blockfetch import BlockFetchClient
from .block_parser import parse_block, iter_label
from .scrolls.cip25 import CIP25_LABEL, extract_cip25_assets, classify_assets
from .scrolls.reconstruct import reconstruct_cip25
from .topology import load_topology


logger = logging.getLogger("lsview")


def _relay_candidates(args) -> list[tuple[str, int]]:
    candidates: list[tuple[str, int]] = []
    if args.relay:
        candidates.append((args.relay, args.port))
    if args.topology:
        candidates.extend(load_topology(args.topology))
    if not candidates:
        raise SystemExit("No relays specified. Use --relay or --topology.")

    seen = set()
    uniq: list[tuple[str, int]] = []
    for host, port in candidates:
        key = (host, int(port))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(key)
    return uniq


async def open_connection(args) -> N2NConnection:
    last_err: Exception | None = None
    for host, port in _relay_candidates(args):
        conn = N2NConnection(host, port, network_magic=args.magic, timeout=args.timeout)
        try:
            await conn.open()
            logger.info("Connected to relay %s:%s", host, port)
            return conn
        except Exception as exc:
            last_err = exc
            logger.warning("Relay failed %s:%s (%s)", host, port, exc)
            try:
                await conn.close()
            except Exception:
                pass

    raise SystemExit(f"Could not connect to any relay. Last error: {last_err}")


async def cmd_tip(args) -> None:
    conn = await open_connection(args)
    try:
        cs = ChainSyncClient(conn)
        resp = await cs.find_intersect([])  # origin
        print(resp)
    finally:
        await conn.close()


async def cmd_fetch_block(args) -> None:
    conn = await open_connection(args)
    try:
        bf = BlockFetchClient(conn)
        pt = Point.from_hex(args.slot, args.hash)
        body = await bf.fetch_block_body(pt)
        if body is None:
            raise SystemExit("Block not found on relay for this point.")
        if args.out:
            with open(args.out, "wb") as f:
                f.write(body)
            print(f"Wrote raw block CBOR to {args.out} ({len(body)} bytes)")
        else:
            print(f"Fetched block body ({len(body)} bytes)")
        await bf.done()
    finally:
        await conn.close()


async def cmd_reconstruct_cip25(args) -> None:
    if args.scroll:
        catalog = load_catalog(args.catalog)
        entry = catalog.get(args.scroll)
        if not entry:
            raise SystemExit(f"Unknown scroll id: {args.scroll}")
        if entry.data.get("type") != "cip25_pages_v1":
            raise SystemExit("Selected scroll is not a CIP-25 pages scroll.")
        args.policy = entry.data.get("policy_id") or args.policy
        args.manifest_asset = entry.data.get("manifest_asset") or args.manifest_asset
        if entry.data.get("manifest_tx") and not args.start_slot and not args.start_hash:
            if entry.data.get("block_slot") and entry.data.get("block_hash"):
                args.start_slot = int(entry.data["block_slot"])
                args.start_hash = entry.data["block_hash"]
        if entry.data.get("block_slot") and entry.data.get("block_hash"):
            args.start_slot = int(entry.data["block_slot"])
            args.start_hash = entry.data["block_hash"]

    if not (args.policy and args.start_slot and args.start_hash):
        raise SystemExit("Missing policy/start point. Provide args or use --scroll with a catalog entry that includes a start point.")

    start_point = Point.from_hex(args.start_slot, args.start_hash)
    wanted_policy = args.policy.lower()

    conn = await open_connection(args)
    pages = []
    manifest = None

    try:
        cs = ChainSyncClient(conn)
        bf = BlockFetchClient(conn)

        intersect = await cs.find_intersect([start_point])
        if intersect.get("type") != "intersect_found":
            raise SystemExit(f"Start point not on relay chain: {intersect}")

        async for pt, _ in cs.stream_headers(max_headers=args.max_blocks, idle_timeout=args.timeout):
            body = await bf.fetch_block_body(pt)
            if body is None:
                continue

            block = parse_block(body)

            for md721 in iter_label(block, CIP25_LABEL):
                assets = extract_cip25_assets(md721, wanted_policy)
                if not assets:
                    continue
                new_pages, new_manifest = classify_assets(assets, args.manifest_asset)
                if new_manifest is not None:
                    manifest = new_manifest
                if new_pages:
                    pages.extend(new_pages)

            if manifest and manifest.total_pages:
                uniq = len({p.asset.asset_name for p in pages})
                if uniq >= manifest.total_pages:
                    break

        await bf.done()
        await cs.done()

    finally:
        await conn.close()

    if not pages:
        raise SystemExit("No CIP-25 pages were found in the scanned window. Increase --max-blocks or start closer.")

    out = reconstruct_cip25(pages=pages, manifest=manifest, out_name=args.out)
    with open(args.out, "wb") as f:
        f.write(out.raw_bytes)

    print(f"Reconstructed: {args.out}")
    print(f"Bytes:         {len(out.raw_bytes)}")
    print(f"Codec:         {out.codec}")
    print(f"Content-Type:  {out.content_type}")
    print(f"SHA-256:       {out.sha256}")


def _tx_hash_from_body(tx_body: object) -> str:
    import cbor2

    raw = cbor2.dumps(tx_body, canonical=True)
    return blake2b_256_hex(raw)


def _extract_outputs(tx_body: object) -> list:
    if isinstance(tx_body, dict):
        return list(tx_body.get(1) or [])
    if isinstance(tx_body, list) and len(tx_body) > 1:
        return list(tx_body[1])
    return []


def _extract_inline_datum(output: object) -> bytes | None:
    datum = None

    if isinstance(output, list) and len(output) >= 3:
        datum = output[2]
    elif isinstance(output, dict):
        datum = output.get(2)

    if datum is None:
        return None

    if isinstance(datum, list) and len(datum) >= 2:
        tag = datum[0]
        if tag == 2:  # inline datum
            datum = datum[1]
        else:
            return None

    if isinstance(datum, bytes):
        try:
            decoded = safe_cbor_loads(datum)
            if isinstance(decoded, bytes):
                return decoded
        except Exception:
            pass
        return datum

    return None


async def cmd_reconstruct_utxo(args) -> None:
    if args.scroll:
        catalog = load_catalog(args.catalog)
        entry = catalog.get(args.scroll)
        if not entry:
            raise SystemExit(f"Unknown scroll id: {args.scroll}")
        if entry.data.get("type") != "utxo_datum_bytes_v1":
            raise SystemExit("Selected scroll is not a Standard Scroll.")
        args.tx_hash = entry.data.get("tx_hash") or args.tx_hash
        if entry.data.get("tx_ix") is not None:
            args.tx_ix = int(entry.data.get("tx_ix"))
        if entry.data.get("block_slot") and entry.data.get("block_hash"):
            args.block_slot = int(entry.data["block_slot"])
            args.block_hash = entry.data["block_hash"]

    if args.tx_ix is None:
        raise SystemExit("Missing --tx-ix (output index). Provide it or select a catalog scroll that includes tx_ix.")

    if args.block_hash and args.block_slot:
        point = Point.from_hex(args.block_slot, args.block_hash)
    else:
        if not args.tx_hash:
            raise SystemExit("Provide --tx-hash or both --block-hash and --block-slot.")
        resolved = resolve_point_from_tx(args.tx_hash, args.blockfrost_key)
        point = Point.from_hex(resolved.slot, resolved.block_hash)

    conn = await open_connection(args)
    try:
        bf = BlockFetchClient(conn)
        body = await bf.fetch_block_body(point)
        if body is None:
            raise SystemExit("Block not found on relay for this point.")

        block = parse_block(body)
        target_hash = args.tx_hash.lower() if args.tx_hash else None

        tx_index = None
        tx_body = None
        for i, tb in enumerate(block.tx_bodies):
            if target_hash:
                if _tx_hash_from_body(tb) != target_hash:
                    continue
            tx_index = i
            tx_body = tb
            break

        if tx_body is None:
            raise SystemExit("Transaction not found in block.")

        outputs = _extract_outputs(tx_body)
        if args.tx_ix >= len(outputs):
            raise SystemExit("tx output index out of range for this transaction.")

        datum_bytes = _extract_inline_datum(outputs[args.tx_ix])
        if datum_bytes is None:
            raise SystemExit("No inline datum bytes found at that tx output.")

        with open(args.out, "wb") as f:
            f.write(datum_bytes)

        print(f"Reconstructed: {args.out}")
        print(f"Bytes:         {len(datum_bytes)}")
        print(f"SHA-256:       {blake2b_256_hex(datum_bytes)}")

        await bf.done()
    finally:
        await conn.close()


def cmd_blockfrost_point(args) -> None:
    point = resolve_point_from_tx(args.tx_hash, args.blockfrost_key)
    print(f"slot={point.slot}")
    print(f"hash={point.block_hash}")


def cmd_refresh_catalog(args) -> None:
    refresh_catalog(args.catalog, args.blockfrost_key)
    print("Catalog refreshed.")


def cmd_list_scrolls(args) -> None:
    catalog = load_catalog(args.catalog)
    for entry in catalog.values():
        data = entry.data
        kind = data.get("type")
        line = f"{entry.id}  ({kind})"
        extra = []
        if data.get("policy_id"):
            extra.append(f"policy={data.get('policy_id')}")
        if data.get("tx_hash"):
            extra.append(f"tx={data.get('tx_hash')}")
        if data.get("manifest_tx"):
            extra.append(f"manifest_tx={data.get('manifest_tx')}")
        if data.get("block_slot"):
            extra.append(f"slot={data.get('block_slot')}")
        if extra:
            line += "  " + " ".join(extra)
        print(line)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lsview", description="Ledger Scrolls P2P Viewer (N2N ChainSync + BlockFetch)")
    p.add_argument("--relay", default="backbone.cardano.iog.io")
    p.add_argument("--port", type=int, default=3001)
    p.add_argument("--topology", help="Path or URL to topology JSON (relay fallback list)")
    p.add_argument("--magic", type=int, default=MAINNET_MAGIC)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("-v", "--verbose", action="store_true")

    sp = p.add_subparsers(dest="cmd", required=True)

    tip = sp.add_parser("tip", help="Query relay tip using intersect origin")
    tip.set_defaults(func=cmd_tip)

    fb = sp.add_parser("fetch-block", help="Fetch a block by exact point (slot + header hash)")
    fb.add_argument("--slot", type=int, required=True)
    fb.add_argument("--hash", required=True, help="Block header hash (64 hex chars)")
    fb.add_argument("--out", help="Write raw block CBOR to file")
    fb.set_defaults(func=cmd_fetch_block)

    rc = sp.add_parser("reconstruct-cip25", help="Reconstruct CIP-25 pages+manifest scroll by scanning forward from a start point")
    rc.add_argument("--scroll", help="Scroll id from catalog (e.g., constitution-e608)")
    rc.add_argument("--catalog", help="Path to catalog JSON (defaults to examples/scrolls.json)")
    rc.add_argument("--policy", help="Policy ID hex")
    rc.add_argument("--manifest-asset", help="Manifest asset name (e.g., CONSTITUTION_E608_MANIFEST)")
    rc.add_argument("--start-slot", type=int)
    rc.add_argument("--start-hash")
    rc.add_argument("--max-blocks", type=int, default=400, help="How many headers/blocks to scan forward")
    rc.add_argument("--out", required=True, help="Output filename")
    rc.set_defaults(func=cmd_reconstruct_cip25)

    bf = sp.add_parser("blockfrost-point", help="Resolve start slot+hash from a tx hash via Blockfrost (optional)")
    bf.add_argument("--tx-hash", required=True, help="Transaction hash to resolve")
    bf.add_argument("--blockfrost-key", help="Blockfrost project_id (or env BLOCKFROST_PROJECT_ID)")
    bf.set_defaults(func=cmd_blockfrost_point)

    rcatalog = sp.add_parser("refresh-catalog", help="Update catalog with block slot/hash via Blockfrost")
    rcatalog.add_argument("--catalog", help="Path to catalog JSON (defaults to examples/scrolls.json)")
    rcatalog.add_argument("--blockfrost-key", help="Blockfrost project_id (or env BLOCKFROST_PROJECT_ID)")
    rcatalog.set_defaults(func=cmd_refresh_catalog)

    lsc = sp.add_parser("list-scrolls", help="List known scrolls from catalog")
    lsc.add_argument("--catalog", help="Path to catalog JSON (defaults to examples/scrolls.json)")
    lsc.set_defaults(func=cmd_list_scrolls)

    ru = sp.add_parser("reconstruct-utxo", help="Reconstruct Standard Scroll from inline datum at a tx output")
    ru.add_argument("--scroll", help="Scroll id from catalog (e.g., hosky-png)")
    ru.add_argument("--catalog", help="Path to catalog JSON (defaults to examples/scrolls.json)")
    ru.add_argument("--tx-hash", help="Transaction hash (optional if block point provided)")
    ru.add_argument("--tx-ix", type=int, help="Output index within the transaction (txin index)")
    ru.add_argument("--block-hash", help="Block header hash (64 hex chars)")
    ru.add_argument("--block-slot", type=int, help="Block slot number")
    ru.add_argument("--blockfrost-key", help="Blockfrost project_id (or env BLOCKFROST_PROJECT_ID)")
    ru.add_argument("--out", required=True, help="Output filename")
    ru.set_defaults(func=cmd_reconstruct_utxo)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
