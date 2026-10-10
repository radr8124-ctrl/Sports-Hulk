# Sports Zenith — Premium Home / Ref Full-Coverage Pass
Date: 2026-10-10 (America/New_York)
Status: LIVE ON HTTPS, VERIFIED AT MULTIPLE BREAKPOINTS
Code baseline: `647411e`; current existing application and premium cream/coral/aqua/gold design.

## Intent
The user requires a memorable premium first impression and the same sports-magazine craftsmanship across Sports Zenith. Preserve the original full-body animated Ref, real scores, honest source-based decisions, signed-in account boundaries, and the existing website. This small UI batch completes the mobile Ref sideline in the Home Fantasy/Survivor/Brain and Learning Loop areas; it is not a redesign of the backend or the betting model.

## What changed
- The original Home `HomeRefStage` now has two additional dedicated editions, `picks` (sage) and `learning` (warm gold), matching existing premium News (mint) and Signal Board (coral) stages.
- `ZenithRefCompanion.jsx` portals the **same** original Ref into these safe in-page booths on phones under 768px, without shrinking or cloning him. The original 113px mobile full-body SVG, spontaneous silent flag/strike/visual whistle gestures, reduced-motion preference, manual control panel, and optional user-initiated short whistle are preserved. Desktop continues the original 150–170px fixed sideline.
- The Home Survivor/Fantasy/Brain shortcuts are now three source-honest, individually clickable, horizontally swipeable magazine cards on phones, with a visible swipe cue and screen-reader group label. On desktop the three-card grid remains. The Brain Record title, actual official win/loss/pending accountability and Survivor sign-in gating remain exactly sourced, not recomputed or inflated.
- The Learning Loop remains fully interactive (Freeze, Grade, Review, Test and its original evidence button), now with a Ref safe stage above the learning controls. No official outcome data or prediction state is altered.
- Added stable `data-home-snapshot-card` hooks and updated one existing palette regression test to target the Fantasy card specifically rather than a brittle positional CSS selector. Avoided duplicate text accessible-name ambiguity by shortening the new sideline caption.
- This is **one homepage UI batch**. Main hero's first-fold cover typography and the betting, Brain Record, Survivor, Fantasy/DFS interior layout upgrades remain separate backlog items.

## Measured evidence
- TDD RED: new/refreshed browser cases failed against the original page at missing picks/learning mobile dock and missing swipe rail; GREEN after changes, **7/7** focused preview cases.
- Isolated preview Chromium mobile screenshot measurements at 390px: Home shortcut section approx **465px**, versus **664px** for the original stacked section in the earlier same-day homepage audit. This reduces that section by ~199px. The Learning Loop gains an in-flow safe stage, so this is **not a claim that overall Home length shrank**.
- Full `node --test *.test.js`: **314/314 passed**.
- Production Vite `npm run build`: successful, with existing nonfatal bundle-size warning.
- Production Playwright combined Home/Ref/News Desk/Scorecard/mobile navigation: **46/46 passed** after correcting one sideline-label accessibility ambiguity; automatic Ref browser tests run serially: **6/6 passed**.
- Actual production HTTPS Chromium at viewport widths **320, 360, 390, 430, 768, 1280 and 1920px**, across four Home zones each: all **28 validations passed** (HTTP 200, correct original figure dimensions, docked only on phones, zero phone Ref-vs-card collisions, zero horizontal document overflow, zero page JavaScript exceptions, zero anonymous private Survivor name leaks).
- At 768px, a raw offscreen signal/picks card rectangle intersects the fixed Ref because it extends beyond the scroll rail, **but the correctly clipped visible card area has 0px² intersection** in both signal and picks rails. No actual visible tablet card occlusion.
- Real `/api/health`: **200**; anonymously accessed `/api/survivor/state`: **401**, private entry boundary preserved.

## Quality and safety boundaries
- No separate new site, plugin subscription, Groq key, LLM inference calls, paid models, sportsbook bets, official Survivor submission, private account data access, data collector, injury claims, or edits to official prediction ledgers.
- The Ref's calls are decorative; they do not represent game penalties or recommended wagering actions. Automatic speech stays silent and reduced-motion-friendly. Physical Safari/iPhone hardware QA is not independently verified; the above responsive checks use real HTTPS in Chromium at iPhone-sized viewports.
- Existing unrelated dirty code (including `commercial_web/src/SurvivorPickEditor.jsx` and betting tests) was not modified, staged or reset.
- Original affected UI files and compiled frontend were saved within the **same VPS** before edit to `.deploy_backups/zenith_home_wow_picks_learning_before_20261010` and SHA-verified. Git archive readback after commit must be checked separately; **neither same-host backup nor a same-host Git commit establishes off-server recovery**.

## Follow-up, preserving the user's 'premium wow across the board' requirement
1. Finish premium magazine-cover first-screen differentiation on Home without moving real game scores out of the first phone viewport or cluttering the original animations.
2. Carry the visual foundation into the existing sports-intelligence interior: Best Bets / Props / PrizePicks / Parlays, Brain Record, authenticated Survivor entry, Fantasy/DFS, then cross-device final QA.
3. Prioritize actionable summary and progressive disclosure. Never present a `PASS` or `SHADOW` model row as a verified playable bet. Don't lose account-specific private entries or the existing versioned source data.

## Repeat
```bash
cd /home/ubuntu/sports-hulk/commercial_web
node --test *.test.js
npm run build
npx --no-install playwright test ref-home-safe-stages.e2e.spec.js ref-mobile-sideline-scorecard.e2e.spec.js retro-wow-ref-cards.e2e.spec.js home-theme-continuity.e2e.spec.js home-news-desk.e2e.spec.js sports-news-hub.e2e.spec.js site-clean-mobile.e2e.spec.js command-center-home.e2e.spec.js --workers=2 --reporter=dot
npx --no-install playwright test ref-spontaneous-calls.e2e.spec.js --workers=1 --reporter=dot
```
