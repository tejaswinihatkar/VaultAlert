"""
VaultAlert — Telegram Userbot Reader (logs in as YOUR account)

Why this exists: a Telegram *bot* can never read another bot's messages, so the
hardware bot's alerts never reach the dashboard. A *human account* CAN read them.
This script logs in as your own Telegram account, silently watches the Vault Alert
group, and forwards every new message/photo to the VaultAlert backend so it shows
up on the dashboard — with ZERO changes to the ESP32 hardware.

It only READS the group and POSTs to your backend. It never sends or posts anything
in Telegram.

────────────────────────────────────────────────────────────────────────────
ONE-TIME SETUP
  1) Get api_id + api_hash (free):  https://my.telegram.org  → "API development tools"
  2) pip install telethon requests
  3) Set env vars (or edit the CONFIG block below):
        TG_API_ID       = <your api_id>
        TG_API_HASH     = <your api_hash>
        TG_GROUP_ID     = -1004493857137            (already your group)
        VA_API_BASE     = https://vaultalert-api.onrender.com/api/v1
  4) Run once interactively to log in (enter your phone + the OTP Telegram sends you):
        python iot/userbot_reader.py
     This creates a `vaultalert_user.session` file. Keep it PRIVATE (it's your login).
  5) Leave it running (laptop) — or deploy as a Render "Background Worker" using the
     same session file uploaded as a secret.
────────────────────────────────────────────────────────────────────────────
"""

import os
import io
import time

import requests
from telethon import TelegramClient, events

# ── CONFIG (env vars preferred; edit fallbacks only for a quick local test) ───
API_ID       = int(os.getenv("TG_API_ID", "0"))
API_HASH     = os.getenv("TG_API_HASH", "")
GROUP_ID     = int(os.getenv("TG_GROUP_ID", "-1004493857137"))
VA_API_BASE  = os.getenv("VA_API_BASE", "https://vaultalert-api.onrender.com/api/v1")
SESSION_NAME = os.getenv("TG_SESSION", "vaultalert_user")

# Hardware bot token — used only so text alerts flow through the same proxy the
# dashboard already reads (so captions/classification stay consistent).
HARDWARE_BOT_TOKEN = os.getenv(
    "TG_HW_BOT_TOKEN", "8722120064:AAF6Yshc950N6CksWbLAeMa537zXG8h5ty0"
)
CHAT_ID = os.getenv("TG_CHAT_ID", "-1004493857137")

if not API_ID or not API_HASH:
    raise SystemExit(
        "Set TG_API_ID and TG_API_HASH first (get them at https://my.telegram.org)."
    )

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)


def push_photo(jpeg_bytes: bytes, caption: str) -> None:
    """Send a captured photo to the dashboard's footage grid."""
    try:
        r = requests.post(
            f"{VA_API_BASE}/camera/snapshot",
            files={"file": ("snapshot.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")},
            data={"caption": caption or "Security Snapshot", "device_id": "telegram_userbot"},
            timeout=30,
        )
        print(f"  → photo pushed [{r.status_code}] '{caption[:40]}'")
    except Exception as e:
        print("  ! photo push failed:", e)


def push_text(text: str) -> None:
    """Send a text alert to the dashboard via the backend proxy (keeps classifier parity)."""
    try:
        r = requests.post(
            f"{VA_API_BASE}/integrations/telegram/bot{HARDWARE_BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text},
            timeout=20,
        )
        print(f"  → text pushed [{r.status_code}] '{text[:40]}'")
    except Exception as e:
        print("  ! text push failed:", e)


@client.on(events.NewMessage(chats=GROUP_ID))
async def on_group_message(event):
    msg = event.message
    caption = (msg.message or "").strip()

    # Photo (or image document) → forward the actual bytes.
    if msg.photo or (msg.document and (msg.document.mime_type or "").startswith("image/")):
        try:
            data = await msg.download_media(bytes)
            push_photo(data, caption or "Security Snapshot")
        except Exception as e:
            print("  ! could not download media:", e)
        if caption:
            push_text(caption)
        return

    # Text-only alert.
    if caption:
        push_text(caption)


def main():
    print("VaultAlert userbot reader starting…")
    print(f"  group   : {GROUP_ID}")
    print(f"  backend : {VA_API_BASE}")
    print("  (first run will ask for your phone number + OTP)")
    with client:
        me = client.loop.run_until_complete(client.get_me())
        print(f"  logged in as: {me.first_name} (@{me.username})  — read-only listener")
        print("  Listening… send a message/photo in the group to test. Ctrl+C to stop.")
        client.run_until_disconnected()


if __name__ == "__main__":
    main()
