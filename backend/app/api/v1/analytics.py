"""VaultAlert — Analytics & Dashboard API Router."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyAuthenticated, CurrentUser, get_current_user
from app.core.database import get_db
from app.schemas.schemas import (
    AccessTrendPoint,
    DashboardMetrics,
    ThreatTrendPoint,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _get_org(current: CurrentUser) -> UUID:
    from fastapi import HTTPException, status
    if not current.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization.")
    return current.org_id


@router.get("/dashboard", response_model=DashboardMetrics)
async def dashboard_metrics(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate dashboard KPIs for the current organization."""
    svc = AnalyticsService(db)
    return await svc.get_dashboard_metrics(_get_org(current))


@router.get("/access-trend", response_model=List[AccessTrendPoint])
async def access_trend(
    days: int = 30,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Daily access granted/denied trend for the last N days."""
    svc = AnalyticsService(db)
    return await svc.get_access_trend(_get_org(current), days=min(days, 90))


@router.get("/threat-trend", response_model=List[ThreatTrendPoint])
async def threat_trend(
    days: int = 30,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Daily threat event trend for the last N days."""
    svc = AnalyticsService(db)
    return await svc.get_threat_trend(_get_org(current), days=min(days, 90))
