# Hardware → Dashboard fix (your actual ESP32 .ino)

## Why hardware alerts don't show on the dashboard
Your ESP32 sends alerts with the **UniversalTelegramBot** library:

```cpp
bot.sendMessage(CHAT_ID, msg, "");   // line 73
```

That library posts straight to `api.telegram.org`. Telegram then **never delivers
a bot's own message to any bot webhook** — so the backend never sees it (proven:
`/webhook-logs` shows only human messages). Manual/human messages work; bot ones don't.

## The fix — send the alert to the VaultAlert backend too (5-min edit)
You already use `HTTPClient` in this sketch (for the CAM relay), so just add one
tiny function and call it wherever you currently call `sendAlert(...)`. This posts
the alert text to the backend proxy, which shows it on the dashboard **and** relays
it to the Telegram group (so the group looks exactly the same as now).

### 1) Add this near the top (after `String CHAT_ID = ...;`, ~line 64)
```cpp
// VaultAlert backend proxy (shows alerts on the dashboard)
const char* VA_BACKEND = "https://vaultalert-api.onrender.com/api/v1/integrations/telegram";
```

### 2) Replace your `sendAlert(...)` function (lines 70–74) with:
```cpp
// Sends a Telegram alert AND mirrors it to the VaultAlert dashboard
void sendAlert(String title, String userName, String extra = "") {
  String msg = title + "\n\nUser: " + (userName.length() ? userName : "-");
  if (extra.length()) msg += "\n" + extra;

  // 1) existing Telegram send (keep it — group still gets the message)
  bot.sendMessage(CHAT_ID, msg, "");

  // 2) NEW: mirror to the VaultAlert backend so it appears on the dashboard
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClientSecure sclient;
    sclient.setInsecure();                 // Render uses a valid cert; skip pinning
    HTTPClient https;
    String url = String(VA_BACKEND) + "/bot" + BOTtoken + "/sendMessage";
    https.begin(sclient, url);
    https.addHeader("Content-Type", "application/x-www-form-urlencoded");
    String body = "chat_id=" + CHAT_ID + "&text=" + msg;
    https.POST(body);
    https.end();
  }
}
```

That's it. Every alert your hardware already sends (`sendAlert(...)`) now also lands
on the dashboard timeline in real time.

> The backend proxy accepts `application/x-www-form-urlencoded` (added in the latest
> deploy), so the simple `chat_id=...&text=...` body above works directly.

### Photos (optional, later)
Snapshots in your setup go through the **laptop Flask relay** (`10.194.218.222:5000`)
to the ESP32-CAM, not this sketch. To show photos on the dashboard too, have the CAM
board (or the Flask relay) POST the JPEG to:
```
POST https://vaultalert-api.onrender.com/api/v1/camera/snapshot
     multipart:  file=<jpeg>,  caption="Snapshot"
```
Text alerts (step 2 above) are enough to confirm end-to-end first.

## Test without hardware
```bash
python iot/fake_hardware.py --text "Unauthorized fingerprint!" --photo
```
Watch the dashboard update within ~3s.
