"""
VaultAlert — Fake Hardware Tester (no ESP32 needed)

Simulates the hardware camera/microcontroller by hitting the LIVE backend exactly
like the real device would, so you can watch the dashboard light up end-to-end.

It exercises the recommended API-proxy path:
    POST {BASE}/integrations/telegram/bot<token>/sendPhoto   (photo + caption)
    POST {BASE}/integrations/telegram/bot<token>/sendMessage (text alert)

Usage (defaults hit the deployed Render backend):
    python iot/fake_hardware.py                 # send one photo + one alert
    python iot/fake_hardware.py --loop 10        # send 10 rounds, 5s apart
    python iot/fake_hardware.py --text "Unauthorized fingerprint!"
    python iot/fake_hardware.py --api http://localhost:8000/api/v1/integrations/telegram

Only dependency: `requests`  (pip install requests)
The image is generated in-memory — no file needed.
"""

import argparse
import io
import struct
import time
import zlib

import requests

# ── Same identifiers the deployed backend/hardware use ────────────────────────
DEFAULT_API = "https://vaultalert-api.onrender.com/api/v1/integrations/telegram"
HARDWARE_BOT_TOKEN = "8722120064:AAF6Yshc950N6CksWbLAeMa537zXG8h5ty0"
CHAT_ID = "-1004493857137"

# A few realistic hardware messages (must match the frontend classifier).
SAMPLE_ALERTS = [
    "Unauthorized fingerprint!",
    "Wrong password attempt!",
    "System Locked!",
    "Access Granted!",
    "Authorized: Bhavesh",
]


def _make_png(width: int = 96, height: int = 96, rgb=(220, 40, 40)) -> bytes:
    """Build a tiny solid-colour PNG in pure Python (no Pillow needed)."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    row = b"\x00" + bytes(rgb) * width
    idat = zlib.compress(row * height, 9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def send_photo(api: str, caption: str) -> None:
    url = f"{api}/bot{HARDWARE_BOT_TOKEN}/sendPhoto"
    png = _make_png()
    files = {"photo": ("snapshot.jpg", io.BytesIO(png), "image/jpeg")}
    data = {"chat_id": CHAT_ID, "caption": caption}
    r = requests.post(url, data=data, files=files, timeout=30)
    print(f"  sendPhoto  -> {r.status_code}  caption='{caption}'")


def send_text(api: str, text: str) -> None:
    url = f"{api}/bot{HARDWARE_BOT_TOKEN}/sendMessage"
    r = requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=30)
    print(f"  sendMessage-> {r.status_code}  text='{text}'")


def main() -> None:
    ap = argparse.ArgumentParser(description="VaultAlert fake-hardware tester")
    ap.add_argument("--api", default=DEFAULT_API, help="Backend telegram-proxy base URL")
    ap.add_argument("--text", help="Send this exact alert text (else cycles samples)")
    ap.add_argument("--photo", action="store_true", help="Also send a snapshot photo each round")
    ap.add_argument("--loop", type=int, default=1, help="How many rounds to send")
    ap.add_argument("--interval", type=float, default=5.0, help="Seconds between rounds")
    args = ap.parse_args()

    print(f"Target backend: {args.api}\n")
    for i in range(args.loop):
        text = args.text or SAMPLE_ALERTS[i % len(SAMPLE_ALERTS)]
        print(f"Round {i + 1}/{args.loop}")
        # A snapshot carries its own caption; text-only sends an alert line.
        if args.photo or args.text is None:
            send_photo(args.api, text)
        else:
            send_text(args.api, text)
        if i + 1 < args.loop:
            time.sleep(args.interval)

    print("\nDone. Open the dashboard — photos land under 'Live Security Footage'")
    print("and alerts in the 'Activity Timeline' / 'Security Incidents' within ~3s.")


if __name__ == "__main__":
    main()
