"""VaultAlert — Device Registration & Firmware API Router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOrManager, AnyAuthenticated, CurrentUser
from app.core.database import get_db
from app.models.models import Device
from app.schemas.schemas import DeviceCreate, DeviceResponse, MessageResponse

router = APIRouter(prefix="/devices", tags=["Device Management"])


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    payload: DeviceCreate,
    current: CurrentUser = AdminOrManager,
    db: AsyncSession = Depends(get_db),
):
    """Register an ESP32 device to a locker. Requires Admin or Manager role."""
    # Check for duplicate serial
    existing = await db.execute(
        select(Device).where(Device.serial_number == payload.serial_number)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device with serial '{payload.serial_number}' already registered.",
        )

    device = Device(
        locker_id=payload.locker_id,
        serial_number=payload.serial_number,
        firmware_version=payload.firmware_version,
        device_type=payload.device_type,
        mqtt_client_id=payload.mqtt_client_id,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: UUID,
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Get device details and last heartbeat ping."""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    return device


@router.post("/{device_id}/firmware-update", response_model=MessageResponse)
async def trigger_firmware_update(
    device_id: UUID,
    current: CurrentUser = AdminOrManager,
    db: AsyncSession = Depends(get_db),
):
    """Trigger an OTA firmware update for a device via MQTT command."""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    # Publish OTA command via Redis → MQTT
    try:
        from app.core.redis_client import get_redis
        import json
        redis = await get_redis()
        channel = f"vaultalert:commands:{device.serial_number}"
        cmd = json.dumps({"action": "ota_update", "device_id": str(device_id)})
        await redis.publish(channel, cmd)
    except Exception:
        pass  # Non-fatal: OTA will retry via heartbeat

    return MessageResponse(message=f"OTA update command dispatched to device {device.serial_number}.")
