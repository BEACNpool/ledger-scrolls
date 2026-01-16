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
# from .hailo_ai import HailoProcessor  # Commented out; optional AI

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MANIFEST_PATH = "config/scrolls_manifest.json"
CONFIG_PATH = "config.yaml"

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

def get_driver(config):
    driver_name = config['driver']
    if driver_name == 'oura':
        return OuraDriver(network="mainnet")
    elif driver_name == 'ogmios':
        return OgmiosDriver(config)
    else:
        raise ValueError(f"Unknown driver: {driver_name}")

def load_manifest():
    with open(MANIFEST_PATH, 'r') as f:
        return json.load(f)

def save_manifest(data):
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(data, f, indent=4)

def list_scrolls(manifest):
    print("\n=== Available Ledger Scrolls ===")
    for name, data in manifest['known_scrolls'].items():
        print(f"[*] {name} (Start Slot: {data['start_slot']})")
    print("================================\n")

def registry_mode(manifest, config):
    """
    Listens to the 'Town Square' address for new registrations (Beacon Protocol).
    """
    registry_addr = manifest['registry_settings']['registry_address']
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
        logger.error("Scroll not found in manifest.")
        return

    data = manifest['known_scrolls'][scroll_name]
    policy_id = data['policy_id']
    start_slot = data['start_slot']
    structure = data['structure']
    cache_dir = config['cache_dir']
    cache_path = os.path.join(cache_dir, f"{scroll_name.replace(' ', '_')}.json")

    # Load cache if exists
    pages = []
    last_slot = start_slot
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            pages = json.load(f)
        if pages:
            last_slot = max(page.get('slot', start_slot) for page in pages) + 1  # Resume from last
        logger.info(f"Resuming from cache ({len(pages)} pages loaded). Starting at slot {last_slot}")

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
            with open(cache_path, 'w') as f:
                json.dump(pages, f, indent=4)
            logger.info(f"Cached page {raw_metadata['i']} at slot {last_slot}")

    # Reconstruct after streaming (or from full cache)
    if pages:
        logger.info(f"Reconstructing {scroll_name} from {len(pages)} pages...")
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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./scroll [help | list | registry | read <Scroll Name>]")
        sys.exit(1)
    
    command = sys.argv[1]
    config = load_config()
    manifest = load_manifest()
    
    if command == "help":
        print("Commands: list (show scrolls), registry (discover new), read <name> (reconstruct)")
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
