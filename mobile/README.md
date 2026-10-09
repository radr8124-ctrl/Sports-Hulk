# Sports Zenith: website, iOS, Android

**Native project foundation, not a shipped app.** Existing React/Vite frontend is packaged with Capacitor; original Sports Zenith servers, sports research, login, Survivor and fantasy data stay shared and unchanged.

- Website: original site remains primary and untouched until safe PWA promotion.
- PWA: install metadata and safe offline fallback staged. Requires a real public HTTPS domain; raw HTTP IP is insufficient.
- iPhone & Android: Capacitor projects reuse the existing React UI and route only Zenith `/api/` and root data JSON to an approved HTTPS backend. No new wagers or separate betting machine.
- No real iPhone/Android builds or store submissions are claimed. Signing, developer accounts, real-device OTP testing, push/deep links, app review, privacy and licensed-gambling/DFS checks remain outstanding.

## Build process

```sh
cd /home/ubuntu/sports-hulk/mobile
npm ci
npm run doctor
ZENITH_MOBILE_API_ORIGIN=https://YOUR-VERIFIED-ZENITH-DOMAIN.example npm run build:web
npm run native:sync
```

The hostname above is a **placeholder**, not a working URL. Native builds intentionally refuse missing or insecure API endpoints. This prevents publishing a disconnected app.

The release app bundles local React UI (no Capacitor `server.url` web wrapper) and uses the shared authorized HTTPS Zenith API. The build removes mutable sports snapshot JSON files from the native package; this prevents freezing yesterday's odds and scores inside an installed app. Real devices need HTTPS/certificate checks; login via Insforge OTP still requires platform testing. Only public client keys may be included; never include server-role credentials or betting provider API keys.

Capacitor 8 requires Node 22+. Android app compilation needs Android Studio and SDK (not installed on the VPS); iOS compilation/signing needs macOS + Xcode or an authorized macOS cloud build. Store accounts and signing require user approval/action. The current `com.sportszenith.mobile` is only a **candidate app identifier**; confirm before registering on either store.

Do not assume Apple's or Google's approval for a sports-betting/DFS-related app. An informational sports-analysis release with genuinely native features, legal review and proper disclosures is the intended first submission.
