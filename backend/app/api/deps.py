"""VaultAlert — Auth & RBAC Dependencies.

FastAPI dependency functions for JWT extraction and role-based access control.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.security import decode_token
from app.models.models import UserRole

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """Minimal user context extracted from JWT — no DB round-trip needed."""

    def __init__(self, user_id: UUID, role: UserRole, org_id: UUID | None = None) -> None:
        self.user_id = user_id
        self.role = role
        self.org_id = org_id


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentUser:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not an access token.")

    user_id = UUID(payload["sub"])
    role = UserRole(payload["role"])
    org_id = UUID(payload["org_id"]) if payload.get("org_id") else None
    return CurrentUser(user_id=user_id, role=role, org_id=org_id)


def require_roles(*roles: UserRole):
    """Returns a dependency that enforces one of the specified roles."""

    async def _check(current: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if current.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in roles]}",
            )
        return current

    return _check


# Convenient role aliases
AdminOnly = Depends(require_roles(UserRole.admin))
AdminOrManager = Depends(require_roles(UserRole.admin, UserRole.manager))
AdminOrOwner = Depends(require_roles(UserRole.admin, UserRole.owner))
AnyAuthenticated = Depends(get_current_user)
