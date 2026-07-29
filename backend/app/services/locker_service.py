"""VaultAlert — Locker Service.

Business logic for locker management, remote commands, and telemetry processing.
"""

from typing import List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Locker, LockerSettings, LockerStatus
from app.repositories.locker_repo import LockerRepository
from app.repositories.event_repo import EventRepository, AccessLogRepository
from app.schemas.schemas import LockerCreate, LockerUpdate, LockerTelemetry


class LockerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LockerRepository(session)
        self.event_repo = EventRepository(session)
        self.access_repo = AccessLogRepository(session)

    async def create_locker(self, org_id: UUID, data: LockerCreate) -> Locker:
        locker = Locker(
            organization_id=org_id,
            name=data.name,
            locker_number=data.locker_number,
            location=data.location,
            gps_lat=data.gps_lat,
            gps_lng=data.gps_lng,
            owner_id=data.owner_id,
        )
        created = await self.repo.create(locker)

        # Create default settings for the locker
        default_settings = LockerSettings(locker_id=created.id)
        self.session.add(default_settings)
        await self.session.flush()

        logger.info(f"Locker created: {created.name} [{created.id}] for org={org_id}")
        return created

    async def get_lockers(self, org_id: UUID, skip: int = 0, limit: int = 100) -> List[Locker]:
        return await self.repo.get_by_organization(org_id, skip=skip, limit=limit)

    async def get_locker(self, locker_id: UUID, org_id: UUID) -> Optional[Locker]:
        locker = await self.repo.get_by_id(locker_id)
        if not locker or locker.organization_id != org_id:
            return None
        return locker

    async def update_locker(self, locker_id: UUID, org_id: UUID, data: LockerUpdate) -> Optional[Locker]:
        locker = await self.get_locker(locker_id, org_id)
        if not locker:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(locker, field, value)
        return await self.repo.update(locker)

    async def delete_locker(self, locker_id: UUID, org_id: UUID) -> bool:
        locker = await self.get_locker(locker_id, org_id)
        if not locker:
            return False
        await self.repo.delete(locker)
        logger.info(f"Locker deleted: {locker_id}")
        return True

    async def remote_unlock(self, locker_id: UUID, org_id: UUID, issued_by: UUID) -> bool:
        """Issue unlock command via MQTT and update status."""
        locker = await self.get_locker(locker_id, org_id)
        if not locker:
            return False
        await self.repo.set_status(locker_id, LockerStatus.unlocked)
        await self._publish_command(locker, "unlock", issued_by)
        logger.info(f"Remote UNLOCK issued for locker={locker_id} by user={issued_by}")
        return True

    async def remote_lock(self, locker_id: UUID, org_id: UUID, issued_by: UUID) -> bool:
        locker = await self.get_locker(locker_id, org_id)
        if not locker:
            return False
        await self.repo.set_status(locker_id, LockerStatus.locked)
        await self._publish_command(locker, "lock", issued_by)
        logger.info(f"Remote LOCK issued for locker={locker_id} by user={issued_by}")
        return True

    async def emergency_lockdown(self, locker_id: UUID, org_id: UUID, issued_by: UUID) -> bool:
        locker = await self.get_locker(locker_id, org_id)
        if not locker:
            return False
        await self.repo.set_status(locker_id, LockerStatus.lockdown)
        await self._publish_command(locker, "lockdown", issued_by)
        logger.warning(f"EMERGENCY LOCKDOWN issued for locker={locker_id} by user={issued_by}")
        return True

    async def process_telemetry(self, telemetry: LockerTelemetry) -> Optional[Locker]:
        """Called by MQTT worker when a device publishes telemetry."""
        if not telemetry.locker_id:
            return None
        locker_id = UUID(telemetry.locker_id)
        return await self.repo.update_telemetry(
            locker_id,
            battery=telemetry.battery,
            signal=telemetry.signal,
            temperature=telemetry.temperature,
            humidity=telemetry.humidity,
            door_state=telemetry.door_status,
            tamper=telemetry.tamper,
            motion=telemetry.motion,
            is_online=True,
        )

    async def _publish_command(self, locker: Locker, command: str, issued_by: UUID) -> None:
        """Publish MQTT command to device."""
        import json
        from datetime import datetime, timezone
        from app.core.redis_client import publish

        payload = json.dumps({
            "command": command,
            "locker_id": str(locker.id),
            "issued_by": str(issued_by),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        })
        # Publish on Redis channel — MQTT worker subscribes and forwards to device
        await publish(f"vaultalert:commands:{locker.id}", payload)
