"""VaultAlert — Event & Access Log Repositories."""

from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AccessLog, Event, EventType, AlertSeverity, AccessStatus
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Event, session)

    async def get_by_locker(
        self, locker_id: UUID, skip: int = 0, limit: int = 50
    ) -> List[Event]:
        result = await self.session.execute(
            select(Event)
            .where(Event.locker_id == locker_id)
            .order_by(Event.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_unresolved(self, org_locker_ids: List[UUID]) -> List[Event]:
        result = await self.session.execute(
            select(Event)
            .where(
                and_(
                    Event.locker_id.in_(org_locker_ids),
                    Event.resolved == False,
                )
            )
            .order_by(Event.timestamp.desc())
        )
        return list(result.scalars().all())

    async def count_today_by_locker_ids(self, locker_ids: List[UUID]) -> int:
        today = date.today()
        result = await self.session.execute(
            select(func.count()).select_from(Event).where(
                and_(
                    Event.locker_id.in_(locker_ids),
                    cast(Event.timestamp, Date) == today,
                )
            )
        )
        return result.scalar_one()

    async def get_daily_trend(self, locker_ids: List[UUID], days: int = 30) -> list:
        """Return daily event counts for the last N days."""
        result = await self.session.execute(
            select(
                cast(Event.timestamp, Date).label("day"),
                func.count().label("count"),
            )
            .where(Event.locker_id.in_(locker_ids))
            .group_by(cast(Event.timestamp, Date))
            .order_by(cast(Event.timestamp, Date).desc())
            .limit(days)
        )
        return [{"date": str(r.day), "count": r.count} for r in result.all()]

    async def mark_resolved(self, event_id: UUID, resolver_id: UUID) -> Optional[Event]:
        event = await self.get_by_id(event_id)
        if event:
            event.resolved = True
            event.resolved_by = resolver_id
            event.resolved_at = datetime.now(tz=timezone.utc)
            await self.session.flush()
        return event

    async def get_avg_threat_score(self, locker_ids: List[UUID]) -> float:
        result = await self.session.execute(
            select(func.avg(Event.threat_score)).where(
                Event.locker_id.in_(locker_ids)
            )
        )
        val = result.scalar_one_or_none()
        return round(float(val or 0.0), 2)


class AccessLogRepository(BaseRepository[AccessLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AccessLog, session)

    async def get_by_locker(
        self, locker_id: UUID, skip: int = 0, limit: int = 50
    ) -> List[AccessLog]:
        result = await self.session.execute(
            select(AccessLog)
            .where(AccessLog.locker_id == locker_id)
            .order_by(AccessLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_today_granted(self, locker_ids: List[UUID]) -> int:
        today = date.today()
        result = await self.session.execute(
            select(func.count()).select_from(AccessLog).where(
                and_(
                    AccessLog.locker_id.in_(locker_ids),
                    AccessLog.status == AccessStatus.granted,
                    cast(AccessLog.timestamp, Date) == today,
                )
            )
        )
        return result.scalar_one()

    async def count_today_denied(self, locker_ids: List[UUID]) -> int:
        today = date.today()
        result = await self.session.execute(
            select(func.count()).select_from(AccessLog).where(
                and_(
                    AccessLog.locker_id.in_(locker_ids),
                    AccessLog.status == AccessStatus.denied,
                    cast(AccessLog.timestamp, Date) == today,
                )
            )
        )
        return result.scalar_one()

    async def get_daily_access_trend(self, locker_ids: List[UUID], days: int = 30) -> list:
        result = await self.session.execute(
            select(
                cast(AccessLog.timestamp, Date).label("day"),
                AccessLog.status,
                func.count().label("count"),
            )
            .where(AccessLog.locker_id.in_(locker_ids))
            .group_by(cast(AccessLog.timestamp, Date), AccessLog.status)
            .order_by(cast(AccessLog.timestamp, Date).desc())
            .limit(days * 2)
        )
        rows = result.all()
        trend: dict = {}
        for r in rows:
            key = str(r.day)
            if key not in trend:
                trend[key] = {"date": key, "granted": 0, "denied": 0}
            trend[key][r.status.value.lower()] = r.count
        return list(trend.values())
