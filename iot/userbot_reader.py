"""
VaultAlert — Telegram Userbot Reader (logs in as YOUR account)

Why this exists: a Telegram *bot* can never read another bot's messages, so the
hardware bot's alerts never reach the dashboard. A *human account* CAN read them.
This script logs in as your own Telegram account, silently watches the Vault Alert
group, and forwards every new photo AND text alert (e.g. "Unauthorized fingerprint!")
to the VaultAlert backend so they show up on the dashboard in real time — with ZERO
changes to the ESP32 hardware.

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
     Make sure you log in with YOUR OWN phone number here, not the hardware bot.
  5) Leave it running (laptop) — or deploy as a Render "Background Worker" using the
     same session file uploaded as a secret.

────────────────────────────────────────────────────────────────────────────
FIX HISTORY (why the code below looks the way it does)
  push_text() used to POST to the bot's own sendMessage endpoint, and the
  camera.py backend endpoint used to echo every received snapshot back into
  the Telegram group with sendPhoto. Both of those re-posted into the same
  group this script watches, so this script would see its own forwarded
  message come back as "new", forward it again, and loop forever.

  Fix (both sides):
    - backend/app/api/v1/camera.py no longer calls Telegram's sendPhoto —
      it only caches the snapshot and broadcasts it to the dashboard.
    - This script no longer calls push_text() (removed) and keeps a short
      in-memory dedupe of recent (image+caption) hashes as a safety net,
      in case anything else in the pipeline ever re-posts into the group.
────────────────────────────────────────────────────────────────────────────
"""

import os
import io
import time
import hashlib

import requests
from telethon import TelegramClient, events

# ── CONFIG (env vars preferred; edit fallbacks only for a quick local test) ───
API_ID       = int(os.getenv("TG_API_ID", "0"))
API_HASH     = os.getenv("TG_API_HASH", "")
GROUP_ID     = int(os.getenv("TG_GROUP_ID", "-1004493857137"))
VA_API_BASE  = os.getenv("VA_API_BASE", "https://vaultalert-api.onrender.com/api/v1")
SESSION_NAME = os.getenv("TG_SESSION", "vaultalert_user")

if not API_ID or not API_HASH:
    raise SystemExit(
        "Set TG_API_ID and TG_API_HASH first (get them at https://my.telegram.org)."
    )

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# ── Dedupe safety net ──────────────────────────────────────────────────────
# Maps sha256(image_bytes + caption) -> last-forwarded timestamp. If the same
# content shows up again within DEDUPE_WINDOW_SECONDS, skip it instead of
# forwarding again. This is a safety net, not the primary fix — the primary
# fix is that camera.py no longer reposts to Telegram at all.
_recent_hashes = {}
DEDUPE_WINDOW_SECONDS = 20


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
    """Send a hardware text alert (e.g. 'Unauthorized fingerprint!') to the dashboard.

    Posts to the backend's text-ingest endpoint, which caches it as an event for the
    timeline. This does NOT re-post into Telegram (that endpoint only caches +
    broadcasts), so it can't cause the old echo loop.
    """
    try:
        r = requests.post(
            f"{VA_API_BASE}/telegram-text",
            json={"message": text},
            timeout=20,
        )
        print(f"  → text pushed [{r.status_code}] '{text[:50]}'")
    except Exception as e:
        print("  ! text push failed:", e)


@client.on(events.NewMessage(chats=GROUP_ID))
async def on_group_message(event):
    msg = event.message
    caption = (msg.message or "").strip()

    print(f"[seen] id={msg.id} from={msg.sender_id} has_photo={bool(msg.photo)} text={caption[:50]!r}")

    now = time.time()

    def is_duplicate(key: str) -> bool:
        last = _recent_hashes.get(key)
        if last and (now - last) < DEDUPE_WINDOW_SECONDS:
            return True
        _recent_hashes[key] = now
        return False

    # Photo (or image document) → forward the actual bytes to the footage grid.
    if msg.photo or (msg.document and (msg.document.mime_type or "").startswith("image/")):
        try:
            data = await msg.download_media(bytes)
        except Exception as e:
            print("  ! could not download media:", e)
            return

        content_hash = hashlib.sha256(data + caption.encode()).hexdigest()
        if is_duplicate(content_hash):
            print(f"  (duplicate photo within {DEDUPE_WINDOW_SECONDS}s, skipping)")
            return
        push_photo(data, caption or "Security Snapshot")
        return

    # Text-only alert (e.g. hardware "Unauthorized fingerprint!") → forward to timeline.
    if caption:
        text_hash = hashlib.sha256(("TEXT:" + caption).encode()).hexdigest()
        if is_duplicate(text_hash):
            print(f"  (duplicate text within {DEDUPE_WINDOW_SECONDS}s, skipping)")
            return
        push_text(caption)
        return


def main():
    print("VaultAlert userbot reader starting…")
    print(f"  group   : {GROUP_ID}")
    print(f"  backend : {VA_API_BASE}")
    print("  (first run will ask for your phone number + OTP)")
    with client:
        me = client.loop.run_until_complete(client.get_me())
        print(f"  logged in as: {me.first_name} (@{me.username})  — read-only listener")
        print("  Listening… send a photo in the group to test. Ctrl+C to stop.")
        client.run_until_disconnected()


if __name__ == "__main__":
    main()
