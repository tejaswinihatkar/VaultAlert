"""
VaultAlert — Redis-based Sliding Window Rate Limiter
- Auth endpoints: 5 req/min per IP
- API endpoints: 60 req/min per user or IP
"""

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from loguru import logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter backed by Redis.
    Degrades gracefully (allows request) if Redis is unavailable.
    """

    AUTH_LIMIT = 5
    AUTH_WINDOW = 60     # seconds
    API_LIMIT = 60
    API_WINDOW = 60      # seconds

    AUTH_PATHS = {"/api/v1/auth/login", "/api/v1/auth/signup", "/api/v1/auth/refresh"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await self._check_and_forward(request, call_next)
        except Exception as e:
            logger.debug(f"Rate limiter error (passing through): {e}")
            return await call_next(request)

    async def _check_and_forward(self, request: Request, call_next: Callable) -> Response:
        from app.core.redis_client import get_redis

        path = request.url.path
        client_ip = (request.client.host if request.client else "unknown")

        is_auth = path in self.AUTH_PATHS
        limit = self.AUTH_LIMIT if is_auth else self.API_LIMIT
        window = self.AUTH_WINDOW if is_auth else self.API_WINDOW
        bucket_type = "auth" if is_auth else "api"

        # Derive a rate-limit key: prefer user identity, fall back to IP
        user_key = client_ip
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer ") and not is_auth:
            from app.core.security import decode_token
            try:
                payload = decode_token(auth_header[7:])
                user_key = f"user:{payload['sub']}"
            except Exception:
                pass

        redis_key = f"ratelimit:{bucket_type}:{user_key}"
        now = int(time.time())
        window_start = now - window

        redis = await get_redis()

        # Remove old entries outside the window
        await redis.zremrangebyscore(redis_key, 0, window_start)

        # Count requests in window
        count = await redis.zcard(redis_key)
        if count >= limit:
            retry_after = window
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Rate limit exceeded. Max {limit} requests per {window}s. "
                        f"Retry after {retry_after}s."
                    )
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Record this request
        await redis.zadd(redis_key, {f"{now}:{id(request)}": now})
        await redis.expire(redis_key, window + 5)

        return await call_next(request)
