"""VaultAlert — Locker Management API Router."""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyAuthenticated, AdminOrManager, CurrentUser, get_current_user
from app.core.database import get_db
from app.schemas.schemas import (
    LockerCreate,
    LockerResponse,
    LockerUpdate,
    MessageResponse,
    PaginatedResponse,
)
from app.services.locker_service import LockerService
from app.models.models import UserRole

router = APIRouter(prefix="/lockers", tags=["Locker Management"])


def _get_org_id(current: CurrentUser) -> UUID:
    if not current.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with an organization.",
        )
    return current.org_id


@router.get("", response_model=List[LockerResponse])
async def list_lockers(
    skip: int = 0,
    limit: int = 100,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all lockers for the current user's organization."""
    org_id = _get_org_id(current)
    svc = LockerService(db)
    return await svc.get_lockers(org_id, skip=skip, limit=limit)


@router.post("", response_model=LockerResponse, status_code=status.HTTP_201_CREATED)
async def create_locker(
    payload: LockerCreate,
    current: CurrentUser = AdminOrManager,
    db: AsyncSession = Depends(get_db),
):
    """Create a new locker. Requires Admin or Manager role."""
    org_id = _get_org_id(current)
    svc = LockerService(db)
    return await svc.create_locker(org_id, payload)


@router.get("/{locker_id}", response_model=LockerResponse)
async def get_locker(
    locker_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed status of a single locker."""
    org_id = _get_org_id(current)
    svc = LockerService(db)
    locker = await svc.get_locker(locker_id, org_id)
    if not locker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locker not found.")
    return locker


@router.put("/{locker_id}", response_model=LockerResponse)
async def update_locker(
    locker_id: UUID,
    payload: LockerUpdate,
    current: CurrentUser = AdminOrManager,
    db: AsyncSession = Depends(get_db),
):
    """Update locker configuration."""
    org_id = _get_org_id(current)
    svc = LockerService(db)
    locker = await svc.update_locker(locker_id, org_id, payload)
    if not locker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locker not found.")
    return locker


@router.delete("/{locker_id}", response_model=MessageResponse)
async def delete_locker(
    locker_id: UUID,
    current: CurrentUser = AdminOrManager,
    db: AsyncSession = Depends(get_db),
):
    """Remove a locker from the organization."""
    org_id = _get_org_id(current)
    svc = LockerService(db)
    deleted = await svc.delete_locker(locker_id, org_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locker not found.")
    return MessageResponse(message="Locker deleted successfully.")


@router.post("/{locker_id}/unlock", response_model=MessageResponse)
async def remote_unlock(
    locker_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Issue a remote unlock command to the locker device."""
    org_id = _get_org_id(current)
    svc = LockerService(db)
    success = await svc.remote_unlock(locker_id, org_id, current.user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locker not found.")
    return MessageResponse(message="Unlock command issued successfully.")


@router.post("/{locker_id}/lock", response_model=MessageResponse)
async def remote_lock(
    locker_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Issue a remote lock command."""
    org_id = _get_org_id(current)
    svc = LockerService(db)
    success = await svc.remote_lock(locker_id, org_id, current.user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locker not found.")
    return MessageResponse(message="Lock command issued successfully.")


@router.post("/{locker_id}/lockdown", response_model=MessageResponse)
async def emergency_lockdown(
    locker_id: UUID,
    current: CurrentUser = AdminOrManager,
    db: AsyncSession = Depends(get_db),
):
    """Trigger emergency lockdown — Admin/Manager only."""
    org_id = _get_org_id(current)
    svc = LockerService(db)
    success = await svc.emergency_lockdown(locker_id, org_id, current.user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locker not found.")
    return MessageResponse(message="Emergency lockdown initiated.")
