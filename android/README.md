# Android TWA — Build & Publish Guide

linguaalayam is published to the Play Store as a **Trusted Web Activity (TWA)** — a thin Android shell that loads the existing PWA at `linguaalayam.org`. No separate codebase; all features come from the web app.

---

## Prerequisites

Install these once:

| Tool | Version | Install |
|---|---|---|
| JDK 17 | LTS | `sudo apt install openjdk-17-jdk` (Ubuntu/Debian) |
| Android SDK | API 34 | Android Studio or `sdkmanager` (CLI) |
| Bubblewrap CLI | latest | `npm install -g @bubblewrap/cli` |
| Node.js | 18+ | via fnm: `fnm install 18` |

Set environment variables:
```bash
export ANDROID_HOME=~/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools
```

---

## First-time setup

### 1. Generate the Android project

From the `android/` directory:

```bash
cd android
bubblewrap init --manifest https://linguaalayam.org/static/manifest.json
```

Bubblewrap reads `twa-manifest.json` and generates the Android Studio project (Gradle files, `AndroidManifest.xml`, resource files). Accept prompts or pass `--no-chrome-os-only`.

### 2. Create a signing keystore

```bash
keytool -genkeypair -v \
  -keystore android-keystore.jks \
  -alias linguaalayam \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000
```

> **Keep `android-keystore.jks` and its passwords safe and backed up.** Losing the keystore means you can never update the app on Play Store. It is gitignored — never commit it.

### 3. Get the SHA-256 fingerprint

```bash
keytool -list -v -keystore android-keystore.jks -alias linguaalayam
```

Copy the `SHA256` fingerprint (format: `AA:BB:CC:...`).

### 4. Update `assetlinks.json` on the server

In `linguaalayam/api/app.py`, replace the placeholder:

```python
"sha256_cert_fingerprints": ["REPLACE_WITH_SHA256_FROM_PLAY_CONSOLE"]
```

with your actual fingerprint (colon-separated hex). Deploy.

Verify it's live:
```bash
curl https://linguaalayam.org/.well-known/assetlinks.json
```

### 5. Build the APK / AAB

```bash
bubblewrap build
```

This produces:
- `app-release-signed.apk` — sideload for testing
- `app-release-bundle.aab` — upload to Play Store (preferred)

---

## Play Store submission

### Create a Play Developer account

1. Go to [play.google.com/console](https://play.google.com/console)
2. Pay the one-time $25 registration fee
3. Complete the account details

### Create the app

1. **Create app** → App name: `linguaalayam` → Default language: Malayalam (ml-IN) → Free → Not primarily for children
2. Package name: **`org.linguaalayam.app`** — this is permanent, cannot be changed after first release

### Required assets (before submission)

| Asset | Size | Notes |
|---|---|---|
| Hi-res icon | 512×512 PNG | Use `linguaalayam/static/icon-512.png` |
| Feature graphic | 1024×500 PNG | Banner shown in Play Store listing — create separately |
| Screenshots | 2–8 per device type | Phone screenshots of the app in use |
| Short description | ≤80 chars | e.g. "Malayalam dictionary · EN↔ML · AI synthesis" |
| Full description | ≤4000 chars | Expand from the README intro |

**Screenshots**: Install the app on a device (sideload the APK), take screenshots with the device, upload. Or use Android Studio Emulator.

**Feature graphic**: A 1024×500 PNG banner — use the wordmark (`linguaalayam/static/logo-source.png`) composed on a purple background.

### Upload and release

1. **Production → Create new release → Upload .aab**
2. Fill release notes
3. Roll out (start at 10–20% for staged rollout)

---

## Updating the app

For content/feature changes: just deploy the web app. TWA loads live from the URL — no app update needed.

For app shell changes (new package version, icon, permissions):

```bash
# bump appVersionCode in twa-manifest.json (+1 each release)
# bump appVersionName to match the web app version
bubblewrap build
# upload new .aab to Play Console
```

---

## Troubleshooting

**Browser bar shows in the TWA** → `assetlinks.json` is wrong or not reachable. Check:
```bash
curl https://linguaalayam.org/.well-known/assetlinks.json
# SHA256 must match the signing key exactly
```

**"App not installed" on sideload** → Enable "Install unknown apps" in Android settings for your file manager.

**Bubblewrap can't find JDK** → Set `JAVA_HOME`:
```bash
export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which javac))))
```
