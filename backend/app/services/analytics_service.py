"""VaultAlert — Analytics Service.

Computes dashboard metrics, trend data, and threat intelligence.
"""

from typing import List
from uuid import UUID

from sqlalchemy import select, func, and_, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Locker, Event, AccessLog, AlertSeverity
from app.repositories.locker_repo import LockerRepository
from app.repositories.event_repo import EventRepository, AccessLogRepository
from app.schemas.schemas import DashboardMetrics, AccessTrendPoint, ThreatTrendPoint


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.locker_repo = LockerRepository(session)
        self.event_repo = EventRepository(session)
        self.access_repo = AccessLogRepository(session)

    async def get_dashboard_metrics(self, org_id: UUID) -> DashboardMetrics:
        lockers = await self.locker_repo.get_by_organization(org_id, limit=1000)
        locker_ids = [l.id for l in lockers]

        total = len(lockers)
        online = sum(1 for l in lockers if l.is_online)
        cameras_online = sum(1 for l in lockers if l.camera_online)
        avg_battery = (
            round(sum(l.battery_status for l in lockers) / total, 1) if total else 0.0
        )

        today_granted = await self.access_repo.count_today_granted(locker_ids) if locker_ids else 0
        today_denied = await self.access_repo.count_today_denied(locker_ids) if locker_ids else 0
        active_alerts = len(await self.event_repo.get_unresolved(locker_ids)) if locker_ids else 0
        avg_threat = await self.event_repo.get_avg_threat_score(locker_ids) if locker_ids else 0.0
        network_health = round((online / total * 100) if total else 0.0, 1)

        return DashboardMetrics(
            total_lockers=total,
            online_lockers=online,
            offline_lockers=total - online,
            today_access_count=today_granted,
            unauthorized_attempts_today=today_denied,
            active_alerts=active_alerts,
            avg_battery=avg_battery,
            threat_score_avg=avg_threat,
            camera_online_count=cameras_online,
            network_health_percent=network_health,
        )

    async def get_access_trend(self, org_id: UUID, days: int = 30) -> List[AccessTrendPoint]:
        lockers = await self.locker_repo.get_by_organization(org_id, limit=1000)
        locker_ids = [l.id for l in lockers]
        raw = await self.access_repo.get_daily_access_trend(locker_ids, days=days)
        return [AccessTrendPoint(**r) for r in raw]

    async def get_threat_trend(self, org_id: UUID, days: int = 30) -> List[ThreatTrendPoint]:
        lockers = await self.locker_repo.get_by_organization(org_id, limit=1000)
        locker_ids = [l.id for l in lockers]
        raw = await self.event_repo.get_daily_trend(locker_ids, days=days)
        return [ThreatTrendPoint(date=r["date"], score=0.0, events=r["count"]) for r in raw]
