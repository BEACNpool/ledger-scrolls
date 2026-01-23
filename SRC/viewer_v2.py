#!/usr/bin/env python3
"""
Ledger Scrolls Viewer - "A library that cannot burn."

A permissionless, decentralized viewer for immutable data on the Cardano blockchain.
Supports configurable Registries, QR code scanning, and experimental P2P "sync deception" queries.

Philosophy:
- No centralized gatekeepers
- Local-first operation prioritized
- Forever-readable as long as pointers remain valid
- Open standard, open source

Author: BEACNpool
License: MIT
"""

import os
import sys
import json
import gzip
import hashlib
import subprocess
import threading
import requests
import binascii
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Setup logging
LOG_DIR = Path.home() / ".ledger-scrolls" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"viewer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("LedgerScrolls")

# GUI imports
try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox, filedialog
except ImportError:
    print("ERROR: tkinter not found. Please install tkinter for your Python distribution.")
    sys.exit(1)

# QR code scanner (optional)
QR_AVAILABLE = False
try:
    import cv2
    from pyzbar import pyzbar
    QR_AVAILABLE = True
    logger.info("QR code scanner available")
except ImportError:
    logger.info("QR code scanner not available (install opencv-python and pyzbar for QR support)")

# Default public Registry (BEACNpool's hosted Registry)
DEFAULT_REGISTRY_ADDRESS = "addr1q9x84f458uyf3k23sr7qfalg3mw2hl0nvv4navps2r7vq69esnxrheg9tfpr8sdyfzpr8jch5p538xjynz78lql9wm6qpl6qxy"
DEFAULT_REGISTRY_POLICY_ID = "895cbbe0e284b60660ed681e389329483d5ca94677cbb583f3124062"
DEFAULT_REGISTRY_ASSET_HEX = "4c535f5245474953545259"  # LS_REGISTRY


# ============================================================================
# DATA MODELS
# ============================================================================

class ScrollType(Enum):
    """Scroll storage format types"""
    STANDARD = "utxo_datum_bytes_v1"  # Locked UTxO with inline datum
    LEGACY = "cip25_pages_v1"  # Pages + Manifest NFTs


class ConnectionMode(Enum):
    """Connection modes for blockchain access"""
    BLOCKFROST = "blockfrost"
    LOCAL_NODE = "local_node"
    P2P_LIGHTWEIGHT = "p2p_lightweight"  # Lightweight P2P sync deception


@dataclass
class RegistryPointer:
    """Pointer to a Registry scroll"""
    address: str
    policy_id: Optional[str] = None
    asset_hex: Optional[str] = None
    name: str = "Custom Registry"


@dataclass
class StandardScrollPointer:
    """Pointer for Standard (Locked UTxO) Scrolls"""
    lock_address: str
    lock_txin: str
    content_type: str
    codec: str  # 'none' or 'gzip'
    sha256: Optional[str] = None


@dataclass
class LegacyScrollPointer:
    """Pointer for Legacy (Pages + Manifest) Scrolls"""
    policy_id: str
    manifest_tx_hash: str
    content_type: str
    codec: str  # 'none' or 'gzip'
    manifest_slot: Optional[str] = None
    segments_per_page: int = 32
    location_hint: Optional[str] = None  # Address hint for hybrid pointer


@dataclass
class NodeConfig:
    """Configuration for local Cardano node connection"""
    host: str
    port: int
    socket_path: Optional[str] = None
    network: str = "mainnet"


@dataclass
class P2PConfig:
    """Configuration for P2P lightweight "sync deception" client"""
    relay_host: str
    relay_port: int = 3001
    network: str = "mainnet"
    cache_dir: Optional[str] = None


# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================

class Config:
    """Manages persistent configuration for the viewer"""
    
    CONFIG_DIR = Path.home() / ".ledger-scrolls"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    DOWNLOADS_DIR = Path.home() / "Downloads" / "LedgerScrolls"
    
    def __init__(self):
        self.config_dir = self.CONFIG_DIR
        self.config_file = self.CONFIG_FILE
        self.downloads_dir = self.DOWNLOADS_DIR
        self._config = self._load_config()
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> Dict:
        """Load configuration from disk"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load config: {e}")
        return {}
    
    def _save_config(self):
        """Save configuration to disk"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config: {e}")
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self._config.get(key, default)
    
    def set(self, key: str, value):
        """Set configuration value"""
        self._config[key] = value
        self._save_config()
    
    def get_blockfrost_key(self) -> Optional[str]:
        """Get saved Blockfrost API key"""
        return self.get('blockfrost_api_key')
    
    def set_blockfrost_key(self, key: str):
        """Save Blockfrost API key"""
        self.set('blockfrost_api_key', key)
    
    def get_node_config(self) -> Optional[NodeConfig]:
        """Get saved node configuration"""
        node_cfg = self.get('node_config')
        if node_cfg:
            return NodeConfig(**node_cfg)
        return None
    
    def set_node_config(self, config: NodeConfig):
        """Save node configuration"""
        self.set('node_config', {
            'host': config.host,
            'port': config.port,
            'socket_path': config.socket_path,
            'network': config.network
        })
    
    def get_registry_pointer(self) -> Optional[RegistryPointer]:
        """Get saved Registry pointer"""
        reg = self.get('registry_pointer')
        if reg:
            return RegistryPointer(**reg)
        return None
    
    def set_registry_pointer(self, pointer: RegistryPointer):
        """Save Registry pointer"""
        self.set('registry_pointer', {
            'address': pointer.address,
            'policy_id': pointer.policy_id,
            'asset_hex': pointer.asset_hex,
            'name': pointer.name
        })
    
    def get_p2p_config(self) -> Optional[P2PConfig]:
        """Get saved P2P configuration"""
        p2p = self.get('p2p_config')
        if p2p:
            return P2PConfig(**p2p)
        return None
    
    def set_p2p_config(self, config: P2PConfig):
        """Save P2P configuration"""
        self.set('p2p_config', {
            'relay_host': config.relay_host,
            'relay_port': config.relay_port,
            'network': config.network,
            'cache_dir': config.cache_dir
        })


# ============================================================================
# QR CODE SCANNER
# ============================================================================

class QRScanner:
    """QR code scanner for easy Registry/address input"""
    
    @staticmethod
    def scan_qr_code() -> Optional[str]:
        """
        Open camera and scan QR code
        Returns the decoded string or None if scan fails
        """
        if not QR_AVAILABLE:
            raise Exception(
                "QR code scanner not available.\n\n"
                "Install with: pip install opencv-python pyzbar"
            )
        
        logger.info("Opening camera for QR scan...")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            raise Exception("Could not open camera. Check camera permissions.")
        
        window_name = "QR Code Scanner - Hold QR code to camera (Press Q to cancel)"
        cv2.namedWindow(window_name)
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Decode QR codes in frame
                decoded_objects = pyzbar.decode(frame)
                
                for obj in decoded_objects:
                    # Draw rectangle around QR code
                    points = obj.polygon
                    if len(points) == 4:
                        pts = [(point.x, point.y) for point in points]
                        cv2.polylines(frame, [np.array(pts, np.int32)], True, (0, 255, 0), 3)
                    
                    # Extract data
                    qr_data = obj.data.decode('utf-8')
                    
                    # Show success message
                    cv2.putText(frame, "QR Code Detected!", (50, 50), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.imshow(window_name, frame)
                    cv2.waitKey(1000)  # Show for 1 second
                    
                    logger.info(f"QR code scanned: {qr_data[:50]}...")
                    return qr_data
                
                # Show instructions
                cv2.putText(frame, "Hold QR code to camera", (50, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, "Press Q to cancel", (50, 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                cv2.imshow(window_name, frame)
                
                # Check for quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("QR scan cancelled by user")
                    return None
        
        finally:
            cap.release()
            cv2.destroyAllWindows()


# ============================================================================
# BLOCKCHAIN CLIENTS
# ============================================================================

class BlockfrostClient:
    """Client for Blockfrost API"""
    
    BASE_URL = "https://cardano-mainnet.blockfrost.io/api/v0"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"project_id": api_key}
    
    def _request(self, endpoint: str, retries: int = 3) -> Dict:
        """Make API request with retry logic"""
        import time
        url = f"{self.BASE_URL}{endpoint}"
        
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=30)
                
                # Handle rate limiting
                if response.status_code == 429:
                    wait_time = 2 ** attempt
                    print(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                time.sleep(0.1)  # Small delay to avoid rate limits
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    raise Exception(f"Blockfrost request failed after {retries} attempts: {e}")
                print(f"Retry {attempt + 1}/{retries}...")
                time.sleep(1)
        
        raise Exception("Max retries exceeded")
    
    def query_utxo_at_address(self, address: str) -> List[Dict]:
        """Query all UTxOs at an address"""
        utxos = []
        page = 1
        
        while True:
            try:
                endpoint = f"/addresses/{address}/utxos?page={page}"
                page_utxos = self._request(endpoint)
                
                if not page_utxos:
                    break
                
                utxos.extend(page_utxos)
                page += 1
                
                if len(page_utxos) < 100:
                    break
            except Exception:
                break
        
        return utxos
    
    def query_tx_metadata(self, tx_hash: str) -> Dict:
        """Query transaction metadata"""
        endpoint = f"/txs/{tx_hash}/metadata"
        return self._request(endpoint)
    
    def query_asset_metadata(self, asset_full: str) -> Dict:
        """Query NFT metadata (policy_id + asset_name)"""
        try:
            endpoint = f"/assets/{asset_full}"
            return self._request(endpoint)
        except Exception as e:
            raise Exception(f"Asset {asset_full[:20]}... not found or error: {e}")


class LocalNodeClient:
    """Client for direct Cardano node queries via cardano-cli"""
    
    def __init__(self, config: NodeConfig):
        self.config = config
        self._check_cardano_cli()
    
    def _check_cardano_cli(self):
        """Verify cardano-cli is available"""
        try:
            subprocess.run(
                ["cardano-cli", "--version"],
                check=True,
                capture_output=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise Exception(
                "cardano-cli not found. Please install Cardano node tools.\n"
                "See: https://developers.cardano.org/docs/get-started/installing-cardano-node"
            )
    
    def _run_cli(self, args: List[str]) -> Dict:
        """Run cardano-cli command and parse JSON output"""
        cmd = ["cardano-cli"] + args
        
        if self.config.socket_path:
            env = os.environ.copy()
            env["CARDANO_NODE_SOCKET_PATH"] = self.config.socket_path
        else:
            env = None
        
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.stdout.strip():
                return json.loads(result.stdout)
            return {}
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"cardano-cli error: {e.stderr}")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse cardano-cli output: {e}")
    
    def query_utxo_at_address(self, address: str) -> List[Dict]:
        """Query UTxOs at address using cardano-cli"""
        args = [
            "query", "utxo",
            f"--{self.config.network}",
            "--address", address,
            "--out-file", "/dev/stdout"
        ]
        
        utxo_set = self._run_cli(args)
        
        # Convert to Blockfrost-like format
        utxos = []
        for txin, data in utxo_set.items():
            tx_hash, tx_ix = txin.split('#')
            
            utxo = {
                "tx_hash": tx_hash,
                "tx_index": int(tx_ix),
                "output_index": int(tx_ix),
                "amount": data.get("value", {}),
                "inline_datum": data.get("inlineDatum"),
                "datum_hash": data.get("datumhash"),
                "address": address
            }
            utxos.append(utxo)
        
        return utxos
    
    def query_tx_metadata(self, tx_hash: str) -> Dict:
        """Query transaction metadata using cardano-cli"""
        args = [
            "query", "tx",
            f"--{self.config.network}",
            "--tx-id", tx_hash,
            "--out-file", "/dev/stdout"
        ]
        
        try:
            tx_data = self._run_cli(args)
            metadata = tx_data.get("metadata", {})
            
            result = []
            for label, value in metadata.items():
                result.append({
                    "label": label,
                    "json_metadata": value
                })
            
            return result
        except Exception:
            return []
    
    def _request(self, endpoint: str) -> Dict:
        """Compatibility method for Registry client"""
        raise NotImplementedError("Local node does not support REST endpoints")


class P2PLightweightClient:
    """
    P2P Lightweight "Sync Deception" Client
    
    Strategy: Connect to a Cardano relay pretending to sync the chain,
    but only request specific blocks/slots we need, then disconnect quickly.
    
    This allows querying specific on-chain data without full node sync
    or centralized API dependency.
    
    Status: EXPERIMENTAL - Protocol implementation in progress
    """
    
    def __init__(self, config: P2PConfig):
        self.config = config
        self.cache_dir = Path(config.cache_dir) if config.cache_dir else Path.home() / ".ledger-scrolls" / "p2p_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.connected = False
        
        logger.info(f"P2P Lightweight Client initialized")
        logger.info(f"Strategy: 'Sync deception' - Query specific blocks then disconnect")
        logger.info(f"Relay: {config.relay_host}:{config.relay_port}")
    
    def connect_to_relay(self) -> bool:
        """
        Attempt to connect to Cardano relay
        
        This initiates the Ouroboros handshake, making the relay think
        we're a syncing node. But we'll only ask for specific data.
        """
        logger.info(f"Attempting to connect to relay {self.config.relay_host}:{self.config.relay_port}...")
        
        try:
            # TODO: Implement Ouroboros mini-protocols:
            # 1. node-to-node handshake (version negotiation)
            # 2. chain-sync (to appear as syncing node)
            # 3. block-fetch (to request specific blocks)
            # 4. local-state-query (to query UTxO sets)
            
            raise NotImplementedError(
                "P2P connection protocol not yet implemented.\n\n"
                "Planned implementation:\n"
                "1. TCP connection to relay\n"
                "2. Ouroboros handshake (pretend to sync)\n"
                "3. Query specific slots/blocks\n"
                "4. Parse CBOR block data\n"
                "5. Extract needed transactions\n"
                "6. Disconnect quickly\n\n"
                "This allows querying chain data without:\n"
                "- Running full node\n"
                "- Relying on centralized APIs\n"
                "- Downloading entire chain history\n\n"
                "Estimated implementation: 2-3 months\n"
                "Use Blockfrost or Local Node mode for now."
            )
        
        except Exception as e:
            logger.error(f"P2P connection failed: {e}")
            raise
    
    def query_utxo_at_address(self, address: str) -> List[Dict]:
        """
        Query UTxOs at address using P2P sync deception
        
        Process:
        1. Connect to relay (pretend to sync)
        2. Use local-state-query mini-protocol to ask for UTxOs
        3. Parse the response
        4. Disconnect
        """
        logger.info(f"P2P Query: UTxO at address {address[:30]}...")
        
        if not self.connected:
            self.connect_to_relay()
        
        # Will be implemented with Ouroboros local-state-query protocol
        raise NotImplementedError("P2P UTxO queries not yet implemented")
    
    def query_block_by_slot(self, slot: int) -> Dict:
        """
        Query a specific block by slot number
        
        This is the core "sync deception" - we ask for one specific block
        instead of syncing the whole chain.
        """
        logger.info(f"P2P Query: Block at slot {slot}...")
        
        if not self.connected:
            self.connect_to_relay()
        
        # Will be implemented with Ouroboros block-fetch protocol
        raise NotImplementedError("P2P block queries not yet implemented")
    
    def query_tx_metadata(self, tx_hash: str) -> Dict:
        """Query transaction metadata using P2P"""
        logger.info(f"P2P Query: Tx metadata for {tx_hash[:20]}...")
        raise NotImplementedError("P2P transaction queries not yet implemented")
    
    def _request(self, endpoint: str) -> Dict:
        """Placeholder for API compatibility"""
        raise NotImplementedError("P2P mode does not use REST endpoints")
    
    def disconnect(self):
        """Gracefully disconnect from relay"""
        if self.connected:
            logger.info("Disconnecting from relay...")
            self.connected = False


# ============================================================================
# REGISTRY CLIENT
# ============================================================================

class RegistryClient:
    """
    Manages the on-chain Registry of Ledger Scrolls
    
    Supports both public and private Registries.
    """
    
    def __init__(self, client, registry_pointer: RegistryPointer, progress_callback=None):
        self.client = client
        self.registry_pointer = registry_pointer
        self.progress_callback = progress_callback
        self.scrolls = []
        self.registry_data = None
    
    def _report_progress(self, message: str):
        """Report progress to callback"""
        if self.progress_callback:
            self.progress_callback(message)
        logger.info(message)
    
    def load_registry(self) -> List[Dict]:
        """Load the Registry from the blockchain"""
        try:
            self._report_progress(f"📜 Loading Registry: {self.registry_pointer.name}")
            self._report_progress(f"📍 Address: {self.registry_pointer.address[:30]}...")
            
            # Query the Registry address
            utxos = self.client.query_utxo_at_address(self.registry_pointer.address)
            
            if not utxos:
                raise Exception(f"No UTxOs found at Registry address")
            
            self._report_progress(f"✓ Found {len(utxos)} UTxO(s) at Registry address")
            
            # Find the UTxO containing the Registry NFT (if policy specified)
            if self.registry_pointer.policy_id and self.registry_pointer.asset_hex:
                registry_utxo = self._find_registry_utxo(utxos)
                if not registry_utxo:
                    raise Exception("Registry NFT not found in UTxOs")
            else:
                # No specific NFT - use first UTxO with inline datum
                registry_utxo = None
                for utxo in utxos:
                    if utxo.get('inline_datum'):
                        registry_utxo = utxo
                        break
                if not registry_utxo:
                    raise Exception("No UTxO with inline datum found")
            
            self._report_progress("✓ Found Registry UTxO")
            
            # Extract inline datum bytes
            registry_bytes = self._extract_datum_bytes(registry_utxo)
            
            self._report_progress(f"✓ Extracted {len(registry_bytes)} bytes from datum")
            
            # Try to decompress (Registry may be gzipped)
            try:
                json_bytes = gzip.decompress(registry_bytes)
                self._report_progress(f"✓ Decompressed to {len(json_bytes)} bytes")
            except:
                # Not gzipped, use as-is
                json_bytes = registry_bytes
                self._report_progress(f"✓ Registry not compressed")
            
            # Parse JSON
            self.registry_data = json.loads(json_bytes.decode('utf-8'))
            
            # Validate schema
            if 'scrolls' not in self.registry_data:
                raise Exception("Invalid Registry: missing 'scrolls' field")
            
            self.scrolls = self.registry_data.get('scrolls', [])
            
            self._report_progress(f"✅ Registry loaded successfully! Found {len(self.scrolls)} scrolls")
            
            return self.scrolls
            
        except Exception as e:
            self._report_progress(f"❌ Failed to load Registry: {e}")
            logger.error(f"Registry load error: {e}", exc_info=True)
            raise
    
    def _find_registry_utxo(self, utxos: List[Dict]) -> Optional[Dict]:
        """Find the UTxO containing the Registry NFT"""
        for utxo in utxos:
            amount = utxo.get('amount', [])
            
            # Handle Blockfrost format (list of dicts)
            if isinstance(amount, list):
                for asset in amount:
                    if isinstance(asset, dict):
                        unit = asset.get('unit', '')
                        if (self.registry_pointer.policy_id in unit and 
                            self.registry_pointer.asset_hex in unit):
                            return utxo
            
            # Handle cardano-cli format (dict)
            elif isinstance(amount, dict):
                for unit, qty in amount.items():
                    if (self.registry_pointer.policy_id in unit and 
                        self.registry_pointer.asset_hex in unit):
                        return utxo
        
        return None
    
    def _extract_datum_bytes(self, utxo: Dict) -> bytes:
        """Extract bytes from inline datum (handles CBOR encoding)"""
        inline_datum = utxo.get('inline_datum')
        
        if not inline_datum:
            raise Exception("UTxO does not contain inline datum")
        
        # Handle CBOR hex string (Blockfrost format)
        if isinstance(inline_datum, str):
            try:
                import cbor2
                cbor_bytes = binascii.unhexlify(inline_datum)
                datum_obj = cbor2.loads(cbor_bytes)
                
                if isinstance(datum_obj, list) and len(datum_obj) >= 2:
                    fields = datum_obj[1]
                    if isinstance(fields, list) and len(fields) > 0:
                        if isinstance(fields[0], bytes):
                            return fields[0]
                        else:
                            hex_data = str(fields[0])
                            return binascii.unhexlify(hex_data)
                elif isinstance(datum_obj, bytes):
                    return datum_obj
                else:
                    raise Exception(f"Unexpected CBOR datum structure: {type(datum_obj)}")
            except ImportError:
                raise Exception("cbor2 library required. Install with: pip install cbor2")
        
        # Handle already-parsed format
        elif isinstance(inline_datum, dict):
            fields = inline_datum.get('fields', [])
            if fields and isinstance(fields, list):
                bytes_field = fields[0].get('bytes')
                if bytes_field:
                    return binascii.unhexlify(bytes_field)
        
        raise Exception(f"Cannot extract bytes from datum format: {type(inline_datum)}")


# ============================================================================
# SCROLL RECONSTRUCTION ENGINE
# ============================================================================

class ScrollReconstructor:
    """Reconstructs scroll files from on-chain data"""
    
    def __init__(self, client, progress_callback=None):
        self.client = client
        self.progress_callback = progress_callback
        self.reconstruction_method = None
    
    def _report_progress(self, message: str):
        """Report progress to callback"""
        if self.progress_callback:
            self.progress_callback(message)
    
    def _verify_hash(self, data: bytes, expected_hash: Optional[str]) -> bool:
        """Verify SHA256 hash of data"""
        if not expected_hash:
            return True
        
        actual_hash = hashlib.sha256(data).hexdigest()
        return actual_hash.lower() == expected_hash.lower()
    
    def _hex_to_bytes(self, hex_str: str) -> bytes:
        """Convert hex string to bytes, cleaning any non-hex characters"""
        hex_str = hex_str.replace('0x', '').replace('0X', '')
        cleaned = ''.join(c for c in hex_str if c in '0123456789abcdefABCDEF')
        
        if len(cleaned) % 2 != 0:
            raise ValueError(f"Hex string has odd length ({len(cleaned)} chars)")
        
        try:
            return binascii.unhexlify(cleaned)
        except binascii.Error as e:
            preview = cleaned[:100]
            raise ValueError(f"Invalid hex string. First 100 chars: {preview}... Error: {e}")
    
    def _decompress(self, data: bytes, codec: str) -> bytes:
        """Decompress data based on codec"""
        if codec == "gzip":
            return gzip.decompress(data)
        elif codec == "none":
            return data
        else:
            raise ValueError(f"Unknown codec: {codec}")
    
    def reconstruct_standard_scroll(self, pointer: StandardScrollPointer) -> Tuple[bytes, str]:
        """Reconstruct a Standard Scroll from locked UTxO datum"""
        self.reconstruction_method = "Standard Scroll (Locked UTxO)"
        self._report_progress("🔍 Querying locked UTxO address...")
        
        utxos = self.client.query_utxo_at_address(pointer.lock_address)
        
        if not utxos:
            raise Exception(f"No UTxOs found at lock address: {pointer.lock_address}")
        
        self._report_progress(f"✓ Found {len(utxos)} UTxO(s) at lock address")
        
        tx_hash, tx_index = pointer.lock_txin.split('#')
        target_utxo = None
        
        for utxo in utxos:
            if (utxo.get('tx_hash') == tx_hash and 
                utxo.get('output_index') == int(tx_index)):
                target_utxo = utxo
                break
        
        if not target_utxo:
            raise Exception(f"Specific UTxO not found: {pointer.lock_txin}")
        
        self._report_progress(f"✓ Found target UTxO: {pointer.lock_txin}")
        
        inline_datum = target_utxo.get('inline_datum')
        if not inline_datum:
            raise Exception("UTxO does not contain inline datum")
        
        self._report_progress("📦 Extracting datum bytes...")
        
        if isinstance(inline_datum, str):
            try:
                import cbor2
                cbor_bytes = self._hex_to_bytes(inline_datum)
                datum_obj = cbor2.loads(cbor_bytes)
                
                if isinstance(datum_obj, list) and len(datum_obj) >= 2:
                    fields = datum_obj[1]
                    if isinstance(fields, list) and len(fields) > 0:
                        hex_data = fields[0].hex() if isinstance(fields[0], bytes) else str(fields[0])
                    else:
                        raise Exception("Unexpected CBOR fields structure")
                elif isinstance(datum_obj, bytes):
                    hex_data = datum_obj.hex()
                else:
                    raise Exception(f"Unexpected CBOR datum structure: {type(datum_obj)}")
            except ImportError:
                raise Exception("cbor2 library required. Install with: pip install cbor2")
        
        elif isinstance(inline_datum, dict):
            fields = inline_datum.get('fields', [])
            if fields and isinstance(fields, list):
                bytes_field = fields[0].get('bytes')
                if bytes_field:
                    hex_data = bytes_field
                else:
                    raise Exception("Datum fields do not contain 'bytes'")
            else:
                raise Exception("Unexpected datum structure")
        else:
            raise Exception(f"Datum is not a string or dict: {type(inline_datum)}")
        
        self._report_progress("🔄 Converting hex to bytes...")
        raw_bytes = self._hex_to_bytes(hex_data)
        
        self._report_progress(f"✓ Extracted {len(raw_bytes)} bytes")
        
        if pointer.codec != "none":
            self._report_progress(f"📂 Decompressing ({pointer.codec})...")
            file_bytes = self._decompress(raw_bytes, pointer.codec)
            self._report_progress(f"✓ Decompressed to {len(file_bytes)} bytes")
        else:
            file_bytes = raw_bytes
        
        if pointer.sha256:
            self._report_progress("🔐 Verifying hash...")
            if self._verify_hash(file_bytes, pointer.sha256):
                self._report_progress("✓ Hash verification PASSED ✓")
            else:
                self._report_progress("⚠️ Hash verification FAILED")
                raise Exception("Hash mismatch - data may be corrupted")
        
        return file_bytes, pointer.content_type
    
    def reconstruct_legacy_scroll(self, pointer: LegacyScrollPointer) -> Tuple[bytes, str]:
        """
        Reconstruct a Legacy Scroll using HYBRID POINTER approach
        
        If location_hint is provided, tries that address first.
        Falls back to full policy scan if needed.
        """
        # Try location hint first (if available)
        if pointer.location_hint:
            try:
                self._report_progress(f"🎯 Trying location hint: {pointer.location_hint[:30]}...")
                self.reconstruction_method = "✅ Hybrid Pointer (Location Hint)"
                
                hint_utxos = self.client.query_utxo_at_address(pointer.location_hint)
                
                if not hint_utxos:
                    self._report_progress("⚠️ No UTxOs at hint address, falling back to full scan")
                    raise Exception("No UTxOs at hint")
                
                self._report_progress(f"✓ Found {len(hint_utxos)} UTxOs at hint address")
                
                units = self._extract_policy_units_from_utxos(hint_utxos, pointer.policy_id)
                
                if not units:
                    self._report_progress("⚠️ No matching policy assets at hint, falling back to full scan")
                    raise Exception("No matching assets at hint")
                
                self._report_progress(f"✅ Found {len(units)} assets at hint address!")
                
                return self._reconstruct_from_units(units, pointer)
                
            except Exception as e:
                self._report_progress(f"⚠️ Location hint failed: {e}")
        
        # Fallback: Full policy scan
        self._report_progress("🔍 Performing full policy scan (this may take longer)...")
        self.reconstruction_method = "⚠️ Full Policy Scan (No Hint)"
        
        return self._reconstruct_via_full_scan(pointer)
    
    def _extract_policy_units_from_utxos(self, utxos: List[Dict], policy_id: str) -> List[str]:
        """Extract all asset units matching the policy from a list of UTxOs"""
        units = []
        
        for utxo in utxos:
            amount = utxo.get('amount', [])
            
            if isinstance(amount, list):
                for asset in amount:
                    if isinstance(asset, dict):
                        unit = asset.get('unit', '')
                        if unit.startswith(policy_id):
                            units.append(unit)
            
            elif isinstance(amount, dict):
                for unit, qty in amount.items():
                    if unit.startswith(policy_id):
                        units.append(unit)
        
        return units
    
    def _reconstruct_via_full_scan(self, pointer: LegacyScrollPointer) -> Tuple[bytes, str]:
        """Reconstruct by scanning all assets under the policy"""
        units = []
        page = 1
        
        while True:
            try:
                batch = self.client._request(f"/assets/policy/{pointer.policy_id}?count=100&page={page}")
                
                if not batch:
                    break
                
                for item in batch:
                    if isinstance(item, str):
                        units.append(item)
                    elif isinstance(item, dict):
                        unit = item.get('asset') or item.get('unit')
                        if unit:
                            units.append(unit)
                
                page += 1
                
                if len(batch) < 100:
                    break
                    
            except Exception:
                break
        
        if not units:
            raise Exception("No assets found under this policy")
        
        self._report_progress(f"✓ Found {len(units)} assets under policy")
        
        return self._reconstruct_from_units(units, pointer)
    
    def _reconstruct_from_units(self, units: List[str], pointer: LegacyScrollPointer) -> Tuple[bytes, str]:
        """Reconstruct scroll from a list of asset units"""
        pages = []
        
        for i, unit in enumerate(units):
            if i % 10 == 0:
                self._report_progress(f"📄 Processing asset {i+1}/{len(units)}...")
            
            try:
                asset_info = self.client.query_asset_metadata(unit)
                
                meta = None
                for key in ('onchain_metadata', 'onchain_metadata_standard', 'metadata'):
                    if key in asset_info and isinstance(asset_info[key], dict):
                        meta = asset_info[key]
                        break
                
                if not meta:
                    continue
                
                asset_name = asset_info.get('asset_name', '')
                is_manifest = (
                    meta.get('role') == 'manifest' or
                    'MANIFEST' in asset_name or
                    ('pages' in meta and isinstance(meta['pages'], list))
                )
                
                if is_manifest:
                    continue
                
                if 'payload' in meta and 'i' in meta:
                    pages.append({
                        'index': int(meta['i']),
                        'payload': meta['payload']
                    })
                    
            except Exception:
                continue
        
        if not pages:
            raise Exception("No page NFTs found with 'payload' and 'i' fields")
        
        self._report_progress(f"✓ Found {len(pages)} pages")
        
        pages.sort(key=lambda p: p['index'])
        
        self._report_progress("🔗 Concatenating payloads...")
        all_hex = ""
        
        for page in pages:
            payload = page['payload']
            
            if isinstance(payload, list):
                for entry in payload:
                    if isinstance(entry, dict) and 'bytes' in entry:
                        hex_str = entry['bytes']
                        hex_str = hex_str.replace('0x', '').replace('0X', '')
                        hex_str = hex_str.replace(' ', '').replace('\n', '').replace('\r', '')
                        all_hex += hex_str
                    elif isinstance(entry, str):
                        hex_str = entry
                        hex_str = hex_str.replace('0x', '').replace('0X', '')
                        hex_str = hex_str.replace(' ', '').replace('\n', '').replace('\r', '')
                        all_hex += hex_str
        
        self._report_progress(f"✓ Concatenated {len(all_hex)} hex characters")
        
        self._report_progress("🔄 Converting hex to bytes...")
        raw_bytes = self._hex_to_bytes(all_hex)
        
        is_gzipped = len(raw_bytes) >= 2 and raw_bytes[0] == 0x1f and raw_bytes[1] == 0x8b
        
        if pointer.codec != "none" or is_gzipped:
            if is_gzipped:
                self._report_progress(f"📂 Detected gzip compression, decompressing...")
            else:
                self._report_progress(f"📂 Decompressing ({pointer.codec})...")
            
            try:
                file_bytes = self._decompress(raw_bytes, "gzip")
                self._report_progress(f"✓ Decompressed to {len(file_bytes)} bytes")
            except Exception as e:
                self._report_progress(f"⚠️ Decompression failed, using raw bytes: {e}")
                file_bytes = raw_bytes
        else:
            file_bytes = raw_bytes
        
        return file_bytes, pointer.content_type


# ============================================================================
# GUI APPLICATION
# ============================================================================

class ScrollViewerGUI:
    """Main GUI application for Ledger Scrolls Viewer"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Ledger Scrolls Viewer - A Library That Cannot Burn")
        self.root.geometry("950x850")
        
        self.config = Config()
        self.client = None
        self.connection_mode = ConnectionMode.BLOCKFROST
        self.registry_client = None
        self.registry_scrolls = []
        self.current_registry = None
        
        self._setup_ui()
        self._load_initial_config()
        
        # Load default Registry in background after UI is ready
        self.root.after(500, self._load_default_registry)
    
    def _setup_ui(self):
        """Setup the user interface"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main container with scrollbar
        main_canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        main_frame = ttk.Frame(scrollable_frame, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            header_frame,
            text="📜 Ledger Scrolls Viewer v2.0",
            font=("Arial", 18, "bold")
        ).pack(anchor=tk.W)
        
        ttk.Label(
            header_frame,
            text='"A library that cannot burn" - Configurable Registries with QR support',
            font=("Arial", 9, "italic")
        ).pack(anchor=tk.W)
        
        # Registry Configuration (NEW)
        registry_config_frame = ttk.LabelFrame(main_frame, text="Registry Configuration", padding="10")
        registry_config_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(registry_config_frame, text="Registry Address:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.registry_addr_entry = ttk.Entry(registry_config_frame, width=50)
        self.registry_addr_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.registry_addr_entry.insert(0, DEFAULT_REGISTRY_ADDRESS)
        
        btn_frame = ttk.Frame(registry_config_frame)
        btn_frame.grid(row=0, column=2)
        
        ttk.Button(
            btn_frame,
            text="Load Registry",
            command=self._load_custom_registry
        ).pack(side=tk.LEFT, padx=2)
        
        if QR_AVAILABLE:
            ttk.Button(
                btn_frame,
                text="📷 Scan QR",
                command=self._scan_qr_registry
            ).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(registry_config_frame, text="Registry Name:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.registry_name_entry = ttk.Entry(registry_config_frame, width=30)
        self.registry_name_entry.grid(row=1, column=1, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.registry_name_entry.insert(0, "Default Public Registry")
        
        self.registry_status_label = ttk.Label(
            registry_config_frame,
            text="📡 Registry: Not loaded",
            font=("Arial", 8),
            foreground="gray"
        )
        self.registry_status_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
        registry_config_frame.columnconfigure(1, weight=1)
        
        # Connection settings
        connection_frame = ttk.LabelFrame(main_frame, text="Connection Settings", padding="10")
        connection_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(connection_frame, text="Mode:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.mode_var = tk.StringVar(value="blockfrost")
        mode_frame = ttk.Frame(connection_frame)
        mode_frame.grid(row=0, column=1, columnspan=2, sticky=tk.W)
        
        ttk.Radiobutton(
            mode_frame,
            text="Blockfrost API",
            variable=self.mode_var,
            value="blockfrost",
            command=self._on_mode_change
        ).pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Radiobutton(
            mode_frame,
            text="Local Node",
            variable=self.mode_var,
            value="local_node",
            command=self._on_mode_change
        ).pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Radiobutton(
            mode_frame,
            text="⚡ P2P Lightweight",
            variable=self.mode_var,
            value="p2p_lightweight",
            command=self._on_mode_change
        ).pack(side=tk.LEFT)
        
        # Blockfrost settings
        self.blockfrost_frame = ttk.Frame(connection_frame)
        self.blockfrost_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        self.blockfrost_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.blockfrost_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.api_key_entry = ttk.Entry(self.blockfrost_frame, show="*")
        self.api_key_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(
            self.blockfrost_frame,
            text="Save",
            command=self._save_blockfrost_key
        ).grid(row=0, column=2)
        
        # Local node settings
        self.node_frame = ttk.Frame(connection_frame)
        self.node_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        self.node_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.node_frame, text="Socket Path:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.node_socket_entry = ttk.Entry(self.node_frame)
        self.node_socket_entry.insert(0, "/opt/cardano/cnode/sockets/node.socket")
        self.node_socket_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(
            self.node_frame,
            text="Test & Save",
            command=self._test_and_save_node_config
        ).grid(row=0, column=2)
        
        self.node_frame.grid_remove()
        
        # P2P settings (ENHANCED)
        self.p2p_frame = ttk.Frame(connection_frame)
        self.p2p_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        self.p2p_frame.columnconfigure(1, weight=1)
        
        # Explanation banner
        p2p_info = ttk.Frame(self.p2p_frame)
        p2p_info.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(
            p2p_info,
            text="⚡ P2P 'Sync Deception' Mode",
            font=("Arial", 10, "bold"),
            foreground="blue"
        ).pack(anchor=tk.W)
        
        ttk.Label(
            p2p_info,
            text="Connect to relay, pretend to sync, query specific blocks, disconnect quickly.",
            font=("Arial", 8),
            foreground="gray"
        ).pack(anchor=tk.W)
        
        ttk.Label(
            p2p_info,
            text="⚠️ EXPERIMENTAL - Protocol implementation in progress",
            font=("Arial", 8, "bold"),
            foreground="orange"
        ).pack(anchor=tk.W)
        
        ttk.Label(self.p2p_frame, text="Relay IP:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.p2p_host_entry = ttk.Entry(self.p2p_frame)
        self.p2p_host_entry.insert(0, "")
        self.p2p_host_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Label(self.p2p_frame, text="Port:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.p2p_port_entry = ttk.Entry(self.p2p_frame)
        self.p2p_port_entry.insert(0, "3001")
        self.p2p_port_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=(5, 0))
        
        ttk.Button(
            self.p2p_frame,
            text="Test Connection",
            command=self._test_p2p_connection
        ).grid(row=2, column=2, pady=(5, 0))
        
        self.p2p_frame.grid_remove()
        
        connection_frame.columnconfigure(1, weight=1)
        
        # Registry Browser
        browser_frame = ttk.LabelFrame(main_frame, text="Scroll Browser", padding="10")
        browser_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(browser_frame, text="Available Scrolls:").pack(anchor=tk.W, pady=(0, 5))
        
        scroll_select_frame = ttk.Frame(browser_frame)
        scroll_select_frame.pack(fill=tk.X)
        scroll_select_frame.columnconfigure(0, weight=1)
        
        self.scroll_combo = ttk.Combobox(scroll_select_frame, state="readonly")
        self.scroll_combo.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.scroll_combo['values'] = ["Loading Registry..."]
        self.scroll_combo.current(0)
        
        ttk.Button(
            scroll_select_frame,
            text="📖 Load Scroll",
            command=self._load_selected_scroll
        ).grid(row=0, column=1, padx=2)
        
        ttk.Button(
            scroll_select_frame,
            text="🔄 Refresh",
            command=self._refresh_registry
        ).grid(row=0, column=2, padx=2)
        
        ttk.Button(
            scroll_select_frame,
            text="🔧 Custom",
            command=self._open_custom_scroll_dialog
        ).grid(row=0, column=3, padx=2)
        
        self.method_label = ttk.Label(
            browser_frame,
            text="",
            font=("Arial", 8, "italic"),
            foreground="gray"
        )
        self.method_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Progress/log area
        log_frame = ttk.LabelFrame(main_frame, text="Progress & Status", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            height=12,
            font=("Courier", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = ttk.Label(
            status_frame,
            text="Ready - Initializing...",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.pack(fill=tk.X)
        
        # Welcome message
        self._log("=" * 80)
        self._log("Welcome to Ledger Scrolls Viewer v2.0")
        self._log("Registry-Based Discovery | QR Support | P2P Lightweight Mode")
        self._log("=" * 80)
        self._log("")
        if QR_AVAILABLE:
            self._log("✓ QR code scanner available")
        else:
            self._log("ℹ️  QR code scanner not available (install opencv-python and pyzbar)")
        self._log("")
    
    def _load_initial_config(self):
        """Load saved configuration"""
        # Blockfrost
        saved_key = self.config.get_blockfrost_key()
        if saved_key:
            self.api_key_entry.insert(0, saved_key)
            self._log("✓ Loaded saved Blockfrost API key")
        
        # Node
        node_config = self.config.get_node_config()
        if node_config and node_config.socket_path:
            self.node_socket_entry.delete(0, tk.END)
            self.node_socket_entry.insert(0, node_config.socket_path)
            self._log("✓ Loaded saved node configuration")
        
        # P2P
        p2p_config = self.config.get_p2p_config()
        if p2p_config:
            self.p2p_host_entry.delete(0, tk.END)
            self.p2p_host_entry.insert(0, p2p_config.relay_host)
            self.p2p_port_entry.delete(0, tk.END)
            self.p2p_port_entry.insert(0, str(p2p_config.relay_port))
            self._log("✓ Loaded saved P2P configuration")
        
        # Registry
        saved_registry = self.config.get_registry_pointer()
        if saved_registry:
            self.registry_addr_entry.delete(0, tk.END)
            self.registry_addr_entry.insert(0, saved_registry.address)
            self.registry_name_entry.delete(0, tk.END)
            self.registry_name_entry.insert(0, saved_registry.name)
            self._log(f"✓ Loaded saved Registry: {saved_registry.name}")
    
    def _load_default_registry(self):
        """Load the default public Registry"""
        self._log("🔄 Loading default Registry...")
        registry_pointer = RegistryPointer(
            address=DEFAULT_REGISTRY_ADDRESS,
            policy_id=DEFAULT_REGISTRY_POLICY_ID,
            asset_hex=DEFAULT_REGISTRY_ASSET_HEX,
            name="Default Public Registry"
        )
        self._load_registry(registry_pointer)
    
    def _load_custom_registry(self):
        """Load a custom Registry from user input"""
        address = self.registry_addr_entry.get().strip()
        name = self.registry_name_entry.get().strip() or "Custom Registry"
        
        if not address:
            messagebox.showwarning("Invalid Input", "Please enter a Registry address")
            return
        
        registry_pointer = RegistryPointer(
            address=address,
            name=name
        )
        
        # Save for next time
        self.config.set_registry_pointer(registry_pointer)
        
        self._load_registry(registry_pointer)
    
    def _scan_qr_registry(self):
        """Scan QR code to get Registry address"""
        try:
            qr_data = QRScanner.scan_qr_code()
            
            if qr_data:
                # QR code might contain JSON with full Registry info or just an address
                try:
                    registry_json = json.loads(qr_data)
                    address = registry_json.get('address')
                    name = registry_json.get('name', 'QR Scanned Registry')
                    policy_id = registry_json.get('policy_id')
                    asset_hex = registry_json.get('asset_hex')
                except:
                    # Plain address
                    address = qr_data
                    name = "QR Scanned Registry"
                    policy_id = None
                    asset_hex = None
                
                # Update UI
                self.registry_addr_entry.delete(0, tk.END)
                self.registry_addr_entry.insert(0, address)
                self.registry_name_entry.delete(0, tk.END)
                self.registry_name_entry.insert(0, name)
                
                # Load it
                registry_pointer = RegistryPointer(
                    address=address,
                    policy_id=policy_id,
                    asset_hex=asset_hex,
                    name=name
                )
                
                self.config.set_registry_pointer(registry_pointer)
                self._load_registry(registry_pointer)
        
        except Exception as e:
            messagebox.showerror("QR Scan Failed", str(e))
    
    def _load_registry(self, registry_pointer: RegistryPointer):
        """Load a Registry in background thread"""
        def load_thread():
            try:
                client = self._get_client()
                self.registry_client = RegistryClient(client, registry_pointer, progress_callback=self._log)
                
                scrolls = self.registry_client.load_registry()
                self.registry_scrolls = scrolls
                self.current_registry = registry_pointer
                
                self.root.after(0, self._populate_registry_dropdown)
                
            except Exception as e:
                error_msg = f"Failed to load Registry: {e}"
                self._log(f"❌ {error_msg}")
                self.root.after(0, lambda: self._set_status("Registry load failed"))
                self.root.after(0, lambda: self._populate_registry_dropdown(failed=True))
        
        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()
    
    def _refresh_registry(self):
        """Reload the current Registry"""
        if self.current_registry:
            self._load_registry(self.current_registry)
        else:
            self._load_custom_registry()
    
    def _populate_registry_dropdown(self, failed=False):
        """Populate dropdown with scrolls"""
        if failed:
            self.scroll_combo['values'] = ["Registry failed to load - use Custom Scroll"]
            self.scroll_combo.current(0)
            self.registry_status_label.config(
                text="📡 Registry: Failed to load",
                foreground="red"
            )
            return
        
        if not self.registry_scrolls:
            self.scroll_combo['values'] = ["No scrolls found"]
            self.scroll_combo.current(0)
            self.registry_status_label.config(
                text="📡 Registry: Loaded (0 scrolls)",
                foreground="orange"
            )
            return
        
        scroll_names = [f"{scroll['title']} ({scroll.get('type', 'unknown')})" 
                       for scroll in self.registry_scrolls]
        
        self.scroll_combo['values'] = scroll_names
        self.scroll_combo.current(0)
        
        self._log(f"✅ Registry populated with {len(self.registry_scrolls)} scrolls")
        self._set_status(f"Ready - {len(self.registry_scrolls)} scrolls available")
        
        registry_name = self.current_registry.name if self.current_registry else "Unknown"
        self.registry_status_label.config(
            text=f"📡 Registry: {registry_name} ({len(self.registry_scrolls)} scrolls)",
            foreground="green"
        )
    
    def _load_selected_scroll(self):
        """Load the selected scroll from dropdown"""
        selection = self.scroll_combo.current()
        
        if selection < 0 or selection >= len(self.registry_scrolls):
            messagebox.showwarning("No Selection", "Please select a scroll")
            return
        
        scroll_entry = self.registry_scrolls[selection]
        scroll_type = scroll_entry.get('type')
        
        if scroll_type == 'utxo_datum_bytes_v1':
            pointer = StandardScrollPointer(
                lock_address=scroll_entry['lock_address'],
                lock_txin=scroll_entry['lock_txin'],
                content_type=scroll_entry['content_type'],
                codec=scroll_entry['codec'],
                sha256=scroll_entry.get('sha256')
            )
        elif scroll_type == 'cip25_pages_v1':
            pointer = LegacyScrollPointer(
                policy_id=scroll_entry['policy_id'],
                manifest_tx_hash=scroll_entry['manifest_tx_hash'],
                content_type=scroll_entry['content_type'],
                codec=scroll_entry['codec'],
                manifest_slot=scroll_entry.get('manifest_slot'),
                location_hint=scroll_entry.get('location_hint')
            )
        else:
            messagebox.showerror("Error", f"Unknown scroll type: {scroll_type}")
            return
        
        self._fetch_scroll(pointer, scroll_entry['title'])
    
    def _on_mode_change(self):
        """Handle connection mode change"""
        mode = self.mode_var.get()
        
        if mode == "blockfrost":
            self.connection_mode = ConnectionMode.BLOCKFROST
            self.blockfrost_frame.grid()
            self.node_frame.grid_remove()
            self.p2p_frame.grid_remove()
            self._log("📡 Switched to Blockfrost API mode")
        elif mode == "local_node":
            self.connection_mode = ConnectionMode.LOCAL_NODE
            self.blockfrost_frame.grid_remove()
            self.node_frame.grid()
            self.p2p_frame.grid_remove()
            self._log("🖥️ Switched to Local Node mode")
        else:
            self.connection_mode = ConnectionMode.P2P_LIGHTWEIGHT
            self.blockfrost_frame.grid_remove()
            self.node_frame.grid_remove()
            self.p2p_frame.grid()
            self._log("⚡ Switched to P2P Lightweight 'Sync Deception' mode")
            self._log("💡 Enter relay IP/port and test connection")
    
    def _save_blockfrost_key(self):
        """Save Blockfrost API key"""
        key = self.api_key_entry.get().strip()
        if not key:
            messagebox.showwarning("Invalid Input", "Please enter an API key")
            return
        
        self.config.set_blockfrost_key(key)
        self._log("✓ Blockfrost API key saved")
        messagebox.showinfo("Success", "API key saved!")
    
    def _test_and_save_node_config(self):
        """Test and save node configuration"""
        socket_path = self.node_socket_entry.get().strip()
        
        if not socket_path:
            messagebox.showwarning("Invalid Input", "Please enter socket path")
            return
        
        node_config = NodeConfig(
            host="localhost",
            port=3001,
            socket_path=socket_path
        )
        
        self._log("🔍 Testing node connection...")
        try:
            test_client = LocalNodeClient(node_config)
            self._log("✓ cardano-cli is available")
            
            self.config.set_node_config(node_config)
            self._log("✓ Node configuration saved")
            messagebox.showinfo("Success", "Node configuration saved!")
            
        except Exception as e:
            self._log(f"❌ Node test failed: {e}")
            messagebox.showerror("Connection Error", str(e))
    
    def _test_p2p_connection(self):
        """Test P2P connection"""
        relay_host = self.p2p_host_entry.get().strip()
        relay_port_str = self.p2p_port_entry.get().strip()
        
        if not relay_host:
            messagebox.showwarning("Invalid Input", "Please enter relay IP address")
            return
        
        try:
            relay_port = int(relay_port_str) if relay_port_str else 3001
        except ValueError:
            messagebox.showwarning("Invalid Input", "Port must be a number")
            return
        
        p2p_config = P2PConfig(
            relay_host=relay_host,
            relay_port=relay_port,
            network="mainnet"
        )
        
        self.config.set_p2p_config(p2p_config)
        
        self._log("⚡ Testing P2P connection...")
        self._log(f"📡 Connecting to {relay_host}:{relay_port}...")
        
        try:
            test_client = P2PLightweightClient(p2p_config)
            test_client.connect_to_relay()
        except NotImplementedError as e:
            self._log("⚠️ P2P protocol not yet implemented")
            messagebox.showinfo("Not Implemented", str(e))
        except Exception as e:
            self._log(f"❌ Connection failed: {e}")
            messagebox.showerror("Connection Error", str(e))
    
    def _log(self, message: str):
        """Add message to log"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def _set_status(self, status: str):
        """Update status bar"""
        self.status_label.config(text=status)
        self.root.update_idletasks()
    
    def _get_client(self):
        """Get appropriate blockchain client"""
        if self.connection_mode == ConnectionMode.BLOCKFROST:
            api_key = self.api_key_entry.get().strip()
            if not api_key:
                raise Exception("Please enter and save Blockfrost API key")
            return BlockfrostClient(api_key)
        
        elif self.connection_mode == ConnectionMode.LOCAL_NODE:
            node_config = self.config.get_node_config()
            if not node_config:
                socket_path = self.node_socket_entry.get().strip()
                if not socket_path:
                    raise Exception("Please configure node settings")
                node_config = NodeConfig(host="localhost", port=3001, socket_path=socket_path)
            
            return LocalNodeClient(node_config)
        
        else:  # P2P
            p2p_config = self.config.get_p2p_config()
            if not p2p_config:
                relay_host = self.p2p_host_entry.get().strip()
                relay_port_str = self.p2p_port_entry.get().strip()
                if not relay_host:
                    raise Exception("Please enter relay IP address")
                p2p_config = P2PConfig(
                    relay_host=relay_host,
                    relay_port=int(relay_port_str) if relay_port_str else 3001
                )
            
            return P2PLightweightClient(p2p_config)
    
    def _fetch_scroll(self, pointer, scroll_title: str):
        """Fetch and save a scroll"""
        def fetch_thread():
            try:
                self._set_status(f"Fetching {scroll_title}...")
                self._log("")
                self._log("=" * 80)
                self._log(f"FETCHING: {scroll_title}")
                self._log("=" * 80)
                
                client = self._get_client()
                reconstructor = ScrollReconstructor(client, progress_callback=self._log)
                
                if isinstance(pointer, StandardScrollPointer):
                    self._log("📌 Scroll Type: Standard (Locked UTxO)")
                    file_bytes, content_type = reconstructor.reconstruct_standard_scroll(pointer)
                else:
                    self._log("📌 Scroll Type: Legacy (Pages + Manifest)")
                    if pointer.location_hint:
                        self._log(f"🎯 Using hybrid pointer with location hint")
                    file_bytes, content_type = reconstructor.reconstruct_legacy_scroll(pointer)
                
                method = reconstructor.reconstruction_method
                self.root.after(0, lambda: self.method_label.config(text=f"Last method: {method}"))
                
                ext_map = {
                    "image/png": ".png",
                    "text/html": ".html",
                    "text/plain": ".txt",
                    "application/pdf": ".pdf"
                }
                
                ext = ext_map.get(content_type, ".bin")
                
                # Auto-detect HTML
                if content_type == "text/plain" and len(file_bytes) > 100:
                    try:
                        preview = file_bytes[:500].decode('utf-8', errors='ignore').lower()
                        if any(m in preview for m in ['<!doctype html', '<html', '<head', '<body']):
                            ext = ".html"
                            self._log("🔍 Auto-detected HTML, using .html extension")
                    except:
                        pass
                
                safe_title = "".join(c for c in scroll_title if c.isalnum() or c in (' ', '-', '_')).strip()
                filename = f"{safe_title}{ext}"
                filepath = self.config.downloads_dir / filename
                
                with open(filepath, 'wb') as f:
                    f.write(file_bytes)
                
                self._log("")
                self._log("=" * 80)
                self._log(f"✅ SUCCESS!")
                self._log(f"📁 Location: {filepath}")
                self._log(f"📊 Size: {len(file_bytes):,} bytes")
                self._log(f"📄 Type: {content_type}")
                self._log(f"🔧 Method: {method}")
                self._log("=" * 80)
                self._set_status(f"Success! Saved to {filepath}")
                
                self.root.after(0, lambda: self._ask_open_file(filepath))
                
            except Exception as e:
                error_msg = str(e)
                self._log("")
                self._log("=" * 80)
                self._log(f"❌ ERROR: {error_msg}")
                self._log("=" * 80)
                self._set_status("Error occurred")
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Error", msg))
        
        thread = threading.Thread(target=fetch_thread, daemon=True)
        thread.start()
    
    def _ask_open_file(self, filepath: Path):
        """Ask user if they want to open the file"""
        response = messagebox.askyesno(
            "File Saved",
            f"Scroll saved to:\n{filepath}\n\nOpen it?"
        )
        
        if response:
            self._open_file(filepath)
    
    def _open_file(self, filepath: Path):
        """Open file with default application"""
        import platform
        
        try:
            if platform.system() == 'Darwin':
                subprocess.call(('open', str(filepath)))
            elif platform.system() == 'Windows':
                os.startfile(str(filepath))
            else:
                subprocess.call(('xdg-open', str(filepath)))
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")
    
    def _open_custom_scroll_dialog(self):
        """Open dialog for custom scroll input"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Custom Scroll")
        dialog.geometry("600x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Scroll Type:").pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        scroll_type_var = tk.StringVar(value="standard")
        
        type_frame = ttk.Frame(dialog)
        type_frame.pack(fill=tk.X, padx=10)
        
        ttk.Radiobutton(
            type_frame,
            text="Standard (Locked UTxO)",
            variable=scroll_type_var,
            value="standard"
        ).pack(anchor=tk.W)
        
        ttk.Radiobutton(
            type_frame,
            text="Legacy (Pages + Manifest)",
            variable=scroll_type_var,
            value="legacy"
        ).pack(anchor=tk.W)
        
        # Standard inputs
        std_frame = ttk.LabelFrame(dialog, text="Standard Scroll", padding="10")
        std_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(std_frame, text="Lock Address:").grid(row=0, column=0, sticky=tk.W)
        std_addr = ttk.Entry(std_frame, width=50)
        std_addr.grid(row=0, column=1, pady=5)
        
        ttk.Label(std_frame, text="Lock TxIn:").grid(row=1, column=0, sticky=tk.W)
        std_txin = ttk.Entry(std_frame, width=50)
        std_txin.grid(row=1, column=1, pady=5)
        
        ttk.Label(std_frame, text="Content Type:").grid(row=2, column=0, sticky=tk.W)
        std_ctype = ttk.Entry(std_frame, width=50)
        std_ctype.insert(0, "image/png")
        std_ctype.grid(row=2, column=1, pady=5)
        
        ttk.Label(std_frame, text="Codec:").grid(row=3, column=0, sticky=tk.W)
        std_codec = tk.StringVar(value="none")
        codec_f = ttk.Frame(std_frame)
        codec_f.grid(row=3, column=1, sticky=tk.W, pady=5)
        ttk.Radiobutton(codec_f, text="none", variable=std_codec, value="none").pack(side=tk.LEFT)
        ttk.Radiobutton(codec_f, text="gzip", variable=std_codec, value="gzip").pack(side=tk.LEFT)
        
        # Legacy inputs
        leg_frame = ttk.LabelFrame(dialog, text="Legacy Scroll", padding="10")
        leg_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(leg_frame, text="Policy ID:").grid(row=0, column=0, sticky=tk.W)
        leg_policy = ttk.Entry(leg_frame, width=50)
        leg_policy.grid(row=0, column=1, pady=5)
        
        ttk.Label(leg_frame, text="Manifest Tx:").grid(row=1, column=0, sticky=tk.W)
        leg_tx = ttk.Entry(leg_frame, width=50)
        leg_tx.grid(row=1, column=1, pady=5)
        
        ttk.Label(leg_frame, text="Location Hint:").grid(row=2, column=0, sticky=tk.W)
        leg_hint = ttk.Entry(leg_frame, width=50)
        leg_hint.grid(row=2, column=1, pady=5)
        
        ttk.Label(leg_frame, text="Content Type:").grid(row=3, column=0, sticky=tk.W)
        leg_ctype = ttk.Entry(leg_frame, width=50)
        leg_ctype.insert(0, "text/html")
        leg_ctype.grid(row=3, column=1, pady=5)
        
        ttk.Label(leg_frame, text="Codec:").grid(row=4, column=0, sticky=tk.W)
        leg_codec = tk.StringVar(value="gzip")
        leg_codec_f = ttk.Frame(leg_frame)
        leg_codec_f.grid(row=4, column=1, sticky=tk.W, pady=5)
        ttk.Radiobutton(leg_codec_f, text="none", variable=leg_codec, value="none").pack(side=tk.LEFT)
        ttk.Radiobutton(leg_codec_f, text="gzip", variable=leg_codec, value="gzip").pack(side=tk.LEFT)
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def fetch_custom():
            try:
                if scroll_type_var.get() == "standard":
                    pointer = StandardScrollPointer(
                        lock_address=std_addr.get().strip(),
                        lock_txin=std_txin.get().strip(),
                        content_type=std_ctype.get().strip(),
                        codec=std_codec.get()
                    )
                    title = "Custom Standard Scroll"
                else:
                    pointer = LegacyScrollPointer(
                        policy_id=leg_policy.get().strip(),
                        manifest_tx_hash=leg_tx.get().strip(),
                        content_type=leg_ctype.get().strip(),
                        codec=leg_codec.get(),
                        location_hint=leg_hint.get().strip() or None
                    )
                    title = "Custom Legacy Scroll"
                
                dialog.destroy()
                self._fetch_scroll(pointer, title)
                
            except Exception as e:
                messagebox.showerror("Invalid Input", str(e))
        
        ttk.Button(btn_frame, text="Fetch Scroll", command=fetch_custom).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main application entry point"""
    root = tk.Tk()
    app = ScrollViewerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
