"""VaultAlert — Authentication API Router."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyAuthenticated, CurrentUser, get_current_user
from app.core.database import get_db
from app.schemas.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    OTPVerifyRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.services.notification_service import NotificationService
from app.repositories.user_repo import UserRepository

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account. Sends an OTP verification email."""
    svc = AuthService(db)
    try:
        user = await svc.register(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    # Fire OTP in background
    async def _send_otp():
        otp = await svc.generate_otp(user.email)
        notif = NotificationService()
        await notif.send_email(
            to_email=user.email,
            subject="Verify your VaultAlert account",
            body_html=f"<p>Your verification code is: <strong style='font-size:24px'>{otp}</strong></p><p>Expires in 5 minutes.</p>",
        )

    background_tasks.add_task(_send_otp)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate and receive JWT access + refresh tokens."""
    svc = AuthService(db)
    try:
        return await svc.login(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rotate refresh token and issue new access token."""
    svc = AuthService(db)
    try:
        return await svc.refresh_tokens(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post("/logout", response_model=MessageResponse)
async def logout(
    payload: RefreshRequest,
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Revoke refresh token server-side."""
    svc = AuthService(db)
    await svc.logout(current.user_id, payload.refresh_token)
    return MessageResponse(message="Successfully logged out.")


@router.post("/verify-otp", response_model=MessageResponse)
async def verify_otp(
    payload: OTPVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify OTP code sent to email."""
    svc = AuthService(db)
    success = await svc.verify_otp(payload.email, payload.otp_code)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP.")
    return MessageResponse(message="Account verified successfully.")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Generate and email a password reset OTP."""
    svc = AuthService(db)
    repo = UserRepository(db)
    user = await repo.get_by_email(payload.email)
    # Always respond with success to prevent email enumeration
    if user:
        async def _send():
            otp = await svc.generate_otp(payload.email)
            notif = NotificationService()
            await notif.send_email(
                to_email=payload.email,
                subject="Reset your VaultAlert password",
                body_html=f"<p>Your password reset code is: <strong style='font-size:24px'>{otp}</strong></p><p>Expires in 5 minutes.</p>",
            )
        background_tasks.add_task(_send)

    return MessageResponse(message="If this email is registered, you will receive a reset code shortly.")


@router.get("/me", response_model=UserResponse)
async def get_me(
    current: CurrentUser = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Returns the currently authenticated user's profile."""
    repo = UserRepository(db)
    user = await repo.get_by_id(current.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user
