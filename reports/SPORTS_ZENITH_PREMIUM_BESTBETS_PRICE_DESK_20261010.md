# Sports Zenith — Premium Best Bets Price Desk
Date: 2026-10-10 (America/New_York)
Status: LIVE ON EXISTING WEBSITE / VALIDATED / VERSIONED GIT RELEASE

## Why
User wants premium "wow" quality throughout Sports Zenith, not only Home. The previous release (commit `17f8d25`) upgraded the shared compact Betting Market Board. This small UI-only batch elevates the **existing Best Bets content** while protecting its original bookmaker/source-led process, honest proof status, and one-screen price visibility.

## Exactly what changed
- `commercial_web/src/App.jsx`: The existing Best Bets page gets an original premium **THE PRICE DESK** ink `#173E52` editorial feature with coral/gold/aqua top stripe, warm ivory proof counters and a dynamic sport/market filter-context label.
- The three counters come **directly from `betting_v2_all_markets_current.json`**: `summary.candidates` (Reviewed), `summary.shadow_plays` (Shadow), and `summary.passes` (PASS/HOLD). The source snapshot inspected at release shows **33 evaluated / 0 shadow / 33 passes**. These are NOT actual wins, playable picks or independent predictive advantages. Until data arrives, an em dash is used rather than inventing zero.
- Prominent words: `Saved model research, not an approved bet.` Better observed bookmaker pricing is **not** proof of a separate model edge.
- Existing detailed research cards get warm magazine-paper surfaces, coral editorial accents and clear `RESEARCH` or paper-`SHADOW PLAY` status while retaining all source odds/quality, original BetMeaning explanations, conservative probability/EV details, and the expandable `View evidence` gate. No model weights, filtering logic, bookmaker feeds or actual bet transactions were changed.
- Selected market filter uses aqua/ink rather than generic slate. The original six sports, moneyline/spread/total choices, filter/reset behavior and sportsbook-first ordering are retained.
- Added stable `data-bestbets-premium-brief`, `data-proof-metric`, `data-bestbets-filter-context`, `data-premium-research-card` hooks to verify what is actually presented. They expose no user details.

## TDD and acceptance
- New `commercial_web/best-bets-premium-brief.e2e.spec.js` created **before** UI implementation. Its original test was RED on the absent premium evidence brief; GREEN after implementation. Two tests initially failed solely because reviewed and passes both displayed the valid source count `33`, producing an ambiguous selector. Production/test code now assigns unique metric identifiers and all **4/4** targeted Playwright tests PASS.
- Source/proof counters, original research-only warning, responsive first-screen bookmaker access, expanded evidence and exact sport/market filtering are asserted.
- Full JS Node regression `node --test *.test.js`: **314/314 PASS**.
- Production Vite frontend `npm run build`: **PASS** (existing nonfatal large-chunk warning).
- Combined betting Playwright regression (Best Bets, original odds, Market Board, Tools, game props, mobile betting side and form, Parlays, Bet Lab, Home theme): **42/42 PASS**.
- Real production HTTPS at **320, 390, 430, 768, 1280 and 1920 pixels**: **6/6 PASS**. Each has HTTP 200, ink premium Price Desk, original source-based stats `33/0/33` at release, an actual research-card evidence link, **zero sideways overflow, zero JS errors and zero anonymous personal-entry leakage**. The `Games, odds and better prices` heading remained in the first 844px viewport: measured y685 at 320px and y602 at 390px.
- HTTPS `/api/health` is HTTP **200**; anonymously accessed `/api/survivor/state` is HTTP **401**. No private Survivor/official pool submission performed.
- Backups of original `App.jsx` and compiled `dist` were preserved under `.deploy_backups/zenith_bestbets_premium_brief_before_20261010/` on the existing OVH VPS; original source SHA-256 readback was verified. This is same-server only, not proof of off-server recovery.

## What remains
- This is a **Best Bets premium visual pass, NOT the entire betting site launch or evidence/edge remediation**. Props, PrizePicks, Parlays and the remaining interior pages still need their own focused readability and premium editorial treatment. Do not conflate source snapshot timestamps with live executable offers; continue showing dated research/withheld claims.
- Physical iOS Safari device testing has not been independently performed; the responsive evidence is real HTTPS in Playwright Chromium.
- Existing unrelated dirty source files, especially `SurvivorPickEditor.jsx`, `bet-meaning.e2e.spec.js`, `props-premium.e2e.spec.js`, were neither edited nor staged.

## Reproduce
```bash
cd /home/ubuntu/sports-hulk/commercial_web
node --test *.test.js
npm run build
npx --no-install playwright test best-bets-premium-brief.e2e.spec.js betting-odds-first.e2e.spec.js betting-market-board-premium.e2e.spec.js betting-tools.e2e.spec.js game-props.e2e.spec.js mobile-betting-side-and-form.e2e.spec.js parlays-premium.e2e.spec.js bet-lab.e2e.spec.js home-theme-continuity.e2e.spec.js --workers=2 --reporter=dot
```
