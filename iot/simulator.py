"""
VaultAlert — IoT Device Simulator
Simulates realistic ESP32 device payloads published to MQTT.
Run: python simulator.py --lockers <locker_id_1> <locker_id_2> ...
"""

import argparse
import asyncio
import json
import random
import uuid
from datetime import datetime, timezone

import aiomqtt
from loguru import logger

MQTT_HOST = "localhost"
MQTT_PORT = 1883
MQTT_USER = "vaultalert_server"
MQTT_PASS = ""

EVENTS = [
    "access_granted",
    "fingerprint_failed",
    "motion_detected",
    "door_left_open",
    "battery_low",
    "tampering",
    "unknown_face",
    "door_forced",
    "access_denied",
]


def random_telemetry(device_serial: str, locker_id: str, org_id: str) -> dict:
    return {
        "device_id": device_serial,
        "locker_id": locker_id,
        "org_id": org_id,
        "event": "telemetry",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "battery": random.randint(15, 100),
        "temperature": round(random.uniform(22.0, 38.0), 1),
        "humidity": round(random.uniform(30.0, 80.0), 1),
        "signal": random.randint(-90, -40),
        "door_status": random.choice(["open", "closed"]),
        "tamper": random.random() < 0.05,
        "motion": random.random() < 0.2,
        "fingerprint_result": random.choice(["match", "fail", None]),
        "fingerprint_index": random.randint(0, 9),
    }


def random_event(device_serial: str, locker_id: str, org_id: str) -> dict:
    event = random.choices(
        EVENTS,
        weights=[30, 15, 20, 10, 5, 5, 5, 5, 5],
        k=1,
    )[0]
    return {
        "device_id": device_serial,
        "locker_id": locker_id,
        "org_id": org_id,
        "event": event,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "battery": random.randint(10, 100),
        "signal": random.randint(-90, -40),
        "description": f"Simulated: {event} on device {device_serial}",
    }


async def simulate_device(
    client: aiomqtt.Client,
    device_serial: str,
    locker_id: str,
    org_id: str,
    telemetry_interval: float,
    event_interval: float,
) -> None:
    """Simulates a single locker device publishing telemetry and random events."""
    logger.info(f"Simulating device [{device_serial}] → locker [{locker_id}]")

    # Announce online
    await client.publish(
        f"vaultalert/devices/{device_serial}/status",
        json.dumps({"device_id": device_serial, "locker_id": locker_id, "org_id": org_id, "status": "online"}),
        qos=1,
    )

    async def _send_telemetry():
        while True:
            payload = random_telemetry(device_serial, locker_id, org_id)
            await client.publish(
                f"vaultalert/devices/{device_serial}/telemetry",
                json.dumps(payload),
                qos=0,
            )
            logger.debug(f"[{device_serial}] Telemetry: battery={payload['battery']}% door={payload['door_status']}")
            await asyncio.sleep(telemetry_interval)

    async def _send_events():
        while True:
            await asyncio.sleep(event_interval + random.uniform(-2, 2))
            payload = random_event(device_serial, locker_id, org_id)
            await client.publish(
                f"vaultalert/devices/{device_serial}/event",
                json.dumps(payload),
                qos=1,
            )
            logger.info(f"[{device_serial}] Event: {payload['event']}")

    await asyncio.gather(_send_telemetry(), _send_events())


async def main(locker_ids: list[str], org_id: str, telemetry_sec: float, event_sec: float) -> None:
    devices = [
        (f"ESP32-SIM-{str(uuid.uuid4())[:8].upper()}", lid)
        for lid in locker_ids
    ]

    logger.info(f"Starting VaultAlert IoT Simulator for {len(devices)} device(s)")
    logger.info(f"MQTT: {MQTT_HOST}:{MQTT_PORT}")

    async with aiomqtt.Client(
        hostname=MQTT_HOST,
        port=MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        identifier=f"vaultalert_simulator_{uuid.uuid4().hex[:8]}",
    ) as client:
        tasks = [
            simulate_device(client, serial, lid, org_id, telemetry_sec, event_sec)
            for serial, lid in devices
        ]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VaultAlert IoT Device Simulator")
    parser.add_argument("--lockers", nargs="+", required=True, help="Locker UUIDs to simulate")
    parser.add_argument("--org", required=True, help="Organization UUID")
    parser.add_argument("--telemetry-interval", type=float, default=5.0, help="Seconds between telemetry publishes")
    parser.add_argument("--event-interval", type=float, default=15.0, help="Average seconds between events")
    args = parser.parse_args()

    asyncio.run(main(
        locker_ids=args.lockers,
        org_id=args.org,
        telemetry_sec=args.telemetry_interval,
        event_sec=args.event_interval,
    ))
