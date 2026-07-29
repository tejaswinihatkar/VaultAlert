"""
VaultAlert — Security Utilities
JWT creation/verification, password hashing, AES-256 encryption for biometric templates.
"""

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Password hashing (bcrypt) ─────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_access_token(subject: str | UUID, role: str, extra: Optional[dict] = None) -> str:
    payload = {
        "sub": str(subject),
        "role": role,
        "type": "access",
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc)
        + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str | UUID, role: str) -> str:
    payload = {
        "sub": str(subject),
        "role": role,
        "type": "refresh",
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Raises JWTError if token is invalid or expired."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ── AES-256-GCM encryption for biometric templates ───────────────────────────
def encrypt_biometric(data: bytes) -> str:
    """Encrypt binary biometric template and return base64-encoded ciphertext."""
    aesgcm = AESGCM(settings.aes_key)
    nonce = AESGCM.generate_key(bit_length=96)[:12]  # 96-bit nonce
    ct = aesgcm.encrypt(nonce, data, None)
    return base64.b64encode(nonce + ct).decode()


def decrypt_biometric(token: str) -> bytes:
    """Decrypt a base64-encoded AES-256-GCM biometric token."""
    raw = base64.b64decode(token.encode())
    nonce, ct = raw[:12], raw[12:]
    aesgcm = AESGCM(settings.aes_key)
    return aesgcm.decrypt(nonce, ct, None)


def hash_fingerprint_template(raw_bytes: bytes) -> str:
    """SHA-256 hash of raw fingerprint bytes — used as a searchable index."""
    return hashlib.sha256(raw_bytes).hexdigest()
