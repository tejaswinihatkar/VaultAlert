"""VaultAlert — Notifications API Router."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyAuthenticated, CurrentUser
from app.core.database import get_db
from app.models.models import Notification
from app.schemas.schemas import NotificationResponse, MessageResponse, PaginatedResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=PaginatedResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Fetch the current user's notification inbox with unread count."""
    skip = (page - 1) * size

    total_result = await db.execute(
        select(func.count()).select_from(Notification).where(Notification.user_id == current.user_id)
    )
    total = total_result.scalar_one()

    unread_result = await db.execute(
        select(func.count()).select_from(Notification).where(
            (Notification.user_id == current.user_id) & (Notification.is_read == False)
        )
    )
    unread_count = unread_result.scalar_one()

    notifs_result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current.user_id)
        .order_by(Notification.timestamp.desc())
        .offset(skip)
        .limit(size)
    )
    notifs = list(notifs_result.scalars().all())
    pages = max(1, -(-total // size))

    return PaginatedResponse(
        items=[NotificationResponse.model_validate(n) for n in notifs],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.put("/{notification_id}/read", response_model=MessageResponse)
async def mark_notification_read(
    notification_id: UUID,
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    await db.execute(
        update(Notification)
        .where(
            (Notification.id == notification_id)
            & (Notification.user_id == current.user_id)
        )
        .values(is_read=True)
    )
    await db.commit()
    return MessageResponse(message="Notification marked as read.")


@router.put("/read-all", response_model=MessageResponse)
async def mark_all_notifications_read(
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications for the current user as read."""
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current.user_id)
        .values(is_read=True)
    )
    await db.commit()
    return MessageResponse(message="All notifications marked as read.")
