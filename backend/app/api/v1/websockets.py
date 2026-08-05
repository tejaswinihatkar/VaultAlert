"""VaultAlert — WebSocket API Endpoints.

Real-time event streaming for the dashboard and per-locker live pages.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger

from app.core.security import decode_token
from app.workers.ws_manager import manager

router = APIRouter(tags=["WebSockets"])


async def _authenticate_ws(token: str | None) -> dict | None:
    """Validate JWT token passed as query param for WS connections."""
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return payload
    except Exception:
        return None


@router.websocket("/ws/live-feed")
async def live_feed_websocket(websocket: WebSocket):
    """
    Public WebSocket endpoint for dashboard real-time security events and camera snapshots.
    Connect: ws://host/ws/live-feed or wss://host/ws/live-feed
    """
    await manager.connect_global(websocket)
    logger.info("WS client connected to live-feed")

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WS client disconnected from live-feed")


@router.websocket("/ws/org/{org_id}")
async def org_websocket(
    websocket: WebSocket,
    org_id: str,
    token: str | None = Query(default=None),
):
    """
    WebSocket endpoint for organization-wide real-time events.
    Connect: ws://host/ws/org/{org_id}?token={access_token}
    """
    payload = await _authenticate_ws(token)
    if not payload or payload.get("sub") is None:
        await websocket.close(code=4001)
        return

    await manager.connect_org(websocket, org_id)
    logger.info(f"WS org room connected: org={org_id} user={payload['sub']}")

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, org_id=org_id)
        logger.info(f"WS org room disconnected: org={org_id}")


@router.websocket("/ws/locker/{locker_id}")
async def locker_websocket(
    websocket: WebSocket,
    locker_id: str,
    token: str | None = Query(default=None),
):
    """
    WebSocket endpoint for live locker monitoring.
    Connect: ws://host/ws/locker/{locker_id}?token={access_token}
    """
    payload = await _authenticate_ws(token)
    if not payload:
        await websocket.close(code=4001)
        return

    await manager.connect_locker(websocket, locker_id)
    logger.info(f"WS locker room connected: locker={locker_id} user={payload['sub']}")

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, locker_id=locker_id)
        logger.info(f"WS locker room disconnected: locker={locker_id}")
