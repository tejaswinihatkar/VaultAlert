"""VaultAlert — Biometric Fingerprint Template API Router."""

import hashlib
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyAuthenticated, AdminOrManager, CurrentUser
from app.core.database import get_db
from app.core.security import encrypt_biometric, decrypt_biometric
from app.models.models import Fingerprint
from app.schemas.schemas import MessageResponse
from pydantic import BaseModel


class FingerprintCreate(BaseModel):
    user_id: UUID
    template_b64: str        # Raw fingerprint template in base64
    sensor_index: int
    label: str | None = None


class FingerprintResponse(BaseModel):
    id: UUID
    user_id: UUID
    sensor_index: int
    label: str | None
    template_hash: str

    model_config = {"from_attributes": True}


router = APIRouter(prefix="/fingerprints", tags=["Biometric Enrollment"])


@router.post("", response_model=FingerprintResponse, status_code=status.HTTP_201_CREATED)
async def enroll_fingerprint(
    payload: FingerprintCreate,
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Store an AES-256-GCM encrypted fingerprint template for a user."""
    # Compute SHA-256 hash of raw template for fast lookups
    raw_bytes = payload.template_b64.encode()
    template_hash = hashlib.sha256(raw_bytes).hexdigest()

    # Check for duplicate sensor slot
    existing = await db.execute(
        select(Fingerprint).where(
            (Fingerprint.user_id == payload.user_id)
            & (Fingerprint.sensor_index == payload.sensor_index)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Sensor slot {payload.sensor_index} already occupied for this user.",
        )

    # Encrypt the template
    encrypted = encrypt_biometric(payload.template_b64)

    fp = Fingerprint(
        user_id=payload.user_id,
        encrypted_template=encrypted,
        template_hash=template_hash,
        sensor_index=payload.sensor_index,
        label=payload.label,
    )
    db.add(fp)
    await db.commit()
    await db.refresh(fp)
    return fp


@router.get("/user/{user_id}", response_model=List[FingerprintResponse])
async def list_fingerprints(
    user_id: UUID,
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """List all enrolled fingerprints for a user (no template data returned)."""
    result = await db.execute(
        select(Fingerprint).where(Fingerprint.user_id == user_id)
    )
    return list(result.scalars().all())


@router.delete("/{fingerprint_id}", response_model=MessageResponse)
async def delete_fingerprint(
    fingerprint_id: UUID,
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Remove an enrolled fingerprint slot."""
    result = await db.execute(select(Fingerprint).where(Fingerprint.id == fingerprint_id))
    fp = result.scalar_one_or_none()
    if not fp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fingerprint not found.")

    # Users can only delete their own fingerprints; admins can delete any
    from app.models.models import UserRole
    if fp.user_id != current.user_id and current.role not in (UserRole.admin, UserRole.manager):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    await db.delete(fp)
    await db.commit()
    return MessageResponse(message="Fingerprint removed successfully.")
