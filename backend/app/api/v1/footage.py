"""
VaultAlert — Footage & Telegram Events Router
Fetches live photos and alert messages from the Telegram group
and serves them to the frontend dashboard.
"""

import os
import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter
import httpx

logger = logging.getLogger("footage")

router = APIRouter(tags=["Footage & Telegram"])

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8722120064:AAF6Yshc950N6CksWbLAeMa537zXG8h5ty0")
TELEGRAM_CHAT_ID   = int(os.getenv("TELEGRAM_CHAT_ID", "-1004493857137"))


async def _get_updates(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch all available updates from the Telegram Bot API."""
    try:
        resp = await client.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
            timeout=10.0,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("result", []) if data.get("ok") else []
    except Exception as e:
        logger.error(f"Telegram getUpdates error: {e}")
        return []


def _msg_from_update(update: dict) -> Optional[dict]:
    """Extract message dict from any update type."""
    return (
        update.get("message")
        or update.get("channel_post")
        or update.get("edited_message")
    )


async def _photo_url(client: httpx.AsyncClient, file_id: str) -> Optional[str]:
    """Resolve a Telegram file_id to a direct download URL."""
    try:
        r = await client.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}",
            timeout=10.0,
        )
        if r.status_code != 200:
            return None
        fp = r.json().get("result", {}).get("file_path")
        return f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{fp}" if fp else None
    except Exception:
        return None


# ── GET /api/v1/footage ───────────────────────────────────────────────────────
@router.get("/footage", response_model=List[Dict[str, Any]])
async def get_footage():
    """
    Returns all photos posted in the Telegram security group, newest first.
    Used by the dashboard's Live Footage / Camera Feed section.
    """
    async with httpx.AsyncClient() as client:
        updates = await _get_updates(client)
        footage: List[Dict[str, Any]] = []

        for update in updates:
            msg = _msg_from_update(update)
            if not msg:
                continue
            if msg.get("chat", {}).get("id") != TELEGRAM_CHAT_ID:
                continue

            photos = msg.get("photo", [])
            if not photos:
                continue

            url = await _photo_url(client, photos[-1]["file_id"])
            if not url:
                continue

            footage.append({
                "file_id":  photos[-1]["file_id"],
                "url":      url,
                "caption":  msg.get("caption") or msg.get("text") or "Security Snapshot",
                "date":     msg.get("date", 0),
            })

        return sorted(footage, key=lambda x: x["date"], reverse=True)


# ── GET /api/v1/telegram-events ───────────────────────────────────────────────
@router.get("/telegram-events", response_model=List[Dict[str, Any]])
async def get_telegram_events():
    """
    Returns all text messages / alerts from the Telegram security group.
    Used by the dashboard's Security Events / Activity Feed section.
    """
    async with httpx.AsyncClient() as client:
        updates = await _get_updates(client)
        events: List[Dict[str, Any]] = []

        for update in updates:
            msg = _msg_from_update(update)
            if not msg:
                continue
            if msg.get("chat", {}).get("id") != TELEGRAM_CHAT_ID:
                continue

            text = msg.get("text") or msg.get("caption") or ""
            if not text:
                continue

            # Resolve photo if present
            photo_url: Optional[str] = None
            photos = msg.get("photo", [])
            if photos:
                photo_url = await _photo_url(client, photos[-1]["file_id"])

            events.append({
                "id":        str(update.get("update_id", msg.get("message_id"))),
                "time":      msg.get("date", 0),
                "message":   text,
                "photo_url": photo_url,
            })

        return sorted(events, key=lambda x: x["time"], reverse=True)
