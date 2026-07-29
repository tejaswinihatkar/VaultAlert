"""
VaultAlert — SQLAlchemy Models
Complete database schema for all 12+ tables.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


# ── Helpers ───────────────────────────────────────────────────────────────────
def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


# ── Enums ─────────────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    admin = "Admin"
    owner = "Owner"
    family = "Family"
    manager = "Manager"
    employee = "Employee"
    guard = "Guard"
    auditor = "Auditor"


class LockerStatus(str, enum.Enum):
    locked = "Locked"
    unlocked = "Unlocked"
    tampered = "Tampered"
    offline = "Offline"
    lockdown = "Lockdown"


class DoorState(str, enum.Enum):
    open = "Open"
    closed = "Closed"


class AccessStatus(str, enum.Enum):
    granted = "Granted"
    denied = "Denied"


class AuthMethod(str, enum.Enum):
    fingerprint = "Fingerprint"
    face = "Face"
    otp = "OTP"
    admin_override = "AdminOverride"
    multi_factor = "MultiFactor"


class EventType(str, enum.Enum):
    door_forced = "DoorForced"
    tampering = "Tampering"
    unknown_face = "UnknownFace"
    fingerprint_failed = "FingerprintFailed"
    otp_failed = "OTPFailed"
    motion_detected = "MotionDetected"
    door_left_open = "DoorLeftOpen"
    camera_offline = "CameraOffline"
    battery_low = "BatteryLow"
    internet_offline = "InternetOffline"
    power_failure = "PowerFailure"
    access_granted = "AccessGranted"
    access_denied = "AccessDenied"
    emergency_lockdown = "EmergencyLockdown"


class NotificationChannel(str, enum.Enum):
    push = "Push"
    sms = "SMS"
    email = "Email"
    telegram = "Telegram"
    whatsapp = "WhatsApp"


class AlertSeverity(str, enum.Enum):
    critical = "Critical"
    warning = "Warning"
    info = "Info"


# ═════════════════════════════════════════════════════════════════════════════
# 1. Organization
# ═════════════════════════════════════════════════════════════════════════════
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    slug = Column(String(100), nullable=False, unique=True)
    subscription_tier = Column(String(50), default="Enterprise")
    logo_url = Column(String(500), nullable=True)
    max_lockers = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    users = relationship("User", back_populates="organization", lazy="noload")
    lockers = relationship("Locker", back_populates="organization", lazy="noload")


# ═════════════════════════════════════════════════════════════════════════════
# 2. User
# ═════════════════════════════════════════════════════════════════════════════
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.employee)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    fcm_token = Column(String(500), nullable=True)  # Firebase device token
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization", back_populates="users")
    fingerprints = relationship("Fingerprint", back_populates="user", lazy="noload")
    faces = relationship("Face", back_populates="user", lazy="noload")
    access_logs = relationship("AccessLog", back_populates="user", lazy="noload")
    notifications = relationship("Notification", back_populates="user", lazy="noload")
    audit_logs = relationship("AuditLog", back_populates="user", lazy="noload")
    locker_permissions = relationship("LockerPermission", back_populates="user", lazy="noload")


# ═════════════════════════════════════════════════════════════════════════════
# 3. Locker
# ═════════════════════════════════════════════════════════════════════════════
class Locker(Base):
    __tablename__ = "lockers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(100), nullable=False)
    locker_number = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    gps_lat = Column(Float, nullable=True)
    gps_lng = Column(Float, nullable=True)
    status = Column(Enum(LockerStatus), default=LockerStatus.locked, nullable=False)
    door_state = Column(Enum(DoorState), default=DoorState.closed, nullable=False)
    battery_status = Column(Integer, default=100)      # percentage
    signal_strength = Column(Integer, default=-50)     # dBm
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    is_online = Column(Boolean, default=False)
    camera_online = Column(Boolean, default=False)
    tamper_detected = Column(Boolean, default=False)
    motion_detected = Column(Boolean, default=False)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization = relationship("Organization", back_populates="lockers")
    owner = relationship("User", foreign_keys=[owner_id])
    device = relationship("Device", back_populates="locker", uselist=False, lazy="noload")
    access_logs = relationship("AccessLog", back_populates="locker", lazy="noload")
    events = relationship("Event", back_populates="locker", lazy="noload")
    permissions = relationship("LockerPermission", back_populates="locker", lazy="noload")
    settings = relationship("LockerSettings", back_populates="locker", uselist=False, lazy="noload")


# ═════════════════════════════════════════════════════════════════════════════
# 4. Device (ESP32 / Raspberry Pi controller)
# ═════════════════════════════════════════════════════════════════════════════
class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    locker_id = Column(UUID(as_uuid=True), ForeignKey("lockers.id", ondelete="CASCADE"), nullable=False, unique=True)
    serial_number = Column(String(100), nullable=False, unique=True, index=True)
    firmware_version = Column(String(50), nullable=False, default="1.0.0")
    device_type = Column(String(50), default="ESP32_Lock_Controller")
    mqtt_client_id = Column(String(150), nullable=True)
    last_ping = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    locker = relationship("Locker", back_populates="device")


# ═════════════════════════════════════════════════════════════════════════════
# 5. Fingerprint Template (AES-256 encrypted)
# ═════════════════════════════════════════════════════════════════════════════
class Fingerprint(Base):
    __tablename__ = "fingerprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    encrypted_template = Column(Text, nullable=False)  # AES-256-GCM base64
    template_hash = Column(String(64), nullable=False, index=True)  # SHA-256 for fast lookup
    sensor_index = Column(Integer, nullable=False)  # Index slot on ESP32 fingerprint sensor
    label = Column(String(100), nullable=True)  # e.g. "Right Index"
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="fingerprints")

    __table_args__ = (
        UniqueConstraint("user_id", "sensor_index", name="uq_user_sensor_slot"),
    )


# ═════════════════════════════════════════════════════════════════════════════
# 6. Face Encoding (multi-embedding for robustness)
# ═════════════════════════════════════════════════════════════════════════════
class Face(Base):
    __tablename__ = "faces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    encrypted_encoding = Column(Text, nullable=False)  # AES-256 encrypted serialized numpy array
    image_url = Column(String(500), nullable=True)     # S3 reference image URL
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="faces")


# ═════════════════════════════════════════════════════════════════════════════
# 7. Locker Permission (access control matrix)
# ═════════════════════════════════════════════════════════════════════════════
class LockerPermission(Base):
    __tablename__ = "locker_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    locker_id = Column(UUID(as_uuid=True), ForeignKey("lockers.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    can_unlock = Column(Boolean, default=True)
    can_view_live = Column(Boolean, default=True)
    can_view_logs = Column(Boolean, default=False)
    can_manage = Column(Boolean, default=False)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)  # Temporary access
    created_at = Column(DateTime(timezone=True), default=utcnow)

    locker = relationship("Locker", back_populates="permissions")
    user = relationship("User", back_populates="locker_permissions")

    __table_args__ = (
        UniqueConstraint("locker_id", "user_id", name="uq_locker_user_permission"),
    )


# ═════════════════════════════════════════════════════════════════════════════
# 8. Access Log
# ═════════════════════════════════════════════════════════════════════════════
class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    locker_id = Column(UUID(as_uuid=True), ForeignKey("lockers.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    auth_method = Column(Enum(AuthMethod), nullable=False)
    status = Column(Enum(AccessStatus), nullable=False)
    fingerprint_id = Column(UUID(as_uuid=True), ForeignKey("fingerprints.id", ondelete="SET NULL"), nullable=True)
    face_id = Column(UUID(as_uuid=True), ForeignKey("faces.id", ondelete="SET NULL"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utcnow, index=True)

    locker = relationship("Locker", back_populates="access_logs")
    user = relationship("User", back_populates="access_logs")


# ═════════════════════════════════════════════════════════════════════════════
# 9. Event (security events with AI threat scoring)
# ═════════════════════════════════════════════════════════════════════════════
class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    locker_id = Column(UUID(as_uuid=True), ForeignKey("lockers.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(Enum(EventType), nullable=False, index=True)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.info, nullable=False)
    threat_score = Column(Float, default=0.0)
    description = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)          # Natural language AI summary
    before_snapshot_url = Column(String(500), nullable=True)
    after_snapshot_url = Column(String(500), nullable=True)
    video_clip_url = Column(String(500), nullable=True)
    fingerprint_id = Column(UUID(as_uuid=True), nullable=True)
    face_id = Column(UUID(as_uuid=True), nullable=True)
    device_battery = Column(Integer, nullable=True)
    device_signal = Column(Integer, nullable=True)
    resolved = Column(Boolean, default=False)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utcnow, index=True)

    locker = relationship("Locker", back_populates="events")


# ═════════════════════════════════════════════════════════════════════════════
# 10. Notification
# ═════════════════════════════════════════════════════════════════════════════
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(Enum(NotificationChannel), nullable=False)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.info)
    is_read = Column(Boolean, default=False)
    sent_status = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="notifications")


# ═════════════════════════════════════════════════════════════════════════════
# 11. Audit Log (immutable security trail)
# ═════════════════════════════════════════════════════════════════════════════
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utcnow, index=True)

    user = relationship("User", back_populates="audit_logs")


# ═════════════════════════════════════════════════════════════════════════════
# 12. Locker Settings
# ═════════════════════════════════════════════════════════════════════════════
class LockerSettings(Base):
    __tablename__ = "locker_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    locker_id = Column(UUID(as_uuid=True), ForeignKey("lockers.id", ondelete="CASCADE"), nullable=False, unique=True)
    motion_sensitivity = Column(String(50), default="Medium")   # Low, Medium, High
    video_retention_days = Column(Integer, default=30)
    lockdown_on_tamper = Column(Boolean, default=True)
    alert_on_door_open = Column(Boolean, default=True)
    alert_battery_threshold = Column(Integer, default=20)       # percent
    auto_lock_after_seconds = Column(Integer, default=30)
    require_mfa = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    locker = relationship("Locker", back_populates="settings")


# ═════════════════════════════════════════════════════════════════════════════
# 13. Firmware Release
# ═════════════════════════════════════════════════════════════════════════════
class FirmwareRelease(Base):
    __tablename__ = "firmware_releases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(String(50), nullable=False, unique=True, index=True)
    binary_url = Column(String(500), nullable=False)
    checksum_sha256 = Column(String(64), nullable=False)
    changelog = Column(Text, nullable=True)
    is_stable = Column(Boolean, default=False)
    min_device_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
