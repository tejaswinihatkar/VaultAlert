"""
VaultAlert — Footage & Telegram Events Router
Reads from the in-memory telegram_cache populated by the background telegram_worker.
This avoids the getUpdates conflict where the worker consumes updates before the API can read them.
"""

from typing import List, Dict, Any
from fastapi import APIRouter
from app.workers import telegram_cache

router = APIRouter(tags=["Footage & Telegram"])


# ── GET /api/v1/footage ───────────────────────────────────────────────────────
@router.get("/footage", response_model=List[Dict[str, Any]])
async def get_footage():
    """
    Returns all cached photos from the Telegram security group, newest first.
    Photos are captured by the background telegram_worker and stored in memory.
    Used by the dashboard's Live Footage / Camera Feed section.
    """
    return telegram_cache.get_photos()


# ── GET /api/v1/telegram-events ───────────────────────────────────────────────
@router.get("/telegram-events", response_model=List[Dict[str, Any]])
async def get_telegram_events():
    """
    Returns all cached text alerts from the Telegram security group, newest first.
    Events are captured by the background telegram_worker and stored in memory.
    Used by the dashboard's Security Events / Activity Feed section.
    """
    return telegram_cache.get_events()
