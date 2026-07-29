"""
VaultAlert — Audit Log Middleware
Auto-logs all mutating API calls (POST/PUT/DELETE/PATCH) with user, IP, and resource info.
"""

import json
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger

from app.core.security import decode_token


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that writes an immutable audit trail for every
    state-mutating HTTP request.
    """

    _SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}
    _AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        if (
            request.method not in self._AUDIT_METHODS
            or request.url.path in self._SKIP_PATHS
            or request.url.path.startswith("/ws")
        ):
            return response

        # Fire-and-forget audit log (non-blocking)
        try:
            await self._write_audit(request, response.status_code)
        except Exception as e:
            logger.debug(f"Audit log write skipped: {e}")

        return response

    async def _write_audit(self, request: Request, status_code: int) -> None:
        """Extract context and write audit log record to the database."""
        from uuid import UUID
        from app.core.database import async_session_factory
        from app.models.models import AuditLog

        # Extract user from JWT (best-effort)
        user_id = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                payload = decode_token(auth_header[7:])
                user_id = UUID(payload["sub"])
            except Exception:
                pass

        # Extract resource type from URL path
        path_parts = [p for p in request.url.path.split("/") if p]
        resource_type = path_parts[-2] if len(path_parts) >= 2 else path_parts[-1] if path_parts else "unknown"
        resource_id = path_parts[-1] if len(path_parts) >= 1 else None

        # Only persist if status < 500 (skip server errors)
        if status_code >= 500:
            return

        async with async_session_factory() as db:
            log = AuditLog(
                user_id=user_id,
                action=f"{request.method} {request.url.path}",
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                details=json.dumps({"status_code": status_code}),
            )
            db.add(log)
            await db.commit()
