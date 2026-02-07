#!/usr/bin/env python3
"""
ouroboros_client.py — Cardano "Relay Impersonator" / Lightweight Proxy Node
===========================================================================
Ledger Scrolls Project (@BEACNpool)

Connects to any Cardano relay via raw TCP, performs Ouroboros mini-protocol
handshakes, fetches specific blocks by slot/hash, extracts transaction
metadata, and disconnects cleanly.

NO full node required. NO centralized API dependency. Pure P2P.

Protocol References (all from Ouroboros Network Specification):
  - MUX framing:     Section 2.1  (Table 2.1 SDU encoding)
  - Handshake:       Section 3.6  (CDDL: msgProposeVersions/msgAcceptVersion)
  - ChainSync:       Section 3.7  (CDDL: msgFindIntersect/msgIntersectFound)
  - BlockFetch:      Section 3.8  (CDDL: msgRequestRange/msgBlock/msgBatchDone)
  - Protocol IDs:    Table 3.14   (N2N: Handshake=0, ChainSync=2, BlockFetch=3)
  - Version numbers: Table 3.20   (NodeToNodeV_14=14, V_15=15)
  - Timeouts:        Section 4.1  (Handshake=10s, Post-handshake=30s SDU)

Inspired by:
  - gOuroboros (Go):  github.com/blinklabs-io/gouroboros
  - Ogmios (Haskell): ogmios.dev
  - PyCardano:        github.com/Python-Cardano/pycardano (cbor2 patterns)

Dependencies: cbor2, Python 3.10+
  pip install cbor2

Author: Ledger Scrolls / BEACNpool
License: MIT
"""

from __future__ import annotations

import asyncio
import cbor2
import hashlib
import io
import logging
import struct
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS — Per Ouroboros Network Specification
# ═══════════════════════════════════════════════════════════════════════════════

# Network magic values (Section 3.6.5 — networkMagic is a Word32)
MAINNET_MAGIC   = 764824073
PREPROD_MAGIC   = 1
PREVIEW_MAGIC   = 2
SANCHONET_MAGIC = 4

# Known public relay endpoints (from gOuroboros / IOG topology)
MAINNET_RELAYS = [
    ("backbone.cardano.iog.io", 3001),
    ("backbone.mainnet.emurgornd.com", 3001),
    ("backbone.mainnet.cardanofoundation.org", 3001),
]

# Mini-protocol IDs — Table 3.14 (Node-to-Node mux protocol numbers)
class MiniProtocol(IntEnum):
    HANDSHAKE    = 0
    CHAIN_SYNC   = 2
    BLOCK_FETCH  = 3
    TX_SUBMISSION = 4
    KEEP_ALIVE   = 8
    PEER_SHARING = 10

# Node-to-Node protocol versions — Table 3.20
# Per CDDL: versionNumber_v14 = 14 / 15
class N2NVersion(IntEnum):
    V14 = 14  # Plomin HF nodes, mandatory mainnet since 2025.01.29
    V15 = 15  # SRV record support

# MUX SDU constraints — Section 2.1.1 / Section 2.1.3
MUX_HEADER_SIZE    = 8       # bytes: [4 timestamp][2 mode|proto_id][2 payload_len]
MUX_MAX_SDU_N2N    = 12288   # max SDU payload for node-to-node
MUX_MODE_INITIATOR = 0       # Mode bit = 0 for initiator (us)
MUX_MODE_RESPONDER = 1       # Mode bit = 1 for responder (relay)

# Timeouts — Section 4.1
HANDSHAKE_SDU_TIMEOUT = 10.0   # seconds, per mux SDU during handshake
PROTOCOL_SDU_TIMEOUT  = 30.0   # seconds, per mux SDU after handshake
IDLE_TIMEOUT          = 5.0    # inbound idleness timeout
BLOCKFETCH_STATE_TIMEOUT = 60.0  # StBusy / StStreaming timeout (Table 3.8)

# ═══════════════════════════════════════════════════════════════════════════════
#  LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logger = logging.getLogger("ouroboros_client")


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Point:
    """
    A chain point — Per CDDL (Appendix A):
      point = origin / [slotNo, headerHash]
      origin = []  ; empty array

    The headerHash is a 32-byte Blake2b-256 hash of the block header.
    """
    slot: int
    block_hash: bytes  # 32 bytes, Blake2b-256

    def to_cbor(self) -> list:
        """Encode as CDDL: [slotNo, headerHash]"""
        return [self.slot, cbor2.CBORTag(24, self.block_hash) if False else self.block_hash]

    def to_cbor_list(self) -> list:
        """Encode as [slot, hash_bytes] for protocol messages."""
        return [self.slot, self.block_hash]

    @classmethod
    def origin(cls) -> list:
        """The origin point — CDDL: origin = []"""
        return []

    def __repr__(self) -> str:
        return f"Point(slot={self.slot}, hash={self.block_hash.hex()[:16]}…)"


@dataclass
class FetchedBlock:
    """A block fetched from the relay, with parsed components."""
    raw_cbor: bytes               # The full CBOR block as received
    era_index: Optional[int] = None  # HFC era tag (0=Byron..6=Conway)
    era_name: Optional[str] = None
    slot: Optional[int] = None
    block_hash: Optional[str] = None
    transactions: List[Any] = field(default_factory=list)
    tx_metadata: Dict[int, Any] = field(default_factory=dict)  # tx_index → metadata
    auxiliary_data: Dict[int, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
#  MUX LAYER — Section 2.1 (Wire Format, Table 2.1)
# ═══════════════════════════════════════════════════════════════════════════════
#
#  SDU Header (8 bytes, big-endian):
#  ┌─────────────────────┬──────────────────────────┬─────────────────┐
#  │  Transmission Time   │  M │ Mini Protocol ID    │  Payload Length │
#  │     (4 bytes)        │(1b)│    (15 bits)         │   (2 bytes)     │
#  └─────────────────────┴──────────────────────────┴─────────────────┘
#
#  Mode bit: 0 = initiator (client/us), 1 = responder (server/relay)
#  Per Section 3.6.8: Handshake messages MUST NOT be split across segments.

def mux_encode(protocol_id: int, payload: bytes, mode: int = MUX_MODE_INITIATOR) -> bytes:
    """
    Wrap a mini-protocol payload in a MUX SDU segment.

    Per Table 2.1 of the Ouroboros Network Spec:
    - Bytes 0-3:  Transmission Time (uint32, lower 32 bits of monotonic µs clock)
    - Bytes 4-5:  [Mode(1 bit)][Mini Protocol ID(15 bits)]  (uint16 big-endian)
    - Bytes 6-7:  Payload length (uint16 big-endian)
    - Bytes 8+:   Payload

    Args:
        protocol_id: Mini-protocol number (Table 3.14)
        payload:     CBOR-encoded protocol message
        mode:        0 = initiator, 1 = responder
    """
    timestamp = int(time.monotonic() * 1_000_000) & 0xFFFFFFFF
    # Mode bit is the MSB of the 16-bit protocol_id field
    proto_with_mode = (mode << 15) | (protocol_id & 0x7FFF)
    header = struct.pack("!IHH", timestamp, proto_with_mode, len(payload))
    return header + payload


def mux_split_and_encode(protocol_id: int, payload: bytes,
                          mode: int = MUX_MODE_INITIATOR,
                          max_payload: int = MUX_MAX_SDU_N2N) -> List[bytes]:
    """
    Split payload into multiple MUX segments if needed.

    Per Section 2.1.2: Messages within a segment must all belong to the same
    mini-protocol. The multiplexer may merge multiple messages from one
    mini-protocol into a single segment.

    Per Section 3.6.8: Handshake messages MUST fit in a single segment.
    """
    if len(payload) <= max_payload:
        return [mux_encode(protocol_id, payload, mode)]

    segments = []
    offset = 0
    while offset < len(payload):
        chunk = payload[offset : offset + max_payload]
        segments.append(mux_encode(protocol_id, chunk, mode))
        offset += max_payload
    return segments


@dataclass
class MuxSegment:
    """A decoded MUX SDU segment."""
    timestamp: int
    mode: int           # 0 = initiator, 1 = responder
    protocol_id: int    # Mini-protocol number
    payload: bytes

    @classmethod
    def decode(cls, header: bytes, payload: bytes) -> "MuxSegment":
        """Decode from raw header (8 bytes) + payload."""
        ts, proto_mode, length = struct.unpack("!IHH", header)
        mode = (proto_mode >> 15) & 0x01
        protocol_id = proto_mode & 0x7FFF
        return cls(timestamp=ts, mode=mode, protocol_id=protocol_id, payload=payload)


# ═══════════════════════════════════════════════════════════════════════════════
#  CBOR PROTOCOL MESSAGE BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════
#
#  All messages follow the CDDL specs from Section 3.6.9, 3.7.8, 3.8.5

class HandshakeMsg:
    """
    Handshake message builders — Section 3.6.9 (Node-to-Node CDDL)

    Per CDDL:
      msgProposeVersions = [0, versionTable]
      msgAcceptVersion   = [1, versionNumber, nodeToNodeVersionData]
      msgRefuse          = [2, refuseReason]

      versionTable = {* versionNumber_v14 => v14.nodeToNodeVersionData}
      versionNumber_v14 = 14 / 15

    Per Section 3.6.5, nodeToNodeVersionData (v14+) =
      [networkMagic, diffusionMode, peerSharing, query]
    Where:
      networkMagic:  uint (Word32)
      diffusionMode: bool (True = InitiatorOnly, False = InitiatorAndResponder)
      peerSharing:   0 / 1 (0 = disabled, 1 = enabled)
      query:         bool (True = version query mode, False = normal)
    """

    @staticmethod
    def propose_versions(network_magic: int = MAINNET_MAGIC,
                          initiator_only: bool = True,
                          peer_sharing: int = 0,
                          query: bool = False,
                          versions: Optional[List[int]] = None) -> bytes:
        """
        Build MsgProposeVersions — CDDL: [0, versionTable]

        Per Section 3.6.5: We propose versions with our desired parameters.
        The relay picks the highest mutually supported version.

        We default to InitiatorOnly mode (we only consume, never produce)
        and disable peer sharing (we don't want to participate in gossip).
        """
        if versions is None:
            versions = [N2NVersion.V14]  # V14 is mandatory since 2025.01.29

        # Per CDDL: versionTable = {* versionNumber => nodeToNodeVersionData}
        # nodeToNodeVersionData = [networkMagic, diffusionMode, peerSharing, query]
        version_table = {}
        for v in sorted(versions):
            version_table[v] = [network_magic, initiator_only, peer_sharing, query]

        # msgProposeVersions = [0, versionTable]
        msg = [0, version_table]
        return cbor2.dumps(msg)

    @staticmethod
    def decode_response(data: bytes) -> dict:
        """
        Decode handshake response (MsgAcceptVersion or MsgRefuse).

        Returns dict with:
          - 'type': 'accept' | 'refuse' | 'query_reply'
          - For accept: 'version', 'network_magic', 'diffusion_mode',
                        'peer_sharing', 'query'
          - For refuse: 'reason', 'detail'
        """
        msg = cbor2.loads(data)
        msg_type = msg[0]

        if msg_type == 1:  # MsgAcceptVersion = [1, versionNumber, versionData]
            version = msg[1]
            vdata = msg[2]
            return {
                "type": "accept",
                "version": version,
                "network_magic": vdata[0] if isinstance(vdata, list) else None,
                "diffusion_mode": vdata[1] if isinstance(vdata, list) and len(vdata) > 1 else None,
                "peer_sharing": vdata[2] if isinstance(vdata, list) and len(vdata) > 2 else None,
                "query": vdata[3] if isinstance(vdata, list) and len(vdata) > 3 else None,
            }
        elif msg_type == 2:  # MsgRefuse = [2, refuseReason]
            reason = msg[1]
            # refuseReason = [0, [versions]] | [1, version, tstr] | [2, version, tstr]
            reason_type = reason[0]
            reasons = {0: "VersionMismatch", 1: "HandshakeDecodeError", 2: "Refused"}
            return {
                "type": "refuse",
                "reason": reasons.get(reason_type, f"Unknown({reason_type})"),
                "detail": reason[1:],
            }
        elif msg_type == 3:  # MsgQueryReply = [3, versionTable]
            return {
                "type": "query_reply",
                "version_table": msg[1],
            }
        else:
            return {"type": "unknown", "raw": msg}


class ChainSyncMsg:
    """
    ChainSync message builders — Section 3.7.8 CDDL

      msgFindIntersect     = [4, base.points]
      msgIntersectFound    = [5, base.point, base.tip]
      msgIntersectNotFound = [6, base.tip]
      chainSyncMsgDone     = [7]
      msgRequestNext       = [0]
    """

    @staticmethod
    def find_intersect(points: List[Point]) -> bytes:
        """
        Build MsgFindIntersect — CDDL: [4, points]

        Per Section 3.7.5: The consumer sends a list of points and the
        producer replies with the most recent point that is on both chains.

        Per Section 3.7.6: For efficient intersection finding, use the
        exponential backoff pattern: [b, b-1, b-2, b-4, b-8, ...]
        For our "snipe" use case, we just send our target point(s).
        """
        point_list = [p.to_cbor_list() for p in points]
        msg = [4, point_list]
        return cbor2.dumps(msg)

    @staticmethod
    def msg_done() -> bytes:
        """Build chainSyncMsgDone — CDDL: [7]"""
        return cbor2.dumps([7])

    @staticmethod
    def request_next() -> bytes:
        """Build MsgRequestNext — CDDL: [0]"""
        return cbor2.dumps([0])

    @staticmethod
    def decode_response(data: bytes) -> dict:
        """Decode ChainSync server response."""
        msg = cbor2.loads(data)
        msg_type = msg[0]

        responses = {
            1: "await_reply",
            2: "roll_forward",
            3: "roll_backward",
            5: "intersect_found",
            6: "intersect_not_found",
        }

        result = {"type": responses.get(msg_type, f"unknown({msg_type})"), "raw": msg}

        if msg_type == 5:  # MsgIntersectFound = [5, point, tip]
            result["point"] = msg[1]
            result["tip"] = msg[2]
        elif msg_type == 6:  # MsgIntersectNotFound = [6, tip]
            result["tip"] = msg[1]
        elif msg_type == 2:  # MsgRollForward = [2, header, tip]
            result["header"] = msg[1]
            result["tip"] = msg[2]
        elif msg_type == 3:  # MsgRollBackward = [3, point, tip]
            result["point"] = msg[1]
            result["tip"] = msg[2]

        return result


class BlockFetchMsg:
    """
    BlockFetch message builders — Section 3.8.5 CDDL

      msgRequestRange = [0, base.point, base.point]
      msgClientDone   = [1]
      msgStartBatch   = [2]
      msgNoBlocks     = [3]
      msgBlock        = [4, base.block]
      msgBatchDone    = [5]

    Per Section 3.8.1: The block fetching mechanism enables a node to
    download a range of blocks. The range is inclusive on both sides.
    """

    @staticmethod
    def request_range(point_from: Point, point_to: Point) -> bytes:
        """
        Build MsgRequestRange — CDDL: [0, point_from, point_to]

        For fetching a single block, set point_from == point_to.
        The range is inclusive on both sides (Section 3.8.2).
        """
        msg = [0, point_from.to_cbor_list(), point_to.to_cbor_list()]
        return cbor2.dumps(msg)

    @staticmethod
    def client_done() -> bytes:
        """Build MsgClientDone — CDDL: [1]"""
        return cbor2.dumps([1])

    @staticmethod
    def decode_response(data: bytes) -> dict:
        """
        Decode BlockFetch server response.

        Returns dict with 'type' being one of:
          'start_batch', 'no_blocks', 'block', 'batch_done'
        """
        msg = cbor2.loads(data)
        msg_type = msg[0]

        responses = {
            2: "start_batch",
            3: "no_blocks",
            4: "block",
            5: "batch_done",
        }

        result = {"type": responses.get(msg_type, f"unknown({msg_type})")}

        if msg_type == 4:  # MsgBlock = [4, block_body]
            result["block_body"] = msg[1]

        return result


class KeepAliveMsg:
    """
    KeepAlive message builders — Section 3.10 CDDL

      msgKeepAlive           = [0, uint]    ; cookie
      msgKeepAliveResponse   = [1, uint]    ; echo back cookie
      keepAliveDone          = [2]
    """

    @staticmethod
    def keep_alive_done() -> bytes:
        """Build keepAliveDone — CDDL: [2]"""
        return cbor2.dumps([2])

    @staticmethod
    def response(cookie: int) -> bytes:
        """Build MsgKeepAliveResponse — CDDL: [1, cookie]"""
        return cbor2.dumps([1, cookie])


# ═══════════════════════════════════════════════════════════════════════════════
#  BLOCK PARSER — Extract transactions and metadata from raw CBOR blocks
# ═══════════════════════════════════════════════════════════════════════════════

# HFC era names (index → name)
ERA_NAMES = {
    0: "Byron",
    1: "Shelley",
    2: "Allegra",
    3: "Mary",
    4: "Alonzo",
    5: "Babbage",
    6: "Conway",
}


def parse_block(block_cbor: Any) -> FetchedBlock:
    """
    Parse a block received from BlockFetch into a FetchedBlock.

    The block comes wrapped in the Hard Fork Combinator encoding.
    For Shelley-based eras (1-6), the structure is typically:

      [era_tag, encoded_block_bytes]

    Where the inner block is:
      [header, tx_bodies, tx_witness_sets, auxiliary_data_map, invalid_txs]

    The auxiliary_data_map maps tx_index → auxiliary_data, where
    auxiliary_data contains metadata labels (like 721 for CIP-25).
    """
    result = FetchedBlock(raw_cbor=b"")

    try:
        # The block from MsgBlock might be raw bytes or a CBOR structure
        if isinstance(block_cbor, bytes):
            result.raw_cbor = block_cbor
            block_data = cbor2.loads(block_cbor)
        else:
            result.raw_cbor = cbor2.dumps(block_cbor)
            block_data = block_cbor

        # Handle HFC wrapping: either a CBOR tag or a 2-element array [era, block]
        era_index = None
        inner_block = block_data

        if isinstance(block_data, cbor2.CBORTag):
            era_index = block_data.tag
            inner_block = block_data.value
        elif isinstance(block_data, list) and len(block_data) == 2:
            # Common pattern: [era_index, block_bytes]
            if isinstance(block_data[0], int) and block_data[0] in range(7):
                era_index = block_data[0]
                inner_block = block_data[1]

        if era_index is not None:
            result.era_index = era_index
            result.era_name = ERA_NAMES.get(era_index, f"Unknown({era_index})")

        # If inner_block is bytes, decode it
        if isinstance(inner_block, bytes):
            inner_block = cbor2.loads(inner_block)

        # Shelley-era block structure:
        # [header, tx_bodies, tx_witness_sets, auxiliary_data_map, ...]
        if isinstance(inner_block, list) and len(inner_block) >= 4:
            header = inner_block[0]
            tx_bodies = inner_block[1]
            # tx_witnesses = inner_block[2]  # Not needed for metadata
            aux_data_map = inner_block[3]

            # Extract header info
            if isinstance(header, list) and len(header) >= 2:
                header_body = header[0]
                if isinstance(header_body, list) and len(header_body) >= 2:
                    result.slot = header_body[1] if isinstance(header_body[1], int) else None

            # Store transactions
            if isinstance(tx_bodies, (list, dict)):
                result.transactions = tx_bodies if isinstance(tx_bodies, list) else list(tx_bodies.values())

            # Extract auxiliary data (metadata)
            if isinstance(aux_data_map, dict):
                for tx_idx, aux_data in aux_data_map.items():
                    result.auxiliary_data[tx_idx] = aux_data
                    # Extract metadata from auxiliary data
                    if isinstance(aux_data, dict):
                        result.tx_metadata[tx_idx] = aux_data
                    elif isinstance(aux_data, list) and len(aux_data) >= 1:
                        # Some eras wrap as [metadata_map, ...]
                        if isinstance(aux_data[0], dict):
                            result.tx_metadata[tx_idx] = aux_data[0]

    except Exception as e:
        logger.warning(f"Block parsing incomplete: {e}")
        # Still return what we have — the raw_cbor is always available

    return result


def extract_cip25_metadata(block: FetchedBlock, policy_id: str) -> List[Dict]:
    """
    Extract CIP-25 (label 721) metadata for a specific policy from a parsed block.

    CIP-25 structure in metadata:
      { 721: { policy_id: { asset_name: { ...fields... } } } }

    Returns list of dicts with asset_name, fields.
    """
    results = []
    for tx_idx, metadata in block.tx_metadata.items():
        if not isinstance(metadata, dict):
            continue
        # CIP-25 is under label 721
        cip25 = metadata.get(721)
        if not isinstance(cip25, dict):
            continue
        # Look for our policy
        policy_data = cip25.get(policy_id) or cip25.get(bytes.fromhex(policy_id))
        if not isinstance(policy_data, dict):
            continue
        for asset_name, fields in policy_data.items():
            if isinstance(fields, dict):
                name = asset_name if isinstance(asset_name, str) else asset_name.hex() if isinstance(asset_name, bytes) else str(asset_name)
                results.append({"tx_index": tx_idx, "asset_name": name, "fields": fields})
    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  ASYNC NETWORK CLIENT — The "Relay Impersonator"
# ═══════════════════════════════════════════════════════════════════════════════

class OuroborosClient:
    """
    Lightweight Ouroboros N2N client that impersonates a syncing node.

    Implements just enough of the Ouroboros mini-protocols to:
    1. Complete the N2N handshake (Section 3.6)
    2. Find chain intersection points (Section 3.7)
    3. Fetch specific blocks by point (Section 3.8)
    4. Cleanly disconnect

    This is the "sync deception" — the relay thinks we're a peer that
    wants to sync from a specific point. We grab what we need and leave.

    Architecture (per Figure 5.2 in the spec):
    ┌─────────────────────────────────────────────────────┐
    │  TCP Connection (single bearer)                     │
    │  ┌───────────────────────────────────────────────┐  │
    │  │  MUX/DEMUX Layer (Section 2.1)                │  │
    │  │  ┌─────────┐ ┌──────────┐ ┌────────────────┐ │  │
    │  │  │Handshake│ │ChainSync │ │  BlockFetch    │ │  │
    │  │  │ (ID: 0) │ │ (ID: 2)  │ │  (ID: 3)      │ │  │
    │  │  └─────────┘ └──────────┘ └────────────────┘ │  │
    │  └───────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────┘
    """

    def __init__(self, host: str, port: int = 3001,
                 network_magic: int = MAINNET_MAGIC,
                 connect_timeout: float = 10.0):
        self.host = host
        self.port = port
        self.network_magic = network_magic
        self.connect_timeout = connect_timeout

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._negotiated_version: Optional[int] = None

        # Per-protocol receive buffers for demuxing
        self._protocol_buffers: Dict[int, asyncio.Queue] = {
            MiniProtocol.HANDSHAKE: asyncio.Queue(),
            MiniProtocol.CHAIN_SYNC: asyncio.Queue(),
            MiniProtocol.BLOCK_FETCH: asyncio.Queue(),
            MiniProtocol.KEEP_ALIVE: asyncio.Queue(),
        }
        self._demux_task: Optional[asyncio.Task] = None

    # ── Connection Management ──────────────────────────────────────────────

    async def connect(self) -> dict:
        """
        Open TCP connection and perform N2N handshake.

        Per Section 3.6.8: Handshake runs BEFORE the multiplexer is fully
        initialized. Each handshake message is transmitted within a single
        MUX segment (no splitting allowed).

        Returns the handshake result dict.
        """
        logger.info(f"Connecting to {self.host}:{self.port}...")

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.connect_timeout,
            )
        except (asyncio.TimeoutError, OSError) as e:
            raise ConnectionError(f"TCP connect to {self.host}:{self.port} failed: {e}") from e

        self._connected = True
        logger.info(f"TCP connected to {self.host}:{self.port}")

        # ── Handshake Phase (Section 3.6) ──
        # Per Section 3.6.5: We propose version(s) with our parameters
        hs_payload = HandshakeMsg.propose_versions(
            network_magic=self.network_magic,
            initiator_only=True,   # We only consume, never produce
            peer_sharing=0,        # No gossip
            query=False,           # Real connection, not version query
            versions=[N2NVersion.V14],
        )

        # Send handshake as a single MUX segment (Section 3.6.8 requires this)
        segment = mux_encode(MiniProtocol.HANDSHAKE, hs_payload, MUX_MODE_INITIATOR)
        self._writer.write(segment)
        await self._writer.drain()
        logger.debug(f"Sent MsgProposeVersions ({len(hs_payload)} bytes CBOR)")

        # Read handshake response (with 10s timeout per Section 4.1)
        seg = await self._read_segment(timeout=HANDSHAKE_SDU_TIMEOUT)
        if seg.protocol_id != MiniProtocol.HANDSHAKE:
            raise ConnectionError(
                f"Expected Handshake response (protocol 0), got protocol {seg.protocol_id}"
            )

        result = HandshakeMsg.decode_response(seg.payload)
        if result["type"] == "accept":
            self._negotiated_version = result["version"]
            logger.info(
                f"Handshake accepted: version={result['version']}, "
                f"magic={result['network_magic']}, "
                f"diffusion={'InitiatorOnly' if result.get('diffusion_mode') else 'Duplex'}"
            )
        elif result["type"] == "refuse":
            raise ConnectionError(f"Handshake refused: {result['reason']} — {result.get('detail')}")
        else:
            raise ConnectionError(f"Unexpected handshake response: {result}")

        # Start the demuxer background task now that handshake is complete
        self._demux_task = asyncio.create_task(self._demux_loop())

        return result

    async def disconnect(self):
        """
        Cleanly disconnect from the relay.

        Sends protocol termination messages where possible, then closes TCP.
        """
        if not self._connected:
            return

        try:
            # Cancel demuxer
            if self._demux_task and not self._demux_task.done():
                self._demux_task.cancel()
                try:
                    await self._demux_task
                except asyncio.CancelledError:
                    pass

            # Close TCP
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
        except Exception as e:
            logger.debug(f"Disconnect cleanup: {e}")
        finally:
            self._connected = False
            logger.info("Disconnected")

    # ── MUX Demuxer ────────────────────────────────────────────────────────

    async def _read_segment(self, timeout: float = PROTOCOL_SDU_TIMEOUT) -> MuxSegment:
        """
        Read a single MUX segment from the TCP stream.

        Per Section 2.1.1: Header is 8 bytes, payload length is in bytes 6-7.
        Per Section 4.1: Timeout bounds how long to receive a single SDU.
        """
        header = await asyncio.wait_for(
            self._reader.readexactly(MUX_HEADER_SIZE),
            timeout=timeout,
        )
        _, proto_mode, payload_len = struct.unpack("!IHH", header)
        payload = await asyncio.wait_for(
            self._reader.readexactly(payload_len),
            timeout=timeout,
        )
        return MuxSegment.decode(header, payload)

    async def _demux_loop(self):
        """
        Background demuxer — routes incoming segments to protocol-specific queues.

        Per Section 2.1.3: The demultiplexer eagerly reads data from the bearer.
        There is a fixed-size buffer between the DEMUX egress and the mini-protocol
        ingress. If a buffer overflows, it means the peer violated the protocol.
        """
        try:
            while self._connected:
                seg = await self._read_segment()
                proto_id = seg.protocol_id

                if proto_id in self._protocol_buffers:
                    await self._protocol_buffers[proto_id].put(seg)
                elif proto_id == MiniProtocol.KEEP_ALIVE:
                    # Auto-respond to keep-alive pings (Section 3.10)
                    await self._handle_keep_alive(seg)
                else:
                    logger.warning(f"Unexpected protocol {proto_id}, ignoring segment")

        except asyncio.CancelledError:
            pass
        except (asyncio.IncompleteReadError, ConnectionResetError):
            logger.info("Connection closed by relay")
            self._connected = False
        except Exception as e:
            logger.error(f"Demux error: {e}")
            self._connected = False

    async def _recv_protocol(self, protocol_id: int,
                              timeout: float = BLOCKFETCH_STATE_TIMEOUT) -> bytes:
        """
        Receive the next message for a specific mini-protocol.

        Waits on the protocol-specific queue filled by the demuxer.
        Multiple segments may need to be reassembled for large messages.
        """
        queue = self._protocol_buffers.get(protocol_id)
        if not queue:
            raise ValueError(f"No buffer for protocol {protocol_id}")

        seg = await asyncio.wait_for(queue.get(), timeout=timeout)
        return seg.payload

    async def _send_protocol(self, protocol_id: int, payload: bytes):
        """Send a message on a specific mini-protocol, splitting if needed."""
        segments = mux_split_and_encode(protocol_id, payload, MUX_MODE_INITIATOR)
        for seg in segments:
            self._writer.write(seg)
        await self._writer.drain()

    async def _handle_keep_alive(self, seg: MuxSegment):
        """
        Auto-respond to KeepAlive pings — Section 3.10

        Per CDDL: msgKeepAlive = [0, cookie]
        Response:  msgKeepAliveResponse = [1, cookie]
        """
        try:
            msg = cbor2.loads(seg.payload)
            if isinstance(msg, list) and msg[0] == 0:
                cookie = msg[1]
                response = KeepAliveMsg.response(cookie)
                await self._send_protocol(MiniProtocol.KEEP_ALIVE, response)
                logger.debug(f"Responded to KeepAlive cookie={cookie}")
        except Exception as e:
            logger.debug(f"KeepAlive handling: {e}")

    # ── ChainSync Operations ───────────────────────────────────────────────

    async def find_intersect(self, points: List[Point]) -> dict:
        """
        Find the intersection point with the relay's chain — Section 3.7.5

        Per the spec: The consumer sends MsgFindIntersect with a list of known
        points. The producer replies with MsgIntersectFound (+ the most recent
        common point) or MsgIntersectNotFound.

        This is useful to:
        1. Verify the relay has our target block
        2. Get the current chain tip
        3. Position the read-pointer for streaming

        Args:
            points: List of Points to check (most recent first)

        Returns:
            Dict with 'type' = 'intersect_found' or 'intersect_not_found',
            plus 'point' and 'tip' if found.
        """
        payload = ChainSyncMsg.find_intersect(points)
        await self._send_protocol(MiniProtocol.CHAIN_SYNC, payload)
        logger.debug(f"Sent MsgFindIntersect with {len(points)} point(s)")

        response_data = await self._recv_protocol(MiniProtocol.CHAIN_SYNC)
        result = ChainSyncMsg.decode_response(response_data)
        logger.info(f"ChainSync: {result['type']}")
        return result

    async def chainsync_done(self):
        """Send chainSyncMsgDone to cleanly terminate the ChainSync protocol."""
        payload = ChainSyncMsg.msg_done()
        await self._send_protocol(MiniProtocol.CHAIN_SYNC, payload)
        logger.debug("Sent chainSyncMsgDone")

    # ── BlockFetch Operations ──────────────────────────────────────────────

    async def fetch_block(self, point: Point) -> Optional[FetchedBlock]:
        """
        Fetch a single block at a specific point — Section 3.8

        Protocol flow (per state machine in Figure 3.5):
          Client → MsgRequestRange(point, point)   [StIdle → StBusy]
          Server → MsgStartBatch                    [StBusy → StStreaming]
          Server → MsgBlock(body)                   [StStreaming → StStreaming]
          Server → MsgBatchDone                     [StStreaming → StIdle]
                  (or MsgNoBlocks if not found)     [StBusy → StIdle]

        Args:
            point: The exact chain point (slot + block header hash)

        Returns:
            FetchedBlock with parsed data, or None if the relay doesn't have it.
        """
        # MsgRequestRange = [0, point_from, point_to]
        payload = BlockFetchMsg.request_range(point, point)
        await self._send_protocol(MiniProtocol.BLOCK_FETCH, payload)
        logger.debug(f"Sent MsgRequestRange for {point}")

        # Wait for response — either MsgStartBatch or MsgNoBlocks
        # Per Table 3.8: StBusy timeout is 60s
        response_data = await self._recv_protocol(
            MiniProtocol.BLOCK_FETCH,
            timeout=BLOCKFETCH_STATE_TIMEOUT,
        )
        response = BlockFetchMsg.decode_response(response_data)

        if response["type"] == "no_blocks":
            logger.warning(f"Relay doesn't have block at {point}")
            return None

        if response["type"] != "start_batch":
            logger.error(f"Unexpected BlockFetch response: {response['type']}")
            return None

        logger.debug("MsgStartBatch received, streaming blocks...")

        # Collect all MsgBlock messages until MsgBatchDone
        # Per Table 3.8: StStreaming timeout is 60s per message
        block_bodies = []
        while True:
            block_data = await self._recv_protocol(
                MiniProtocol.BLOCK_FETCH,
                timeout=BLOCKFETCH_STATE_TIMEOUT,
            )
            block_response = BlockFetchMsg.decode_response(block_data)

            if block_response["type"] == "block":
                block_bodies.append(block_response["block_body"])
                logger.debug(f"Received MsgBlock ({len(block_bodies)} so far)")

            elif block_response["type"] == "batch_done":
                logger.info(f"MsgBatchDone — received {len(block_bodies)} block(s)")
                break

            else:
                logger.warning(f"Unexpected in streaming: {block_response['type']}")
                break

        if not block_bodies:
            return None

        # Parse the first (and usually only) block
        return parse_block(block_bodies[0])

    async def fetch_block_range(self, point_from: Point, point_to: Point) -> List[FetchedBlock]:
        """
        Fetch a range of blocks — Section 3.8

        Range is inclusive on both sides. Use for fetching multiple
        consecutive blocks (e.g., all pages of a Ledger Scroll).
        """
        payload = BlockFetchMsg.request_range(point_from, point_to)
        await self._send_protocol(MiniProtocol.BLOCK_FETCH, payload)
        logger.debug(f"Sent MsgRequestRange from {point_from} to {point_to}")

        response_data = await self._recv_protocol(MiniProtocol.BLOCK_FETCH)
        response = BlockFetchMsg.decode_response(response_data)

        if response["type"] == "no_blocks":
            logger.warning("Relay doesn't have the requested range")
            return []

        if response["type"] != "start_batch":
            return []

        blocks = []
        while True:
            block_data = await self._recv_protocol(MiniProtocol.BLOCK_FETCH)
            block_response = BlockFetchMsg.decode_response(block_data)

            if block_response["type"] == "block":
                blocks.append(parse_block(block_response["block_body"]))
            elif block_response["type"] == "batch_done":
                break
            else:
                break

        logger.info(f"Fetched {len(blocks)} blocks in range")
        return blocks

    async def blockfetch_done(self):
        """Send MsgClientDone to cleanly terminate BlockFetch — CDDL: [1]"""
        payload = BlockFetchMsg.client_done()
        await self._send_protocol(MiniProtocol.BLOCK_FETCH, payload)
        logger.debug("Sent MsgClientDone (BlockFetch)")

    # ── High-Level "Snipe" Operation ───────────────────────────────────────

    async def snipe_block(self, slot: int, block_hash_hex: str) -> Optional[FetchedBlock]:
        """
        The complete "sync deception" — connect, grab one block, disconnect.

        This is the primary operation for Ledger Scrolls: fetch a specific
        block's data without syncing the entire chain.

        Args:
            slot:           The slot number of the target block
            block_hash_hex: The block header hash as a hex string (64 chars)

        Returns:
            FetchedBlock with all parsed data, or None if not found.

        Example:
            block = await client.snipe_block(
                slot=12345678,
                block_hash_hex="abc123def456..."
            )
        """
        point = Point(slot=slot, block_hash=bytes.fromhex(block_hash_hex))

        # Step 1: Verify the relay knows about this block (ChainSync)
        intersect = await self.find_intersect([point])
        if intersect["type"] != "intersect_found":
            logger.warning(f"Point not found on relay's chain. Tip: {intersect.get('tip')}")
            # Try BlockFetch anyway — the relay might still have it in its database
            logger.info("Attempting BlockFetch despite intersection miss...")

        # Step 2: Fetch the block (BlockFetch)
        block = await self.fetch_block(point)

        # Step 3: Signal we're done
        try:
            await self.blockfetch_done()
        except Exception:
            pass  # Best-effort cleanup

        return block


# ═══════════════════════════════════════════════════════════════════════════════
#  CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def fetch_block_at_point(
    slot: int,
    block_hash_hex: str,
    relay_host: str = "backbone.cardano.iog.io",
    relay_port: int = 3001,
    network_magic: int = MAINNET_MAGIC,
) -> Optional[FetchedBlock]:
    """
    One-shot function: connect to relay, fetch one block, disconnect.

    This is the simplest way to use the client. Example:

        import asyncio

        block = asyncio.run(fetch_block_at_point(
            slot=141017832,
            block_hash_hex="a1b2c3d4e5f6...",
            relay_host="backbone.cardano.iog.io",
        ))

        if block:
            print(f"Got block from era: {block.era_name}")
            print(f"Raw CBOR: {len(block.raw_cbor)} bytes")
    """
    client = OuroborosClient(relay_host, relay_port, network_magic)
    try:
        await client.connect()
        block = await client.snipe_block(slot, block_hash_hex)
        return block
    finally:
        await client.disconnect()


async def query_chain_tip(
    relay_host: str = "backbone.cardano.iog.io",
    relay_port: int = 3001,
    network_magic: int = MAINNET_MAGIC,
) -> dict:
    """
    Connect and ask the relay for its current chain tip.

    Uses ChainSync MsgFindIntersect with origin to get the tip info.
    """
    client = OuroborosClient(relay_host, relay_port, network_magic)
    try:
        await client.connect()
        # Finding intersection with origin will give us the tip
        result = await client.find_intersect([])
        return result
    finally:
        await client.disconnect()


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI — Interactive testing interface
# ═══════════════════════════════════════════════════════════════════════════════

async def cli_main():
    """Interactive CLI for testing the Ouroboros client."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Cardano Relay Impersonator — Fetch blocks via Ouroboros P2P",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch a specific block by slot + hash
  python ouroboros_client.py fetch --slot 141017832 --hash abc123...

  # Test handshake only
  python ouroboros_client.py handshake --relay backbone.cardano.iog.io

  # Query chain tip
  python ouroboros_client.py tip

  # Query handshake versions (version query mode)
  python ouroboros_client.py versions
        """,
    )
    parser.add_argument("--relay", default="backbone.cardano.iog.io", help="Relay hostname")
    parser.add_argument("--port", type=int, default=3001, help="Relay port")
    parser.add_argument("--magic", type=int, default=MAINNET_MAGIC, help="Network magic")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # handshake command
    hs_parser = subparsers.add_parser("handshake", help="Test N2N handshake only")

    # fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch a block by slot + hash")
    fetch_parser.add_argument("--slot", type=int, required=True, help="Slot number")
    fetch_parser.add_argument("--hash", required=True, help="Block header hash (hex)")
    fetch_parser.add_argument("--output", "-o", help="Save raw CBOR to file")

    # tip command
    tip_parser = subparsers.add_parser("tip", help="Query current chain tip")

    # versions command
    ver_parser = subparsers.add_parser("versions", help="Query supported N2N versions")

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.command:
        parser.print_help()
        return

    if args.command == "handshake":
        print(f"\n{'='*60}")
        print(f"  Ouroboros N2N Handshake Test")
        print(f"  Relay: {args.relay}:{args.port}")
        print(f"  Magic: {args.magic}")
        print(f"{'='*60}\n")

        client = OuroborosClient(args.relay, args.port, args.magic)
        try:
            result = await client.connect()
            print(f"\n✓ Handshake successful!")
            print(f"  Negotiated version: {result['version']}")
            print(f"  Network magic:      {result['network_magic']}")
            print(f"  Diffusion mode:     {'InitiatorOnly' if result.get('diffusion_mode') else 'Duplex'}")
            print(f"  Peer sharing:       {result.get('peer_sharing')}")
        except Exception as e:
            print(f"\n✗ Handshake failed: {e}")
        finally:
            await client.disconnect()

    elif args.command == "fetch":
        print(f"\n{'='*60}")
        print(f"  Block Snipe Operation")
        print(f"  Relay: {args.relay}:{args.port}")
        print(f"  Slot:  {args.slot}")
        print(f"  Hash:  {args.hash[:16]}...")
        print(f"{'='*60}\n")

        client = OuroborosClient(args.relay, args.port, args.magic)
        try:
            await client.connect()
            block = await client.snipe_block(args.slot, args.hash)

            if block:
                print(f"\n✓ Block fetched successfully!")
                print(f"  Era:        {block.era_name or 'Unknown'}")
                print(f"  Raw CBOR:   {len(block.raw_cbor)} bytes")
                print(f"  Slot:       {block.slot}")
                print(f"  TXs:        {len(block.transactions)}")
                print(f"  Metadata:   {len(block.tx_metadata)} tx(s) with metadata")

                if args.output:
                    with open(args.output, "wb") as f:
                        f.write(block.raw_cbor)
                    print(f"  Saved to:   {args.output}")
            else:
                print("\n✗ Block not found on this relay")

        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await client.disconnect()

    elif args.command == "tip":
        print(f"\nQuerying chain tip from {args.relay}:{args.port}...")
        try:
            result = await query_chain_tip(args.relay, args.port, args.magic)
            tip = result.get("tip")
            if tip:
                print(f"\n✓ Chain tip info:")
                print(f"  Raw: {tip}")
            else:
                print(f"\n  Result: {result}")
        except Exception as e:
            print(f"\n✗ Error: {e}")

    elif args.command == "versions":
        print(f"\nQuerying supported versions from {args.relay}:{args.port}...")
        # Use query=True in handshake to get version info
        hs_payload = HandshakeMsg.propose_versions(
            network_magic=args.magic,
            initiator_only=True,
            peer_sharing=0,
            query=True,  # Version query mode
            versions=[N2NVersion.V14],
        )

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(args.relay, args.port),
                timeout=10.0,
            )
            segment = mux_encode(MiniProtocol.HANDSHAKE, hs_payload, MUX_MODE_INITIATOR)
            writer.write(segment)
            await writer.drain()

            header = await asyncio.wait_for(reader.readexactly(MUX_HEADER_SIZE), timeout=10.0)
            _, _, payload_len = struct.unpack("!IHH", header)
            payload = await asyncio.wait_for(reader.readexactly(payload_len), timeout=10.0)

            result = HandshakeMsg.decode_response(payload)
            if result["type"] == "query_reply":
                print(f"\n✓ Supported versions:")
                for version, vdata in result["version_table"].items():
                    print(f"  v{version}: magic={vdata[0]}, "
                          f"diffusion={'InitiatorOnly' if vdata[1] else 'Duplex'}, "
                          f"peerSharing={vdata[2]}, query={vdata[3]}")
            else:
                print(f"\n  Response: {result}")

            writer.close()
            await writer.wait_closed()
        except Exception as e:
            print(f"\n✗ Error: {e}")


if __name__ == "__main__":
    asyncio.run(cli_main())
