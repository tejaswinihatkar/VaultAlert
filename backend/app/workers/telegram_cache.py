"""
VaultAlert — In-Memory Telegram Cache
Stores the last 100 photos and 200 events received from Telegram.
The telegram_worker writes to this cache; the footage API reads from it.
"""
from collections import deque
from typing import Dict, Any, List

# Thread-safe deques acting as ring buffers
_photos: deque = deque(maxlen=100)   # List[Dict] — {file_id, url, caption, date}
_events: deque = deque(maxlen=200)   # List[Dict] — {id, time, message, photo_url}


def add_photo(entry: Dict[str, Any]) -> None:
    """Store a resolved photo entry (with direct URL)."""
    # Avoid duplicates by file_id
    existing_ids = {p["file_id"] for p in _photos}
    if entry["file_id"] not in existing_ids:
        _photos.appendleft(entry)


def add_event(entry: Dict[str, Any]) -> None:
    """Store a text event entry."""
    existing_ids = {e["id"] for e in _events}
    if entry["id"] not in existing_ids:
        _events.appendleft(entry)


def get_photos() -> List[Dict[str, Any]]:
    """Return all cached photos, newest first."""
    return sorted(list(_photos), key=lambda x: x.get("date", 0), reverse=True)


def get_events() -> List[Dict[str, Any]]:
    """Return all cached events, newest first."""
    return sorted(list(_events), key=lambda x: x.get("time", 0), reverse=True)
