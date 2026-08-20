"""
VaultAlert — Footage & Telegram Events Router
Reads from the in-memory telegram_cache populated by the background telegram_worker.
Includes a proxy endpoint to serve Telegram photos server-side (avoids CORS issues).
"""

import time
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import httpx
from app.workers import telegram_cache
from app.workers.ws_manager import manager as ws_manager
from app.services import history_service

router = APIRouter(tags=["Footage & Telegram"])

TELEGRAM_BOT_TOKEN = "8722120064:AAF6Yshc950N6CksWbLAeMa537zXG8h5ty0"


class TextAlert(BaseModel):
    message: str
    photo_url: Optional[str] = None


# ── POST /api/v1/telegram-text ────────────────────────────────────────────────
@router.post("/telegram-text")
async def ingest_text_alert(payload: TextAlert):
    """
    Ingest a hardware TEXT alert (e.g. "Unauthorized fingerprint!") forwarded by the
    userbot reader. Caches it as a timeline event and broadcasts over WebSocket.
    Does NOT re-post to Telegram, so it can't create an echo loop. Content-deduped
    by telegram_cache.add_event.
    """
    text = (payload.message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty message.")

    evt_id = telegram_cache.add_event({
        "time": int(time.time()),
        "message": text,
        "photo_url": payload.photo_url,
    })
    await ws_manager.broadcast_global("security_event", {
        "id": evt_id,
        "originalMessage": text,
        "timestamp": int(time.time() * 1000),
        "photo_url": payload.photo_url,
    })
    # Persist to DB for historical/timestamped view (best-effort, non-blocking).
    asyncio.create_task(history_service.persist_alert(text, payload.photo_url))
    return {"status": "ok", "id": evt_id}


# ── GET /api/v1/footage ───────────────────────────────────────────────────────
@router.get("/footage", response_model=List[Dict[str, Any]])
async def get_footage():
    """
    Returns all cached photos from the Telegram security group, newest first.
    Each item has a proxied 'url' pointing to /api/v1/footage/photo/{file_id}
    so the browser never needs to call Telegram directly.
    """
    return telegram_cache.get_photos()


# ── GET /api/v1/footage/photo/{file_id} ───────────────────────────────────────
@router.get("/footage/photo/{file_id}")
async def proxy_telegram_photo(file_id: str):
    """
    Downloads a Telegram photo by file_id and streams it to the browser.
    This avoids any CORS or auth issues with direct Telegram URLs.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: resolve file_id → file_path
        r = await client.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
        )
        data = r.json()
        if not data.get("ok"):
            raise HTTPException(status_code=404, detail=f"Telegram file not found: {data.get('description')}")

        file_path = data["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

        # Step 2: download the image bytes
        img = await client.get(download_url)
        if img.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to download photo from Telegram")

        content_type = img.headers.get("content-type", "image/jpeg")
        return Response(
            content=img.content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )


# ── POST /api/v1/footage/clear ────────────────────────────────────────────────
@router.post("/footage/clear")
async def clear_live_cache():
    """
    Clear the live in-memory cache (footage + events shown on the dashboard now).
    Persistent DB history is NOT affected. New alerts will repopulate it.
    """
    counts = telegram_cache.clear()
    return {"status": "ok", "cleared": counts}


# ── GET /api/v1/history ───────────────────────────────────────────────────────
@router.get("/history")
async def get_history(limit: int = 200, severity: Optional[str] = None):
    """
    Persistent, timestamped alert history from the DB (survives restarts).
    Newest first. Optional ?severity=Critical|Warning|Info and ?limit=N.
    Returns [] gracefully if the DB is unavailable so the dashboard never breaks.
    """
    from sqlalchemy import select, desc
    from app.core.database import AsyncSessionLocal
    from app.models.models import Event

    try:
        async with AsyncSessionLocal() as db:
            stmt = select(Event).order_by(desc(Event.timestamp)).limit(min(limit, 1000))
            if severity:
                from app.models.models import AlertSeverity
                try:
                    stmt = stmt.where(Event.severity == AlertSeverity(severity))
                except ValueError:
                    pass
            rows = (await db.execute(stmt)).scalars().all()
            return [
                {
                    "id": str(e.id),
                    "message": e.description or e.event_type.value,
                    "event_type": e.event_type.value,
                    "severity": e.severity.value,
                    "photo_url": e.before_snapshot_url,
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                }
                for e in rows
            ]
    except Exception as e:
        from loguru import logger
        logger.warning(f"history read failed: {e}")
        return []


# ── GET /api/v1/telegram-events ───────────────────────────────────────────────
@router.get("/telegram-events", response_model=List[Dict[str, Any]])
async def get_telegram_events():
    """
    Returns all cached text alerts from the Telegram security group, newest first.
    """
    return telegram_cache.get_events()
