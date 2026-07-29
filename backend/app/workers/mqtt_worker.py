"""VaultAlert — MQTT Subscriber Worker.

Subscribes to all device MQTT topics, parses payloads, updates the database,
broadcasts WebSocket events, and fires security alerts on threat events.
"""

import asyncio
import json
from datetime import datetime, timezone

import aiomqtt
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import (
    AccessLog, AccessStatus, AuthMethod, Event, EventType, AlertSeverity
)
from app.repositories.locker_repo import LockerRepository
from app.repositories.event_repo import EventRepository, AccessLogRepository
from app.schemas.schemas import LockerTelemetry
from app.workers.ws_manager import manager as ws_manager

# ── MQTT Topic Structure ──────────────────────────────────────────────────────
# vaultalert/devices/{device_serial}/telemetry   → periodic sensor data
# vaultalert/devices/{device_serial}/event       → security/access events
# vaultalert/devices/{device_serial}/status      → online/offline heartbeat

TOPIC_PREFIX = "vaultalert/devices"
THREAT_EVENT_TYPES = {
    "door_forced", "tampering", "fingerprint_failed",
    "otp_failed", "unknown_face", "motion_detected",
}

# Maps MQTT event strings → EventType enum + severity + threat score
EVENT_MAP = {
    "door_forced":         (EventType.door_forced,        AlertSeverity.critical, 0.95),
    "tampering":           (EventType.tampering,          AlertSeverity.critical, 0.90),
    "unknown_face":        (EventType.unknown_face,        AlertSeverity.critical, 0.85),
    "fingerprint_failed":  (EventType.fingerprint_failed,  AlertSeverity.warning,  0.60),
    "otp_failed":          (EventType.otp_failed,          AlertSeverity.warning,  0.55),
    "motion_detected":     (EventType.motion_detected,     AlertSeverity.info,     0.30),
    "door_left_open":      (EventType.door_left_open,      AlertSeverity.warning,  0.40),
    "camera_offline":      (EventType.camera_offline,      AlertSeverity.warning,  0.35),
    "battery_low":         (EventType.battery_low,         AlertSeverity.warning,  0.20),
    "internet_offline":    (EventType.internet_offline,    AlertSeverity.warning,  0.25),
    "power_failure":       (EventType.power_failure,       AlertSeverity.critical, 0.70),
    "access_granted":      (EventType.access_granted,      AlertSeverity.info,     0.00),
    "access_denied":       (EventType.access_denied,       AlertSeverity.warning,  0.50),
}


async def _handle_telemetry(session: AsyncSession, payload: dict, device_serial: str) -> None:
    """Process periodic telemetry — update locker state, broadcast to WS."""
    try:
        telemetry = LockerTelemetry(
            device_id=device_serial,
            locker_id=payload.get("locker_id"),
            event=payload.get("event", "telemetry"),
            timestamp=datetime.now(tz=timezone.utc),
            battery=payload.get("battery"),
            temperature=payload.get("temperature"),
            humidity=payload.get("humidity"),
            signal=payload.get("signal"),
            door_status=payload.get("door_status"),
            tamper=payload.get("tamper"),
            motion=payload.get("motion"),
        )

        locker_repo = LockerRepository(session)
        if telemetry.locker_id:
            await locker_repo.update_telemetry(
                locker_id=telemetry.locker_id,
                battery=telemetry.battery,
                signal=telemetry.signal,
                temperature=telemetry.temperature,
                humidity=telemetry.humidity,
                door_state=telemetry.door_status,
                tamper=telemetry.tamper,
                motion=telemetry.motion,
                is_online=True,
            )
            await session.commit()

            # Broadcast to locker WebSocket room
            await ws_manager.broadcast_to_locker(
                locker_id=telemetry.locker_id,
                event_type="telemetry_update",
                data=payload,
            )
    except Exception as exc:
        logger.error(f"Telemetry processing error for {device_serial}: {exc}")
        await session.rollback()


async def _handle_event(session: AsyncSession, payload: dict, device_serial: str) -> None:
    """Process a security/access event — create Event record and broadcast alert."""
    try:
        event_key = payload.get("event", "").lower()
        locker_id = payload.get("locker_id")
        if not locker_id:
            return

        event_type, severity, threat_score = EVENT_MAP.get(
            event_key,
            (EventType.motion_detected, AlertSeverity.info, 0.1),
        )

        event = Event(
            locker_id=locker_id,
            event_type=event_type,
            severity=severity,
            threat_score=threat_score,
            description=payload.get("description", f"Device {device_serial}: {event_key}"),
            device_battery=payload.get("battery"),
            device_signal=payload.get("signal"),
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)

        # Broadcast to org room and locker room
        event_data = {
            "event_id": str(event.id),
            "locker_id": locker_id,
            "event_type": event_type.value,
            "severity": severity.value,
            "threat_score": threat_score,
            "timestamp": event.timestamp.isoformat(),
            "description": event.description,
        }
        org_id = payload.get("org_id")
        if org_id:
            await ws_manager.broadcast_to_org(org_id, "security_event", event_data)
        await ws_manager.broadcast_to_locker(locker_id, "security_event", event_data)

        logger.warning(f"Security event [{severity.value}]: {event_type.value} on locker={locker_id}")
    except Exception as exc:
        logger.error(f"Event processing error for {device_serial}: {exc}")
        await session.rollback()


async def _handle_status(session: AsyncSession, payload: dict, device_serial: str) -> None:
    """Handle device heartbeat / connection status messages."""
    locker_id = payload.get("locker_id")
    is_online = payload.get("status") == "online"
    if locker_id:
        locker_repo = LockerRepository(session)
        await locker_repo.update_telemetry(locker_id, is_online=is_online)
        await session.commit()
        await ws_manager.broadcast_to_locker(
            locker_id,
            "device_online" if is_online else "device_offline",
            {"locker_id": locker_id, "online": is_online},
        )


async def run_mqtt_subscriber() -> None:
    """Main MQTT subscriber loop — reconnects on failure with exponential backoff."""
    backoff = 2
    while True:
        try:
            logger.info(f"Connecting to MQTT broker at {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
            async with aiomqtt.Client(
                hostname=settings.MQTT_BROKER_HOST,
                port=settings.MQTT_BROKER_PORT,
                username=settings.MQTT_USERNAME,
                password=settings.MQTT_PASSWORD,
                identifier=settings.MQTT_CLIENT_ID,
            ) as client:
                backoff = 2
                await client.subscribe(f"{TOPIC_PREFIX}/+/telemetry")
                await client.subscribe(f"{TOPIC_PREFIX}/+/event")
                await client.subscribe(f"{TOPIC_PREFIX}/+/status")
                logger.info("MQTT subscriber active. Listening for device messages...")

                async for message in client.messages:
                    topic = str(message.topic)
                    parts = topic.split("/")
                    if len(parts) < 4:
                        continue

                    device_serial = parts[2]
                    msg_type = parts[3]

                    try:
                        payload = json.loads(message.payload.decode("utf-8"))
                    except json.JSONDecodeError:
                        logger.warning(f"Malformed MQTT payload from {device_serial}")
                        continue

                    async with AsyncSessionLocal() as session:
                        if msg_type == "telemetry":
                            await _handle_telemetry(session, payload, device_serial)
                        elif msg_type == "event":
                            await _handle_event(session, payload, device_serial)
                        elif msg_type == "status":
                            await _handle_status(session, payload, device_serial)

        except aiomqtt.MqttError as exc:
            logger.error(f"MQTT connection error: {exc}. Retrying in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except Exception as exc:
            logger.exception(f"Unexpected MQTT worker error: {exc}")
            await asyncio.sleep(backoff)
