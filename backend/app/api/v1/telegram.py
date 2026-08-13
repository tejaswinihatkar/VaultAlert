"""VaultAlert — Telegram Bot Integration Router with Instant Webhook Push."""

import time
import httpx
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.core.config import settings
from app.services.s3_service import s3_service
from app.workers.ws_manager import manager as ws_manager
from app.workers import telegram_cache
from app.models.models import Event, EventType, AlertSeverity
from app.schemas.schemas import EventResponse

router = APIRouter(prefix="/integrations/telegram", tags=["Telegram Integration"])

TELEGRAM_BOT_TOKEN = "8722120064:AAF6Yshc950N6CksWbLAeMa537zXG8h5ty0"
TELEGRAM_CHAT_ID = -1004493857137


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Telegram Webhook Receiver.
    Telegram pushes updates here in real-time (< 200ms latency).
    Extracts photos/text, caches them, and streams via WebSockets instantly.
    """
    try:
        data = await request.json()
        telegram_cache.add_payload(data)

        msg = (
            data.get("message")
            or data.get("channel_post")
            or data.get("edited_message")
            or data.get("edited_channel_post")
            or {}
        )

        if not msg:
            return {"status": "ok", "detail": "no message payload"}

        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "") or msg.get("caption", "")
        photos = msg.get("photo", [])
        document = msg.get("document")
        is_doc_image = document and document.get("mime_type", "").startswith("image/")

        logger.info(f"Telegram Webhook msg from chat_id={chat_id} text='{text[:40]}' photos={len(photos)} doc_image={bool(is_doc_image)}")

        file_id = None
        photo_url_direct = None

        if photos or is_doc_image:
            file_id = photos[-1]["file_id"] if photos else document["file_id"]
            photo_url_direct = f"https://vaultalert-api.onrender.com/api/v1/footage/photo/{file_id}"

            photo_entry = {
                "file_id": file_id,
                "url": photo_url_direct,
                "caption": text or "Security Snapshot",
                "date": msg.get("date", int(time.time())),
            }
            telegram_cache.add_photo(photo_entry)

            # Broadcast camera_snapshot over WebSocket
            await ws_manager.broadcast_global("camera_snapshot", {
                "file_id": file_id,
                "url": photo_url_direct,
                "caption": text or "Security Snapshot",
                "timestamp": msg.get("date", int(time.time())) * 1000,
            })

        if text or photo_url_direct:
            evt_id = str(msg.get("message_id", f"tg_{int(time.time())}"))
            telegram_cache.add_event({
                "id": evt_id,
                "time": msg.get("date", int(time.time())),
                "message": text or "Security snapshot captured.",
                "photo_url": photo_url_direct,
            })

            # Broadcast security_event over WebSocket
            await ws_manager.broadcast_global("security_event", {
                "id": evt_id,
                "originalMessage": text or "Security snapshot captured.",
                "timestamp": msg.get("date", int(time.time())) * 1000,
                "photo_url": photo_url_direct,
            })

        return {"status": "ok", "processed": True, "has_photo": bool(photos)}

    except Exception as e:
        logger.error(f"Error handling Telegram webhook: {e}")
        return {"status": "error", "detail": str(e)}


@router.post("/setup-webhook")
async def setup_telegram_webhook():
    """
    Registers Render URL as the Telegram Bot Webhook.
    """
    webhook_url = "https://vaultalert-api.onrender.com/api/v1/integrations/telegram/webhook"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={webhook_url}"
        )
        return r.json()


@router.post("/alert", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def receive_telegram_alert(
    x_telegram_bot_token: str = Header(..., alias="X-Telegram-Bot-Token"),
    locker_id: UUID = Form(...),
    event_type: str = Form(...),
    description: str = Form(...),
    severity: str = Form(...),
    threat_score: float = Form(0.0),
    photo: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
):
    if x_telegram_bot_token != settings.SECRET_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid integration token.")

    snapshot_url = None
    if photo:
        photo_bytes = await photo.read()
        snapshot_url = await s3_service.upload_snapshot(
            data=photo_bytes,
            locker_id=str(locker_id),
            event_id=f"tg_{locker_id.hex[:10]}",
            suffix="captured"
        )

    try:
        mapped_event_type = EventType(event_type)
    except ValueError:
        mapped_event_type = EventType.motion_detected

    try:
        mapped_severity = AlertSeverity(severity)
    except ValueError:
        mapped_severity = AlertSeverity.info

    event = Event(
        locker_id=locker_id,
        event_type=mapped_event_type,
        severity=mapped_severity,
        threat_score=threat_score,
        description=description,
        before_snapshot_url=snapshot_url,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    event_data = {
        "id": str(event.id),
        "locker_id": str(locker_id),
        "event_type": event.event_type.value,
        "severity": event.severity.value,
        "threat_score": threat_score,
        "timestamp": event.timestamp.isoformat(),
        "description": event.description,
        "before_snapshot_url": event.before_snapshot_url,
        "resolved": event.resolved,
    }
    
    await ws_manager.broadcast_to_locker(locker_id, "security_event", event_data)

    return event


@router.get("/webhook-logs")
async def get_webhook_logs():
    """Return the last 20 raw webhook payloads received for troubleshooting."""
    return telegram_cache.get_payloads()
