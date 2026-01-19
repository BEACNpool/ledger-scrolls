import argparse
import sys
import os
import json
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
        help="Title or id of the scroll to reconstruct (partial match ok)",
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
        help="Use Blockfrost API for metadata queries (recommended for MVP)",
    )

    parser.add_argument(
        "--blockfrost-key",
        type=str,
        help="Blockfrost project ID/API key (required when --use-blockfrost is used)",
    )

    parser.add_argument(
        "--registry-file",
        type=str,
        help="Optional: path to local JSON file containing custom registry data",
    )

    args = parser.parse_args()

    # Enforce Blockfrost key requirement when mode is selected
    if args.use_blockfrost and not args.blockfrost_key:
        parser.error("--blockfrost-key is required when using --use-blockfrost")

    # Quick list mode
    if args.list:
        try:
            if args.registry_file and os.path.exists(args.registry_file):
                with open(args.registry_file, "r", encoding="utf-8") as f:
                    custom_data = json.load(f)
                scrolls = custom_data.get("scrolls", [])
            else:
                scrolls = get_scrolls(use_registry=True)
        except Exception as e:
            print(f"Error loading registry: {e}", file=sys.stderr)
            print("Falling back to demo scrolls.")
            scrolls = DEFAULT_SCROLLS.copy()

        print("\nAvailable Scrolls:")
        print("-" * 50)
        for s in scrolls:
            title = s.get("title", "Untitled")
            sid = s.get("id", "-")
            print(f"  • {title}  (id: {sid})")
        return

    # Require scroll selection for reconstruction
    if not args.scroll:
        parser.print_help()
        sys.exit(1)

    # Load scrolls
    try:
        if args.registry_file and os.path.exists(args.registry_file):
            with open(args.registry_file, "r", encoding="utf-8") as f:
                custom_data = json.load(f)
            scrolls = custom_data.get("scrolls", [])
            print(f"Loaded {len(scrolls)} scrolls from custom registry file")
        else:
            scrolls = get_scrolls(use_registry=True)
    except Exception as e:
        print(f"Error loading scrolls/registry: {e}", file=sys.stderr)
        print("Falling back to built-in demo scrolls.")
        scrolls = DEFAULT_SCROLLS.copy()

    # Find requested scroll (case-insensitive partial match on title or id)
    target = args.scroll.lower()
    scroll = next(
        (
            s
            for s in scrolls
            if target in (s.get("title", "").lower(), s.get("id", "").lower())
        ),
        None,
    )

    if not scroll:
        print(f"Scroll not found: '{args.scroll}'", file=sys.stderr)
        print("\nAvailable options:")
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
        data, content_type = reconstruct(
            scroll,
            manifest,
            bf_key=args.blockfrost_key,  # Important: pass key to reconstruct
        )

        # Guess file extension
        ext = "html" if "html" in content_type.lower() else "txt"
        if "pdf" in content_type.lower():
            ext = "pdf"
        elif "json" in content_type.lower():
            ext = "json"

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
