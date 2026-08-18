# Flask face server (`app_face_recognition.py`) — forward camera photos to the dashboard

> You are running **`app_face_recognition.py`** (the dlib/face_recognition version),
> not `app.py`. It has the **same** `/recognize` and `/relay` routes, so the edits
> below apply identically — just to this file.

Send this to the teammate running the face server (the laptop at `10.194.218.222:5000`).
It already receives the ESP32-CAM's JPEG in `/recognize` and saves it as
`last_received.jpg` (line 235). We just forward that same photo to the VaultAlert
backend so it shows under **Live Security Footage** on the dashboard.

**No new dependency** — uses Python's built-in `urllib` (no need to touch their
`face_recognition`/opencv install).

---

## Change 1 — add this helper near the top (after the imports, ~line 50)

```python
import urllib.request, uuid  # add to the existing imports

VA_SNAPSHOT_URL = "https://vaultalert-api.onrender.com/api/v1/camera/snapshot"

def forward_to_vaultalert(jpeg_bytes, caption="Security Snapshot"):
    """Best-effort: push the captured frame to the VaultAlert dashboard."""
    try:
        boundary = uuid.uuid4().hex
        parts = []
        # caption field
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode())
        # file field
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"snapshot.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n".encode()
            + jpeg_bytes + b"\r\n"
        )
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
        req = urllib.request.Request(
            VA_SNAPSHOT_URL, data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        print("VaultAlert forward failed:", e)
```

## Change 2 — call it inside `/recognize`, right after the image is saved (line 235)

Find this line:
```python
    cv2.imwrite("last_received.jpg", frame)
```
Add **one line** right below it:
```python
    forward_to_vaultalert(img_bytes, "Live Camera Snapshot")
```

That's it. `img_bytes` is the raw JPEG the CAM already sent (line 204), so we forward
the original photo — every recognition attempt now also appears on the dashboard.

---

## Optional — also mirror the ESP32's text status messages

The main ESP32 posts short status strings (e.g. `PHOTO:...`, `System Locked!`) to the
relay mailbox `POST /relay/<topic>`. To surface those on the dashboard too, add one
line at the end of the existing `relay_post` function (after it stores the message):

```python
@app.route("/relay/<topic>", methods=["POST"])
def relay_post(topic):
    message = request.get_data(as_text=True)
    with relay_lock:
        relay_next_id[0] += 1
        msg_id = relay_next_id[0]
        relay_topics.setdefault(topic, deque(maxlen=50)).append((msg_id, message))

    # NEW: mirror hardware status text to the VaultAlert dashboard
    if topic == "vaultalert-resp" and message:
        try:
            data = urllib.parse.urlencode({"chat_id": "-1004493857137", "text": message}).encode()
            urllib.request.urlopen(
                "https://vaultalert-api.onrender.com/api/v1/integrations/telegram/"
                "bot8722120064:AAF6Yshc950N6CksWbLAeMa537zXG8h5ty0/sendMessage",
                data=data, timeout=10,
            ).read()
        except Exception as e:
            print("VaultAlert text forward failed:", e)

    return jsonify({"ok": True, "id": msg_id})
```
(Add `import urllib.parse` up top if not present.)

---

## How to test
Restart `app.py`, then run one face recognition (or enroll) on the ESP32-CAM.
The captured photo should appear on the dashboard's **Live Security Footage** grid
within ~3 seconds. Photos are the frames from `/recognize`; text alerts (if Change 3
added) show in the timeline.
