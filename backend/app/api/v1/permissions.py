"""VaultAlert — Locker Permissions (Access Control) API Router."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOrManager, AnyAuthenticated, CurrentUser
from app.core.database import get_db
from app.models.models import LockerPermission
from app.schemas.schemas import PermissionCreate, PermissionResponse, MessageResponse

router = APIRouter(tags=["Access Control"])


@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def grant_access(
    payload: PermissionCreate,
    current: CurrentUser = AdminOrManager,
    db: AsyncSession = Depends(get_db),
):
    """Grant locker access to a user. Requires Admin or Manager role."""
    # Check for existing permission
    existing = await db.execute(
        select(LockerPermission).where(
            (LockerPermission.locker_id == payload.locker_id)
            & (LockerPermission.user_id == payload.user_id)
        )
    )
    perm = existing.scalar_one_or_none()
    if perm:
        # Update existing permission instead of creating duplicate
        perm.can_unlock = payload.can_unlock
        perm.can_view_live = payload.can_view_live
        perm.can_view_logs = payload.can_view_logs
        perm.can_manage = payload.can_manage
        perm.valid_from = payload.valid_from
        perm.valid_until = payload.valid_until
        await db.commit()
        await db.refresh(perm)
        return perm

    permission = LockerPermission(
        locker_id=payload.locker_id,
        user_id=payload.user_id,
        can_unlock=payload.can_unlock,
        can_view_live=payload.can_view_live,
        can_view_logs=payload.can_view_logs,
        can_manage=payload.can_manage,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
    )
    db.add(permission)
    await db.commit()
    await db.refresh(permission)
    return permission


@router.get("/lockers/{locker_id}/permissions", response_model=List[PermissionResponse])
async def list_locker_permissions(
    locker_id: UUID,
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """List all users who have access to a specific locker."""
    result = await db.execute(
        select(LockerPermission)
        .where(LockerPermission.locker_id == locker_id)
        .order_by(LockerPermission.created_at.desc())
    )
    return list(result.scalars().all())


@router.delete("/permissions/{permission_id}", response_model=MessageResponse)
async def revoke_access(
    permission_id: UUID,
    current: CurrentUser = AdminOrManager,
    db: AsyncSession = Depends(get_db),
):
    """Revoke locker access from a user. Requires Admin or Manager role."""
    result = await db.execute(
        select(LockerPermission).where(LockerPermission.id == permission_id)
    )
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found.")

    await db.delete(perm)
    await db.commit()
    return MessageResponse(message="Access revoked successfully.")
