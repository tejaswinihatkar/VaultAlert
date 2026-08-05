"""
VaultAlert — Telegram Alert Polling Service.
Listens to the Telegram Group, extracts alert text/images,
caches them for the API, and optionally saves to DB.
"""

import asyncio
import httpx
from loguru import logger
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.models import Event, EventType, AlertSeverity, Locker
from app.services.s3_service import s3_service
from app.workers.ws_manager import manager as ws_manager
from app.workers import telegram_cache

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = "8722120064:AAF6Yshc950N6CksWbLAeMa537zXG8h5ty0"
TELEGRAM_CHAT_ID   = -1004493857137   # supergroup / channel ID


def _extract_message(update: dict) -> dict:
    """
    Return whichever message-like object is present in the update.
    Telegram sends different keys depending on the chat type.
    """
    return (
        update.get("message")
        or update.get("channel_post")
        or update.get("edited_message")
        or update.get("edited_channel_post")
        or {}
    )


async def start_telegram_listener():
    """Starts the Telegram polling daemon as a background task."""
    asyncio.create_task(run_telegram_poller())
    logger.info("Telegram background listener registered.")


async def run_telegram_poller():
    """Polls Telegram API for new posts containing alerts or photos."""
    offset = 0
    # Use a generous timeout — Telegram long-poll is 25 s, so client needs > 25 s
    client = httpx.AsyncClient(timeout=60.0)
    logger.info("Telegram background poller started.")

    while True:
        try:
            url = (
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
                f"/getUpdates?offset={offset}&timeout=25"
                f"&allowed_updates=[\"message\",\"channel_post\",\"edited_message\",\"edited_channel_post\"]"
            )
            response = await client.get(url)

            if response.status_code != 200:
                logger.warning(f"Telegram API {response.status_code}: {response.text[:200]}")
                await asyncio.sleep(5)
                continue

            updates = response.json().get("result", [])

            for update in updates:
                # Always advance offset so we don't re-process
                offset = update["update_id"] + 1

                msg = _extract_message(update)
                if not msg:
                    continue

                # ── Chat ID guard ─────────────────────────────────────────────
                chat_id = msg.get("chat", {}).get("id")
                if chat_id != TELEGRAM_CHAT_ID:
                    logger.debug(f"Skipping update from chat {chat_id} (expected {TELEGRAM_CHAT_ID})")
                    continue

                text   = msg.get("text", "") or msg.get("caption", "")
                photos = msg.get("photo", [])

                if not photos and not text:
                    continue

                logger.info(f"Telegram update — chat={chat_id} text='{text[:60]}' photos={len(photos)}")
                await process_telegram_msg(client, msg, text, photos)

        except asyncio.CancelledError:
            logger.info("Telegram poller cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in Telegram poller: {e}")
            await asyncio.sleep(5)


async def process_telegram_msg(
    client: httpx.AsyncClient,
    message: dict,
    text: str,
    photos: list,
):
    """
    1. Resolves photo URLs and writes to the in-memory cache immediately.
    2. Optionally saves to DB if a Locker exists.
    Cache write is ALWAYS first — DB failure must not block the dashboard.
    """
    photo_url_direct: str | None = None

    # ── 1. Resolve & cache photo ──────────────────────────────────────────────
    if photos:
        try:
            file_id   = photos[-1]["file_id"]
            file_resp = await client.get(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}",
                timeout=15.0,
            )
            file_path = file_resp.json().get("result", {}).get("file_path")
            if file_path:
                photo_url_direct = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

                # ✅ Cache FIRST — always, no DB dependency
                telegram_cache.add_photo({
                    "file_id": file_id,
                    "url":     photo_url_direct,
                    "caption": text or "Security Snapshot",
                    "date":    message.get("date", 0),
                })
                logger.info(f"Cached photo: {photo_url_direct}")
        except Exception as e:
            logger.error(f"Failed to resolve Telegram photo: {e}")

    # ── 2. Cache text event ───────────────────────────────────────────────────
    if text or photo_url_direct:
        telegram_cache.add_event({
            "id":        str(message.get("message_id", "")),
            "time":      message.get("date", 0),
            "message":   text or "Security snapshot captured.",
            "photo_url": photo_url_direct,
        })
        logger.info(f"Cached event: '{text[:60]}'")

    # ── 3. DB save (optional — skip gracefully if no locker) ─────────────────
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Locker).limit(1))
            locker = result.scalar_one_or_none()
            if not locker:
                logger.debug("No locker in DB — skipping DB save (cache already updated).")
                return

            # Download photo bytes for S3 (best-effort)
            snapshot_url = None
            if photo_url_direct:
                try:
                    img_res = await client.get(photo_url_direct, timeout=20.0)
                    if img_res.status_code == 200:
                        snapshot_url = await s3_service.upload_snapshot(
                            data=img_res.content,
                            locker_id=str(locker.id),
                            event_id=f"tg_{message.get('message_id', 'unknown')}",
                            suffix="captured",
                        )
                except Exception as e:
                    logger.error(f"S3 upload failed: {e}")

            severity   = AlertSeverity.critical if any(k in text.lower() for k in ("forced", "breach", "tamper", "unauthorized")) else AlertSeverity.warning
            event_type = EventType.door_forced  if "forced" in text.lower() else EventType.tampering

            event = Event(
                locker_id=locker.id,
                event_type=event_type,
                severity=severity,
                threat_score=0.95 if severity == AlertSeverity.critical else 0.70,
                description=text or "Telegram Bot Alert: Security event triggered.",
                before_snapshot_url=snapshot_url,
            )
            db.add(event)
            await db.commit()
            await db.refresh(event)

            await ws_manager.broadcast_to_locker(locker.id, "security_event", {
                "id":                  str(event.id),
                "locker_id":           str(locker.id),
                "event_type":          event.event_type.value,
                "severity":            event.severity.value,
                "threat_score":        event.threat_score,
                "timestamp":           event.timestamp.isoformat(),
                "description":         event.description,
                "before_snapshot_url": event.before_snapshot_url,
                "resolved":            event.resolved,
            })
            logger.info(f"Saved & broadcasted Telegram event ID: {event.id}")

    except Exception as e:
        logger.error(f"DB save failed for Telegram event (cache still updated): {e}")
