"""VaultAlert — Security Events API Router."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyAuthenticated, CurrentUser, get_current_user
from app.core.database import get_db
from app.models.models import Event, AlertSeverity, EventType, Locker
from app.schemas.schemas import EventResponse, EventResolveRequest, MessageResponse, PaginatedResponse
from app.repositories.event_repo import EventRepository

router = APIRouter(tags=["Events & Surveillance"])


@router.get("/events", response_model=PaginatedResponse)
async def list_all_events(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    severity: Optional[AlertSeverity] = None,
    resolved: Optional[bool] = None,
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Get paginated security events for the current organization."""
    if not current.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not associated with an organization."
        )

    conditions = [Locker.organization_id == current.org_id]
    if severity is not None:
        conditions.append(Event.severity == severity)
    if resolved is not None:
        conditions.append(Event.resolved == resolved)

    where_clause = and_(*conditions)
    skip = (page - 1) * size

    total_result = await db.execute(
        select(func.count())
        .select_from(Event)
        .join(Locker)
        .where(where_clause)
    )
    total = total_result.scalar_one()

    events_result = await db.execute(
        select(Event)
        .join(Locker)
        .where(where_clause)
        .order_by(Event.timestamp.desc())
        .offset(skip)
        .limit(size)
    )
    events = list(events_result.scalars().all())
    pages = max(1, -(-total // size))

    return PaginatedResponse(
        items=[EventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )



@router.get("/lockers/{locker_id}/events", response_model=PaginatedResponse)
async def list_events(
    locker_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    severity: Optional[AlertSeverity] = None,
    resolved: Optional[bool] = None,
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Get paginated security events for a locker with optional filters."""
    conditions = [Event.locker_id == locker_id]
    if severity is not None:
        conditions.append(Event.severity == severity)
    if resolved is not None:
        conditions.append(Event.resolved == resolved)

    where_clause = and_(*conditions)
    skip = (page - 1) * size

    total_result = await db.execute(
        select(func.count()).select_from(Event).where(where_clause)
    )
    total = total_result.scalar_one()

    events_result = await db.execute(
        select(Event)
        .where(where_clause)
        .order_by(Event.timestamp.desc())
        .offset(skip)
        .limit(size)
    )
    events = list(events_result.scalars().all())
    pages = max(1, -(-total // size))

    return PaginatedResponse(
        items=[EventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post("/events/{event_id}/resolve", response_model=MessageResponse)
async def resolve_event(
    event_id: UUID,
    payload: EventResolveRequest,
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Mark a security event as resolved."""
    repo = EventRepository(db)
    event = await repo.mark_resolved(event_id, resolver_id=current.user_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    await db.commit()
    return MessageResponse(message="Event resolved successfully.")
