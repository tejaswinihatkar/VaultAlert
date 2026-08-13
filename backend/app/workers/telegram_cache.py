"""
VaultAlert — In-Memory Snapshot & Event Cache
Stores the last 100 photos and 200 security events (from Telegram & Direct Hardware Camera Uploads).
"""
import uuid
import time
from collections import deque
from typing import Dict, Any, List

_photos: deque = deque(maxlen=100)   # List[Dict] — {file_id, url, caption, date}
_events: deque = deque(maxlen=200)   # List[Dict] — {id, time, message, photo_url}
_payloads: deque = deque(maxlen=20)  # List[Dict] — raw webhook payloads for diagnostics


def add_payload(payload: Dict[str, Any]) -> None:
    """Store raw incoming webhook payload for live debugging."""
    _payloads.appendleft(payload)


def get_payloads() -> List[Dict[str, Any]]:
    """Return the last 20 raw webhook payloads."""
    return list(_payloads)


def add_photo(entry: Dict[str, Any]) -> str:
    """Store a photo entry (Telegram or Direct Upload). Returns file_id."""
    file_id = entry.get("file_id") or f"snap_{uuid.uuid4().hex[:12]}"
    entry["file_id"] = file_id
    if "date" not in entry:
        entry["date"] = int(time.time())

    existing_ids = {p["file_id"] for p in _photos}
    if file_id not in existing_ids:
        _photos.appendleft(entry)
    return file_id


def add_event(entry: Dict[str, Any]) -> str:
    """Store a text event entry. Returns event id."""
    event_id = entry.get("id") or f"evt_{uuid.uuid4().hex[:12]}"
    entry["id"] = event_id
    if "time" not in entry:
        entry["time"] = int(time.time())

    existing_ids = {e["id"] for e in _events}
    if event_id not in existing_ids:
        _events.appendleft(entry)
    return event_id


def get_photos() -> List[Dict[str, Any]]:
    """Return all cached photos, newest first."""
    return sorted(list(_photos), key=lambda x: x.get("date", 0), reverse=True)


def get_events() -> List[Dict[str, Any]]:
    """Return all cached events, newest first."""
    return sorted(list(_events), key=lambda x: x.get("time", 0), reverse=True)
