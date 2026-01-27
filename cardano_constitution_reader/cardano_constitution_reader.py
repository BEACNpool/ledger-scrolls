#!/usr/bin/env python3
"""
Cardano Constitution Reader
===========================

Fetch and verify the Cardano Constitution directly from on-chain NFT metadata.

This tool reconstructs the Constitution text from immutable blockchain storage,
verifies cryptographic integrity, and provides beautiful terminal output that
reflects the elegance and importance of Cardano's founding governance document.

Author: BEACNpool
License: MIT
Part of: Ledger Scrolls Project
"""

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
import zlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
    from rich.table import Table
    from rich.syntax import Syntax
    from rich import box
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' library not found. Install with: pip install rich")
    print("Falling back to basic output...\n")

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

__version__ = "2.0.0"
__author__ = "BEACNpool"
__description__ = "Cardano Constitution Reader - Immutable Governance Framework Viewer"

# API Configuration
BASE_URL = "https://cardano-mainnet.blockfrost.io/api/v0"
MAX_API_RETRIES = 6
INITIAL_BACKOFF_SECONDS = 0.75
API_RATE_LIMIT_DELAY = 0.25
API_TIMEOUT_SECONDS = 20
RETRYABLE_HTTP_CODES = (429, 500, 502, 503, 504)

# File Paths
CONFIG_DIR = Path.home() / ".constitution_reader"
CONFIG_FILE = CONFIG_DIR / "config.json"
CACHE_DIR = CONFIG_DIR / "cache"

# Regex Patterns
HEX64_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
PAGE_PATTERN = re.compile(r"PAGE\s*0*(\d+)", re.IGNORECASE)

# ═══════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Constitution:
    """Represents a Cardano Constitution version."""
    epoch: str
    name: str
    policy_id: str
    expected_sha256: str
    ratified_epoch: int
    enacted_epoch: int
    blurb: str
    voting_period: Optional[str] = None
    notable_changes: list[str] = field(default_factory=list)
    
    @property
    def short_policy(self) -> str:
        """Return abbreviated policy ID for display."""
        return f"{self.policy_id[:8]}...{self.policy_id[-8:]}"
    
    @property
    def display_name(self) -> str:
        """Return formatted display name."""
        return f"Cardano Constitution – Epoch {self.epoch}"


@dataclass
class MintsData:
    """Structured mints file data."""
    manifest_tx: Optional[str] = None
    pages: dict[int, str] = field(default_factory=dict)


@dataclass
class FetchResult:
    """Result of constitution fetch operation."""
    raw_bytes: bytes
    computed_hash: str
    verified: bool
    file_size: int
    fetch_time: float
    mode: str  # "fast" or "legacy"


@dataclass
class VerificationReport:
    """Constitution verification details."""
    constitution: Constitution
    computed_hash: str
    expected_hash: str
    verified: bool
    file_size: int
    timestamp: str
    mode: str
    tool_version: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            "document": "Cardano Constitution",
            "epoch": self.constitution.epoch,
            "timestamp": self.timestamp,
            "file_size_bytes": self.file_size,
            "expected_sha256": self.expected_hash,
            "computed_sha256": self.computed_hash,
            "verified": self.verified,
            "fetch_mode": self.mode,
            "tool": f"constitution_reader v{self.tool_version}",
            "blockchain": "Cardano Mainnet",
            "policy_id": self.constitution.policy_id,
            "ratified_epoch": self.constitution.ratified_epoch,
            "enacted_epoch": self.constitution.enacted_epoch
        }


# Constitution Definitions
CONSTITUTIONS = {
    "608": Constitution(
        epoch="608",
        name="Cardano Constitution – Epoch 608 (current)",
        policy_id="ef91a425ef57d92db614085ef03718407fb293cb4b770bc6e03f9750",
        expected_sha256="98a29aec8664b62912c1c0355ebae1401b7c0e53d632e8f05479e7821935abf1",
        ratified_epoch=608,
        enacted_epoch=609,
        blurb="Current Constitution text (amended). Ratified at epoch 608 and enacted at epoch 609.",
        voting_period="Epochs 603-607",
        notable_changes=[
            "Updated parameter guardrails",
            "Clarified treasury withdrawal procedures",
            "Enhanced Constitutional Committee provisions"
        ]
    ),
    "541": Constitution(
        epoch="541",
        name="Cardano Constitution – Epoch 541 (historical)",
        policy_id="d7559bbfa87f53674570fd01f564687c2954503b510ead009148a31d",
        expected_sha256="1939c1627e49b5267114cbdb195d4ac417e545544ba6dcb47e03c679439e9566",
        ratified_epoch=541,
        enacted_epoch=542,
        blurb="First ratified Constitution text (baseline governance framework). Ratified at epoch 541 and enacted at epoch 542.",
        voting_period="Epochs 536-540",
        notable_changes=[
            "Established foundational governance structure",
            "Defined Constitutional Committee role",
            "Set initial parameter guardrails"
        ]
    ),
}

# ═══════════════════════════════════════════════════════════════════════════
# CONSOLE SETUP
# ═══════════════════════════════════════════════════════════════════════════

if RICH_AVAILABLE:
    console = Console()
else:
    # Fallback console for basic printing
    class FallbackConsole:
        def print(self, *args, **kwargs):
            print(*args)
        
        def pager(self):
            return self
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
    
    console = FallbackConsole()

# ═══════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════

class ConstitutionError(Exception):
    """Base exception for constitution reader."""
    pass


class IntegrityError(ConstitutionError):
    """Raised when hash verification fails."""
    def __init__(self, expected: str, actual: str):
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"\n⚠️  INTEGRITY VERIFICATION FAILED\n"
            f"Expected: {expected}\n"
            f"Computed: {actual}\n\n"
            f"This may indicate:\n"
            f"  • Network corruption during download\n"
            f"  • Incomplete page reconstruction\n"
            f"  • Mismatch between policy and expected version\n\n"
            f"The Constitution hash is a cryptographic guarantee.\n"
            f"Do not proceed with unverified data."
        )


class APIError(ConstitutionError):
    """Raised when Blockfrost API fails."""
    pass


# ═══════════════════════════════════════════════════════════════════════════
# BLOCKFROST API CLIENT
# ═══════════════════════════════════════════════════════════════════════════

class BlockfrostClient:
    """Elegant Blockfrost API client with retry logic and rate limiting."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.base_url = BASE_URL
    
    def get(self, endpoint: str, params: Optional[dict] = None) -> dict | list:
        """
        Make GET request with automatic retry and rate limiting.
        
        Args:
            endpoint: API endpoint (e.g., "txs/{hash}/metadata")
            params: Optional query parameters
            
        Returns:
            JSON response as dict or list
            
        Raises:
            APIError: If request fails after all retries
        """
        qs = f"?{urlencode(params)}" if params else ""
        url = f"{self.base_url}/{endpoint}{qs}"
        headers = {"project_id": self.project_id}
        
        backoff = INITIAL_BACKOFF_SECONDS
        
        for attempt in range(1, MAX_API_RETRIES + 1):
            try:
                req = Request(url, headers=headers, method="GET")
                with urlopen(req, timeout=API_TIMEOUT_SECONDS) as resp:
                    raw = resp.read().decode("utf-8")
                    data = json.loads(raw)
                    time.sleep(API_RATE_LIMIT_DELAY)  # Be gentle on free tier
                    return data
            
            except HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                
                if e.code in RETRYABLE_HTTP_CODES and attempt < MAX_API_RETRIES:
                    sleep_s = backoff * (2 ** (attempt - 1))
                    if RICH_AVAILABLE:
                        console.print(
                            f"  [yellow]Blockfrost HTTP {e.code}[/yellow] "
                            f"(attempt {attempt}/{MAX_API_RETRIES}) – "
                            f"retrying in {sleep_s:.1f}s..."
                        )
                    else:
                        print(f"  Blockfrost HTTP {e.code} (attempt {attempt}/{MAX_API_RETRIES}) – retrying in {sleep_s:.1f}s...")
                    time.sleep(sleep_s)
                    continue
                
                raise APIError(f"Blockfrost error {e.code}: {body or e.reason}") from None
            
            except (URLError, socket.timeout, TimeoutError) as e:
                if attempt < MAX_API_RETRIES:
                    sleep_s = backoff * (2 ** (attempt - 1))
                    if RICH_AVAILABLE:
                        console.print(
                            f"  [yellow]Network/timeout error[/yellow] "
                            f"(attempt {attempt}/{MAX_API_RETRIES}) – "
                            f"retrying in {sleep_s:.1f}s..."
                        )
                    else:
                        print(f"  Network/timeout error (attempt {attempt}/{MAX_API_RETRIES}) – retrying in {sleep_s:.1f}s...")
                    time.sleep(sleep_s)
                    continue
                
                raise APIError(f"Network/timeout error: {e}") from None
        
        raise APIError("Failed after all retries (unexpected)")

# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def looks_like_txhash(s: str) -> bool:
    """Check if string matches transaction hash format."""
    return isinstance(s, str) and bool(HEX64_RE.match(s.strip()))


def try_decode_asset_name(asset_name_hex: str) -> str:
    """Attempt to decode asset name from hex to UTF-8."""
    try:
        return bytes.fromhex(asset_name_hex).decode("utf-8", errors="ignore")
    except Exception:
        return asset_name_hex


def is_manifest_asset(asset_name_hex: str) -> bool:
    """Check if asset name indicates a manifest (not a page)."""
    name = try_decode_asset_name(asset_name_hex).upper()
    return ("MANIFEST" in name and "PAGE" not in name) or name.endswith("_MANIFEST")


def is_wsl() -> bool:
    """Detect if running in Windows Subsystem for Linux."""
    if os.getenv("WSL_DISTRO_NAME") or os.getenv("WSL_INTEROP"):
        return True
    try:
        with open("/proc/sys/kernel/osrelease", "r", encoding="utf-8") as f:
            s = f.read().lower()
        return ("microsoft" in s) or ("wsl" in s)
    except Exception:
        return False


def wsl_to_windows_path(path: Path) -> Optional[str]:
    """Convert WSL path to Windows path."""
    try:
        out = subprocess.check_output(["wslpath", "-w", str(path)], text=True).strip()
        return out or None
    except Exception:
        return None


def open_text_file(path: Path) -> None:
    """Open text file in default application (cross-platform)."""
    try:
        if is_wsl():
            win_path = wsl_to_windows_path(path)
            if win_path:
                if win_path.startswith("\\\\"):
                    subprocess.Popen(["explorer.exe", win_path])
                else:
                    subprocess.Popen(["notepad.exe", win_path])
                return
            subprocess.Popen(["explorer.exe", "."])
            return
        
        if sys.platform.startswith("win"):
            subprocess.Popen(["notepad.exe", str(path)])
            return
        
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
            return
        
        subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        if RICH_AVAILABLE:
            console.print(f"[yellow]Could not automatically open file. Located at:[/yellow]\n  {path}")
        else:
            print(f"Could not automatically open file. Located at:\n  {path}")


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def load_config() -> dict:
    """Load configuration from file."""
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_config(config: dict) -> None:
    """Save configuration to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def resolve_api_key(args, config: dict) -> Optional[str]:
    """Resolve API key from multiple sources (CLI > env > config)."""
    if args.api_key:
        return args.api_key.strip()
    
    env_key = os.getenv("BLOCKFROST_PROJECT_ID") or os.getenv("BLOCKFROST_API_KEY")
    if env_key:
        return env_key.strip()
    
    saved = config.get("blockfrost_api_key")
    if saved:
        return str(saved).strip()
    
    return None


# ═══════════════════════════════════════════════════════════════════════════
# CACHE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def get_cached_constitution(epoch: str) -> Optional[bytes]:
    """Check if constitution is already cached locally."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"constitution_epoch_{epoch}.txt"
    
    if cache_file.exists():
        if RICH_AVAILABLE:
            console.print(f"[yellow]✓ Found cached version[/yellow] at {cache_file}")
        else:
            print(f"✓ Found cached version at {cache_file}")
        return cache_file.read_bytes()
    
    return None


def cache_constitution(epoch: str, data: bytes) -> None:
    """Save constitution to local cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"constitution_epoch_{epoch}.txt"
    cache_file.write_bytes(data)


# ═══════════════════════════════════════════════════════════════════════════
# MINTS FILE PARSING
# ═══════════════════════════════════════════════════════════════════════════

def load_mints_file(path: Path) -> MintsData:
    """
    Parse constitution mints file with tolerance for multiple formats.
    
    Supported formats:
    - {"manifest_tx": "...", "pages": [{"page": 1, "tx": "..."}]}
    - {"PAGE001": {"tx": "...", "i": 1}}
    
    Args:
        path: Path to mints JSON file
        
    Returns:
        MintsData with manifest_tx and pages dict
    """
    data = MintsData()
    obj = json.loads(path.read_text(encoding="utf-8"))
    
    # Try direct manifest keys
    for key in ("manifest_mint_tx", "manifest_tx", "manifestTx", "manifestMintTx", "manifest_mint"):
        if looks_like_txhash(obj.get(key, "")):
            data.manifest_tx = obj[key].strip()
            break
    
    # Try pages list format
    if isinstance(obj.get("pages"), list):
        for item in obj["pages"]:
            if not isinstance(item, dict):
                continue
            page_num = item.get("page") or item.get("i") or item.get("index")
            tx_hash = item.get("tx") or item.get("tx_hash") or item.get("txhash")
            if page_num is not None and looks_like_txhash(tx_hash or ""):
                data.pages[int(page_num)] = tx_hash.strip()
    
    # Try PAGE### format
    for key, value in obj.items():
        match = PAGE_PATTERN.search(str(key))
        if match and isinstance(value, dict):
            page_num = int(match.group(1))
            tx_hash = value.get("tx") or value.get("tx_hash") or value.get("txhash")
            if looks_like_txhash(tx_hash or ""):
                data.pages[page_num] = tx_hash.strip()
    
    return data


# ═══════════════════════════════════════════════════════════════════════════
# PAGE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════

def extract_page_payload_any_asset(policy_id: str, metadata_list: list) -> Optional[tuple[int, str]]:
    """
    Extract page payload from CIP-721 metadata without needing exact asset name.
    
    Returns:
        Tuple of (page_index, payload_hex) or None
    """
    for m in metadata_list:
        if str(m.get("label")) != "721":
            continue
        
        meta = m.get("json_metadata", {}) or {}
        policy_bucket = meta.get(policy_id)
        if not isinstance(policy_bucket, dict):
            continue
        
        for _asset_key, page_data in policy_bucket.items():
            if not isinstance(page_data, dict):
                continue
            if "i" not in page_data or "payload" not in page_data:
                continue
            
            i = page_data["i"]
            payload = page_data["payload"]
            
            hex_parts: list[str] = []
            if isinstance(payload, list):
                for p in payload:
                    if isinstance(p, str):
                        hex_parts.append(p.replace("0x", "").strip())
                    elif isinstance(p, dict) and isinstance(p.get("bytes"), str):
                        hex_parts.append(p["bytes"].replace("0x", "").strip())
            elif isinstance(payload, str):
                hex_parts.append(payload.replace("0x", "").strip())
            
            full_hex = "".join(hex_parts).strip()
            if not full_hex:
                continue
            
            try:
                page_index = int(i)
            except Exception:
                continue
            
            return (page_index, full_hex)
    
    return None


def extract_payload_hex_from_721(
    policy_id: str,
    asset_name_hex: str,
    metadata_list: list
) -> Optional[tuple[int, str]]:
    """
    Extract page payload from CIP-721 metadata using asset name.
    
    Returns:
        Tuple of (page_index, payload_hex) or None
    """
    key_utf8 = try_decode_asset_name(asset_name_hex)
    key_hex_fallback = asset_name_hex
    
    for m in metadata_list:
        if str(m.get("label")) != "721":
            continue
        meta = m.get("json_metadata", {}) or {}
        if policy_id not in meta:
            continue
        
        asset_dict = meta.get(policy_id, {}) or {}
        candidate_keys = [key_utf8, key_utf8.upper(), key_hex_fallback, key_hex_fallback.upper()]
        
        page_data = None
        for k in candidate_keys:
            if k in asset_dict:
                page_data = asset_dict[k]
                break
        if not isinstance(page_data, dict):
            continue
        
        if "i" not in page_data or "payload" not in page_data:
            continue
        
        i = page_data["i"]
        payload = page_data["payload"]
        
        hex_parts: list[str] = []
        if isinstance(payload, list):
            for p in payload:
                if isinstance(p, str):
                    hex_parts.append(p.replace("0x", "").strip())
                elif isinstance(p, dict) and "bytes" in p and isinstance(p["bytes"], str):
                    hex_parts.append(p["bytes"].replace("0x", "").strip())
        elif isinstance(payload, str):
            hex_parts.append(payload.replace("0x", "").strip())
        
        if not hex_parts:
            continue
        
        full_hex = "".join(hex_parts).strip()
        if not full_hex:
            continue
        
        try:
            page_index = int(i)
        except Exception:
            continue
        
        return (page_index, full_hex)
    
    return None


# ═══════════════════════════════════════════════════════════════════════════
# CONSTITUTION FETCHING - FAST MODE
# ═══════════════════════════════════════════════════════════════════════════

def fetch_constitution_bytes_fast(
    policy_id: str,
    client: BlockfrostClient,
    page_mint_txs: dict[int, str]
) -> bytes:
    """
    Fast path: use known mint tx hashes to fetch tx metadata directly.
    
    Args:
        policy_id: NFT policy ID
        client: Blockfrost API client
        page_mint_txs: Dict mapping page index to tx hash
        
    Returns:
        Reconstructed constitution bytes
        
    Raises:
        ConstitutionError: If fetch fails
    """
    if not page_mint_txs:
        raise ConstitutionError("Fast mode requested but no page tx hashes were found in the mints file.")
    
    pages: list[tuple[int, str]] = []
    ordered_pages = sorted(page_mint_txs.keys())
    
    if RICH_AVAILABLE:
        console.print(f"  [cyan]Fast mode: fetching metadata for {len(ordered_pages)} page txs...[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                "[cyan]Fetching pages...",
                total=len(ordered_pages)
            )
            
            for idx, page_i in enumerate(ordered_pages, start=1):
                tx = page_mint_txs[page_i]
                progress.update(task, description=f"[cyan]Page {page_i:03d}: {tx[:8]}…")
                
                metadata_list = client.get(f"txs/{tx}/metadata")
                if not isinstance(metadata_list, list):
                    raise ConstitutionError(f"Unexpected metadata response for tx {tx}")
                
                extracted = extract_page_payload_any_asset(policy_id, metadata_list)
                if not extracted:
                    raise ConstitutionError(f"Could not find 721 payload in tx {tx} for page {page_i}")
                
                i_found, payload_hex = extracted
                pages.append((i_found, payload_hex))
                
                progress.update(task, advance=1)
    else:
        print(f"  Fast mode: fetching metadata for {len(ordered_pages)} page txs...")
        for idx, page_i in enumerate(ordered_pages, start=1):
            tx = page_mint_txs[page_i]
            print(f"  Page {page_i:03d} ({idx}/{len(ordered_pages)}): tx {tx[:8]}…")
            
            metadata_list = client.get(f"txs/{tx}/metadata")
            if not isinstance(metadata_list, list):
                raise ConstitutionError(f"Unexpected metadata response for tx {tx}")
            
            extracted = extract_page_payload_any_asset(policy_id, metadata_list)
            if not extracted:
                raise ConstitutionError(f"Could not find 721 payload in tx {tx} for page {page_i}")
            
            i_found, payload_hex = extracted
            pages.append((i_found, payload_hex))
    
    pages.sort(key=lambda x: x[0])
    total_hex = "".join(h for _, h in pages)
    
    try:
        data = bytes.fromhex(total_hex)
    except ValueError:
        raise ConstitutionError("Reconstruction failed: payload hex was invalid.") from None
    
    # Auto-detect and decompress gzip
    if data[:2] == b"\x1f\x8b":
        if RICH_AVAILABLE:
            console.print("  [cyan]Detected gzip compression – decompressing...[/cyan]")
        else:
            print("  Detected gzip compression – decompressing...")
        try:
            data = zlib.decompress(data, 16 + zlib.MAX_WBITS)
        except zlib.error:
            raise ConstitutionError("Gzip decompression failed (data corrupted or not gzip).") from None
    
    return data


# ═══════════════════════════════════════════════════════════════════════════
# CONSTITUTION FETCHING - LEGACY MODE
# ═══════════════════════════════════════════════════════════════════════════

def fetch_constitution_bytes_legacy(policy_id: str, client: BlockfrostClient) -> bytes:
    """
    Legacy path: scan all assets under policy to find pages.
    
    Args:
        policy_id: NFT policy ID
        client: Blockfrost API client
        
    Returns:
        Reconstructed constitution bytes
        
    Raises:
        ConstitutionError: If fetch fails
    """
    if RICH_AVAILABLE:
        console.print("  [cyan]Querying assets under policy (paginated)...[/cyan]")
    else:
        print("  Querying assets under policy (paginated)...")
    
    all_assets: list[dict] = []
    page = 1
    
    while True:
        assets_page = client.get(f"assets/policy/{policy_id}", {"page": page, "count": 100})
        if not isinstance(assets_page, list):
            raise ConstitutionError("Unexpected API response while listing assets.")
        
        if RICH_AVAILABLE:
            console.print(f"  [dim]Page {page}... ({len(assets_page)} items)[/dim]")
        else:
            print(f"  Page {page}... ({len(assets_page)} items)")
        
        if not assets_page:
            break
        
        all_assets.extend(assets_page)
        if len(assets_page) < 100:
            break
        page += 1
    
    if RICH_AVAILABLE:
        console.print(f"  [cyan]Total assets under policy: {len(all_assets)}[/cyan]")
        console.print("  [cyan]Reconstructing pages (this can take ~10–60s on free tier)...[/cyan]")
    else:
        print(f"  Total assets under policy: {len(all_assets)}")
        print("  Reconstructing pages (this can take ~10–60s on free tier)...")
    
    pages: list[tuple[int, str]] = []
    total = len(all_assets)
    
    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Processing assets...", total=total)
            
            for idx, asset_info in enumerate(all_assets, start=1):
                if asset_info.get("quantity") != "1":
                    progress.update(task, advance=1)
                    continue
                
                asset = asset_info.get("asset")
                if not asset or len(asset) <= 56:
                    progress.update(task, advance=1)
                    continue
                
                asset_name_hex = asset[56:]
                if is_manifest_asset(asset_name_hex):
                    progress.update(task, advance=1)
                    continue
                
                pretty_name = try_decode_asset_name(asset_name_hex).strip()
                pretty_name = pretty_name if pretty_name else asset_name_hex
                progress.update(task, description=f"[cyan]Processing: {pretty_name[:30]}")
                
                # Get mint tx
                tx_hash = None
                details = client.get(f"assets/{asset}")
                if isinstance(details, dict):
                    tx_hash = details.get("initial_mint_tx_hash")
                
                if not tx_hash:
                    history = client.get(f"assets/{asset}/history", {"order": "asc", "count": 50})
                    if isinstance(history, list):
                        for e in history:
                            if e.get("action") == "minted" and e.get("tx_hash"):
                                tx_hash = e["tx_hash"]
                                break
                
                if not tx_hash:
                    progress.update(task, advance=1)
                    continue
                
                metadata_list = client.get(f"txs/{tx_hash}/metadata")
                if not isinstance(metadata_list, list):
                    progress.update(task, advance=1)
                    continue
                
                extracted = extract_payload_hex_from_721(policy_id, asset_name_hex, metadata_list)
                if extracted:
                    pages.append(extracted)
                
                progress.update(task, advance=1)
    else:
        for idx, asset_info in enumerate(all_assets, start=1):
            if asset_info.get("quantity") != "1":
                continue
            
            asset = asset_info.get("asset")
            if not asset or len(asset) <= 56:
                continue
            
            asset_name_hex = asset[56:]
            if is_manifest_asset(asset_name_hex):
                continue
            
            pretty_name = try_decode_asset_name(asset_name_hex).strip()
            pretty_name = pretty_name if pretty_name else asset_name_hex
            print(f"  Processing asset {idx}/{total}: {pretty_name}")
            
            # Get mint tx
            tx_hash = None
            details = client.get(f"assets/{asset}")
            if isinstance(details, dict):
                tx_hash = details.get("initial_mint_tx_hash")
            
            if not tx_hash:
                history = client.get(f"assets/{asset}/history", {"order": "asc", "count": 50})
                if isinstance(history, list):
                    for e in history:
                        if e.get("action") == "minted" and e.get("tx_hash"):
                            tx_hash = e["tx_hash"]
                            break
            
            if not tx_hash:
                continue
            
            metadata_list = client.get(f"txs/{tx_hash}/metadata")
            if not isinstance(metadata_list, list):
                continue
            
            extracted = extract_payload_hex_from_721(policy_id, asset_name_hex, metadata_list)
            if extracted:
                pages.append(extracted)
    
    if not pages:
        raise ConstitutionError("No valid page NFTs found under this policy.")
    
    pages.sort(key=lambda x: x[0])
    total_hex = "".join(h for _, h in pages)
    
    try:
        data = bytes.fromhex(total_hex)
    except ValueError:
        raise ConstitutionError("Reconstruction failed: payload hex was invalid.") from None
    
    # Auto-detect and decompress gzip
    if data[:2] == b"\x1f\x8b":
        if RICH_AVAILABLE:
            console.print("  [cyan]Detected gzip compression – decompressing...[/cyan]")
        else:
            print("  Detected gzip compression – decompressing...")
        try:
            data = zlib.decompress(data, 16 + zlib.MAX_WBITS)
        except zlib.error:
            raise ConstitutionError("Gzip decompression failed (data corrupted or not gzip).") from None
    
    return data


# ═══════════════════════════════════════════════════════════════════════════
# DISPLAY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def display_banner():
    """Display application banner."""
    if RICH_AVAILABLE:
        console.print()
        console.print(Panel.fit(
            "[bold cyan]⚖️  CARDANO CONSTITUTION READER[/bold cyan]\n"
            "[dim]Immutable Governance Framework • Verified On-Chain[/dim]\n"
            f"[dim]v{__version__} by {__author__}[/dim]",
            border_style="cyan",
            box=box.DOUBLE
        ))
        console.print()
    else:
        print("\n" + "═" * 64)
        print("   ⚖️  CARDANO CONSTITUTION READER")
        print("   Immutable Governance Framework • Verified On-Chain")
        print(f"   v{__version__} by {__author__}")
        print("═" * 64 + "\n")


def display_about():
    """Display about information."""
    about_text = (
        "The Cardano Constitution is the governance framework for the Cardano blockchain. "
        "It establishes rights and responsibilities of participants, defines governance processes "
        "and voting thresholds, and sets guardrails for protocol parameters and treasury withdrawals.\n\n"
        "This tool reconstructs the Constitution text from on-chain NFT page payloads (CIP-721 metadata) "
        "and verifies integrity with SHA-256 cryptographic hashing."
    )
    
    if RICH_AVAILABLE:
        console.print(Panel(about_text, title="About", border_style="dim", box=box.ROUNDED))
        console.print()
    else:
        print(about_text + "\n")


def display_available_versions():
    """Display table of available constitution versions."""
    if RICH_AVAILABLE:
        table = Table(title="Available Constitution Versions", box=box.ROUNDED)
        table.add_column("Epoch", style="cyan", no_wrap=True)
        table.add_column("Status", style="green")
        table.add_column("Enacted", style="yellow")
        table.add_column("Description")
        
        for epoch in sorted(CONSTITUTIONS.keys(), key=int, reverse=True):
            conf = CONSTITUTIONS[epoch]
            status = "✓ Current" if epoch == "608" else "Historical"
            table.add_row(
                epoch,
                status,
                f"Epoch {conf.enacted_epoch}",
                conf.blurb[:60] + ("..." if len(conf.blurb) > 60 else "")
            )
        
        console.print(table)
        console.print()
    else:
        print("Available Constitution Versions:")
        print("=" * 60)
        for epoch in sorted(CONSTITUTIONS.keys(), key=int, reverse=True):
            conf = CONSTITUTIONS[epoch]
            status = "CURRENT" if epoch == "608" else "Historical"
            print(f"  Epoch {epoch} [{status}]")
            print(f"    Enacted: Epoch {conf.enacted_epoch}")
            print(f"    {conf.blurb}")
            print()


def display_constitution_info(constitution: Constitution):
    """Display detailed constitution metadata."""
    if RICH_AVAILABLE:
        table = Table(title="Constitution Details", box=box.ROUNDED)
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")
        
        table.add_row("Version", f"Epoch {constitution.epoch}")
        table.add_row("Name", constitution.name)
        table.add_row("Ratified", f"Epoch {constitution.ratified_epoch}")
        table.add_row("Enacted", f"Epoch {constitution.enacted_epoch}")
        if constitution.voting_period:
            table.add_row("Voting Period", constitution.voting_period)
        table.add_row("Policy ID", constitution.short_policy)
        table.add_row("Full Policy", constitution.policy_id)
        
        if constitution.notable_changes:
            changes = "\n".join(f"• {c}" for c in constitution.notable_changes)
            table.add_row("Key Changes", changes)
        
        console.print()
        console.print(table)
        console.print()
    else:
        print("\nConstitution Details:")
        print("=" * 60)
        print(f"  Version: Epoch {constitution.epoch}")
        print(f"  Ratified: Epoch {constitution.ratified_epoch}")
        print(f"  Enacted: Epoch {constitution.enacted_epoch}")
        if constitution.voting_period:
            print(f"  Voting Period: {constitution.voting_period}")
        print(f"  Policy ID: {constitution.policy_id}")
        if constitution.notable_changes:
            print("  Key Changes:")
            for change in constitution.notable_changes:
                print(f"    • {change}")
        print()


def display_verification(result: FetchResult, constitution: Constitution):
    """Display verification results with beautiful formatting."""
    if RICH_AVAILABLE:
        table = Table(title="Integrity Verification", box=box.DOUBLE)
        table.add_column("Check", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")
        table.add_column("Status", justify="center")
        
        table.add_row(
            "Expected SHA256",
            constitution.expected_sha256[:40] + "...",
            ""
        )
        table.add_row(
            "Computed SHA256",
            result.computed_hash[:40] + "...",
            ""
        )
        table.add_row(
            "File Size",
            f"{result.file_size:,} bytes",
            ""
        )
        table.add_row(
            "Fetch Mode",
            result.mode.upper(),
            ""
        )
        table.add_row(
            "Fetch Time",
            f"{result.fetch_time:.1f}s",
            ""
        )
        
        if result.verified:
            table.add_row(
                "Verification",
                "Hashes Match",
                "[bold green]✓ VERIFIED[/bold green]"
            )
        else:
            table.add_row(
                "Verification",
                "Hash Mismatch",
                "[bold red]✗ FAILED[/bold red]"
            )
        
        console.print()
        console.print(table)
        console.print()
        
        if result.verified:
            console.print(
                Panel(
                    f"[bold green]Constitution Epoch {constitution.epoch} is cryptographically verified ✓[/bold green]\n"
                    f"[dim]This document is immutably stored on the Cardano blockchain[/dim]",
                    border_style="green",
                    box=box.ROUNDED
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold red]⚠️  VERIFICATION FAILED[/bold red]\n"
                    f"[yellow]Expected: {constitution.expected_sha256}[/yellow]\n"
                    f"[yellow]Computed: {result.computed_hash}[/yellow]\n\n"
                    f"[dim]Do not trust this data. Possible network corruption or reconstruction error.[/dim]",
                    border_style="red",
                    box=box.ROUNDED
                )
            )
    else:
        print("\nIntegrity Verification:")
        print("=" * 60)
        print(f"  Expected SHA256: {constitution.expected_sha256}")
        print(f"  Computed SHA256: {result.computed_hash}")
        print(f"  File Size: {result.file_size:,} bytes")
        print(f"  Fetch Mode: {result.mode.upper()}")
        print(f"  Fetch Time: {result.fetch_time:.1f}s")
        
        if result.verified:
            print(f"\n  ✓ VERIFIED - Constitution Epoch {constitution.epoch} is authentic")
        else:
            print(f"\n  ✗ FAILED - Hash mismatch detected!")
            print(f"  Do not trust this data.")
        print()


def display_constitution_text(text: bytes, constitution: Constitution):
    """Display constitution text in terminal with paging."""
    try:
        content = text.decode('utf-8')
        
        if RICH_AVAILABLE:
            console.print()
            console.print(Panel(
                f"[bold cyan]Displaying: {constitution.display_name}[/bold cyan]\n"
                f"[dim]Use arrow keys to scroll, 'q' to quit[/dim]",
                border_style="cyan"
            ))
            console.print()
            
            # Display with pager for long content
            with console.pager():
                console.print(content)
        else:
            print(f"\n{'=' * 60}")
            print(f"Constitution Epoch {constitution.epoch}")
            print('=' * 60)
            print(content)
            print('=' * 60)
    
    except UnicodeDecodeError:
        if RICH_AVAILABLE:
            console.print("[yellow]Binary content detected - cannot display as text[/yellow]")
        else:
            print("Binary content detected - cannot display as text")


# ═══════════════════════════════════════════════════════════════════════════
# VERIFICATION & EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def create_verification_report(
    result: FetchResult,
    constitution: Constitution
) -> VerificationReport:
    """Create verification report from fetch result."""
    return VerificationReport(
        constitution=constitution,
        computed_hash=result.computed_hash,
        expected_hash=constitution.expected_sha256,
        verified=result.verified,
        file_size=result.file_size,
        timestamp=datetime.now().isoformat(),
        mode=result.mode,
        tool_version=__version__
    )


def export_verification_report(report: VerificationReport, out_dir: Path) -> Path:
    """Export verification report as JSON."""
    report_file = out_dir / f"verification_epoch_{report.constitution.epoch}.json"
    report_file.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return report_file


# ═══════════════════════════════════════════════════════════════════════════
# MAIN FETCH ORCHESTRATION
# ═══════════════════════════════════════════════════════════════════════════

def fetch_constitution(
    constitution: Constitution,
    api_key: str,
    mints_file: Optional[Path] = None,
    use_cache: bool = True
) -> FetchResult:
    """
    Main orchestration for fetching constitution.
    
    Args:
        constitution: Constitution to fetch
        api_key: Blockfrost API key
        mints_file: Optional path to mints file for fast mode
        use_cache: Whether to use cached version if available
        
    Returns:
        FetchResult with verification details
    """
    start_time = time.time()
    
    # Check cache first
    if use_cache:
        cached = get_cached_constitution(constitution.epoch)
        if cached:
            computed_hash = hashlib.sha256(cached).hexdigest()
            fetch_time = time.time() - start_time
            return FetchResult(
                raw_bytes=cached,
                computed_hash=computed_hash,
                verified=(computed_hash == constitution.expected_sha256),
                file_size=len(cached),
                fetch_time=fetch_time,
                mode="cache"
            )
    
    # Initialize API client
    client = BlockfrostClient(api_key)
    
    # Determine fetch mode
    mode = "legacy"
    mints_data = None
    
    if mints_file and mints_file.exists():
        if RICH_AVAILABLE:
            console.print(f"  [cyan]Using mints file:[/cyan] {mints_file}")
        else:
            print(f"  Using mints file: {mints_file}")
        
        mints_data = load_mints_file(mints_file)
        if mints_data.manifest_tx:
            if RICH_AVAILABLE:
                console.print(f"  [cyan]Manifest mint tx:[/cyan] {mints_data.manifest_tx}")
            else:
                print(f"  Manifest mint tx: {mints_data.manifest_tx}")
        
        if mints_data.pages:
            mode = "fast"
    else:
        # Auto-detect mints file
        candidate = Path(__file__).resolve().parent / f"constitution_epoch_{constitution.epoch}_mints.json"
        if candidate.exists():
            if RICH_AVAILABLE:
                console.print(f"  [cyan]Auto-detected mints file:[/cyan] {candidate}")
            else:
                print(f"  Auto-detected mints file: {candidate}")
            
            mints_data = load_mints_file(candidate)
            if mints_data.pages:
                mode = "fast"
    
    # Fetch constitution
    if mode == "fast" and mints_data:
        raw_bytes = fetch_constitution_bytes_fast(
            constitution.policy_id,
            client,
            mints_data.pages
        )
    else:
        raw_bytes = fetch_constitution_bytes_legacy(
            constitution.policy_id,
            client
        )
    
    # Cache the result
    cache_constitution(constitution.epoch, raw_bytes)
    
    # Compute hash and verify
    computed_hash = hashlib.sha256(raw_bytes).hexdigest()
    verified = (computed_hash == constitution.expected_sha256)
    fetch_time = time.time() - start_time
    
    return FetchResult(
        raw_bytes=raw_bytes,
        computed_hash=computed_hash,
        verified=verified,
        file_size=len(raw_bytes),
        fetch_time=fetch_time,
        mode=mode
    )


# ═══════════════════════════════════════════════════════════════════════════
# COMMAND LINE INTERFACE
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  {sys.argv[0]} --epoch 608
  {sys.argv[0]} --epoch 541 --api-key mainnet...
  {sys.argv[0]} --epoch 608 --display
  {sys.argv[0]} --epoch 608 --export-verification

For more information, visit: https://github.com/BEACNpool/ledger-scrolls
        """
    )
    
    parser.add_argument(
        "--epoch",
        choices=sorted(CONSTITUTIONS.keys()),
        help="Which constitution version to fetch (541 or 608)"
    )
    parser.add_argument(
        "--api-key",
        help="Blockfrost Mainnet API key (or set env BLOCKFROST_PROJECT_ID)"
    )
    parser.add_argument(
        "--config",
        default=str(CONFIG_FILE),
        help=f"Config path (default: {CONFIG_FILE})"
    )
    parser.add_argument(
        "--out-dir",
        default=str(Path.cwd()),
        help="Where to save output files (default: current directory)"
    )
    parser.add_argument(
        "--no-save-key",
        action="store_true",
        help="Do not persist API key to config"
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Fail instead of prompting for missing values"
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the downloaded file after saving"
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not prompt to open the file"
    )
    parser.add_argument(
        "--display",
        action="store_true",
        help="Display constitution text in terminal (with paging)"
    )
    parser.add_argument(
        "--export-verification",
        action="store_true",
        help="Export verification report as JSON"
    )
    parser.add_argument(
        "--mints-file",
        help="Path to constitution_epoch_XXX_mints.json (enables fast mode)"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Skip cache and fetch fresh from blockchain"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    args = parser.parse_args()
    
    # Display banner and about
    display_banner()
    display_about()
    
    # Load config
    config = load_config()
    
    # Resolve API key
    api_key = resolve_api_key(args, config)
    
    if not api_key:
        if args.non_interactive:
            if RICH_AVAILABLE:
                console.print("[red]Error: Missing API key. Provide --api-key or set BLOCKFROST_PROJECT_ID.[/red]")
            else:
                print("Error: Missing API key. Provide --api-key or set BLOCKFROST_PROJECT_ID.")
            sys.exit(1)
        
        if RICH_AVAILABLE:
            console.print("[yellow]No API key found (CLI/env/config).[/yellow]")
            console.print("A Blockfrost key is required to query the on-chain metadata.")
            console.print("Get a free key at [link=https://blockfrost.io]https://blockfrost.io[/link]")
            console.print('[dim]Note: Free tier is sufficient; this script rate-limits requests.[/dim]\n')
        else:
            print("No API key found (CLI/env/config).")
            print("A Blockfrost key is required to query the on-chain metadata.")
            print("Get a free key at https://blockfrost.io\n")
        
        api_key = input("Paste your Blockfrost Mainnet API key (mainnet...): ").strip()
    
    if not api_key.startswith("mainnet"):
        if RICH_AVAILABLE:
            console.print("[red]Error: Blockfrost key should start with 'mainnet...'[/red]")
        else:
            print("Error: Blockfrost key should start with 'mainnet...'")
        sys.exit(1)
    
    # Save API key
    if (not args.no_save_key) and (config.get("blockfrost_api_key") != api_key):
        config["blockfrost_api_key"] = api_key
        save_config(config)
        if RICH_AVAILABLE:
            console.print(f"[green]✓ API key saved to:[/green] {CONFIG_FILE}")
        else:
            print(f"✓ API key saved to: {CONFIG_FILE}")
    
    # Select epoch
    epoch = args.epoch
    if not epoch:
        if args.non_interactive:
            if RICH_AVAILABLE:
                console.print("[red]Error: Missing --epoch (541 or 608).[/red]")
            else:
                print("Error: Missing --epoch (541 or 608).")
            sys.exit(1)
        
        display_available_versions()
        epoch = input("Enter epoch number (541 or 608): ").strip()
    
    if epoch not in CONSTITUTIONS:
        if RICH_AVAILABLE:
            console.print("[red]Invalid epoch. Use 541 or 608.[/red]")
        else:
            print("Invalid epoch. Use 541 or 608.")
        sys.exit(1)
    
    constitution = CONSTITUTIONS[epoch]
    
    # Display constitution info
    display_constitution_info(constitution)
    
    # Prepare mints file path
    mints_file = None
    if args.mints_file:
        mints_file = Path(args.mints_file).expanduser()
    
    try:
        # Fetch constitution
        if RICH_AVAILABLE:
            console.print(Panel(
                f"[bold cyan]Fetching: {constitution.display_name}[/bold cyan]\n"
                f"[dim]Policy: {constitution.policy_id}[/dim]",
                border_style="cyan"
            ))
            console.print()
        else:
            print(f"\nFetching: {constitution.display_name}")
            print(f"Policy: {constitution.policy_id}\n")
        
        result = fetch_constitution(
            constitution,
            api_key,
            mints_file,
            use_cache=(not args.no_cache)
        )
        
        # Display verification
        display_verification(result, constitution)
        
        if not result.verified:
            raise IntegrityError(constitution.expected_sha256, result.computed_hash)
        
        # Save file
        filename = f"Cardano_Constitution_Epoch_{epoch}.txt"
        out_dir = Path(args.out_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = (out_dir / filename).resolve()
        out_path.write_bytes(result.raw_bytes)
        
        if RICH_AVAILABLE:
            console.print()
            console.print(Panel(
                f"[bold green]Successfully saved immutable document[/bold green]\n\n"
                f"[cyan]Location:[/cyan] {out_path}\n"
                f"[cyan]Size:[/cyan] {result.file_size:,} bytes\n"
                f"[cyan]SHA256:[/cyan] {result.computed_hash}",
                border_style="green",
                box=box.ROUNDED
            ))
        else:
            print("\nSuccessfully saved immutable document:")
            print(f"  Location: {out_path}")
            print(f"  Size: {result.file_size:,} bytes")
            print(f"  SHA256: {result.computed_hash}")
        
        # Export verification report
        if args.export_verification:
            report = create_verification_report(result, constitution)
            report_path = export_verification_report(report, out_dir)
            if RICH_AVAILABLE:
                console.print(f"\n[green]✓ Verification report exported:[/green] {report_path}")
            else:
                print(f"\n✓ Verification report exported: {report_path}")
        
        # Display constitution text
        if args.display:
            display_constitution_text(result.raw_bytes, constitution)
        
        # Open file
        if not args.no_open and not args.display:
            choice = "y" if args.open else (input("\nOpen the file now? (Y/n): ").strip().lower() or "y")
            if choice.startswith("y"):
                open_text_file(out_path)
        
        if RICH_AVAILABLE:
            console.print("\n" + "═" * 60 + "\n")
        else:
            print("\n" + "═" * 60 + "\n")
    
    except (ConstitutionError, IntegrityError) as e:
        if RICH_AVAILABLE:
            console.print(f"\n[red bold]Error:[/red bold] {e}")
        else:
            print(f"\nError: {e}")
        sys.exit(1)
    
    except KeyboardInterrupt:
        if RICH_AVAILABLE:
            console.print("\n[yellow]Interrupted by user[/yellow]")
        else:
            print("\nInterrupted by user")
        sys.exit(130)
    
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(f"\n[red bold]Unexpected error:[/red bold] {e}")
        else:
            print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
