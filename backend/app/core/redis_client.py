"""
VaultAlert — Redis Client
Provides an async Redis connection pool for caching, pub/sub, and job queues.
"""

from typing import Optional
import redis.asyncio as aioredis
from loguru import logger

from app.core.config import settings

_redis_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Return (and lazily initialise) the global Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
        logger.info("Redis connection pool initialised.")
    return _redis_pool


async def close_redis() -> None:
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
        logger.info("Redis connection pool closed.")


# ── Cache helpers ─────────────────────────────────────────────────────────────
async def cache_set(key: str, value: str, ttl: int = 300) -> None:
    r = await get_redis()
    await r.setex(key, ttl, value)


async def cache_get(key: str) -> Optional[str]:
    r = await get_redis()
    return await r.get(key)


async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)


# ── Pub/Sub helpers ───────────────────────────────────────────────────────────
async def publish(channel: str, message: str) -> None:
    r = await get_redis()
    await r.publish(channel, message)
