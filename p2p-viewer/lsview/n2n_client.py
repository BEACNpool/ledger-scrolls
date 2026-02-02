from __future__ import annotations

import asyncio
import logging
import struct
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, Optional, Tuple

import cbor2

from .cbor_helpers import safe_cbor_loads

logger = logging.getLogger("lsview.n2n")

MAINNET_MAGIC = 764824073

MUX_HEADER_SIZE = 8
MUX_MODE_INITIATOR = 0  # initiator mode bit = 0


class MiniProtocol(IntEnum):
    HANDSHAKE = 0
    CHAINSYNC = 2
    BLOCK_FETCH = 3


class N2NVersion(IntEnum):
    V14 = 14


def mux_encode(protocol_id: int, payload: bytes, initiator: bool = True, timestamp: int = 0) -> bytes:
    mp = ((int(protocol_id) & 0x7FFF) << 1) | (0 if initiator else 1)
    header = struct.pack(">IHH", timestamp & 0xFFFFFFFF, mp & 0xFFFF, len(payload) & 0xFFFF
    )
    return header + payload


def mux_decode_header(header: bytes) -> Tuple[int, int, bool, int]:
    if len(header) != MUX_HEADER_SIZE:
        raise ValueError("invalid mux header size")
    timestamp, mp, length = struct.unpack(">IHH", header)
    proto_id = (mp >> 1) & 0x7FFF
    initiator = (mp & 1) == 0
    return timestamp, proto_id, initiator, length


class HandshakeMsg:
    @staticmethod
    def propose_versions(
        network_magic: int = MAINNET_MAGIC,
        initiator_only: bool = True,
        peer_sharing: int = 0,
        query: bool = False,
        versions: Optional[list[int]] = None,
    ) -> bytes:
        if versions is None:
            versions = [int(N2NVersion.V14)]
        version_table: Dict[int, list] = {}
        for v in versions:
            version_table[int(v)] = [int(network_magic), bool(initiator_only), int(peer_sharing), bool(query)]
        msg = [0, version_table]  # MsgProposeVersions
        return cbor2.dumps(msg)

    @staticmethod
    def decode_response(payload: bytes) -> Dict[str, Any]:
        msg = safe_cbor_loads(payload)
        if not isinstance(msg, list) or not msg:
            raise ValueError("invalid handshake response")

        if msg[0] == 1:  # MsgAcceptVersion
            _, version, data = msg
            return {"type": "accept", "version": int(version), "data": data}
        if msg[0] == 2:  # MsgRefuse
            return {"type": "refuse", "raw": msg}
        if msg[0] == 3:  # MsgQueryReply
            return {"type": "query_reply", "version_table": msg[1]}
        return {"type": "unknown", "raw": msg}


@dataclass
class N2NConnection:
    relay_host: str
    relay_port: int
    network_magic: int = MAINNET_MAGIC
    timeout: float = 60.0

    reader: Optional[asyncio.StreamReader] = None
    writer: Optional[asyncio.StreamWriter] = None
    negotiated_version: Optional[int] = None

    async def open(self) -> Dict[str, Any]:
        self.reader, self.writer = await asyncio.wait_for(
            asyncio.open_connection(self.relay_host, self.relay_port),
            timeout=self.timeout,
        )
        return await self.handshake()

    async def close(self) -> None:
        if self.writer is not None:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except (ConnectionResetError, OSError):
                pass
            except Exception:
                pass
        self.reader = None
        self.writer = None

    async def handshake(self) -> Dict[str, Any]:
        assert self.writer and self.reader
        payload = HandshakeMsg.propose_versions(
            network_magic=self.network_magic,
            initiator_only=True,
            peer_sharing=0,
            query=False,
        )
        self.writer.write(mux_encode(int(MiniProtocol.HANDSHAKE), payload))
        await self.writer.drain()

        header = await asyncio.wait_for(self.reader.readexactly(MUX_HEADER_SIZE), timeout=self.timeout)
        _ts, proto, _initiator, length = mux_decode_header(header)
        if proto != int(MiniProtocol.HANDSHAKE):
            raise ValueError(f"unexpected protocol during handshake: {proto}")
        resp_payload = await asyncio.wait_for(self.reader.readexactly(length), timeout=self.timeout)
        decoded = HandshakeMsg.decode_response(resp_payload)

        if decoded["type"] != "accept":
            raise RuntimeError(f"handshake failed: {decoded}")

        self.negotiated_version = decoded["version"]
        logger.info("Handshake OK: version=%s magic=%s", self.negotiated_version, self.network_magic)
        return {"version": self.negotiated_version, "network_magic": self.network_magic, "data": decoded.get("data")}

    async def send(self, protocol: MiniProtocol, cbor_payload: bytes) -> None:
        assert self.writer
        self.writer.write(mux_encode(int(protocol), cbor_payload))
        await self.writer.drain()

    async def recv(self, expected_protocol: MiniProtocol) -> bytes:
        assert self.reader
        header = await asyncio.wait_for(self.reader.readexactly(MUX_HEADER_SIZE), timeout=self.timeout)
        _ts, proto, _initiator, length = mux_decode_header(header)
        if proto != int(expected_protocol):
            raise ValueError(f"unexpected protocol: got={proto} expected={int(expected_protocol)}")
        payload = await asyncio.wait_for(self.reader.readexactly(length), timeout=self.timeout)
        return payload
