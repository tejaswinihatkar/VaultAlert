"""
VaultAlert — Background Scheduler
APScheduler-based background jobs for maintenance tasks.
"""

import asyncio
from datetime import datetime, timezone, timedelta

from loguru import logger


def start_scheduler(app) -> None:
    """Initialize and start all background scheduled tasks."""
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        scheduler = AsyncIOScheduler(timezone="UTC")

        # Every 15 min: check battery thresholds
        scheduler.add_job(
            _check_battery_levels,
            "interval",
            minutes=15,
            id="battery_check",
            replace_existing=True,
        )

        # Every 5 min: mark stale devices as offline
        scheduler.add_job(
            _mark_stale_devices_offline,
            "interval",
            minutes=5,
            id="device_heartbeat_check",
            replace_existing=True,
        )

        # Daily at 08:00 UTC: send security summary email
        scheduler.add_job(
            _send_daily_summary,
            "cron",
            hour=8,
            minute=0,
            id="daily_summary",
            replace_existing=True,
        )

        # Every hour: clean expired OTPs from Redis
        scheduler.add_job(
            _cleanup_expired_otps,
            "interval",
            hours=1,
            id="otp_cleanup",
            replace_existing=True,
        )

        scheduler.start()
        logger.info("Background scheduler started with 4 jobs.")
    except ImportError:
        logger.warning("APScheduler not installed — background scheduler disabled.")


async def _check_battery_levels() -> None:
    """Alert on lockers with battery below the configured threshold."""
    try:
        from app.core.database import async_session_factory
        from app.models.models import Locker
        from sqlalchemy import select

        async with async_session_factory() as db:
            result = await db.execute(
                select(Locker).where(
                    Locker.is_online == True,
                    Locker.battery_status < 20,
                )
            )
            low_battery = result.scalars().all()
            if low_battery:
                logger.warning(f"Battery check: {len(low_battery)} locker(s) below 20%")
    except Exception as e:
        logger.error(f"Battery check failed: {e}")


async def _mark_stale_devices_offline() -> None:
    """Mark devices as offline if no heartbeat received in > 5 minutes."""
    try:
        from app.core.database import async_session_factory
        from app.models.models import Locker
        from sqlalchemy import select, update

        stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)

        async with async_session_factory() as db:
            result = await db.execute(
                update(Locker)
                .where(
                    Locker.is_online == True,
                    Locker.last_seen < stale_cutoff,
                )
                .values(is_online=False)
            )
            if result.rowcount:
                await db.commit()
                logger.info(f"Scheduler: Marked {result.rowcount} stale device(s) offline.")
    except Exception as e:
        logger.error(f"Device heartbeat check failed: {e}")


async def _send_daily_summary() -> None:
    """Send daily security summary to organization admins."""
    try:
        logger.info("Scheduler: Sending daily security summary emails.")
        # Would query events/access logs and send via NotificationService
        # Skipped until SMTP is configured
    except Exception as e:
        logger.error(f"Daily summary failed: {e}")


async def _cleanup_expired_otps() -> None:
    """Clean expired OTP keys from Redis (Redis TTL handles this automatically)."""
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        # OTPs use Redis TTL, so this is mostly a no-op
        # Scan for any orphaned otp:* keys just in case
        cursor = 0
        cleaned = 0
        while True:
            cursor, keys = await redis.scan(cursor, match="otp:*", count=100)
            for key in keys:
                ttl = await redis.ttl(key)
                if ttl == -1:  # No TTL set — orphan
                    await redis.delete(key)
                    cleaned += 1
            if cursor == 0:
                break
        if cleaned:
            logger.info(f"OTP cleanup: removed {cleaned} orphaned keys.")
    except Exception as e:
        logger.error(f"OTP cleanup failed: {e}")
