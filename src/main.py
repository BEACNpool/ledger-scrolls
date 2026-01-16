import sys
import json
import logging
import argparse
import shutil
from pathlib import Path

from oura_driver import OuraDriver
from beacon_protocol import BeaconParser
from hailo_ai import HailoProcessor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "manifest.json"


def load_manifest() -> dict:
    if not CONFIG_PATH.exists():
        logger.warning("Manifest not found, creating empty one")
        return {"registry_settings": {}, "known_scrolls": {}}
    
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load manifest: {e}")
        sys.exit(1)


def save_manifest(data: dict):
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("Manifest saved successfully")
    except Exception as e:
        logger.error(f"Failed to save manifest: {e}")


def check_oura_binary():
    if not shutil.which("oura"):
        logger.error(
            "oura binary not found! Please install oura[](https://github.com/txpipe/oura)"
        )
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Ledger Scrolls - Cardano immutable data viewer",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # List command
    subparsers.add_parser("list", help="List all known scrolls")

    # Registry listen mode
    subparsers.add_parser("registry", help="Listen for new scroll registrations")

    # Read specific scroll
    read_parser = subparsers.add_parser("read", help="Read/reconstruct a scroll")
    read_parser.add_argument("scroll_name", type=str, help="Name of the scroll to read")

    # Global options
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    manifest = load_manifest()

    check_oura_binary()

    if args.command == "list":
        if not manifest.get("known_scrolls"):
            print("No scrolls registered yet.")
            return
        
        print("\nKnown Scrolls:")
        for name, info in manifest["known_scrolls"].items():
            print(f"  • {name}")
            print(f"    PolicyID:  {info['policy_id']}")
            print(f"    Start slot: {info['start_slot']}")
            print(f"    Structure:  {info.get('structure', 'Unknown')}")
            print()

    elif args.command == "registry":
        print("Starting registry listener mode...")
        driver = OuraDriver(network=manifest["registry_settings"].get("listen_network", "mainnet"))
        registry_addr = manifest["registry_settings"].get("registry_address")
        
        if not registry_addr or "YOUR_TOWN_SQUARE_ADDRESS_HERE" in registry_addr:
            print("ERROR: Please update registry_address in manifest.json first!")
            sys.exit(1)

        for tx in driver.stream_address(registry_addr):
            registration = BeaconParser.parse_registration(tx)
            if registration:
                name = registration.get("project", "Unnamed")
                manifest["known_scrolls"][name] = {
                    "policy_id": registration["policy_id"],
                    "start_slot": registration["start_slot"],
                    "structure": registration.get("structure", "Unknown"),
                    "description": registration.get("description", "")
                }
                save_manifest(manifest)
                print(f"New scroll registered: {name}")

    elif args.command == "read":
        scroll_name = args.scroll_name
        if scroll_name not in manifest["known_scrolls"]:
            print(f"Scroll '{scroll_name}' not found in known scrolls.")
            print("Run 'ledger-scrolls list' to see available scrolls.")
            sys.exit(1)

        info = manifest["known_scrolls"][scroll_name]
        print(f"Reconstructing scroll: {scroll_name}")
        print(f"PolicyID: {info['policy_id']}")
        print(f"Starting from slot: {info['start_slot']}\n")

        driver = OuraDriver(network=manifest["registry_settings"].get("listen_network", "mainnet"))
        processor = HailoProcessor()

        try:
            for tx in driver.stream_policy(info["policy_id"], info["start_slot"]):
                metadata = BeaconParser.extract_metadata(tx)
                if metadata:
                    cleaned = processor.process(metadata, info.get("structure", "Unknown"))
                    print(cleaned)
                    print("-" * 80)
        except KeyboardInterrupt:
            print("\nStopped by user.")
        except Exception as e:
            logger.error(f"Error during scroll reconstruction: {e}", exc_info=True)


if __name__ == "__main__":
    main()
