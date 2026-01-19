# src/cli.py
import argparse
import sys
import os
from pathlib import Path

from .viewer import (
    get_scrolls,
    fetch_manifest,
    reconstruct,
    DEFAULT_SCROLLS,
)


def main():
    parser = argparse.ArgumentParser(
        description="Ledger Scrolls - Viewer for on-chain immutable documents",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available scrolls and exit",
    )

    parser.add_argument(
        "--scroll",
        type=str,
        help="Title or id of the scroll to reconstruct",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="scroll_output",
        help="Output file path/prefix (default: scroll_output)",
    )

    parser.add_argument(
        "--use-blockfrost",
        action="store_true",
        help="Use Blockfrost API instead of local node for metadata queries",
    )

    parser.add_argument(
        "--blockfrost-key",
        type=str,
        help="Blockfrost project ID/API key (required if --use-blockfrost)",
    )

    parser.add_argument(
        "--registry-file",
        type=str,
        help="Optional: path to local JSON file with custom registry data",
    )

    args = parser.parse_args()

    # Quick list mode
    if args.list:
        scrolls = get_scrolls(use_registry=not args.registry_file)
        print("\nAvailable Scrolls:")
        print("-" * 40)
        for s in scrolls:
            print(f"  • {s.get('title', 'Untitled')}  (id: {s.get('id', '-')})")
        return

    if not args.scroll:
        parser.print_help()
        sys.exit(1)

    # Load scrolls
    try:
        if args.registry_file and os.path.exists(args.registry_file):
            with open(args.registry_file, "r", encoding="utf-8") as f:
                custom_data = {"scrolls": json.load(f)}
            scrolls = custom_data.get("scrolls", [])
        else:
            scrolls = get_scrolls()
    except Exception as e:
        print(f"Error loading scrolls/registry: {e}", file=sys.stderr)
        sys.exit(1)

    # Find requested scroll (try title first, then id)
    target = args.scroll.lower()
    scroll = next(
        (s for s in scrolls if target in (s.get("title", "").lower(), s.get("id", "").lower())),
        None,
    )

    if not scroll:
        print(f"Scroll not found: {args.scroll}", file=sys.stderr)
        print("Available titles/ids:")
        for s in scrolls:
            print(f"  - {s.get('title')} ({s.get('id')})")
        sys.exit(1)

    print(f"\nReconstructing: {scroll.get('title', scroll.get('id', 'Unknown'))}")

    try:
        print("→ Fetching manifest...")
        manifest = fetch_manifest(
            scroll,
            use_blockfrost=args.use_blockfrost,
            bf_key=args.blockfrost_key,
        )

        print("→ Reconstructing document...")
        data, content_type = reconstruct(scroll, manifest)

        # Guess extension
        ext = "html" if "html" in content_type.lower() else "txt"
        if "pdf" in content_type.lower():
            ext = "pdf"

        out_path = Path(f"{args.output}.{ext}")
        with open(out_path, "wb") as f:
            f.write(data)

        print(f"\nSuccess!")
        print(f"Document saved to: {out_path.absolute()}")
        print(f"Size: {len(data):,} bytes")
        print(f"Content-Type: {content_type}")

    except Exception as e:
        print(f"\nFailed to reconstruct scroll:\n{str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
