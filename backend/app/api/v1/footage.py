"""
VaultAlert — Footage & Telegram Events Router
Reads from the in-memory telegram_cache populated by the background telegram_worker.
Includes a proxy endpoint to serve Telegram photos server-side (avoids CORS issues).
"""

import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import httpx
from app.workers import telegram_cache
from app.workers.ws_manager import manager as ws_manager

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


# ── GET /api/v1/telegram-events ───────────────────────────────────────────────
@router.get("/telegram-events", response_model=List[Dict[str, Any]])
async def get_telegram_events():
    """
    Returns all cached text alerts from the Telegram security group, newest first.
    """
    return telegram_cache.get_events()
