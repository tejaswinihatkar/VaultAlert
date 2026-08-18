# Telegram Userbot Reader — setup (no hardware changes)

Logs into Telegram **as your own account**, silently watches the Vault Alert group,
and forwards every message + photo to the VaultAlert backend → dashboard. Because it's
a human account (not a bot), it CAN see the hardware bot's alerts. **Your ESP32 is not
touched at all.** It only reads + forwards; it never posts in Telegram.

---

## What YOU need to do (5 steps, ~10 min)

### 1. Get your Telegram API keys (free)
- Go to **https://my.telegram.org** → log in with your phone → **API development tools**.
- Create an app (any name, e.g. "VaultAlert"). Copy the two values:
  - **api_id** (a number)
  - **api_hash** (a long string)

### 2. Install the two libraries (on the laptop or wherever you'll run it)
```bash
pip install -r iot/requirements-userbot.txt
```

### 3. Set your keys as environment variables
Windows (PowerShell):
```powershell
setx TG_API_ID "123456"
setx TG_API_HASH "your_api_hash_here"
```
Mac/Linux:
```bash
export TG_API_ID=123456
export TG_API_HASH=your_api_hash_here
```
(The group ID `-1004493857137` and backend URL are already defaulted in the script.)

### 4. Run it once to log in
```bash
python iot/userbot_reader.py
```
- It will ask for **your phone number**, then the **OTP code** Telegram sends you
  (and your 2FA password if you have one). This happens **once** — it saves a
  `vaultalert_user.session` file so you never log in again.

### 5. Leave it running
- Keep that terminal open (laptop), **or** deploy it as an always-on service (below).
- Test: send any message/photo in the group → it appears on the dashboard in ~3s.
  This now includes the **hardware bot's** alerts.

---

## Keep it always-on (optional — so the laptop can be off)
Deploy as a **Render Background Worker**:
1. First run step 4 **locally** to generate `vaultalert_user.session`.
2. In Render → New → **Background Worker**, same repo, root `iot/`:
   - Build: `pip install -r requirements-userbot.txt`
   - Start: `python userbot_reader.py`
3. Add env vars `TG_API_ID`, `TG_API_HASH` in Render.
4. Upload the `vaultalert_user.session` file (Render "Secret Files") so it doesn't
   re-ask for OTP. **Never commit this file to git** (it's your login).

---

## Safety
- The `.session` file = your Telegram login. Keep it private; store as a secret, not in git.
- Read-only: the script never sends messages or posts in the group.
- Use your normal number, or a spare number if you prefer extra isolation.
- Telegram permits userbots for personal automation; a quiet single-group reader is low-risk.

## Test without touching hardware
Just type a message in the group yourself, or have any member send a photo — it flows
to the dashboard. Once the ESP32/CAM posts its alerts to the group as usual, those flow
too, automatically.
