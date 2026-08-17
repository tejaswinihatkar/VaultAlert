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


@router.post("/bot{bot_token}/{method}")
async def telegram_api_proxy(
    bot_token: str,
    method: str,
    request: Request
):
    """
    Drop-in HTTP Proxy for Telegram Bot API.
    Intercepts hardware camera uploads, displays them on website instantly (< 100ms),
    and forwards the request to Telegram Group Chat.
    """
    import base64
    content_type = request.headers.get("content-type", "")

    text = ""
    photo_bytes = None
    photo_name = "snapshot.jpg"
    photo_mime = "image/jpeg"
    form_fields: dict = {}   # non-photo form fields, captured once for re-forwarding

    # 1. Parse payload for dashboard caching.
    # NOTE: request.form()/body() can only be consumed ONCE — read it here and
    # reuse the captured values when forwarding to Telegram below.
    try:
        if "multipart/form-data" in content_type:
            form = await request.form()
            for k, v in form.items():
                if k == "photo" and hasattr(v, "read"):
                    photo_bytes = await v.read()
                    photo_name = getattr(v, "filename", "snapshot.jpg")
                    photo_mime = getattr(v, "content_type", "image/jpeg")
                else:
                    form_fields[k] = v
            text = form_fields.get("caption", "") or form_fields.get("text", "")
        elif "application/json" in content_type:
            form_fields = await request.json()
            text = form_fields.get("caption", "") or form_fields.get("text", "")
    except Exception as parse_err:
        logger.warning(f"Proxy parsing warning: {parse_err}")

    # 2. Push to local cache & WebSocket instantly
    if photo_bytes or text:
        file_id = f"proxy_{int(time.time())}"
        data_url = None
        
        if photo_bytes:
            b64 = base64.b64encode(photo_bytes).decode("utf-8")
            data_url = f"data:{photo_mime};base64,{b64}"
            
            telegram_cache.add_photo({
                "file_id": file_id,
                "url": data_url,
                "caption": text or "Hardware Alert Snapshot",
                "date": int(time.time()),
            })
            
            await ws_manager.broadcast_global("camera_snapshot", {
                "file_id": file_id,
                "url": data_url,
                "caption": text or "Hardware Alert Snapshot",
                "timestamp": int(time.time() * 1000),
            })

        evt_id = f"evt_{int(time.time())}"
        telegram_cache.add_event({
            "id": evt_id,
            "time": int(time.time()),
            "message": text or "Security snapshot captured.",
            "photo_url": data_url,
        })
        
        await ws_manager.broadcast_global("security_event", {
            "id": evt_id,
            "originalMessage": text or "Security snapshot captured.",
            "timestamp": int(time.time() * 1000),
            "photo_url": data_url,
        })
        logger.info("Interceded hardware Telegram request: pushed to live dashboard.")

    # 3. Forward payload to Telegram Bot API — reuse the ALREADY-parsed values
    #    (the request stream is consumed; do not re-read request.form()/json()).
    from fastapi import Response
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"https://api.telegram.org/bot{bot_token}/{method}"
        try:
            if "multipart/form-data" in content_type:
                files_dict = {}
                if photo_bytes:
                    files_dict["photo"] = (photo_name, photo_bytes, photo_mime)
                r = await client.post(url, data=form_fields, files=files_dict)
            elif "application/json" in content_type:
                r = await client.post(url, json=form_fields)
            else:
                r = await client.post(url, content=await request.body())

            # Return Telegram's exact response back to the hardware
            return Response(
                content=r.content,
                status_code=r.status_code,
                headers={"Content-Type": r.headers.get("Content-Type", "application/json")}
            )
        except Exception as forward_err:
            logger.error(f"Failed to forward request to Telegram: {forward_err}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to forward to Telegram API")


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
    if x_telegram_bot_token not in (settings.SECRET_KEY, TELEGRAM_BOT_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid integration token.")

    snapshot_url = None
    photo_bytes = None
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

    # ── Forward to Telegram Group Chat in Real-Time ──
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if photo_bytes:
                await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                    data={"chat_id": TELEGRAM_CHAT_ID, "caption": description},
                    files={"photo": (photo.filename or "snapshot.jpg", photo_bytes, photo.content_type or "image/jpeg")}
                )
                logger.info(f"Forwarded photo alert to Telegram chat {TELEGRAM_CHAT_ID}")
            else:
                await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id": TELEGRAM_CHAT_ID, "text": description}
                )
                logger.info(f"Forwarded text alert to Telegram chat {TELEGRAM_CHAT_ID}")
    except Exception as tg_err:
        logger.error(f"Failed to forward alert to Telegram: {tg_err}")

    return event


@router.get("/webhook-logs")
async def get_webhook_logs():
    """Return the last 20 raw webhook payloads received for troubleshooting."""
    return telegram_cache.get_payloads()
