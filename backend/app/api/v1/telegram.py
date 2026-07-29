"""VaultAlert — Telegram Bot Integration Router."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.services.s3_service import s3_service
from app.workers.ws_manager import manager as ws_manager
from app.models.models import Event, EventType, AlertSeverity
from app.schemas.schemas import EventResponse

router = APIRouter(prefix="/integrations/telegram", tags=["Telegram Integration"])


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
    # 1. Authenticate Token against SECRET_KEY or custom token
    if x_telegram_bot_token != settings.SECRET_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid integration token.")

    # 2. Upload photo if present
    snapshot_url = None
    if photo:
        photo_bytes = await photo.read()
        snapshot_url = await s3_service.upload_snapshot(
            data=photo_bytes,
            locker_id=str(locker_id),
            event_id=f"tg_{locker_id.hex[:10]}",
            suffix="captured"
        )

    # 3. Save Event to DB
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

    # 4. Broadcast live via WebSockets
    event_data = {
        "id": str(event.id),
        "locker_id": str(locker_id),
        "event_type": event.event_type.value,
        "severity": event.severity.value,
        "threat_score": event.threat_score,
        "timestamp": event.timestamp.isoformat(),
        "description": event.description,
        "before_snapshot_url": event.before_snapshot_url,
        "resolved": event.resolved,
    }
    
    await ws_manager.broadcast_to_locker(locker_id, "security_event", event_data)

    return event
