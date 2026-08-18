"""
VaultAlert — Direct Camera Ingestion Router
Allows hardware camera modules (e.g. ESP32-CAM) to upload JPEG snapshots directly over HTTP.
Instantly broadcasts incoming frames to frontend clients via WebSockets (< 100ms latency).

NOTE: This endpoint no longer forwards snapshots back to the Telegram group.
It used to call Telegram's sendPhoto after caching each snapshot, which created
an infinite loop with iot/userbot_reader.py: userbot forwards a Telegram photo
here -> this endpoint re-posts it to Telegram -> userbot sees that as a new
message -> forwards it here again -> forever. Snapshots that arrive here (from
the ESP32-CAM directly, or via userbot_reader.py) are now only cached and
broadcast to the dashboard, never re-sent to Telegram.
"""

import time
import base64
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from app.workers import telegram_cache
from app.workers.ws_manager import manager as ws_manager

router = APIRouter(tags=["Camera Ingestion"])


class Base64SnapshotPayload(BaseModel):
    device_id: Optional[str] = "esp32_cam_01"
    image_base64: str
    caption: Optional[str] = "Direct Camera Snapshot"
    event_type: Optional[str] = "camera_snapshot"


@router.post("/camera/snapshot")
async def upload_camera_snapshot(
    file: Optional[UploadFile] = File(None),
    device_id: str = Form("esp32_cam_01"),
    caption: str = Form("Direct Camera Snapshot"),
    event_type: str = Form("camera_snapshot"),
):
    """
    Direct HTTP upload for ESP32-CAM / Hardware Camera modules, and for the
    Telegram userbot relay. Accepts multipart JPEG file, caches it, and
    streams it to connected dashboard clients via WebSockets.
    """
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file provided in multipart payload.",
        )

    try:
        contents = await file.read()
        b64 = base64.b64encode(contents).decode("utf-8")
        mime = file.content_type or "image/jpeg"
        data_url = f"data:{mime};base64,{b64}"

        photo_entry = {
            "caption": caption,
            "url": data_url,
            "date": int(time.time()),
            "device_id": device_id,
        }
        file_id = telegram_cache.add_photo(photo_entry)

        event_entry = {
            "id": file_id,
            "message": f"PHOTO:{caption}",
            "time": int(time.time()),
            "photo_url": data_url,
        }
        telegram_cache.add_event(event_entry)

        # Broadcast via WebSocket
        broadcast_data = {
            "file_id": file_id,
            "url": data_url,
            "caption": caption,
            "event_type": event_type,
            "timestamp": int(time.time() * 1000),
            "device_id": device_id,
        }
        await ws_manager.broadcast_global("camera_snapshot", broadcast_data)

        logger.info(f"Direct camera snapshot received from {device_id}: cached and broadcasted.")
        return {
            "status": "success",
            "file_id": file_id,
            "message": "Snapshot cached and streamed via WebSocket.",
        }

    except Exception as e:
        logger.error(f"Error processing camera snapshot upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process image payload: {str(e)}",
        )


@router.post("/camera/snapshot-base64")
async def upload_camera_snapshot_base64(payload: Base64SnapshotPayload):
    """
    Base64 JSON endpoint for low-spec hardware microcontrollers.
    """
    try:
        b64_str = payload.image_base64
        if not b64_str.startswith("data:"):
            data_url = f"data:image/jpeg;base64,{b64_str}"
            mime = "image/jpeg"
            raw_bytes = base64.b64decode(b64_str)
        else:
            # Parse header
            header, base64_data = b64_str.split(",", 1)
            mime = header.split(";")[0].split(":")[1]
            raw_bytes = base64.b64decode(base64_data)
            data_url = b64_str

        photo_entry = {
            "caption": payload.caption or "Direct Camera Snapshot",
            "url": data_url,
            "date": int(time.time()),
            "device_id": payload.device_id,
        }
        file_id = telegram_cache.add_photo(photo_entry)

        event_entry = {
            "id": file_id,
            "message": f"PHOTO:{payload.caption}",
            "time": int(time.time()),
            "photo_url": data_url,
        }
        telegram_cache.add_event(event_entry)

        broadcast_data = {
            "file_id": file_id,
            "url": data_url,
            "caption": payload.caption,
            "event_type": payload.event_type,
            "timestamp": int(time.time() * 1000),
            "device_id": payload.device_id,
        }
        await ws_manager.broadcast_global("camera_snapshot", broadcast_data)

        return {
            "status": "success",
            "file_id": file_id,
            "message": "Snapshot cached and streamed via WebSocket.",
        }

    except Exception as e:
        logger.error(f"Error processing base64 snapshot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process base64 payload: {str(e)}",
        )
