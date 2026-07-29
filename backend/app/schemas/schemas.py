"""
VaultAlert — Pydantic Schemas
Request/response validation models for all API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.models import (
    AccessStatus,
    AlertSeverity,
    AuthMethod,
    DoorState,
    EventType,
    LockerStatus,
    NotificationChannel,
    UserRole,
)


# ── Shared base ───────────────────────────────────────────────────────────────
class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: Optional[datetime] = None


# ═════════════════════════════════════════════════════════════════════════════
# Auth Schemas
# ═════════════════════════════════════════════════════════════════════════════
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None
    role: UserRole = UserRole.employee

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(min_length=6, max_length=6)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


# ═════════════════════════════════════════════════════════════════════════════
# Organization Schemas
# ═════════════════════════════════════════════════════════════════════════════
class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9\-]+$")
    subscription_tier: str = "Enterprise"


class OrganizationResponse(TimestampMixin):
    id: uuid.UUID
    name: str
    slug: str
    subscription_tier: str
    is_active: bool

    model_config = {"from_attributes": True}


# ═════════════════════════════════════════════════════════════════════════════
# User Schemas
# ═════════════════════════════════════════════════════════════════════════════
class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    organization_id: Optional[uuid.UUID]
    avatar_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    fcm_token: Optional[str] = None


# ═════════════════════════════════════════════════════════════════════════════
# Locker Schemas
# ═════════════════════════════════════════════════════════════════════════════
class LockerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    locker_number: Optional[str] = None
    location: Optional[str] = None
    gps_lat: Optional[float] = Field(None, ge=-90, le=90)
    gps_lng: Optional[float] = Field(None, ge=-180, le=180)
    owner_id: Optional[uuid.UUID] = None


class LockerUpdate(BaseModel):
    name: Optional[str] = None
    locker_number: Optional[str] = None
    location: Optional[str] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    owner_id: Optional[uuid.UUID] = None


class LockerResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    locker_number: Optional[str]
    location: Optional[str]
    gps_lat: Optional[float]
    gps_lng: Optional[float]
    status: LockerStatus
    door_state: DoorState
    battery_status: int
    signal_strength: int
    temperature: Optional[float]
    humidity: Optional[float]
    is_online: bool
    camera_online: bool
    tamper_detected: bool
    motion_detected: bool
    last_seen: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class LockerTelemetry(BaseModel):
    """Real-time telemetry payload from MQTT."""
    device_id: str
    locker_id: Optional[str] = None
    event: str
    timestamp: datetime
    battery: Optional[int] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    signal: Optional[int] = None
    fingerprint_result: Optional[str] = None  # "match" | "fail" | "unknown"
    fingerprint_index: Optional[int] = None
    door_status: Optional[str] = None          # "open" | "closed"
    tamper: Optional[bool] = None
    motion: Optional[bool] = None


# ═════════════════════════════════════════════════════════════════════════════
# Device Schemas
# ═════════════════════════════════════════════════════════════════════════════
class DeviceCreate(BaseModel):
    locker_id: uuid.UUID
    serial_number: str = Field(min_length=5, max_length=100)
    firmware_version: str = Field(default="1.0.0")
    device_type: str = "ESP32_Lock_Controller"
    mqtt_client_id: Optional[str] = None


class DeviceResponse(BaseModel):
    id: uuid.UUID
    locker_id: uuid.UUID
    serial_number: str
    firmware_version: str
    device_type: str
    last_ping: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ═════════════════════════════════════════════════════════════════════════════
# Event Schemas
# ═════════════════════════════════════════════════════════════════════════════
class EventResponse(BaseModel):
    id: uuid.UUID
    locker_id: uuid.UUID
    event_type: EventType
    severity: AlertSeverity
    threat_score: float
    description: Optional[str]
    ai_summary: Optional[str]
    before_snapshot_url: Optional[str]
    after_snapshot_url: Optional[str]
    video_clip_url: Optional[str]
    resolved: bool
    timestamp: datetime

    model_config = {"from_attributes": True}


class EventResolveRequest(BaseModel):
    resolution_note: Optional[str] = None


# ═════════════════════════════════════════════════════════════════════════════
# Access Log Schemas
# ═════════════════════════════════════════════════════════════════════════════
class AccessLogResponse(BaseModel):
    id: uuid.UUID
    locker_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    auth_method: AuthMethod
    status: AccessStatus
    timestamp: datetime

    model_config = {"from_attributes": True}


# ═════════════════════════════════════════════════════════════════════════════
# Analytics Schemas
# ═════════════════════════════════════════════════════════════════════════════
class DashboardMetrics(BaseModel):
    total_lockers: int
    online_lockers: int
    offline_lockers: int
    today_access_count: int
    unauthorized_attempts_today: int
    active_alerts: int
    avg_battery: float
    threat_score_avg: float
    camera_online_count: int
    network_health_percent: float


class AccessTrendPoint(BaseModel):
    date: str           # YYYY-MM-DD
    granted: int
    denied: int


class ThreatTrendPoint(BaseModel):
    date: str
    score: float
    events: int


# ═════════════════════════════════════════════════════════════════════════════
# Notification Schemas
# ═════════════════════════════════════════════════════════════════════════════
class NotificationResponse(BaseModel):
    id: uuid.UUID
    title: str
    message: str
    channel: NotificationChannel
    severity: AlertSeverity
    is_read: bool
    timestamp: datetime

    model_config = {"from_attributes": True}


# ═════════════════════════════════════════════════════════════════════════════
# Locker Permission Schemas
# ═════════════════════════════════════════════════════════════════════════════
class PermissionCreate(BaseModel):
    locker_id: uuid.UUID
    user_id: uuid.UUID
    can_unlock: bool = True
    can_view_live: bool = True
    can_view_logs: bool = False
    can_manage: bool = False
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class PermissionResponse(BaseModel):
    id: uuid.UUID
    locker_id: uuid.UUID
    user_id: uuid.UUID
    can_unlock: bool
    can_view_live: bool
    can_view_logs: bool
    can_manage: bool
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ═════════════════════════════════════════════════════════════════════════════
# Generic Responses
# ═════════════════════════════════════════════════════════════════════════════
class MessageResponse(BaseModel):
    message: str
    success: bool = True


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    size: int
    pages: int
