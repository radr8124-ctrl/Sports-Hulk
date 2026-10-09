# Sports Zenith — website, iPhone & Android testing (October 9, 2026)

**Scope:** Non-destructive production browser and packaged mobile-source checks. Do not misread these as completed iPhone/Android app builds, authenticated device tests, real betting results, or app-store approval.

## Completed

- The public Cloudflare HTTPS domain, both apex and www HTTP→HTTPS redirects, valid certificate, API health, DNS, and persistent OVH tunnel all passed.
- **52/52 route-render checks passed** (13 pages × 320px simulated small iPhone, 390px simulated iPhone, 768px simulated tablet, 1280px Chromium desktop). No page JavaScript exceptions or horizontal document overflow. All routes were evaluated as anonymous visitors.
- The mobile sign-in modal opened. **No OTP sent and no account signed in.** Private Survivor pool data remained behind authentication; anonymous account preferences API returned HTTP 401. All tested product requests were read-only; 102 Cloudflare RUM telemetry requests were intercepted locally instead of being submitted.
- NFL, MLB, NBA, NHL, CFB and CBB scoreboard tabs all loaded; CBB honestly reported no games in the current window. Game Center UI opened for NFL, MLB, NBA, NHL, and CFB. The sampled games did not exercise independent remote detailed boxscore fetches; **full provider player/team boxscore completeness remains unverified**.
- The production Progressive Web App (PWA) service worker registered and cached only its offline page and icons, never player/account data, odds or scores. **Existing open screens originally remained visibly stale after the connection dropped**. This is fixed by `commercial_web/public/pwa-init.js`: on an actual simulated network-disconnect event the overlay masks the entire existing React app from sight and assistive technology, including while changing Survivor/other routes; when connection returns, a no-store `GET /api/health` is validated and the app reloads before revealing refreshed content.
- The revised network-loss guard was versioned as `/pwa-init.js?v=network-safety-2` because Cloudflare had a **four-hour cached copy** of the original plain script. Only the static script and this one script reference in live HTML changed; the production React JS/CSS asset references stayed exactly the same.
- Verified identical network-guard script bytes across **the live website, original source, native mobile `www/`, iOS project asset tree and Android project asset tree**. No new native binaries were signed.
- Six website/PWA/native API-bridge unit tests and seven mobile source/snapshot tests passed, plus the browser network-loss+reconnect smoke and the repeated 52-route browser matrix. Original frozen MLB Full16 and NFL nine-feature model input hashes remained unchanged.

## Outstanding before store release

1. **Real device testing** with iPhone Safari/WKWebView and Android WebView. Native CapacitorHttp is enabled in the source, but the physical native bridge has not yet been verified; the backend intentionally does not allow arbitrary browser CORS to authenticated endpoints.
2. Actual signed-in email OTP, account preferences, private Survivor entry upload/save/readback, authenticated fantasy roster, real-device alerts and navigation back handling. No authentic user data was changed in this audit.
3. Full official per-player boxscore source verification for a completed fixture with detailed data available, independent of the panel simply opening.
4. Test true app cold-start/offline operation on device. The browser connectivity simulation definitively tested **disconnection and recovery on an open page**, not the complete offline install-start lifecycle.
5. Android SDK/Java toolchain, iOS Xcode/macOS signing, native push notifications, store enrollment, privacy disclosures and sports research/DFS betting-compliance review.

## Reproducibility and rollback

- Browser matrix: `cd commercial_web && node zenith-live-cross-platform-smoke.cjs` (requires installed Playwright and Chromium); machine receipt `reports/SPORTS_ZENITH_PRODUCTION_READ_ONLY_BROWSER_SMOKE.json`.
- Disconnection/reconnection: `cd commercial_web && node zenith-live-network-loss-smoke.cjs`.
- Website unit tests: `node --test commercial_web/zenith-three-platform.test.js`.
- Mobile source tests: `npm --prefix mobile test`.
- Cloudflare gate: `bash scripts/verify_sports_zenith_cloudflare.sh --require-redirect`.
- Machine acceptance `reports/SPORTS_ZENITH_READONLY_MOBILE_PLATFORM_QA_ACCEPTANCE_2026-10-09.json`, including 52/52 route results, original frozen source checksum evidence, and first SHA of updated offline script.
- Original live HTML and previous static script are saved on the **same VPS** at `.deploy_backups/sports_zenith_cross_platform_offline_gate_20261009T1745Z/`. Rollback is an operator-controlled reversion of only those two files if necessary (no backend or models need modification). Independent **off-VPS restore remains unverified**.

**Outcome:** Website and browser-level mobile experience pass; the stale-score visibility issue from connection loss was repaired and regression-tested. Neither iOS nor Android device/notification/login/store-readiness is yet proven, and no predictive advantage or betting profit is claimed.
