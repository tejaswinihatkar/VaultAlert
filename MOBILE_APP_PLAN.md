# VaultAlert → Mobile App (APK) — Implementation Plan

Goal: ship the **existing** VaultAlert dashboard as a **real installable Android app** (`.apk`) that behaves like a native app on a phone. **No feature/logic changes** — same login, same ntfy SSE + WebSocket live feed, same footage polling, same UI. Only the *delivery/runtime* changes from a web page to an installed app.

---

## Decision: which approach

The frontend is a single-page Next.js 14 client component (`"use client"`) that talks to remote HTTP/WS/SSE endpoints. It has **no Next.js server features** (no server actions, no route handlers, no SSR data). That makes it a perfect fit for a **static export wrapped in Capacitor**.

**Chosen: Capacitor (WebView shell) over a static Next export.**

| Option | Verdict |
|---|---|
| **Capacitor + `next export`** ✅ | Keeps 100% of existing React/TSX/Tailwind logic byte-for-byte. Compiles the static build into a native Android project → real signed APK, real app icon, installs & launches like any app. Lowest risk, fastest, matches "keep logic as is". |
| React Native / Expo rewrite ❌ | Would require rewriting every component, timeline, framer-motion, tailwind. Violates "keep the logic as it is". Rejected. |
| PWA / "Add to Home Screen" ❌ | Not a real installable APK; can't be side-loaded/downloaded as a file. Rejected. |
| Trusted Web Activity (TWA) ❌ | Requires a hosted HTTPS origin + asset-links; more moving parts than Capacitor for the same result. Rejected. |

---

## Constraints to respect (do not break)

1. **`API_BASE` / `NTFY_TOPIC`** are read from `NEXT_PUBLIC_*` env at build time — must be baked into the export.
2. App calls **`http`/`ws`** as well as `https`/`wss` (`API_BASE.startsWith("https")` branch). Android 9+ blocks cleartext by default → must allow (or force HTTPS). Prod `.env.production` is already HTTPS, so default to HTTPS-only and only relax if a local backend is needed.
3. `localStorage` (`va_logged_in`) — works as-is inside the Capacitor WebView (persistent). No change.
4. `EventSource` (SSE) + `WebSocket` + `fetch` cross-origin to `ntfy.sh` and the API — these are remote origins, so **CORS is already handled server-side**; from a native WebView the origin is `https://localhost`/`capacitor://`, so confirm ntfy.sh + API allow it (ntfy.sh is public/permissive; API already serves the web app cross-origin).
5. `next/image` remote patterns → irrelevant after static export since footage uses a plain `<img>`. Fine.
6. Google Fonts (`Inter` via `next/font`) — `next/font` inlines/self-hosts at build, works in static export. Fine.

---

## Step-by-step

### Phase 1 — Make Next.js produce a static export
Files: `frontend/next.config.js`, `frontend/package.json`

1. Add to `next.config.js`:
   - `output: "export"`
   - `images: { unoptimized: true }` (static export can't use the image optimizer; app uses plain `<img>` anyway)
   - Drop the `async headers()` block — **not supported with `output: "export"`** (headers only apply to a running Next server). Security headers become irrelevant for a local WebView bundle.
2. Remove/neutralize `src/middleware.ts` — **middleware is incompatible with `output: "export"`** and it's already a no-op (`NextResponse.next()`). Delete the file.
3. Add scripts to `package.json`:
   - `"export": "next build"` (with `output: "export"`, `next build` emits `out/`)
4. Verify: `npm run export` → produces `frontend/out/index.html` + assets. Open `out/index.html` locally to sanity-check it renders the login screen.

### Phase 2 — Add Capacitor
Run in `frontend/`:
```
npm i -D @capacitor/cli
npm i @capacitor/core @capacitor/android
npx cap init VaultAlert io.vaultalert.app --web-dir=out
```
- `appId`: `io.vaultalert.app`  ·  `appName`: `VaultAlert`  ·  `webDir`: `out`
- Commit generated `capacitor.config.ts`.

### Phase 3 — Add the Android platform
```
npx cap add android
```
Creates `frontend/android/` (Gradle project). This is the native shell that becomes the APK.

### Phase 4 — Network / security config (Android)
File: `frontend/android/app/src/main/AndroidManifest.xml` (+ `res/xml/network_security_config.xml`)

- **Permissions:** add `<uses-permission android:name="android.permission.INTERNET"/>` (usually present).
- **Cleartext:** prod is HTTPS/WSS → keep `android:usesCleartextTraffic="false"` (secure default). Only if a dev wants to point `API_BASE` at a `http://` LAN backend, add a `network_security_config.xml` whitelisting that host and reference it from the manifest. Document both; default = HTTPS-only.
- Set app label/icon: `android:label="VaultAlert"`; generate launcher icons (Phase 6).

### Phase 5 — Build the web assets into the app
```
npm run export        # regenerate out/
npx cap sync android  # copy out/ into android/ + update native deps
```
Re-run this pair after **every** frontend change. (Optional convenience script: `"android:build": "next build && cap sync android"`.)

### Phase 6 — Branding (make it feel like a real app)
- App icon: VaultAlert uses a `Lock` glyph on an indigo→violet gradient. Produce a 1024×1024 PNG in that style, run through Capacitor asset tooling (`@capacitor/assets`) to emit all Android densities + splash.
- Splash screen: same gradient + lock, so cold-start looks intentional.
- Confirm `android:label="VaultAlert"` shows under the icon.

### Phase 7 — Produce the APK
Two paths:

**A. Debug APK (fastest, for side-loading/testing):**
```
cd frontend/android
./gradlew assembleDebug
# → android/app/build/outputs/apk/debug/app-debug.apk
```
Installable immediately via `adb install app-debug.apk` or by copying the file to a phone and tapping it (enable "Install unknown apps").

**B. Release APK (signed, for distribution):**
1. Generate a keystore: `keytool -genkey -v -keystore vaultalert.keystore -alias vaultalert -keyalg RSA -keysize 2048 -validity 10000`
2. Add signing config to `android/app/build.gradle` (reference keystore via `gradle.properties`, never commit the keystore/passwords).
3. `./gradlew assembleRelease` → `app-release.apk` (signed, installable, shareable).

### Phase 8 — Verify on a device/emulator
- Install APK on an Android emulator (or physical phone).
- Checklist (must match web behaviour exactly):
  1. App icon + name appear on the launcher; cold start shows splash → login screen.
  2. Login with `admin@vaultalert.io` / `admin` → dashboard renders.
  3. Re-open app → still logged in (localStorage persisted). Logout clears it.
  4. Live-connection pill turns green (SSE/WS reach ntfy.sh + API from the device).
  5. Incoming ntfy events append to the timeline in real time.
  6. Footage grid loads / shows the offline card if service down — same as web.
  7. Relative timestamps tick every second.

---

## Files touched (summary)

| File | Change |
|---|---|
| `frontend/next.config.js` | `output:"export"`, `images.unoptimized`, remove `headers()` |
| `frontend/src/middleware.ts` | **delete** (incompatible with export, already no-op) |
| `frontend/package.json` | add `export` + `android:build` scripts, Capacitor deps |
| `frontend/capacitor.config.ts` | **new** — Capacitor config (appId, webDir=out) |
| `frontend/android/**` | **new** — generated native Android project (the APK source) |
| `frontend/android/app/src/main/AndroidManifest.xml` | label/icon; cleartext posture |
| app icon / splash assets | **new** — VaultAlert branding |

**Zero changes** to `dashboard/page.tsx`, `providers.tsx`, `layout.tsx`, types, or any business logic.

---

## Prerequisites (build environment)
- Node.js (already used) · JDK 17 · Android SDK + `ANDROID_HOME` · Gradle (wrapper is generated, so no manual install).
- CI option: GitHub Actions with `android-actions/setup-android` to build the APK on every push and attach `app-debug.apk` / `app-release.apk` as an artifact the user can download.

## Risks / watch-items
1. **Cleartext block** — if anyone repoints `API_BASE` to `http://`, the app silently fails to connect. Mitigated: default HTTPS-only + documented `network_security_config.xml` escape hatch.
2. **CORS from `capacitor://localhost` origin** — verify ntfy.sh + the Render API accept the WebView origin; if the API is restrictive, add its origin to the backend CORS allowlist (backend change, outside the "keep logic" scope — flag to user first).
3. **Env at build time** — `NEXT_PUBLIC_*` are frozen into the export; rebuild + `cap sync` to change endpoints. No runtime env on device.
4. **Static export routing** — app is single-route (`/`), so no dynamic route pitfalls.

## Rough effort
Phases 1–5: ~1–2 hrs. Phase 6 branding: ~30 min. Phase 7 signing + APK: ~30 min. Phase 8 device verification: ~30 min.
