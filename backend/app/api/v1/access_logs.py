"""VaultAlert — Access Logs API Router."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyAuthenticated, CurrentUser
from app.core.database import get_db
from app.models.models import AccessLog
from app.schemas.schemas import AccessLogResponse, PaginatedResponse

router = APIRouter(tags=["Access Logs"])


@router.get("/lockers/{locker_id}/access-logs", response_model=PaginatedResponse)
async def list_access_logs(
    locker_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Get paginated access history for a locker."""
    skip = (page - 1) * size

    total_result = await db.execute(
        select(func.count()).select_from(AccessLog).where(AccessLog.locker_id == locker_id)
    )
    total = total_result.scalar_one()

    logs_result = await db.execute(
        select(AccessLog)
        .where(AccessLog.locker_id == locker_id)
        .order_by(AccessLog.timestamp.desc())
        .offset(skip)
        .limit(size)
    )
    logs = list(logs_result.scalars().all())
    pages = max(1, -(-total // size))

    return PaginatedResponse(
        items=[AccessLogResponse.model_validate(lg) for lg in logs],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )
