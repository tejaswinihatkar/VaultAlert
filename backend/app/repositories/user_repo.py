"""VaultAlert — User Repository."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_organization(self, org_id: UUID, skip: int = 0, limit: int = 100):
        result = await self.session.execute(
            select(User)
            .where(User.organization_id == org_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_fcm_token(self, user_id: UUID, token: str) -> None:
        user = await self.get_by_id(user_id)
        if user:
            user.fcm_token = token
            await self.session.flush()

    async def update_last_login(self, user_id: UUID) -> None:
        from datetime import datetime, timezone
        user = await self.get_by_id(user_id)
        if user:
            user.last_login = datetime.now(tz=timezone.utc)
            await self.session.flush()
