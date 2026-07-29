"""VaultAlert — Authentication Service.

Handles registration, login, JWT lifecycle, OTP generation/verification,
and token blacklisting via Redis.
"""

import secrets
import string
from datetime import timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis_client import cache_delete, cache_get, cache_set
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.models import User, UserRole
from app.repositories.user_repo import UserRepository
from app.schemas.schemas import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
)


OTP_TTL_SECONDS = 300  # 5 minutes
REFRESH_BLACKLIST_PREFIX = "blacklist:refresh:"
OTP_PREFIX = "otp:"


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    # ── Registration ──────────────────────────────────────────────────────────
    async def register(self, data: SignupRequest) -> User:
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise ValueError("An account with this email already exists.")

        user = User(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            role=data.role,
            organization_id=data.organization_id,
        )
        created = await self.user_repo.create(user)
        logger.info(f"New user registered: {created.email} | role={created.role}")
        return created

    # ── Login ─────────────────────────────────────────────────────────────────
    async def login(self, data: LoginRequest) -> TokenResponse:
        user = await self.user_repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise ValueError("Invalid email or password.")
        if not user.is_active:
            raise ValueError("Account is deactivated. Contact your administrator.")

        await self.user_repo.update_last_login(user.id)

        access_token = create_access_token(subject=user.id, role=user.role.value)
        refresh_token = create_refresh_token(subject=user.id, role=user.role.value)

        # Store refresh token in Redis for validation (allows server-side revocation)
        await cache_set(
            key=f"refresh:{user.id}:{refresh_token[-16:]}",
            value=str(user.id),
            ttl=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )

        logger.info(f"User login: {user.email}")
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ── Token Refresh ─────────────────────────────────────────────────────────
    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise ValueError("Invalid or expired refresh token.")

        if payload.get("type") != "refresh":
            raise ValueError("Token is not a refresh token.")

        user_id = payload["sub"]
        role = payload["role"]

        # Validate against Redis store
        cache_key = f"refresh:{user_id}:{refresh_token[-16:]}"
        stored = await cache_get(cache_key)
        if not stored:
            raise ValueError("Refresh token has been revoked or expired.")

        # Rotate — invalidate old, issue new
        await cache_delete(cache_key)
        access_token = create_access_token(subject=user_id, role=role)
        new_refresh = create_refresh_token(subject=user_id, role=role)
        await cache_set(
            key=f"refresh:{user_id}:{new_refresh[-16:]}",
            value=user_id,
            ttl=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ── Logout ────────────────────────────────────────────────────────────────
    async def logout(self, user_id: UUID, refresh_token: str) -> None:
        cache_key = f"refresh:{user_id}:{refresh_token[-16:]}"
        await cache_delete(cache_key)
        logger.info(f"User {user_id} logged out.")

    # ── OTP Generation ────────────────────────────────────────────────────────
    async def generate_otp(self, email: str) -> str:
        """Generate a 6-digit OTP, store in Redis for 5 minutes, return it."""
        otp = "".join(secrets.choice(string.digits) for _ in range(6))
        await cache_set(key=f"{OTP_PREFIX}{email}", value=otp, ttl=OTP_TTL_SECONDS)
        logger.info(f"OTP generated for {email}")
        return otp

    async def verify_otp(self, email: str, otp_code: str) -> bool:
        stored = await cache_get(f"{OTP_PREFIX}{email}")
        if not stored or stored != otp_code:
            return False
        await cache_delete(f"{OTP_PREFIX}{email}")

        # Mark user as verified
        user = await self.user_repo.get_by_email(email)
        if user:
            user.is_verified = True
            await self.session.flush()
        return True
