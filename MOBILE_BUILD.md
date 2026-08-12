# VaultAlert — Android APK build

The mobile app is the **same** VaultAlert dashboard, bundled into a native Android
WebView shell with [Capacitor](https://capacitorjs.com). No app logic changed — only
the delivery: a real installable `.apk`.

## Prerequisites
- Node.js 20+
- JDK 17
- Android SDK (platform `android-34`, build-tools `34.0.0`, platform-tools)
- `ANDROID_HOME` / `sdk.dir` pointing at the SDK

## Build steps (from `frontend/`)
```bash
# 1. Static-export the Next.js app  ->  frontend/out/
npm run export

# 2. Copy the export into the native Android project
npx cap sync android

# 3. Build the APK
cd android
echo "sdk.dir=$ANDROID_HOME" > local.properties     # once
./gradlew assembleDebug
```
Output: `frontend/android/app/build/outputs/apk/debug/app-debug.apk`

Shortcut for steps 1–2: `npm run android:build`.

## Install on a phone
- Copy `app-debug.apk` to the device and tap it (enable *Install unknown apps*), **or**
- `adb install app-debug.apk`

## Signed release APK (for distribution)
```bash
keytool -genkey -v -keystore vaultalert.keystore -alias vaultalert \
  -keyalg RSA -keysize 2048 -validity 10000
# add a signingConfig referencing the keystore in android/app/build.gradle
cd android && ./gradlew assembleRelease
```
Keep the keystore + passwords out of git.

## Config / endpoints
API + ntfy topic are read from `frontend/.env.production` (`NEXT_PUBLIC_API_BASE`,
`NEXT_PUBLIC_NTFY_TOPIC`) at **build time** and frozen into the APK. To change them,
edit the env, then re-run `npm run android:build` + `./gradlew assembleDebug`.

Prod endpoints are HTTPS/WSS, so cleartext traffic stays **disabled** (secure default).
If you point `API_BASE` at an `http://` LAN backend, add a
`res/xml/network_security_config.xml` whitelisting that host and reference it from
`AndroidManifest.xml`.

## Notes
- `next.config.js` sets `output:"export"` + `images.unoptimized`; the no-op
  `middleware.ts` and `headers()` were removed (unsupported by static export).
- Build worker parallelism is capped (`experimental.cpus`) to fit constrained
  containers; harmless on a normal dev machine.
