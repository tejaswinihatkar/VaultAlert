"""VaultAlert — User Management API Router."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOrManager, AnyAuthenticated, CurrentUser, get_current_user
from app.core.database import get_db
from app.models.models import User, UserRole
from app.schemas.schemas import UserResponse, UserUpdate, PaginatedResponse

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """List all users in the current organization."""
    if not current.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with an organization.",
        )
    result = await db.execute(
        select(User)
        .where(User.organization_id == current.org_id)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Update user profile. Users can edit their own profile; Admin/Manager can edit others."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Permission check: self-edit or admin/manager
    if user_id != current.user_id and current.role not in (UserRole.admin, UserRole.manager):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own profile.",
        )

    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url
    if payload.fcm_token is not None:
        user.fcm_token = payload.fcm_token

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=dict)
async def deactivate_user(
    user_id: UUID,
    current: CurrentUser = AdminOrManager,
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a user account. Requires Admin or Manager role."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if user_id == current.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    user.is_active = False
    await db.commit()
    return {"message": "User deactivated successfully.", "success": True}
