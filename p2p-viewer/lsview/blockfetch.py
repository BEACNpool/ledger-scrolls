from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import cbor2

from .cbor_helpers import Point, safe_cbor_loads
from .n2n_client import MiniProtocol, N2NConnection


class BlockFetchMsg:
    REQUEST_RANGE = 0
    CLIENT_DONE = 1
    START_BATCH = 2
    NO_BLOCKS = 3
    BLOCK = 4
    BATCH_DONE = 5

    @staticmethod
    def request_range(point_from: Point, point_to: Point) -> bytes:
        return cbor2.dumps([BlockFetchMsg.REQUEST_RANGE, point_from.to_cbor(), point_to.to_cbor()])

    @staticmethod
    def client_done() -> bytes:
        return cbor2.dumps([BlockFetchMsg.CLIENT_DONE])

    @staticmethod
    def decode(msg_bytes: bytes) -> Dict[str, Any]:
        msg = safe_cbor_loads(msg_bytes)
        if not isinstance(msg, list) or not msg:
            raise ValueError("invalid BlockFetch msg")
        tag = msg[0]
        if tag == BlockFetchMsg.START_BATCH:
            return {"type": "start_batch"}
        if tag == BlockFetchMsg.NO_BLOCKS:
            return {"type": "no_blocks"}
        if tag == BlockFetchMsg.BLOCK:
            return {"type": "block", "block_body": msg[1]}
        if tag == BlockFetchMsg.BATCH_DONE:
            return {"type": "batch_done"}
        return {"type": "unknown", "raw": msg}


@dataclass
class BlockFetchClient:
    conn: N2NConnection

    async def fetch_block_body(self, point: Point) -> Optional[bytes]:
        await self.conn.send(MiniProtocol.BLOCK_FETCH, BlockFetchMsg.request_range(point, point_to=point))

        first = BlockFetchMsg.decode(await self.conn.recv(MiniProtocol.BLOCK_FETCH))
        if first["type"] == "no_blocks":
            return None
        if first["type"] != "start_batch":
            return None

        block_body = None
        while True:
            resp = BlockFetchMsg.decode(await self.conn.recv(MiniProtocol.BLOCK_FETCH))
            if resp["type"] == "block":
                bb = resp["block_body"]
                block_body = bb if isinstance(bb, bytes) else cbor2.dumps(bb)
            elif resp["type"] == "batch_done":
                break
            else:
                break

        return block_body

    async def done(self) -> None:
        try:
            await self.conn.send(MiniProtocol.BLOCK_FETCH, BlockFetchMsg.client_done())
        except Exception:
            pass
