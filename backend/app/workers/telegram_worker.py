"""
VaultAlert — Telegram Alert Polling Service.
Listens to the Telegram Group, extracts alert text/images, and pushes them live to the database and frontend.
"""

import asyncio
import httpx
from loguru import logger
from sqlalchemy import select
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Event, EventType, AlertSeverity, Locker
from app.services.s3_service import s3_service
from app.workers.ws_manager import manager as ws_manager

# Configure these inside your environment settings
TELEGRAM_BOT_TOKEN = "8722120064:AAF6Yshc950N6CksWbLAeMa537zXG8h5ty0"
TELEGRAM_CHAT_ID = -1004493857137

async def start_telegram_listener():
    """Starts the Telegram polling daemon thread."""
    asyncio.create_task(run_telegram_poller())
    logger.info("Telegram background listener registered.")

async def run_telegram_poller():
    """Polls Telegram API for new posts containing alerts or photos."""
    offset = 0
    client = httpx.AsyncClient(timeout=30.0)
    logger.info("Telegram background poller started.")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=20"
            response = await client.get(url)
            if response.status_code != 200:
                await asyncio.sleep(5)
                continue
                
            updates = response.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                
                # Check message content
                message = update.get("message", {})
                chat = message.get("chat", {})
                
                # Verify message is from the configured supergroup
                if chat.get("id") != TELEGRAM_CHAT_ID:
                    continue
                
                text = message.get("text", "")
                caption = message.get("caption", "")
                photos = message.get("photo", [])
                
                full_text = text or caption
                
                # Check if it has any alert details or photos
                if photos or "alert" in full_text.lower() or "breach" in full_text.lower() or "tamper" in full_text.lower():
                    await process_telegram_msg(client, message, full_text, photos)
                    
        except Exception as e:
            logger.error(f"Error in Telegram poller: {e}")
            await asyncio.sleep(5)

async def process_telegram_msg(client: httpx.AsyncClient, message: dict, text: str, photos: list):
    """Parses message text and uploads images to DB and WebSocket streams."""
    async with AsyncSessionLocal() as db:
        # Get first locker registered to bind the event to
        result = await db.execute(select(Locker).limit(1))
        locker = result.scalar_one_or_none()
        if not locker:
            logger.warning("No locker registered in system to associate Telegram alert.")
            return

        # 1. Download photo if attached
        snapshot_url = None
        if photos:
            try:
                # Grab the largest resolution photo
                file_id = photos[-1]["file_id"]
                file_info = await client.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}")
                file_path = file_info.json()["result"]["file_path"]
                photo_endpoint = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                
                # Download bytes
                img_res = await client.get(photo_endpoint)
                if img_res.status_code == 200:
                    snapshot_url = await s3_service.upload_snapshot(
                        data=img_res.content,
                        locker_id=str(locker.id),
                        event_id=f"tg_{message['message_id']}",
                        suffix="captured"
                    )
            except Exception as e:
                logger.error(f"Failed to download Telegram photo: {e}")

        # 2. Derive event details
        severity = AlertSeverity.critical if ("forced" in text.lower() or "breach" in text.lower()) else AlertSeverity.warning
        event_type = EventType.door_forced if "forced" in text.lower() else EventType.tampering

        description = text if text else f"Telegram Bot Alert: Security event triggered."

        # 3. Save to database
        event = Event(
            locker_id=locker.id,
            event_type=event_type,
            severity=severity,
            threat_score=0.95 if severity == AlertSeverity.critical else 0.70,
            description=description,
            before_snapshot_url=snapshot_url,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        # 4. Push WebSocket broadcast
        event_data = {
            "id": str(event.id),
            "locker_id": str(locker.id),
            "event_type": event.event_type.value,
            "severity": event.severity.value,
            "threat_score": event.threat_score,
            "timestamp": event.timestamp.isoformat(),
            "description": event.description,
            "before_snapshot_url": event.before_snapshot_url,
            "resolved": event.resolved,
        }
        await ws_manager.broadcast_to_locker(locker.id, "security_event", event_data)
        logger.info(f"Broadcasted Telegram incident ID: {event.id} to dashboard.")
