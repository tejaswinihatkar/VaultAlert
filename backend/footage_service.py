import os
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from dotenv import load_dotenv

# Load env vars
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("footage_service")

app = FastAPI(title="VaultAlert Footage Service")

# Open CORS to allow direct requests from Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def get_telegram_updates(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not configured.")
        return []
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        resp = await client.get(url, timeout=10.0)
        if resp.status_code != 200:
            logger.error(f"Failed to get updates from Telegram API: {resp.status_code} - {resp.text}")
            return []
        data = resp.json()
        if not data.get("ok"):
            logger.error(f"Telegram API returned ok=False: {data}")
            return []
        return data.get("result", [])
    except Exception as e:
        logger.exception(f"Error calling Telegram getUpdates: {e}")
        return []

@app.get("/api/v1/footage", response_model=List[Dict[str, Any]])
async def get_footage():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return []

    try:
        target_chat_id = int(str(TELEGRAM_CHAT_ID).strip())
    except ValueError:
        logger.error(f"Invalid TELEGRAM_CHAT_ID format: {TELEGRAM_CHAT_ID}")
        return []

    try:
        async with httpx.AsyncClient() as client:
            updates = await get_telegram_updates(client)
            footage_list = []

            for update in updates:
                msg = update.get("message") or update.get("channel_post") or update.get("edited_message")
                if not msg:
                    continue

                msg_chat_id = msg.get("chat", {}).get("id")
                if msg_chat_id is not None and int(msg_chat_id) != target_chat_id:
                    continue

                photo_list = msg.get("photo")
                if not photo_list or len(photo_list) == 0:
                    continue

                largest_photo = photo_list[-1]
                file_id = largest_photo.get("file_id")
                if not file_id:
                    continue

                file_info_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
                file_resp = await client.get(file_info_url)
                if file_resp.status_code != 200:
                    continue

                file_data = file_resp.json()
                if not file_data.get("ok"):
                    continue

                file_path = file_data.get("result", {}).get("file_path")
                if not file_path:
                    continue

                photo_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                caption = msg.get("caption") or msg.get("text") or "Security Snapshot"
                date = msg.get("date")

                footage_list.append({
                    "file_id": file_id,
                    "url": photo_url,
                    "caption": caption,
                    "date": date
                })

            footage_list.sort(key=lambda x: x.get("date", 0), reverse=True)
            return footage_list
    except Exception as e:
        logger.exception(f"Error in get_footage: {e}")
        return []

@app.get("/api/v1/telegram-events", response_model=List[Dict[str, Any]])
async def get_telegram_events():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return []

    try:
        target_chat_id = int(str(TELEGRAM_CHAT_ID).strip())
    except ValueError:
        logger.error(f"Invalid TELEGRAM_CHAT_ID format: {TELEGRAM_CHAT_ID}")
        return []

    try:
        async with httpx.AsyncClient() as client:
            updates = await get_telegram_updates(client)
            events_list = []

            for update in updates:
                msg = update.get("message") or update.get("channel_post") or update.get("edited_message")
                if not msg:
                    continue

                msg_chat_id = msg.get("chat", {}).get("id")
                if msg_chat_id is not None and int(msg_chat_id) != target_chat_id:
                    continue

                message_text = msg.get("text") or msg.get("caption") or ""
                if not message_text:
                    continue

                # Check if it has an associated photo
                photo_url: Optional[str] = None
                photo_list = msg.get("photo")
                if photo_list and len(photo_list) > 0:
                    largest_photo = photo_list[-1]
                    file_id = largest_photo.get("file_id")
                    if file_id:
                        file_info_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
                        file_resp = await client.get(file_info_url)
                        if file_resp.status_code == 200:
                            file_data = file_resp.json()
                            file_path = file_data.get("result", {}).get("file_path")
                            if file_path:
                                photo_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

                events_list.append({
                    "id": str(update.get("update_id", msg.get("message_id"))),
                    "time": msg.get("date"),
                    "message": message_text,
                    "photo_url": photo_url
                })

            events_list.sort(key=lambda x: x.get("time", 0), reverse=True)
            return events_list
    except Exception as e:
        logger.exception(f"Error in get_telegram_events: {e}")
        return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("footage_service:app", host="0.0.0.0", port=8000, reload=True)
