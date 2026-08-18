# Hardware not showing on dashboard — the fix (ESP32 firmware)

## Diagnosis (proven from live backend)
`GET /api/v1/integrations/telegram/webhook-logs` on the deployed backend shows the
last 10 updates Telegram delivered: **all `is_bot: false` (humans), 0 photos, 0 bot
messages.** Telegram **never delivers a bot's messages to another bot** — not even
as group admin / privacy-off. So the reader-bot webhook can *never* see the hardware
bot's alerts. That's why manual (human) messages appear but hardware alerts don't.

**No backend change can fix this** — the data physically never arrives.

## The fix: point the hardware at the backend proxy (one URL change)
The backend already exposes a drop-in Telegram proxy that caches + live-pushes to the
dashboard AND forwards to the Telegram group. It is verified working (sendPhoto → 200,
photo lands in `/footage` instantly).

Change the ESP32 base URL only:

| | URL |
|---|---|
| Before | `https://api.telegram.org/bot<TOKEN>/sendPhoto` |
| After  | `https://vaultalert-api.onrender.com/api/v1/integrations/telegram/bot<TOKEN>/sendPhoto` |

Same token, same `chat_id`, same `caption`, same multipart `photo` field. Nothing
else changes. `sendMessage` (text alerts) works the same way.

### Arduino / ESP32 snippet
```cpp
// BEFORE:
// String host = "https://api.telegram.org";

// AFTER — route through VaultAlert backend proxy:
String host = "https://vaultalert-api.onrender.com/api/v1/integrations/telegram";
String botToken = "8722120064:AAF6Yshc950N6CksWbLAeMa537zXG8h5ty0";
String chatId  = "-1004493857137";

// Photo upload (multipart) — path stays identical after the host swap:
String url = host + "/bot" + botToken + "/sendPhoto";
// http.begin(client, url);  ... POST multipart: chat_id, caption, photo=<jpeg bytes>

// Text alert:
String urlMsg = host + "/bot" + botToken + "/sendMessage";
// POST form: chat_id, text="Unauthorized fingerprint!"
```

> If the ESP32 library can't do HTTPS/TLS, the proxy also accepts plain uploads at
> `POST /api/v1/camera/snapshot` (multipart JPEG) or
> `POST /api/v1/camera/snapshot-base64` (JSON base64) — no Telegram formatting needed.

## Verify without hardware
```bash
python iot/fake_hardware.py --text "Unauthorized fingerprint!" --photo
```
Then watch the dashboard "Live Security Footage" grid update within ~3s.
