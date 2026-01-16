import sys
import json
import logging
from .oura_driver import OuraDriver
from .beacon_protocol import BeaconParser
from .hailo_ai import HailoProcessor

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MANIFEST_PATH = "config/manifest.json"

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

def registry_mode(manifest):
    """
    Listens to the 'Town Square' address for new registrations (Beacon Protocol).
    """
    registry_addr = manifest['registry_settings']['registry_address']
    logger.info(f"Listening to Registry Beacon at: {registry_addr}")
    
    driver = OuraDriver(network="mainnet")
    # In a real scenario, this listens to the tip. 
    # For now, we simulate listening to the address filter.
    
    for tx in driver.stream_address(registry_addr):
        # Pass raw TX to Protocol Parser
        new_scroll = BeaconParser.parse_registration(tx)
        
        if new_scroll:
            logger.info(f"New Scroll Discovered: {new_scroll['name']}")
            manifest['known_scrolls'][new_scroll['name']] = {
                "policy_id": new_scroll['policy_id'],
                "start_slot": new_scroll['start_slot'],
                "structure": new_scroll['structure'],
                "description": "Discovered via Beacon"
            }
            save_manifest(manifest)

def reader_mode(scroll_name, manifest):
    """
    Spins up Oura starting at the specific slot for the specific Policy ID.
    No API. Pure P2P.
    """
    if scroll_name not in manifest['known_scrolls']:
        logger.error("Scroll not found in manifest.")
        return

    data = manifest['known_scrolls'][scroll_name]
    logger.info(f"Booting up AI Indexer for: {scroll_name}")
    logger.info(f"Jumping direct to Slot: {data['start_slot']}")
    
    # Initialize Hardware
    ai_chip = HailoProcessor()
    driver = OuraDriver(network="mainnet")
    
    # Start streaming from the specific history point
    # We filter specifically for this Policy ID
    stream = driver.stream_policy(data['policy_id'], start_slot=data['start_slot'])
    
    for tx in stream:
        # 1. Extract Metadata
        raw_metadata = BeaconParser.extract_metadata(tx)
        
        if raw_metadata:
            # 2. Pass to AI HAT for cleanup/understanding
            clean_text = ai_chip.process(raw_metadata, structure=data['structure'])
            
            # 3. Output/Store
            print(f"\n[AI READ]: {clean_text}")

if __name__ == "__main__":
    manifest = load_manifest()
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.main [list | registry | read <Project Name>]")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == "list":
        list_scrolls(manifest)
    elif command == "registry":
        registry_mode(manifest)
    elif command == "read":
        if len(sys.argv) < 3:
            print("Error: Please specify a project name.")
        else:
            project_name = " ".join(sys.argv[2:])
            reader_mode(project_name, manifest)
