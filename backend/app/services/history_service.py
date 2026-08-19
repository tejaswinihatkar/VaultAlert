"""
VaultAlert — Alert History Persistence (additive, best-effort).

Writes each incoming hardware alert/snapshot into the persistent `events` table so
the dashboard can show timestamped historical data that survives restarts. This is
LAYERED ON TOP of the existing in-memory telegram_cache — it never blocks or replaces
the live pipeline: every DB call is wrapped so a DB failure only logs and returns.

All hardware alerts attach to a single auto-provisioned "Main Vault 01" locker (under
a default organization), so the events.locker_id foreign key stays intact.
"""

import uuid
from typing import Optional

from loguru import logger
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import Event, EventType, AlertSeverity, Locker, Organization

# Stable IDs so the default org/locker are created once and reused.
_DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
_DEFAULT_LOCKER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000b1")

# Cached after first ensure() so we don't hit the DB every alert.
_locker_ready = False


def classify(message: str) -> tuple[EventType, AlertSeverity]:
    """Map a raw hardware message to a DB EventType + severity (mirrors the frontend)."""
    m = (message or "").strip().lower()
    if "unauthorized fingerprint" in m or "unknown" in m:
        return EventType.unknown_face, AlertSeverity.critical
    if "wrong password" in m or "wrong pin" in m or "access denied" in m:
        return EventType.access_denied, AlertSeverity.warning
    if "system locked" in m or "lockdown" in m:
        return EventType.emergency_lockdown, AlertSeverity.critical
    if "fingerprint" in m and "fail" in m:
        return EventType.fingerprint_failed, AlertSeverity.warning
    if "access granted" in m or "locker opened" in m or "authorized" in m:
        return EventType.access_granted, AlertSeverity.info
    if "tamper" in m or "forced" in m or "breach" in m:
        return EventType.tampering, AlertSeverity.critical
    if "photo" in m or "snapshot" in m or "face" in m:
        return EventType.motion_detected, AlertSeverity.info
    return EventType.motion_detected, AlertSeverity.info


async def _ensure_default_locker(db) -> Optional[uuid.UUID]:
    """Create the default org + locker once (idempotent). Returns locker id or None."""
    global _locker_ready
    existing = await db.get(Locker, _DEFAULT_LOCKER_ID)
    if existing:
        _locker_ready = True
        return _DEFAULT_LOCKER_ID

    if not await db.get(Organization, _DEFAULT_ORG_ID):
        db.add(Organization(
            id=_DEFAULT_ORG_ID, name="VaultAlert", slug="vaultalert",
        ))
        await db.flush()

    db.add(Locker(
        id=_DEFAULT_LOCKER_ID,
        organization_id=_DEFAULT_ORG_ID,
        name="Main Vault 01",
        locker_number="01",
        location="Primary Site",
    ))
    await db.flush()
    _locker_ready = True
    return _DEFAULT_LOCKER_ID


async def persist_alert(message: str, snapshot_url: Optional[str] = None) -> None:
    """Best-effort: write one alert to the events table. Never raises."""
    try:
        async with AsyncSessionLocal() as db:
            locker_id = await _ensure_default_locker(db)
            if not locker_id:
                return
            event_type, severity = classify(message)
            db.add(Event(
                locker_id=locker_id,
                event_type=event_type,
                severity=severity,
                description=message,
                before_snapshot_url=snapshot_url,
            ))
            await db.commit()
    except Exception as e:
        # DB is a bonus layer — a failure must not affect the live cache/WS path.
        logger.warning(f"history persist skipped (DB unavailable?): {e}")
