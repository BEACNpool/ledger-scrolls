import sys
import json
import logging
import os
import binascii
import gzip
import yaml
from .oura_driver import OuraDriver
from .ogmios_driver import OgmiosDriver  # New driver
from .beacon_protocol import BeaconParser

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MANIFEST_PATH = "config/scrolls_manifest.json"
CONFIG_PATH = "config.yaml"

def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {CONFIG_PATH}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        sys.exit(1)

def get_driver(config):
    driver_name = config.get('driver', 'oura')
    if driver_name == 'oura':
        return OuraDriver(network="mainnet")
    elif driver_name == 'ogmios':
        return OgmiosDriver(config)
    else:
        raise ValueError(f"Unknown driver: {driver_name}. Supported: oura, ogmios")

def load_manifest():
    try:
        with open(MANIFEST_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Manifest file not found: {MANIFEST_PATH}. Creating empty.")
        manifest = {"known_scrolls": {}}
        save_manifest(manifest)
        return manifest
    except Exception as e:
        logger.error(f"Error loading manifest: {e}")
        sys.exit(1)

def save_manifest(data):
    try:
        with open(MANIFEST_PATH, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving manifest: {e}")

def list_scrolls(manifest):
    print("\n=== Available Ledger Scrolls ===")
    if not manifest.get('known_scrolls'):
        print("No scrolls found in manifest yet.")
    for name, data in manifest['known_scrolls'].items():
        print(f"[*] {name} (Start Slot: {data.get('start_slot', 'N/A')})")
    print("================================\n")

def registry_mode(manifest, config):
    """
    Listens to the registry beacon address for new registrations (Beacon Protocol).
    """
    registry_addr = config.get('registry_address')
    if not registry_addr or registry_addr == "UPDATE_once_built_addr1_YOUR_TOWN_SQUARE_ADDRESS_HERE":
        logger.error("Registry address not set or still placeholder in config.yaml!")
        return

    logger.info(f"Listening to Registry Beacon at: {registry_addr}")

    try:
        driver = get_driver(config)
    except Exception as e:
        logger.warning(f"Primary driver failed: {e}. Falling back to oura.")
        driver = OuraDriver(network="mainnet")

    for tx in driver.stream_address(registry_addr):
        new_scroll = BeaconParser.parse_registration(tx)
        if new_scroll:
            logger.info(f"New Scroll Discovered: {new_scroll['name']}")
            manifest['known_scrolls'][new_scroll['name']] = {
                "policy_id": new_scroll['policy_id'],
                "start_slot": new_scroll['start_slot'],
                "structure": new_scroll['structure'],
                "description": new_scroll.get('description', "Discovered via Beacon")
            }
            save_manifest(manifest)

def reader_mode(scroll_name, manifest, config):
    """
    Streams from start_slot, collects metadata by policy, caches locally, reconstructs gzip to HTML.
    Resumes from cache if exists.
    """
    if scroll_name not in manifest['known_scrolls']:
        logger.error(f"Scroll '{scroll_name}' not found in manifest.")
        return

    data = manifest['known_scrolls'][scroll_name]
    policy_id = data['policy_id']
    start_slot = data.get('start_slot', 0)
    structure = data.get('structure', 'Unknown')
    cache_dir = config.get('cache_dir', 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{scroll_name.replace(' ', '_')}.json")

    # Load cache if exists
    pages = []
    last_slot = start_slot
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                pages = json.load(f)
            if pages:
                last_slot = max(page.get('slot', start_slot) for page in pages) + 1
                logger.info(f"Resuming from cache ({len(pages)} pages loaded). Starting at slot {last_slot}")
        except Exception as e:
            logger.warning(f"Failed to load cache {cache_path}: {e}. Starting fresh.")

    try:
        driver = get_driver(config)
    except Exception as e:
        logger.warning(f"Primary driver failed: {e}. Falling back to oura.")
        driver = OuraDriver(network="mainnet")

    stream = driver.stream_policy(policy_id, start_slot=last_slot)

    for tx in stream:
        raw_metadata = BeaconParser.extract_metadata(tx)
        if raw_metadata and 'i' in raw_metadata and 'payload' in raw_metadata:
            raw_metadata['slot'] = tx.get('slot', last_slot)  # For resumability
            pages.append(raw_metadata)
            last_slot = raw_metadata['slot']
            # Save cache incrementally
            try:
                with open(cache_path, 'w') as f:
                    json.dump(pages, f, indent=4)
                logger.info(f"Cached page {raw_metadata['i']} at slot {last_slot}")
            except Exception as e:
                logger.error(f"Failed to save cache: {e}")

    # Reconstruct
    if pages:
        logger.info(f"Reconstructing '{scroll_name}' from {len(pages)} pages...")
        gz_bytes = bytearray()
        for page in sorted(pages, key=lambda p: int(p["i"])):
            for segment in page.get("payload", []):
                if "bytes" in segment:
                    try:
                        gz_bytes.extend(binascii.unhexlify(segment["bytes"]))
                    except binascii.Error as e:
                        logger.error(f"Invalid hex in page {page['i']}: {e}")
        try:
            raw_data = gzip.decompress(bytes(gz_bytes))
            output_file = f"{scroll_name.replace(' ', '_')}.html"
            with open(output_file, 'wb') as f:
                f.write(raw_data)
            logger.info(f"Reconstructed to {output_file} ({len(raw_data)} bytes)")
        except OSError as e:
            logger.error(f"Decompression failed: {e}")
    else:
        logger.warning("No pages found for reconstruction.")

def interactive_mode(config, manifest):
    while True:
        print("\n=== Ledger Scrolls Interactive Mode ===")
        print("1. List Known Scrolls")
        print("2. Discover from Registry (Beacon)")
        print("3. Manually Add Scroll (Custom Policy + Slot)")
        print("4. Reconstruct Scroll")
        print("5. Exit")
        choice = input("Enter choice (1-5): ").strip()

        if choice == '1':
            list_scrolls(manifest)
        elif choice == '2':
            registry_mode(manifest, config)
            manifest = load_manifest()  # Reload after discovery
        elif choice == '3':
            name = input("Scroll Name: ").strip()
            policy_id = input("Policy ID: ").strip()
            start_slot = int(input("Start Slot: ").strip())
            structure = input("Structure (e.g. Book/Text): ").strip()
            desc = input("Description: ").strip()
            manifest['known_scrolls'][name] = {
                "policy_id": policy_id,
                "start_slot": start_slot,
                "structure": structure,
                "description": desc
            }
            save_manifest(manifest)
            print(f"Added '{name}' to manifest.")
        elif choice == '4':
            name = input("Enter scroll name to reconstruct: ").strip()
            reader_mode(name, manifest, config)
        elif choice == '5':
            print("Exiting interactive mode.")
            break
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    config = load_config()
    manifest = load_manifest()

    if len(sys.argv) < 2:
        print("Usage: ./scroll [help | list | registry | read <name> | interactive]")
        sys.exit(1)

    command = sys.argv[1].lower()
    if command == "help":
        print("Commands: help, list, registry, read <name>, interactive")
    elif command == "list":
        list_scrolls(manifest)
    elif command == "registry":
        registry_mode(manifest, config)
    elif command == "read":
        if len(sys.argv) < 3:
            print("Error: Specify scroll name, e.g., 'The Cardano Bible'")
        else:
            scroll_name = " ".join(sys.argv[2:])
            reader_mode(scroll_name, manifest, config)
    elif command == "interactive":
        interactive_mode(config, manifest)
    else:
        print(f"Unknown command: {command}")
        print("Available: help, list, registry, read <name>, interactive")
