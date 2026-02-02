from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Tuple

import cbor2

from .cbor_helpers import Point, blake2b_256, safe_cbor_loads
from .n2n_client import MiniProtocol, N2NConnection

logger = logging.getLogger("lsview.chainsync")


class ChainSyncMsg:
    REQUEST_NEXT = 0
    AWAIT_REPLY = 1
    ROLL_FORWARD = 2
    ROLL_BACKWARD = 3
    FIND_INTERSECT = 4
    INTERSECT_FOUND = 5
    INTERSECT_NOT_FOUND = 6
    DONE = 7

    @staticmethod
    def find_intersect(points: List[Point]) -> bytes:
        pts = [p.to_cbor() for p in points]
        return cbor2.dumps([ChainSyncMsg.FIND_INTERSECT, pts])

    @staticmethod
    def request_next() -> bytes:
        return cbor2.dumps([ChainSyncMsg.REQUEST_NEXT])

    @staticmethod
    def done() -> bytes:
        return cbor2.dumps([ChainSyncMsg.DONE])

    @staticmethod
    def decode(msg_bytes: bytes) -> Dict[str, Any]:
        msg = safe_cbor_loads(msg_bytes)
        if not isinstance(msg, list) or not msg:
            raise ValueError("invalid ChainSync msg")
        tag = msg[0]
        if tag == ChainSyncMsg.AWAIT_REPLY:
            return {"type": "await_reply"}
        if tag == ChainSyncMsg.ROLL_FORWARD:
            return {"type": "roll_forward", "header": msg[1], "tip": msg[2]}
        if tag == ChainSyncMsg.ROLL_BACKWARD:
            return {"type": "roll_backward", "point": msg[1], "tip": msg[2]}
        if tag == ChainSyncMsg.INTERSECT_FOUND:
            return {"type": "intersect_found", "point": msg[1], "tip": msg[2]}
        if tag == ChainSyncMsg.INTERSECT_NOT_FOUND:
            return {"type": "intersect_not_found", "tip": msg[1]}
        return {"type": "unknown", "raw": msg}


def _unwrap_header_bytes(header_obj: Any) -> Tuple[str, bytes]:
    """
    The roll_forward header is an HFC Header. You commonly see:
      - [era, header_bytes]
      - CBORTag(era, header_bytes)

    Returns (era_tag, header_bytes).
    """
    if isinstance(header_obj, list) and len(header_obj) == 2 and isinstance(header_obj[1], (bytes, bytearray)):
        return str(header_obj[0]), bytes(header_obj[1])

    if isinstance(header_obj, cbor2.CBORTag) and isinstance(header_obj.value, (bytes, bytearray)):
        return str(header_obj.tag), bytes(header_obj.value)

    raise ValueError(f"unsupported header representation: {type(header_obj)}")


def header_point(header_obj: Any) -> Point:
    era, hb = _unwrap_header_bytes(header_obj)
    decoded = safe_cbor_loads(hb)

    slot = None
    if isinstance(decoded, list) and decoded:
        body = decoded[0]
        if isinstance(body, list) and len(body) > 1 and isinstance(body[1], int):
            slot = int(body[1])

    if slot is None:
        raise ValueError(f"could not extract slot from header bytes (era={era})")

    return Point(slot=slot, block_hash=blake2b_256(hb))


@dataclass
class ChainSyncClient:
    conn: N2NConnection

    async def find_intersect(self, points: List[Point]) -> Dict[str, Any]:
        await self.conn.send(MiniProtocol.CHAINSYNC, ChainSyncMsg.find_intersect(points))
        return ChainSyncMsg.decode(await self.conn.recv(MiniProtocol.CHAINSYNC))

    async def done(self) -> None:
        try:
            await self.conn.send(MiniProtocol.CHAINSYNC, ChainSyncMsg.done())
        except Exception:
            pass

    async def stream_headers(self, max_headers: int, idle_timeout: float = 15.0) -> AsyncIterator[Tuple[Point, Any]]:
        yielded = 0
        while yielded < max_headers:
            await self.conn.send(MiniProtocol.CHAINSYNC, ChainSyncMsg.request_next())

            while True:
                try:
                    msg_bytes = await asyncio.wait_for(self.conn.recv(MiniProtocol.CHAINSYNC), timeout=idle_timeout)
                except asyncio.TimeoutError:
                    return

                resp = ChainSyncMsg.decode(msg_bytes)

                if resp["type"] == "await_reply":
                    continue

                if resp["type"] == "roll_forward":
                    pt = header_point(resp["header"])
                    yielded += 1
                    yield pt, resp["header"]
                    break

                if resp["type"] == "roll_backward":
                    logger.warning("Chain rollback encountered; continuing.")
                    break

                break
