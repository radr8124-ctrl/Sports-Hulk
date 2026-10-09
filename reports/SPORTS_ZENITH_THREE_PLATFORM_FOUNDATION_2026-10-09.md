# Sports Zenith — Website + iPhone + Android foundation (Oct 9, 2026)

**Scope:** Preserve the existing website and sports betting/research brain. Create one shared React platform for a browser-installed site and separately packaged iOS/Android apps. **This is a development foundation, NOT App Store or Play Store launch.**

## Verified finished work

- Website PWA assets are served by the existing web server with HTTP 200: `/manifest.json` (`application/json`), `/pwa-init.js`, `/sw.js`, `/offline.html` and provisional Sports Zenith 192/512/maskable/Apple icon PNGs. The current live compiled HTML was modified **only in head metadata**; previous compiled CSS/JS references are byte-identical. Existing website, original accounts/Survivor/DFS/betting research remain served by the same code and API.
- PWA service worker installs **only from secure HTTPS/localhost** and caches only the offline fallback/icons, **never game scores, personal accounts, bookmaker odds, API calls, or historical user data**. No public TLS hostname was verified for the Sports Zenith site; browser PWA installation on a raw HTTP IP remains blocked.
- Existing mobile navigation and safe-area styling are retained. No separate model, API backend, wager service, or database was created.
- Capacitor **8.5.3** iOS and Android native project templates generated in `mobile/ios` and `mobile/android` (same **candidate** bundle ID `com.sportszenith.mobile`). App shell is designed to bundle the existing React UI locally rather than rely on a production `server.url` wrapper.
- Native-only fetch bridge `commercial_web/src/nativeApiBridge.js` preserves website same-origin behavior and maps `/api/` and root live JSON feeds to a verified HTTPS Zenith API on native platforms; it does not rewrite outside domains, React assets or the install manifest. Original Bearer headers and POST bodies are preserved.
- `mobile/scripts/build-web.mjs` fails closed unless a user-authorized HTTPS hostname actually answers the expected Sports Zenith `/api/health` with valid TLS and known score-source indicators. No real production mobile origin is embedded now.
- Native build safety strips all mutable packaged sports JSON data files before sync; a **test-only compiled React preview** showed **51 JSON runtime data files removed**. Thus a signed mobile binary must fetch fresh scores/odds rather than ship stale vendor quotes. Test build used a deliberately non-real `.invalid` hostname in a local staging directory only, **not packaged into either platform**.
- Android `allowBackup=false` reduces automatic backup of app WebView/account state; iOS retains default ATS HTTPS protections.
- Provisional artwork uses an SZ lettermark; final brand/icon and app-store bundle identifiers need user approval.

## Proven tests and backups

- 6 website PWA/native bridge Node tests passed (including testing the **actual** `pwa-init.js` script in simulated HTTP/HTTPS/native contexts), plus 7 Capacitor/source bundle safety Node tests.
- Existing Vite commercial website compiled in isolation; mobile-targeted React Vite bundle compiled with a test-only origin in isolation. Both builds passed, and current live website root/API assets remain healthy.
- Original pre-change source files and live `dist/index.html` are checksum-backed locally under `.deploy_backups/zenith_3platform_mobile_fnd_20261009T1115_PRECHANGE/`. Acceptance report: `reports/SPORTS_ZENITH_WEB_IOS_ANDROID_FOUNDATION_ACCEPTANCE_2026-10-09.json`.
- Immutable research model SHA-256s still match: original MLB Full16 `0cea5e38c94451cacbc1ff552276c5df7aa1e341296b127fd0cfa6a2d19c66a8` and original NFL nine-feature `b74351d24c0cf591624a74c8dc2d33f84ea34f1374c65d782219bc5d95b60602`. No sports picks/grades/betting rules altered.

## Release blockers (do not call apps launched)

1. **Confirm a public HTTPS domain** for Sports Zenith, with properly routed authenticated `/api/` and JSON feeds. The site currently appears to be served directly by an HTTP VPS/IP; independent external TLS hostname has not been verified. This is the next essential user detail.
2. Set verified backend origin, run native bundled UI release build and `npx cap sync`; test OTP sign-in, authentication, account preferences, saving Survivor picks, scores, real network failures and native CORS on physical iOS/Android devices.
3. Native compilations need macOS/Xcode for iOS or authorized macOS cloud build, Android SDK/Studio for Android. Both projects were generated here, **not compiled/signed** on the Ubuntu VPS.
4. Add legitimate native value (team-specific push notifications, favorite alerts, sensible device navigation), privacy disclosures, accessibility, store assets/screenshots, Crash/analytics opt-in and parental/age restrictions as applicable. Store reviewer accounts and developer signing need user action.
5. **Sports-betting and real-money fantasy/DFS App Store/Google Play legal review is mandatory.** The build currently adds no wager functions; do not assume that every current research, odds or contest feature may be approved for every territory. We will keep actual wagers and real-money transactions outside the initial native release unless specifically licensed and authorized.

The website is preserved, and each native platform uses one shared source tree. **Off-VPS disaster recovery remains unverified**; Git source versioning and VPS-local checks are not a substitute for independently restored backup.
