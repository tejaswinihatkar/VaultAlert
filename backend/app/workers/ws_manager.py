"""VaultAlert — WebSocket Connection Manager.

Manages active WebSocket clients, broadcasts real-time events to rooms (per-locker, org-wide, or global live-feed).
"""

import json
from collections import defaultdict
from typing import Dict, Set
from uuid import UUID

from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    """Thread-safe WebSocket connection manager with room support."""

    def __init__(self) -> None:
        # org_id → set of WebSocket connections
        self._org_rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
        # locker_id → set of WebSocket connections
        self._locker_rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
        # Global live feed room
        self._global_feed: Set[WebSocket] = set()

    async def connect_global(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._global_feed.add(websocket)
        logger.debug(f"WS client connected to global live feed | total={len(self._global_feed)}")

    async def connect_org(self, websocket: WebSocket, org_id: str) -> None:
        await websocket.accept()
        self._org_rooms[org_id].add(websocket)
        logger.debug(f"WS client connected to org room: {org_id} | total={len(self._org_rooms[org_id])}")

    async def connect_locker(self, websocket: WebSocket, locker_id: str) -> None:
        await websocket.accept()
        self._locker_rooms[locker_id].add(websocket)
        logger.debug(f"WS client connected to locker room: {locker_id}")

    def disconnect(self, websocket: WebSocket, org_id: str | None = None, locker_id: str | None = None) -> None:
        self._global_feed.discard(websocket)
        if org_id:
            self._org_rooms[org_id].discard(websocket)
        if locker_id:
            self._locker_rooms[locker_id].discard(websocket)

    async def broadcast_global(self, event_type: str, data: dict) -> None:
        """Broadcast an event to all global feed listeners (e.g. dashboard)."""
        message = json.dumps({"type": event_type, "data": data})
        dead: Set[WebSocket] = set()
        for ws in list(self._global_feed):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._global_feed.discard(ws)

    async def broadcast_to_org(self, org_id: str, event_type: str, data: dict) -> None:
        """Broadcast an event to all clients watching an organization."""
        await self.broadcast_global(event_type, data)
        message = json.dumps({"type": event_type, "data": data})
        dead: Set[WebSocket] = set()
        for ws in list(self._org_rooms.get(org_id, [])):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._org_rooms[org_id].discard(ws)

    async def broadcast_to_locker(self, locker_id: str, event_type: str, data: dict) -> None:
        """Broadcast an event to all clients watching a specific locker."""
        await self.broadcast_global(event_type, data)
        message = json.dumps({"type": event_type, "data": data})
        dead: Set[WebSocket] = set()
        for ws in list(self._locker_rooms.get(locker_id, [])):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._locker_rooms[locker_id].discard(ws)


# ── Global singleton ─────────────────────────────────────────────────────────
manager = ConnectionManager()
