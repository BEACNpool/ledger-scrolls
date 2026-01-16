import sys
import json
import logging
import argparse
import shutil
from pathlib import Path

# Assuming these modules exist in your project structure
from oura_driver import OuraDriver
from beacon_protocol import BeaconParser
from hailo_ai import HailoProcessor

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- Constants ---
# We look for config relative to this script's location
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "manifest.json"

# Default "Public" Showcase (The Bible / BTC Whitepaper)
# This ensures the tool works out-of-the-box even without a config file.
DEFAULT_MANIFEST = {
    "registry_settings": {
        "listen_network": "mainnet",
        "registry_address": "" # User can fill this in to follow a specific "Town Square"
    },
    "known_scrolls": {
        "BTC_Whitepaper": {
            "policy_id": "4ff143...", # Placeholder: Update with actual if known
            "start_slot": 4492799,
            "structure": "raw_text",
            "description": "The Bitcoin Whitepaper on Cardano"
        }
    }
}

def load_manifest() -> dict:
    """Loads the local registry of known scrolls."""
    if not CONFIG_PATH.exists():
        logger.warning(f"Manifest not found at {CONFIG_PATH}. Creating default...")
        save_manifest(DEFAULT_MANIFEST)
        return DEFAULT_MANIFEST
    
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load manifest: {e}")
        # Return default so the program doesn't crash on a bad config file
        return DEFAULT_MANIFEST


def save_manifest(data: dict):
    """Saves the local registry."""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.debug("Manifest saved successfully")
    except Exception as e:
        logger.error(f"Failed to save manifest: {e}")


def check_oura_binary():
    """Ensures the 'oura' tool is installed and available in PATH."""
    if not shutil.which("oura"):
        logger.error(
            "CRITICAL: 'oura' binary not found!\n"
            "Ledger Scrolls relies on 'oura' to connect to the blockchain.\n"
            "Please install it from: https://github.com/txpipe/oura"
        )
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Ledger Scrolls - Immutable. Permissionless. Decentralized.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="Example:\n  python main.py read --policy <ID> --slot <NUM>\n  python main.py read MySavedScroll"
    )
    
    # Global flags
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # --- Command: LIST ---
    subparsers.add_parser("list", help="Show all scrolls saved in your local library")

    # --- Command: REGISTRY ---
    reg_parser = subparsers.add_parser("registry", help="Listen to a public Town Square for new scrolls")
    reg_parser.add_argument("--network", default="mainnet", help="Network to listen on (mainnet/testnet)")

    # --- Command: READ ---
    read_parser = subparsers.add_parser("read", help="Read a scroll from the blockchain")
    
    # Argument group: Users can EITHER provide a name OR raw connection details
    source_group = read_parser.add_argument_group("Source Selection")
    source_group.add_argument("name", nargs="?", help="Name of a saved scroll (e.g., 'BTC_Whitepaper')")
    
    # Private/Direct Mode arguments
    direct_group = read_parser.add_argument_group("Direct Connection (Private Mode)")
    direct_group.add_argument("--policy", help="Policy ID to stream directly")
    direct_group.add_argument("--address", help="Wallet Address to stream directly")
    direct_group.add_argument("--slot", type=int, help="Start slot (required for optimization)")
    direct_group.add_argument("--schema", default="default", help="Data structure schema (optional)")

    args = parser.parse_args()

    # Apply logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled.")

    # Pre-flight checks
    check_oura_binary()
    manifest = load_manifest()

    # --- HANDLER: LIST ---
    if args.command == "list":
        if not manifest.get("known_scrolls"):
            print("No scrolls found in library.")
            print("Tip: Use 'read --policy ...' to add a new one manually.")
            return
        
        print(f"\n{'NAME':<20} | {'START SLOT':<12} | {'DESCRIPTION'}")
        print("-" * 60)
        for name, info in manifest["known_scrolls"].items():
            desc = info.get('description', 'No description')
            print(f"{name:<20} | {info['start_slot']:<12} | {desc}")
        print()

    # --- HANDLER: REGISTRY ---
    elif args.command == "registry":
        print(">> Connecting to Registry (Town Square)...")
        
        # Determine network and address
        network = args.network or manifest["registry_settings"].get("listen_network", "mainnet")
        registry_addr = manifest["registry_settings"].get("registry_address")
        
        if not registry_addr:
            logger.error("No registry_address configured in manifest.json.")
            sys.exit(1)

        driver = OuraDriver(network=network)
        
        try:
            # Note: We rely on BeaconParser to handle the specific logic of "what is a registration"
            for tx in driver.stream_address(registry_addr):
                registration = BeaconParser.parse_registration(tx)
                
                if registration:
                    name = registration.get("project", "Unnamed")
                    # Save to local manifest
                    manifest["known_scrolls"][name] = {
                        "policy_id": registration["policy_id"],
                        "start_slot": registration["start_slot"],
                        "structure": registration.get("structure", "default"),
                        "description": registration.get("description", "")
                    }
                    save_manifest(manifest)
                    print(f" [+] Discovered and saved new scroll: {name}")
                    
        except KeyboardInterrupt:
            print("\nStopping registry listener.")

    # --- HANDLER: READ ---
    elif args.command == "read":
        target_policy = None
        target_address = None
        start_slot = 0
        structure = "default"

        # Case A: Named Scroll (from Manifest)
        if args.name:
            if args.name in manifest["known_scrolls"]:
                info = manifest["known_scrolls"][args.name]
                target_policy = info.get("policy_id")
                start_slot = info.get("start_slot", 0)
                structure = info.get("structure", "default")
                logger.info(f"Loaded '{args.name}' from library.")
            else:
                logger.error(f"Scroll '{args.name}' not found in library.")
                sys.exit(1)
        
        # Case B: Direct Mode (Command Line Args)
        elif args.policy or args.address:
            target_policy = args.policy
            target_address = args.address
            start_slot = args.slot if args.slot is not None else 0
            structure = args.schema
            logger.info("Using Direct Connection mode.")
            
            if not start_slot and not args.verbose:
                logger.warning("No start slot provided. Syncing from tip might take a while.")
        
        else:
            logger.error("You must provide a scroll Name OR connection details (--policy/--address).")
            sys.exit(1)

        # Execute Reading
        print(f"\n>> Opening Scroll (Start Slot: {start_slot})...")
        print(">> Press Ctrl+C to stop reading.\n")

        driver = OuraDriver(network=manifest["registry_settings"].get("listen_network", "mainnet"))
        processor = HailoProcessor()

        try:
            # Stream based on what identifier we have (Policy ID is preferred for NFTs/Tokens)
            stream_generator = None
            if target_policy:
                stream_generator = driver.stream_policy(target_policy, start_slot)
            elif target_address:
                stream_generator = driver.stream_address(target_address, start_slot)
            
            if stream_generator:
                for tx in stream_generator:
                    # Parse metadata
                    metadata = BeaconParser.extract_metadata(tx)
                    if metadata:
                        # Process/Clean the data using the AI/Processor layer
                        cleaned = processor.process(metadata, structure)
                        if cleaned:
                            print(cleaned)
                            print("-" * 40)
            else:
                logger.error("Could not initialize stream. Missing policy or address.")

        except KeyboardInterrupt:
            print("\nScroll closed.")
        except Exception as e:
            logger.error(f"Error reading scroll: {e}", exc_info=True)

if __name__ == "__main__":
    main()
