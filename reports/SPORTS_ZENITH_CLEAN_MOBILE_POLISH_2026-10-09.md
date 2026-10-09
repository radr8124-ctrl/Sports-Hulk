# Sports Zenith — Compact mobile clarity pass (October 9, 2026 UTC)

## User requirement
Make the **existing** Sports Zenith website look cleaner and easier to use, especially on iPhone. No rebrand, redesign, reminder, model refit, odds-promotion, betting advice, saved Survivor change or external pool submission.

## Changes actually deployed
- **Survivor:** Replaced an oversized dashboard-style introduction and three large metadata cards with a compact, full-width responsive title, status, and small summary chips. Removed narrow mobile text wrapping; verified at 390 px iPhone.
- **Survivor market review:** First **three** available source-verified market comparisons are immediately visible; remaining comparisons expand on demand. Cards show team, opponent, game time, market-only no-vig percentage, risk hint, and a relevant next-schedule signal. Full original sportsbook source, risk list and future fixtures remain available through a per-card expander. Archived quote banners and EXPIRED / NOT LIVE labels are retained.
- **Full raw Survivor decision board:** remains accessible via an explicit `Full Survivor research board` collapsed disclosure. It previously presented nine verbose cards even though model/market values were largely unavailable. Expanded board shows original research, values and reasons; missing strategy indices now display `—` instead of misleading `0.0`.
- **Bets:** Repetitive readiness text shortened. Primary NFL odds freshness warning remains visible in plain language. Exact source details and stale-moneyline counts remain readable with `View source verification details`; this does not turn research odds into verified bets.
- **Home:** Shortened oversized hero/title/intro without changing the brand, navigation, call-to-action behavior, or screen organization. Decorative metric tiles are hidden on mobile; they remain available at desktop widths. Bottom mobile tab navigation preserved.
- Changed public anonymous Survivor pick-count message to `Week 5 · sign in for pool rules` instead of the clumsy `see official rules pick(s)`.

## Visual and functional acceptance
- Actual live `https://sportszenith.com/#survivor` headless browser at **390 x 844** observed page body height about **8,054 px before**, **2,672 px after**. This is a snapshot-specific measurement: content changes over time. Initial top of market review near y=300 px after polish, first team card visible near the first fold rather than thousands of pixels below. Mobile header full-width, with no cramped single-word-per-line title.
- Home live mobile page height about **3,921 px before** vs **3,425 after**. Bets about **3,200 before** vs **3,112 after**. For all three, horizontal overflow **zero**.
- Actual mobile and desktop page still show source proof and verified market observations. All 13 Friday source-matched NFL game references remain market research only; full raw Survivor board is one tap away.
- **11 Playwright browser acceptance tests passed**, including three new Home/Survivor/Bets clean-mobile usability tests plus NFL original quote/Survivor expiry/future-games logic.
- **193 existing website Node tests passed**. **42 Survivor Python tests passed**. Production Vite build succeeded.
- Live HTTPS health endpoint reported HTTP 200. No change to production survivor saved pick state, winner ledger, private API access, sport models, survivor deadlines or sportsbook source pricing.

## Recovery and limits
- All three edited source files backed up before editing and independently SHA256-verified under `.deploy_backups/site_clarity_polish_before_20261009T2215Z`: `commercial_web/src/App.jsx`, `SurvivorMarketReview.jsx`, `BestBetsMarketCoverage.jsx` (and `styles.css` unchanged).
- **`commercial_web/src/SurvivorPickEditor.jsx` was already modified by another workflow and was NOT touched or included in this polish.** Scoped commit only of the three intended UI files, browser test and report.
- No screenshots were shared or exported to the user, and no claim of off-VPS full recovery. Authenticating and validating a real private Survivor account still requires the user signing in; only anonymous public views and simulated browser tests were inspected.
