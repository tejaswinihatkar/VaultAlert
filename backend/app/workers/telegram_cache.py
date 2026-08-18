"""
VaultAlert — In-Memory Snapshot & Event Cache
Stores the last 100 photos and 200 security events (from Telegram & Direct Hardware Camera Uploads).
"""
import uuid
import time
import hashlib
from collections import deque
from typing import Dict, Any, List

_photos: deque = deque(maxlen=100)   # List[Dict] — {file_id, url, caption, date}
_events: deque = deque(maxlen=200)   # List[Dict] — {id, time, message, photo_url}
_payloads: deque = deque(maxlen=20)  # List[Dict] — raw webhook payloads for diagnostics
_seen_messages: deque = deque(maxlen=500)  # message keys already processed (webhook dedupe)


def seen_message(key: str) -> bool:
    """Return True if this Telegram message key was already processed (and record it).

    Telegram delivers the same group message once per bot that has a webhook on the
    URL, so the webhook fires twice for one photo. Keying on chat:message_id:date
    lets us drop the duplicate delivery.
    """
    if key in _seen_messages:
        return True
    _seen_messages.append(key)
    return False


def add_payload(payload: Dict[str, Any]) -> None:
    """Store raw incoming webhook payload for live debugging."""
    _payloads.appendleft(payload)


def get_payloads() -> List[Dict[str, Any]]:
    """Return the last 20 raw webhook payloads."""
    return list(_payloads)


# If the same image arrives again within this window it's treated as a duplicate
# (e.g. userbot restarts and re-forwards, or two delivery paths carry one photo).
_DEDUPE_WINDOW_SECONDS = 60


def add_photo(entry: Dict[str, Any]) -> str:
    """Store a photo entry (Telegram or Direct Upload). Returns file_id.

    Dedupes by IMAGE CONTENT (not the file_id): direct uploads get a fresh random
    file_id every time, so identical photos would otherwise appear twice on the
    dashboard. We hash the image URL/bytes + caption and collapse re-sends of the
    same content that land within _DEDUPE_WINDOW_SECONDS, returning the existing id.
    """
    now = int(time.time())
    content_key = f"{entry.get('url', '')}|{entry.get('caption', '')}"
    content_hash = hashlib.sha256(content_key.encode()).hexdigest()

    for p in _photos:
        if p.get("_hash") == content_hash and (now - p.get("date", 0)) < _DEDUPE_WINDOW_SECONDS:
            return p["file_id"]  # duplicate content — reuse the original entry

    file_id = entry.get("file_id") or f"snap_{uuid.uuid4().hex[:12]}"
    entry["file_id"] = file_id
    entry["_hash"] = content_hash
    if "date" not in entry:
        entry["date"] = now

    if file_id not in {p["file_id"] for p in _photos}:
        _photos.appendleft(entry)
    return file_id


def add_event(entry: Dict[str, Any]) -> str:
    """Store a text event entry. Returns event id.

    Also content-deduped (message + photo_url) within _DEDUPE_WINDOW_SECONDS so a
    photo's paired event doesn't show twice when the same snapshot is re-forwarded.
    """
    now = int(time.time())
    content_key = f"{entry.get('message', '')}|{entry.get('photo_url', '')}"
    content_hash = hashlib.sha256(content_key.encode()).hexdigest()

    for e in _events:
        if e.get("_hash") == content_hash and (now - e.get("time", 0)) < _DEDUPE_WINDOW_SECONDS:
            return e["id"]  # duplicate content — reuse the original entry

    event_id = entry.get("id") or f"evt_{uuid.uuid4().hex[:12]}"
    entry["id"] = event_id
    entry["_hash"] = content_hash
    if "time" not in entry:
        entry["time"] = now

    if event_id not in {e["id"] for e in _events}:
        _events.appendleft(entry)
    return event_id


def _public(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Copy without internal bookkeeping fields (e.g. the dedupe _hash)."""
    return {k: v for k, v in entry.items() if not k.startswith("_")}


def get_photos() -> List[Dict[str, Any]]:
    """Return all cached photos, newest first."""
    return [_public(p) for p in sorted(_photos, key=lambda x: x.get("date", 0), reverse=True)]


def get_events() -> List[Dict[str, Any]]:
    """Return all cached events, newest first."""
    return [_public(e) for e in sorted(_events, key=lambda x: x.get("time", 0), reverse=True)]
