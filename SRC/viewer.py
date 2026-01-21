#!/usr/bin/env python3
"""
Ledger Scrolls Viewer - "A library that cannot burn."

A permissionless, decentralized viewer for immutable data on the Cardano blockchain.
Supports both Blockfrost API and direct local node communication.

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
    P2P_EXPERIMENTAL = "p2p_experimental"  # Lightweight P2P client


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


@dataclass
class NodeConfig:
    """Configuration for local Cardano node connection"""
    host: str
    port: int
    socket_path: Optional[str] = None
    network: str = "mainnet"


@dataclass
class P2PConfig:
    """Configuration for experimental P2P lightweight client"""
    relay_host: str
    relay_port: int = 6000
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
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                
                # Small delay to avoid rate limits
                time.sleep(0.1)
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    raise Exception(f"Blockfrost request failed after {retries} attempts: {e}")
                print(f"Retry {attempt + 1}/{retries}...")
                time.sleep(1)  # Wait before retry
        
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
                
                if len(page_utxos) < 100:  # Blockfrost page size
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
            # Provide more context in error
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
        
        # Add socket path if configured
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
            
            # Parse JSON if output exists
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
        # Note: cardano-cli doesn't have a direct metadata query
        # We need to query the full tx and extract metadata
        args = [
            "query", "tx",
            f"--{self.config.network}",
            "--tx-id", tx_hash,
            "--out-file", "/dev/stdout"
        ]
        
        try:
            tx_data = self._run_cli(args)
            metadata = tx_data.get("metadata", {})
            
            # Convert to Blockfrost-like format
            result = []
            for label, value in metadata.items():
                result.append({
                    "label": label,
                    "json_metadata": value
                })
            
            return result
        except Exception:
            # Fallback: try to get tx info if full query not supported
            return []


class P2PLightweightClient:
    """
    EXPERIMENTAL: Lightweight P2P client for direct blockchain queries
    
    This client connects directly to Cardano relay nodes via the Ouroboros P2P protocol
    to fetch specific data without requiring a full node sync.
    
    Status: UNDER CONSTRUCTION - May have bugs and limitations
    """
    
    def __init__(self, config: P2PConfig):
        self.config = config
        self.cache_dir = Path(config.cache_dir) if config.cache_dir else Path.home() / ".ledger-scrolls" / "p2p_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"P2P Client initialized - Relay: {config.relay_host}:{config.relay_port}")
        logger.warning("P2P Lightweight mode is EXPERIMENTAL - expect bugs!")
    
    def query_utxo_at_address(self, address: str) -> List[Dict]:
        """
        Query UTxOs at address using P2P protocol
        
        NOTE: This is a stub implementation. Full P2P protocol implementation required.
        """
        logger.info(f"P2P Query: UTxO at address {address[:20]}...")
        
        # TODO: Implement Ouroboros mini-protocol query
        # For now, raise informative error
        raise NotImplementedError(
            "P2P UTxO queries not yet implemented.\n"
            "This requires implementing Ouroboros local-state-query mini-protocol.\n"
            "Current workaround: Use Blockfrost or Local Node mode.\n\n"
            "Estimated implementation: 4-6 weeks\n"
            "See lightweight_p2p_client_design.md for technical details."
        )
    
    def query_tx_metadata(self, tx_hash: str) -> Dict:
        """
        Query transaction metadata using P2P protocol
        
        NOTE: This is a stub implementation. Full P2P protocol implementation required.
        """
        logger.info(f"P2P Query: Tx metadata for {tx_hash[:20]}...")
        
        # TODO: Implement block-fetch + CBOR parsing
        raise NotImplementedError(
            "P2P transaction queries not yet implemented.\n"
            "This requires:\n"
            "  1. Ouroboros block-fetch mini-protocol\n"
            "  2. CBOR block parsing\n"
            "  3. Transaction extraction\n\n"
            "Use Blockfrost or Local Node mode for now."
        )
    
    def _request(self, endpoint: str) -> Dict:
        """Placeholder for API compatibility"""
        raise NotImplementedError("P2P mode does not use REST endpoints")
    
    # Future methods to implement:
    def _connect_to_relay(self):
        """Establish TCP connection and perform Ouroboros handshake"""
        pass
    
    def _fetch_block_by_hash(self, block_hash: str):
        """Use block-fetch mini-protocol to get specific block"""
        pass
    
    def _parse_block_cbor(self, cbor_data: bytes):
        """Parse CBOR-encoded block data"""
        pass
    
    def _extract_tx_from_block(self, block, tx_hash: str):
        """Extract specific transaction from parsed block"""
        pass


# ============================================================================
# SCROLL RECONSTRUCTION ENGINE
# ============================================================================

class ScrollReconstructor:
    """Reconstructs scroll files from on-chain data"""
    
    def __init__(self, client, progress_callback=None):
        self.client = client
        self.progress_callback = progress_callback
    
    def _report_progress(self, message: str):
        """Report progress to callback"""
        if self.progress_callback:
            self.progress_callback(message)
        else:
            print(message)
    
    def _verify_hash(self, data: bytes, expected_hash: Optional[str]) -> bool:
        """Verify SHA256 hash of data"""
        if not expected_hash:
            return True
        
        actual_hash = hashlib.sha256(data).hexdigest()
        return actual_hash.lower() == expected_hash.lower()
    
    def _hex_to_bytes(self, hex_str: str) -> bytes:
        """Convert hex string to bytes, cleaning any non-hex characters"""
        # Remove whitespace, newlines, and any other non-hex characters
        cleaned = ''.join(c for c in hex_str if c in '0123456789abcdefABCDEF')
        
        if len(cleaned) % 2 != 0:
            raise ValueError(f"Hex string has odd length ({len(cleaned)} chars) after cleaning")
        
        try:
            return binascii.unhexlify(cleaned)
        except binascii.Error as e:
            # Show first 100 chars for debugging
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
        """
        Reconstruct a Standard Scroll from locked UTxO datum
        
        Returns: (file_bytes, content_type)
        """
        self._report_progress("🔍 Querying locked UTxO address...")
        
        # Query UTxOs at lock address
        utxos = self.client.query_utxo_at_address(pointer.lock_address)
        
        if not utxos:
            raise Exception(f"No UTxOs found at lock address: {pointer.lock_address}")
        
        self._report_progress(f"✓ Found {len(utxos)} UTxO(s) at lock address")
        
        # Find the specific UTxO by txin
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
        
        # Extract inline datum
        inline_datum = target_utxo.get('inline_datum')
        if not inline_datum:
            raise Exception("UTxO does not contain inline datum")
        
        self._report_progress("📦 Extracting datum bytes...")
        
        # Parse datum structure
        # Blockfrost returns inline_datum as a string (CBOR hex), need to decode
        # Standard format after decode: {"constructor": 0, "fields": [{"bytes": "hex..."}]}
        
        if isinstance(inline_datum, str):
            # Blockfrost returns CBOR hex string, we need to extract bytes from it
            # For now, try to decode it as JSON first in case it's already parsed
            try:
                import cbor2
                # Decode CBOR hex string
                cbor_bytes = self._hex_to_bytes(inline_datum)
                datum_obj = cbor2.loads(cbor_bytes)
                
                # Handle CBOR structure
                if isinstance(datum_obj, list) and len(datum_obj) >= 2:
                    # CBOR array format: [constructor, fields]
                    fields = datum_obj[1]
                    if isinstance(fields, list) and len(fields) > 0:
                        # First field should be bytes
                        hex_data = fields[0].hex() if isinstance(fields[0], bytes) else str(fields[0])
                    else:
                        raise Exception("Unexpected CBOR fields structure")
                elif isinstance(datum_obj, bytes):
                    # Direct bytes
                    hex_data = datum_obj.hex()
                else:
                    raise Exception(f"Unexpected CBOR datum structure: {type(datum_obj)}")
            except ImportError:
                # Fallback: Try to extract hex directly from CBOR without library
                # This is a simplified approach for the specific datum format we use
                raise Exception("cbor2 library required for datum parsing. Install with: pip install cbor2")
            except Exception as e:
                raise Exception(f"Failed to parse CBOR datum: {e}")
        
        elif isinstance(inline_datum, dict):
            # Already parsed format
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
            raise Exception(f"Datum is not a string or dict, it's: {type(inline_datum)}")
        
        self._report_progress("🔄 Converting hex to bytes...")
        raw_bytes = self._hex_to_bytes(hex_data)
        
        self._report_progress(f"✓ Extracted {len(raw_bytes)} bytes")
        
        # Decompress if needed
        if pointer.codec != "none":
            self._report_progress(f"📂 Decompressing ({pointer.codec})...")
            file_bytes = self._decompress(raw_bytes, pointer.codec)
            self._report_progress(f"✓ Decompressed to {len(file_bytes)} bytes")
        else:
            file_bytes = raw_bytes
        
        # Verify hash
        if pointer.sha256:
            self._report_progress("🔐 Verifying hash...")
            if self._verify_hash(file_bytes, pointer.sha256):
                self._report_progress("✓ Hash verification PASSED ✓")
            else:
                self._report_progress("⚠️  Hash verification FAILED")
                raise Exception("Hash mismatch - data may be corrupted")
        
        return file_bytes, pointer.content_type
    
    def reconstruct_legacy_scroll(self, pointer: LegacyScrollPointer) -> Tuple[bytes, str]:
        """
        Reconstruct a Legacy Scroll from pages + manifest NFTs
        Matches the approach used in the working website
        
        Returns: (file_bytes, content_type)
        """
        self._report_progress("📜 Fetching all assets under policy...")
        
        # Step 1: Fetch all asset units under the policy
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
        
        self._report_progress(f"✓ Found {len(units)} assets")
        
        # Step 2: Fetch each asset and extract pages
        pages = []
        manifest = None
        
        for i, unit in enumerate(units):
            if i % 10 == 0:
                self._report_progress(f"🔍 Processing asset {i+1}/{len(units)}...")
            
            try:
                asset_info = self.client.query_asset_metadata(unit)
                
                # Extract metadata
                meta = None
                for key in ('onchain_metadata', 'onchain_metadata_standard', 'metadata'):
                    if key in asset_info and isinstance(asset_info[key], dict):
                        meta = asset_info[key]
                        break
                
                if not meta:
                    continue
                
                # Check if manifest
                asset_name = asset_info.get('asset_name', '')
                is_manifest = (
                    meta.get('role') == 'manifest' or
                    'MANIFEST' in asset_name or
                    ('pages' in meta and isinstance(meta['pages'], list))
                )
                
                if is_manifest and not manifest:
                    manifest = meta
                    continue
                
                # Check if page (has payload and index 'i')
                if 'payload' in meta and 'i' in meta:
                    pages.append({
                        'index': int(meta['i']),
                        'payload': meta['payload']
                    })
                    
            except Exception as e:
                continue
        
        if not pages:
            raise Exception("No page NFTs found with 'payload' and 'i' fields")
        
        self._report_progress(f"✓ Found {len(pages)} pages")
        
        # Step 3: Sort by index
        pages.sort(key=lambda p: p['index'])
        
        # Step 4: Concatenate payloads
        self._report_progress("🔗 Concatenating payloads...")
        all_hex = ""
        
        for page in pages:
            payload = page['payload']
            
            # Handle payload format
            if isinstance(payload, list):
                for entry in payload:
                    if isinstance(entry, dict) and 'bytes' in entry:
                        hex_str = entry['bytes']
                        # Remove 0x prefix and clean
                        hex_str = hex_str.replace('0x', '').replace('0X', '')
                        hex_str = hex_str.replace(' ', '').replace('\n', '').replace('\r', '')
                        all_hex += hex_str
                    elif isinstance(entry, str):
                        hex_str = entry
                        # Remove 0x prefix and clean
                        hex_str = hex_str.replace('0x', '').replace('0X', '')
                        hex_str = hex_str.replace(' ', '').replace('\n', '').replace('\r', '')
                        all_hex += hex_str
        
        self._report_progress(f"✓ Concatenated {len(all_hex)} hex characters")
        
        # Step 5: Convert to bytes
        self._report_progress("🔄 Converting hex to bytes...")
        raw_bytes = self._hex_to_bytes(all_hex)
        
        # Step 6: Decompress if needed
        # Check if data starts with gzip magic bytes (1f 8b) even if codec says "none"
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
                self._report_progress(f"⚠️  Decompression failed, using raw bytes: {e}")
                file_bytes = raw_bytes
        else:
            file_bytes = raw_bytes
        
        return file_bytes, pointer.content_type
    
    def _parse_manifest(self, metadata_list: List[Dict], policy_id: str) -> Dict:
        """Parse manifest from transaction metadata"""
        manifest_data = None
        all_asset_names = []
        
        # Look for CIP-25 structure
        for item in metadata_list:
            if item.get('label') == '721':  # CIP-25 label
                json_metadata = item.get('json_metadata', {})
                
                # Navigate CIP-25 structure
                if policy_id in json_metadata:
                    policy_data = json_metadata[policy_id]
                    
                    # Collect all asset names for page discovery
                    all_asset_names = list(policy_data.keys()) if isinstance(policy_data, dict) else []
                    
                    # Find manifest entry
                    for asset_name, asset_data in policy_data.items():
                        if isinstance(asset_data, dict):
                            if asset_data.get('role') == 'manifest':
                                manifest_data = asset_data
                                break
                            # Also check if this IS the manifest (direct format)
                            if 'pages' in asset_data or 'page_count' in asset_data:
                                manifest_data = asset_data
                                break
        
        # Fallback: look for direct metadata
        if not manifest_data:
            for item in metadata_list:
                json_metadata = item.get('json_metadata', {})
                if json_metadata.get('role') == 'manifest':
                    manifest_data = json_metadata
                    break
                # Check for manifest indicators
                if 'pages' in json_metadata or 'page_count' in json_metadata:
                    manifest_data = json_metadata
                    break
        
        if not manifest_data:
            raise Exception("Could not find manifest in transaction metadata")
        
        # If manifest doesn't have explicit page list, try to extract from asset names
        if 'pages' not in manifest_data or not isinstance(manifest_data.get('pages'), list):
            # Look for page-like asset names
            page_assets = [name for name in all_asset_names 
                          if ('page' in name.lower() or 'p' in name.lower()) 
                          and name.lower() != 'manifest'
                          and not name.endswith('MANIFEST')]
            
            if page_assets:
                # Add discovered pages to manifest
                manifest_data['discovered_pages'] = sorted(page_assets)
        
        return manifest_data
    
    def _fetch_legacy_page(self, policy_id: str, page_num: int) -> Dict:
        """Fetch a single legacy page NFT"""
        # Construct asset name (common patterns)
        # Bible uses BIBLE_P0001 format, BTC uses BTCWP_P0001
        possible_names = [
            f"BIBLE_P{page_num:04d}",  # Bible format
            f"BTCWP_P{page_num:04d}",  # Bitcoin Whitepaper format
            f"page_{page_num:04d}",    # page_0001 format
            f"Page_{page_num:04d}",    # Page_0001 format
            f"page_{page_num}",
            f"Page{page_num}",
            f"{page_num}",
            f"p{page_num}",
            f"page{page_num}",
            f"PAGE{page_num}",
        ]
        
        errors = []
        
        # Try each naming pattern
        for name in possible_names:
            # Convert to hex
            name_hex = name.encode('utf-8').hex()
            asset_full = f"{policy_id}{name_hex}"
            
            try:
                asset_info = self.client.query_asset_metadata(asset_full)
                
                # Extract metadata - try multiple locations
                for key in ('onchain_metadata', 'onchain_metadata_standard', 'metadata'):
                    if key in asset_info:
                        meta = asset_info[key]
                        if isinstance(meta, dict) and meta:
                            return meta
                
                # Try nested metadata
                if 'onchain_metadata_standard' in asset_info:
                    std = asset_info['onchain_metadata_standard']
                    if isinstance(std, dict) and 'metadata' in std:
                        meta = std['metadata']
                        if isinstance(meta, dict) and meta:
                            return meta
                
            except Exception as e:
                errors.append(f"{name}: {str(e)[:50]}")
                continue
        
        # If all patterns failed, provide detailed error
        error_detail = "\n  ".join(errors[:3])  # Show first 3 errors
        raise Exception(f"Could not fetch page {page_num}. Tried patterns:\n  {error_detail}")
    
    def _fetch_legacy_page_by_name(self, policy_id: str, page_name: str) -> Dict:
        """Fetch a single legacy page NFT by explicit asset name"""
        # Convert asset name to hex if not already
        if all(c in '0123456789abcdefABCDEF' for c in page_name) and len(page_name) % 2 == 0:
            # Already hex
            name_hex = page_name
        else:
            # Convert to hex
            name_hex = page_name.encode('utf-8').hex()
        
        asset_full = f"{policy_id}{name_hex}"
        
        try:
            asset_info = self.client.query_asset_metadata(asset_full)
            
            # Extract metadata - try multiple locations (matching working script approach)
            for key in ('onchain_metadata', 'onchain_metadata_standard', 'metadata'):
                if key in asset_info:
                    meta = asset_info[key]
                    if isinstance(meta, dict) and meta:
                        return meta
            
            # Try nested metadata field
            if 'onchain_metadata_standard' in asset_info:
                std = asset_info['onchain_metadata_standard']
                if isinstance(std, dict) and 'metadata' in std:
                    meta = std['metadata']
                    if isinstance(meta, dict) and meta:
                        return meta
            
            raise Exception(f"No valid metadata found for asset {page_name}")
            
        except Exception as e:
            raise Exception(f"Could not fetch page '{page_name}': {e}")
    
    def _extract_page_payload(self, page_metadata: Dict) -> List[str]:
        """Extract payload segments from page metadata"""
        # Try different field names used in various implementations
        possible_fields = ['payload', 'segments', 'seg', 'data']
        
        for field in possible_fields:
            if field in page_metadata:
                data = page_metadata[field]
                
                # Handle list of dicts with "bytes" field (CIP-25 format)
                if isinstance(data, list):
                    hex_segments = []
                    for item in data:
                        if isinstance(item, dict) and 'bytes' in item:
                            # CIP-25 format: {"bytes": "hexstring"}
                            hex_str = item['bytes']
                            # Clean whitespace and validate it's hex
                            hex_str = hex_str.replace(' ', '').replace('\n', '').replace('\r', '')
                            hex_segments.append(hex_str)
                        elif isinstance(item, str):
                            # Direct hex string - clean it
                            hex_str = item.replace(' ', '').replace('\n', '').replace('\r', '')
                            hex_segments.append(hex_str)
                    if hex_segments:
                        return hex_segments
                
                elif isinstance(data, str):
                    # Single string - clean it
                    hex_str = data.replace(' ', '').replace('\n', '').replace('\r', '')
                    return [hex_str]
        
        raise Exception(f"Could not find payload in page metadata. Available fields: {list(page_metadata.keys())}")


# ============================================================================
# GUI APPLICATION
# ============================================================================

class ScrollViewerGUI:
    """Main GUI application for Ledger Scrolls Viewer"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Ledger Scrolls Viewer - A Library That Cannot Burn")
        self.root.geometry("900x700")
        
        self.config = Config()
        self.client = None
        self.connection_mode = ConnectionMode.BLOCKFROST
        
        self._setup_ui()
        self._load_initial_config()
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        title_label = ttk.Label(
            header_frame,
            text="📜 Ledger Scrolls Viewer",
            font=("Arial", 18, "bold")
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        subtitle_label = ttk.Label(
            header_frame,
            text='"A library that cannot burn" - Permissionless immutable data on Cardano',
            font=("Arial", 9, "italic")
        )
        subtitle_label.grid(row=1, column=0, sticky=tk.W)
        
        # Connection settings
        connection_frame = ttk.LabelFrame(main_frame, text="Connection Settings", padding="10")
        connection_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        connection_frame.columnconfigure(1, weight=1)
        
        # Connection mode selection
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
            text="Local Node (cardano-cli)",
            variable=self.mode_var,
            value="local_node",
            command=self._on_mode_change
        ).pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Radiobutton(
            mode_frame,
            text="⚠️ P2P Lightweight (EXPERIMENTAL)",
            variable=self.mode_var,
            value="p2p_experimental",
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
        
        ttk.Label(self.node_frame, text="Node Host:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.node_host_entry = ttk.Entry(self.node_frame)
        self.node_host_entry.insert(0, "localhost")
        self.node_host_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Label(self.node_frame, text="Port:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.node_port_entry = ttk.Entry(self.node_frame)
        self.node_port_entry.insert(0, "3001")
        self.node_port_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=(5, 0))
        
        ttk.Label(self.node_frame, text="Socket Path:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.node_socket_entry = ttk.Entry(self.node_frame)
        self.node_socket_entry.insert(0, "")
        self.node_socket_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=(5, 0))
        
        ttk.Button(
            self.node_frame,
            text="Test & Save",
            command=self._test_and_save_node_config
        ).grid(row=3, column=1, sticky=tk.E, pady=(5, 0))
        
        self.node_frame.grid_remove()  # Hide by default
        
        # P2P Experimental settings
        self.p2p_frame = ttk.Frame(connection_frame)
        self.p2p_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        self.p2p_frame.columnconfigure(1, weight=1)
        
        # Warning banner
        warning_frame = ttk.Frame(self.p2p_frame)
        warning_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(
            warning_frame,
            text="⚠️ EXPERIMENTAL FEATURE - UNDER CONSTRUCTION",
            foreground="orange",
            font=("Arial", 9, "bold")
        ).pack()
        
        ttk.Label(
            warning_frame,
            text="Direct P2P protocol implementation in progress. May not work yet.",
            foreground="gray",
            font=("Arial", 8)
        ).pack()
        
        ttk.Label(self.p2p_frame, text="Relay Host:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.p2p_host_entry = ttk.Entry(self.p2p_frame)
        self.p2p_host_entry.insert(0, "")
        self.p2p_host_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Label(self.p2p_frame, text="Relay Port:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.p2p_port_entry = ttk.Entry(self.p2p_frame)
        self.p2p_port_entry.insert(0, "6000")
        self.p2p_port_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=(5, 0))
        
        ttk.Button(
            self.p2p_frame,
            text="Test Connection (Not Implemented)",
            command=self._test_p2p_connection,
            state="disabled"
        ).grid(row=3, column=1, sticky=tk.E, pady=(5, 0))
        
        # Log file location info
        ttk.Label(
            self.p2p_frame,
            text=f"Debug logs: {LOG_FILE}",
            foreground="gray",
            font=("Arial", 7)
        ).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        self.p2p_frame.grid_remove()  # Hide by default
        
        # Quick demos
        demo_frame = ttk.LabelFrame(main_frame, text="Quick Demos", padding="10")
        demo_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        demo_buttons_frame = ttk.Frame(demo_frame)
        demo_buttons_frame.pack(fill=tk.X)
        
        ttk.Button(
            demo_buttons_frame,
            text="🖼️ Load Hosky PNG (Standard)",
            command=self._load_hosky_demo
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            demo_buttons_frame,
            text="📖 Load Bible (Legacy)",
            command=self._load_bible_demo
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            demo_buttons_frame,
            text="📄 Load Bitcoin Whitepaper (Legacy)",
            command=self._load_btc_demo
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            demo_buttons_frame,
            text="🔧 Custom Scroll",
            command=self._open_custom_scroll_dialog
        ).pack(side=tk.LEFT)
        
        # Progress/log area
        log_frame = ttk.LabelFrame(main_frame, text="Progress & Status", padding="10")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            height=15,
            font=("Courier", 9)
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(
            status_frame,
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Initial welcome message
        self._log("=" * 80)
        self._log("Welcome to Ledger Scrolls Viewer")
        self._log("A permissionless, decentralized viewer for immutable data on Cardano")
        self._log("=" * 80)
        self._log("")
        self._log("Choose a connection mode and load a scroll to begin.")
        self._log("Demo scrolls available: Hosky PNG, Bible, Bitcoin Whitepaper")
        self._log("")
    
    def _load_initial_config(self):
        """Load saved configuration"""
        # Load Blockfrost key
        saved_key = self.config.get_blockfrost_key()
        if saved_key:
            self.api_key_entry.insert(0, saved_key)
            self._log("✓ Loaded saved Blockfrost API key")
        
        # Load node config
        node_config = self.config.get_node_config()
        if node_config:
            self.node_host_entry.delete(0, tk.END)
            self.node_host_entry.insert(0, node_config.host)
            self.node_port_entry.delete(0, tk.END)
            self.node_port_entry.insert(0, str(node_config.port))
            if node_config.socket_path:
                self.node_socket_entry.delete(0, tk.END)
                self.node_socket_entry.insert(0, node_config.socket_path)
            self._log("✓ Loaded saved node configuration")
    
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
        else:  # p2p_experimental
            self.connection_mode = ConnectionMode.P2P_EXPERIMENTAL
            self.blockfrost_frame.grid_remove()
            self.node_frame.grid_remove()
            self.p2p_frame.grid()
            self._log("⚡ Switched to P2P Lightweight (EXPERIMENTAL) mode")
            self._log("⚠️  WARNING: This mode is under construction!")
            self._log(f"📋 Debug logs will be saved to: {LOG_FILE}")
    
    def _test_p2p_connection(self):
        """Test P2P connection (placeholder)"""
        messagebox.showinfo(
            "Not Implemented",
            "P2P connection testing not yet implemented.\n\n"
            "This feature is under construction and will be available in a future update.\n\n"
            "Estimated completion: 4-6 weeks\n"
            "See lightweight_p2p_client_design.md for technical details."
        )
    
    def _save_blockfrost_key(self):
        """Save Blockfrost API key"""
        key = self.api_key_entry.get().strip()
        if not key:
            messagebox.showwarning("Invalid Input", "Please enter an API key")
            return
        
        self.config.set_blockfrost_key(key)
        self._log("✓ Blockfrost API key saved")
        messagebox.showinfo("Success", "API key saved successfully!")
    
    def _test_and_save_node_config(self):
        """Test and save node configuration"""
        host = self.node_host_entry.get().strip()
        port_str = self.node_port_entry.get().strip()
        socket_path = self.node_socket_entry.get().strip() or None
        
        if not host or not port_str:
            messagebox.showwarning("Invalid Input", "Please enter host and port")
            return
        
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showwarning("Invalid Input", "Port must be a number")
            return
        
        node_config = NodeConfig(host=host, port=port, socket_path=socket_path)
        
        # Test connection
        self._log("🔍 Testing node connection...")
        try:
            test_client = LocalNodeClient(node_config)
            self._log("✓ cardano-cli is available")
            
            self.config.set_node_config(node_config)
            self._log("✓ Node configuration saved")
            messagebox.showinfo("Success", "Node configuration saved successfully!")
            
        except Exception as e:
            self._log(f"❌ Node test failed: {e}")
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
        """Get appropriate blockchain client based on mode"""
        if self.connection_mode == ConnectionMode.BLOCKFROST:
            api_key = self.api_key_entry.get().strip()
            if not api_key:
                raise Exception("Please enter and save Blockfrost API key first")
            return BlockfrostClient(api_key)
        
        elif self.connection_mode == ConnectionMode.LOCAL_NODE:
            node_config = self.config.get_node_config()
            if not node_config:
                # Try to create from current UI values
                host = self.node_host_entry.get().strip()
                port_str = self.node_port_entry.get().strip()
                socket_path = self.node_socket_entry.get().strip() or None
                
                if not host or not port_str:
                    raise Exception("Please configure and test node settings first")
                
                node_config = NodeConfig(host=host, port=int(port_str), socket_path=socket_path)
            
            return LocalNodeClient(node_config)
        
        else:  # P2P_EXPERIMENTAL
            relay_host = self.p2p_host_entry.get().strip()
            relay_port_str = self.p2p_port_entry.get().strip()
            
            if not relay_host:
                raise Exception("Please enter relay host IP address")
            
            relay_port = int(relay_port_str) if relay_port_str else 6000
            
            p2p_config = P2PConfig(
                relay_host=relay_host,
                relay_port=relay_port,
                network="mainnet"
            )
            
            logger.info(f"Creating P2P client for {relay_host}:{relay_port}")
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
                
                # Get client
                client = self._get_client()
                
                # Create reconstructor
                reconstructor = ScrollReconstructor(client, progress_callback=self._log)
                
                # Reconstruct based on type
                if isinstance(pointer, StandardScrollPointer):
                    self._log("📌 Scroll Type: Standard (Locked UTxO + Inline Datum)")
                    file_bytes, content_type = reconstructor.reconstruct_standard_scroll(pointer)
                else:
                    self._log("📌 Scroll Type: Legacy (Pages + Manifest NFTs)")
                    file_bytes, content_type = reconstructor.reconstruct_legacy_scroll(pointer)
                
                # Determine file extension
                ext_map = {
                    "image/png": ".png",
                    "text/html": ".html",
                    "text/plain": ".txt",
                    "application/pdf": ".pdf"
                }
                
                # Get extension from content type
                ext = ext_map.get(content_type, ".bin")
                
                # Auto-detect HTML even if content_type says text/plain
                if content_type == "text/plain" and len(file_bytes) > 100:
                    # Check if content starts with HTML markers
                    try:
                        preview = file_bytes[:500].decode('utf-8', errors='ignore').lower()
                        if any(marker in preview for marker in ['<!doctype html', '<html', '<head', '<body']):
                            ext = ".html"
                            self._log("🔍 Auto-detected HTML content, using .html extension")
                    except:
                        pass
                
                # Save file
                safe_title = "".join(c for c in scroll_title if c.isalnum() or c in (' ', '-', '_')).strip()
                filename = f"{safe_title}{ext}"
                filepath = self.config.downloads_dir / filename
                
                with open(filepath, 'wb') as f:
                    f.write(file_bytes)
                
                self._log("")
                self._log("=" * 80)
                self._log(f"✅ SUCCESS! Scroll reconstructed and saved:")
                self._log(f"📁 Location: {filepath}")
                self._log(f"📊 Size: {len(file_bytes):,} bytes")
                self._log(f"📄 Type: {content_type}")
                self._log("=" * 80)
                self._set_status(f"Success! Saved to {filepath}")
                
                # Ask to open file
                self.root.after(0, lambda: self._ask_open_file(filepath))
                
            except Exception as e:
                error_msg = str(e)
                self._log("")
                self._log("=" * 80)
                self._log(f"❌ ERROR: {error_msg}")
                self._log("=" * 80)
                self._set_status("Error occurred")
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Error", msg))
        
        # Run in background thread
        thread = threading.Thread(target=fetch_thread, daemon=True)
        thread.start()
    
    def _ask_open_file(self, filepath: Path):
        """Ask user if they want to open the saved file"""
        response = messagebox.askyesno(
            "File Saved",
            f"Scroll saved successfully to:\n{filepath}\n\nWould you like to open it?"
        )
        
        if response:
            self._open_file(filepath)
    
    def _open_file(self, filepath: Path):
        """Open file with default application"""
        import platform
        import subprocess
        
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', str(filepath)))
            elif platform.system() == 'Windows':
                os.startfile(str(filepath))
            else:  # Linux
                subprocess.call(('xdg-open', str(filepath)))
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")
    
    def _load_hosky_demo(self):
        """Load Hosky PNG demo"""
        pointer = StandardScrollPointer(
            lock_address="addr1w8qvvu0m5jpkgxn3hwfd829hc5kfp0cuq83tsvgk44752dsea0svn",
            lock_txin="728660515c6d9842d9f0ffd273f2b487a4070fd9f4bd5455a42e3a56880389be#0",
            content_type="image/png",
            codec="none",
            sha256="798e3296d45bb42e7444dbf64e1eb16b02c86a233310407e7d8baf97277f642f"
        )
        
        self._fetch_scroll(pointer, "Hosky PNG")
    
    def _load_bible_demo(self):
        """Load Bible demo"""
        pointer = LegacyScrollPointer(
            policy_id="2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0",
            manifest_tx_hash="cfda418ddc84888ac39116ffba691a4f90b3232f4c2633cd56f102cfebda0ee4",
            content_type="text/html",
            codec="gzip",
            manifest_slot="175750638",
            segments_per_page=32
        )
        
        self._fetch_scroll(pointer, "Bible")
    
    def _load_btc_demo(self):
        """Load Bitcoin Whitepaper demo"""
        pointer = LegacyScrollPointer(
            policy_id="8dc3cb836ab8134c75e369391b047f5c2bf796df10d9bf44a33ef6d1",
            manifest_tx_hash="2575347068f77b21cfe8d9c23d9082a68bfe4ef7ba7a96608af90515acbe228f",
            content_type="text/plain",
            codec="none",
            manifest_slot="176360887"
        )
        
        self._fetch_scroll(pointer, "Bitcoin Whitepaper")
    
    def _open_custom_scroll_dialog(self):
        """Open dialog for custom scroll input"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Custom Scroll")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Scroll type selection
        type_frame = ttk.LabelFrame(dialog, text="Scroll Type", padding="10")
        type_frame.pack(fill=tk.X, padx=10, pady=10)
        
        scroll_type_var = tk.StringVar(value="standard")
        
        ttk.Radiobutton(
            type_frame,
            text="Standard (Locked UTxO + Inline Datum)",
            variable=scroll_type_var,
            value="standard"
        ).pack(anchor=tk.W)
        
        ttk.Radiobutton(
            type_frame,
            text="Legacy (Pages + Manifest NFTs)",
            variable=scroll_type_var,
            value="legacy"
        ).pack(anchor=tk.W)
        
        # Standard scroll inputs
        standard_frame = ttk.LabelFrame(dialog, text="Standard Scroll Parameters", padding="10")
        standard_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(standard_frame, text="Lock Address:").grid(row=0, column=0, sticky=tk.W, pady=5)
        std_addr_entry = ttk.Entry(standard_frame, width=60)
        std_addr_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(standard_frame, text="Lock TxIn (hash#index):").grid(row=1, column=0, sticky=tk.W, pady=5)
        std_txin_entry = ttk.Entry(standard_frame, width=60)
        std_txin_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(standard_frame, text="Content Type:").grid(row=2, column=0, sticky=tk.W, pady=5)
        std_ctype_entry = ttk.Entry(standard_frame, width=60)
        std_ctype_entry.insert(0, "image/png")
        std_ctype_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(standard_frame, text="Codec:").grid(row=3, column=0, sticky=tk.W, pady=5)
        std_codec_var = tk.StringVar(value="none")
        codec_frame = ttk.Frame(standard_frame)
        codec_frame.grid(row=3, column=1, sticky=tk.W, pady=5)
        ttk.Radiobutton(codec_frame, text="none", variable=std_codec_var, value="none").pack(side=tk.LEFT)
        ttk.Radiobutton(codec_frame, text="gzip", variable=std_codec_var, value="gzip").pack(side=tk.LEFT)
        
        ttk.Label(standard_frame, text="SHA256 (optional):").grid(row=4, column=0, sticky=tk.W, pady=5)
        std_sha_entry = ttk.Entry(standard_frame, width=60)
        std_sha_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Legacy scroll inputs
        legacy_frame = ttk.LabelFrame(dialog, text="Legacy Scroll Parameters", padding="10")
        legacy_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(legacy_frame, text="Policy ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        leg_policy_entry = ttk.Entry(legacy_frame, width=60)
        leg_policy_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(legacy_frame, text="Manifest Tx Hash:").grid(row=1, column=0, sticky=tk.W, pady=5)
        leg_tx_entry = ttk.Entry(legacy_frame, width=60)
        leg_tx_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(legacy_frame, text="Content Type:").grid(row=2, column=0, sticky=tk.W, pady=5)
        leg_ctype_entry = ttk.Entry(legacy_frame, width=60)
        leg_ctype_entry.insert(0, "text/html")
        leg_ctype_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(legacy_frame, text="Codec:").grid(row=3, column=0, sticky=tk.W, pady=5)
        leg_codec_var = tk.StringVar(value="gzip")
        leg_codec_frame = ttk.Frame(legacy_frame)
        leg_codec_frame.grid(row=3, column=1, sticky=tk.W, pady=5)
        ttk.Radiobutton(leg_codec_frame, text="none", variable=leg_codec_var, value="none").pack(side=tk.LEFT)
        ttk.Radiobutton(leg_codec_frame, text="gzip", variable=leg_codec_var, value="gzip").pack(side=tk.LEFT)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def fetch_custom():
            scroll_type = scroll_type_var.get()
            
            try:
                if scroll_type == "standard":
                    pointer = StandardScrollPointer(
                        lock_address=std_addr_entry.get().strip(),
                        lock_txin=std_txin_entry.get().strip(),
                        content_type=std_ctype_entry.get().strip(),
                        codec=std_codec_var.get(),
                        sha256=std_sha_entry.get().strip() or None
                    )
                    title = "Custom Standard Scroll"
                else:
                    pointer = LegacyScrollPointer(
                        policy_id=leg_policy_entry.get().strip(),
                        manifest_tx_hash=leg_tx_entry.get().strip(),
                        content_type=leg_ctype_entry.get().strip(),
                        codec=leg_codec_var.get()
                    )
                    title = "Custom Legacy Scroll"
                
                dialog.destroy()
                self._fetch_scroll(pointer, title)
                
            except Exception as e:
                messagebox.showerror("Invalid Input", str(e))
        
        ttk.Button(button_frame, text="Fetch Scroll", command=fetch_custom).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)


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