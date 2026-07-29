"""VaultAlert — Locker Repository."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Locker, LockerStatus
from app.repositories.base import BaseRepository


class LockerRepository(BaseRepository[Locker]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Locker, session)

    async def get_by_organization(self, org_id: UUID, skip: int = 0, limit: int = 100) -> List[Locker]:
        result = await self.session.execute(
            select(Locker)
            .where(Locker.organization_id == org_id)
            .order_by(Locker.name)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_organization(self, org_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Locker).where(Locker.organization_id == org_id)
        )
        return result.scalar_one()

    async def get_online_count(self, org_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Locker).where(
                and_(Locker.organization_id == org_id, Locker.is_online == True)
            )
        )
        return result.scalar_one()

    async def update_telemetry(
        self,
        locker_id: UUID,
        *,
        battery: Optional[int] = None,
        signal: Optional[int] = None,
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        door_state: Optional[str] = None,
        tamper: Optional[bool] = None,
        motion: Optional[bool] = None,
        is_online: Optional[bool] = None,
    ) -> Optional[Locker]:
        from datetime import datetime, timezone
        locker = await self.get_by_id(locker_id)
        if not locker:
            return None
        if battery is not None:
            locker.battery_status = battery
        if signal is not None:
            locker.signal_strength = signal
        if temperature is not None:
            locker.temperature = temperature
        if humidity is not None:
            locker.humidity = humidity
        if door_state is not None:
            from app.models.models import DoorState
            locker.door_state = DoorState(door_state)
        if tamper is not None:
            locker.tamper_detected = tamper
        if motion is not None:
            locker.motion_detected = motion
        if is_online is not None:
            locker.is_online = is_online
        locker.last_seen = datetime.now(tz=timezone.utc)
        await self.session.flush()
        return locker

    async def set_status(self, locker_id: UUID, status: LockerStatus) -> Optional[Locker]:
        locker = await self.get_by_id(locker_id)
        if locker:
            locker.status = status
            await self.session.flush()
        return locker
