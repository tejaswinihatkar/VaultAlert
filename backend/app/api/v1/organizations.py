"""VaultAlert — Organization Management API Router."""

import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOnly, AnyAuthenticated, CurrentUser
from app.core.database import get_db
from app.models.models import Organization
from app.schemas.schemas import OrganizationCreate, OrganizationResponse, MessageResponse

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    current: CurrentUser = AdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Create a new organization. Requires Admin role."""
    existing = await db.execute(
        select(Organization).where(
            (Organization.name == payload.name) | (Organization.slug == payload.slug)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization name or slug already exists.",
        )

    org = Organization(
        name=payload.name,
        slug=payload.slug,
        subscription_tier=payload.subscription_tier,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Get organization details."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")
    return org


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: UUID,
    payload: OrganizationCreate,
    current: CurrentUser = AdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Update organization settings. Requires Admin role."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    org.name = payload.name
    org.slug = payload.slug
    org.subscription_tier = payload.subscription_tier
    await db.commit()
    await db.refresh(org)
    return org
