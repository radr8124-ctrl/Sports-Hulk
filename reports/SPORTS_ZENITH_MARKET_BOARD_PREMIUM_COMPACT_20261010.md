# Sports Zenith — Compact Premium Market Board Release
Date: 2026-10-10 (America/New_York)
Status: **Live HTTPS verified; release source and test files versioned in project Git**
Repository: `/home/ubuntu/sports-hulk`
Existing website: `https://sportszenith.com/`

## User direction
The user wants premium sports-magazine design consistently across Sports Zenith and does not want to pay for AI APIs or restart any prior app work. They requested continued UI work, and a prior conversation turn appeared stuck before the Parlay layout was rechecked. This checkpoint resumes the existing committed Home work instead of restarting a new homepage or touching private Survivor records.

## Precisely scoped upgrade
- `commercial_web/src/App.jsx`, `BettingSubnav` only: premium dark ink `#173E52`, gold `#FFD36A`, coral and aqua accent stripe on a compact Market Board.
- Six original destinations: Best Bets, Props, PrizePicks, Tools, Parlays, Bet Lab; active section indicated with `aria-current=page`. On phones the tab row scrolls horizontally and the original selection scroll remains scoped to the navigation rail instead of unexpectedly moving the entire document.
- The compact, single-row 72px mobile Market Board replaced the first vertical 121px two-row candidate, a **49px reduction**, after a 390px Parlay test showed the important `ALL LEGS MUST WIN` rule below the fold. The final mobile market board uses 44px minimum touch targets.
- No change to actual sportsbook odds, pricing, model/fair probability, prop or PrizePicks projections, loss records, fantasy or Survivor data. The branded label `Proof before picks` is a promise of *evidence rules*, not proof of a bet advantage.
- `commercial_web/betting-market-board-premium.e2e.spec.js` adds 3 targeted end-to-end browser tests for the branded theme, 6 genuine route navigations, mobile horizontal swipe, safe layout and private-entry exclusion.

## Checks performed
- Test-driven RED: the earlier generic grey navigation did not have the premium Market Board container; new test failed. First premium version passed the 3 new browser checks, but **1 of 38 original combined tests** failed: `parlays-premium.e2e.spec.js` required the `ALL LEGS MUST WIN` rule in the first 844px phone viewport.
- Refined from the 121px/two-row header to a compact 72px/single-row editorial strip with original 44px interactive controls. Final targeted Parlay mobile test: **1/1 pass**.
- Complete combined browser suite `betting-market-board-premium.e2e.spec.js betting-odds-first.e2e.spec.js betting-tools.e2e.spec.js game-props.e2e.spec.js mobile-betting-side-and-form.e2e.spec.js parlays-premium.e2e.spec.js bet-lab.e2e.spec.js home-theme-continuity.e2e.spec.js`: **38/38 pass**.
- Node JavaScript suite: **314/314 passed**; Vite frontend production build **PASS** (existing nonfatal >500KB bundle-size warning).
- Real production HTTPS headless Chromium at **320, 390, 430, 768, 1280px** for `#best-bets`, `#props`, `#prizepicks` and `#parlays`: **20/20 pass**. Each HTTP 200, premium ink masthead, exactly six real tab controls, correct active route, no JS errors, no horizontal document overflow and no anonymous private Survivor entry name.
- Real `/api/health`: HTTP **200**; anonymous `/api/survivor/state`: **401**, confirming no public leak from this UI release.
- Scoped `commercial_web/src/App.jsx` source backup and prior built assets stored on **same VPS** under `.deploy_backups/zenith_premium_market_nav_before_20261010/`. This is not independently verified off-server disaster recovery.

## Follow-up
This release improves the **shared market navigation only**. The interior data panels remain large and retain some generic slate/white layout; *do not claim the whole betting suite is visually finished*. Continue with concise above-the-fold sport/proof summaries, progressive disclosure, premium research cards and controlled real-source terminology. Focus next on the evidence-heavy Bet/Props/PrizePicks/Parlays panels, followed by the Brain Record, Survivor and Fantasy/DFS premium UI batches, with screenshots and red/green tests. Preserve all official score/odds/model accountability records and private pool access.

## Repro commands
```bash
cd /home/ubuntu/sports-hulk/commercial_web
node --test *.test.js
npm run build
npx --no-install playwright test betting-market-board-premium.e2e.spec.js betting-odds-first.e2e.spec.js betting-tools.e2e.spec.js game-props.e2e.spec.js mobile-betting-side-and-form.e2e.spec.js parlays-premium.e2e.spec.js bet-lab.e2e.spec.js home-theme-continuity.e2e.spec.js --workers=2 --reporter=dot
```
