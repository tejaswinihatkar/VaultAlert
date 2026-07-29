"""
VaultAlert — FastAPI Application Entry Point

Assembles all routers, middleware, CORS, lifespan events, and background workers.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger

from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis_client import close_redis, get_redis

# ── API Routers ───────────────────────────────────────────────────────────────
from app.api.v1 import (
    auth, lockers, analytics, websockets,
    events, access_logs, devices, organizations,
    users, permissions, notifications, fingerprints, telegram,
)

# ── Background Workers ────────────────────────────────────────────────────────
from app.workers.mqtt_worker import run_mqtt_subscriber


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} — env={settings.APP_ENV}")

    # Create all tables (use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified.")

    # Warm up Redis
    await get_redis()
    logger.info("Redis connection pool ready.")

    # Start MQTT subscriber as background task
    mqtt_task = asyncio.create_task(run_mqtt_subscriber())
    logger.info("MQTT subscriber started.")

    # Start Telegram Polling daemon
    from app.workers.telegram_worker import start_telegram_listener
    await start_telegram_listener()

    yield  # Application runs here

    # Graceful shutdown
    mqtt_task.cancel()
    try:
        await mqtt_task
    except asyncio.CancelledError:
        pass
    await close_redis()
    await engine.dispose()
    logger.info(f"{settings.APP_NAME} shutdown complete.")


# ── Application factory ────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "AI-Powered Smart Locker Monitoring & Security Platform. "
            "Real-time IoT device management, multi-factor authentication, "
            "surveillance, analytics, and threat intelligence."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        contact={
            "name": "VaultAlert Engineering",
            "email": "engineering@vaultalert.io",
            "url": "https://vaultalert.io",
        },
        license_info={"name": "Proprietary", "url": "https://vaultalert.io/license"},
    )

    # ── Middleware ─────────────────────────────────────────────────────────────
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Routes ─────────────────────────────────────────────────────────────
    app.include_router(auth.router,          prefix="/api/v1")
    app.include_router(lockers.router,       prefix="/api/v1")
    app.include_router(analytics.router,     prefix="/api/v1")
    app.include_router(events.router,        prefix="/api/v1")
    app.include_router(access_logs.router,   prefix="/api/v1")
    app.include_router(devices.router,       prefix="/api/v1")
    app.include_router(organizations.router, prefix="/api/v1")
    app.include_router(users.router,         prefix="/api/v1")
    app.include_router(permissions.router,   prefix="/api/v1")
    app.include_router(notifications.router, prefix="/api/v1")
    app.include_router(fingerprints.router,  prefix="/api/v1")
    app.include_router(telegram.router,      prefix="/api/v1")
    app.include_router(websockets.router)  # No prefix — /ws/... endpoints

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["System"], include_in_schema=False)
    async def health():
        return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}

    return app


app = create_app()
