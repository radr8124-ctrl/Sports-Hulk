# Sports Zenith — Survivor Premium Command Desk

Date: 2026-10-10 America/New_York. Scope: existing production Sports Zenith, Week 5 Survivor presentation only.

## User instruction and preservation
The user explicitly declined to choose a Week 5 team yet and asked to continue building. No user pick or external pool submission was authorized. No new team was saved, no official pool row was imported or changed, and no frozen model prediction was modified.

## Deployed behavior
- Existing Survivor route now opens with a compact THE SURVIVOR DESK navy/ink, coral, gold, aqua editorial masthead consistent with Props/PrizePicks.
- Three privacy-scoped counts: private saved pick count vs rule-required count, already-used teams, genuinely qualified model shadow recommendations. Anonymous or unlinked viewers get em-dashes, not fabricated zeros or another member's data.
- The status reads NOT YET CHOSEN only for active linked entries with no private pick, SAVED IN ZENITH ONLY for saved Zenith picks, NOT ACTIVE for inactive entries, and SIGN IN / LINK ENTRY when not authorized.
- The latest official pool sheet is explicitly identified by its verified week; prior Week 4 counts cannot be presented as a live Week 5 field. No user-reported Dallas loss list is merged into the official pool.
- A shadow candidate is counted only after original rules are confirmed, the recommendation status is SHADOW_RECOMMENDATION_READY, and an actual team-bearing row is present. No candidate is shown as an independently proven winner. At the time of this release there are zero qualified picks.
- Short source-honesty copy on phones; explicit evidence, bookmaker/model uncertainty and external organizer warning on larger screens. Existing Saturday 6 PM ET deadline banner and private pick editor stay directly below the masthead and before the longer market/risk research. No call-to-action silently saves a pick.

## Testing
- Test-first: introduced `commercial_web/survivor-premium-cover.test.js` (7 cases; initially missing module as expected), plus `commercial_web/premium-survivor-cover.e2e.spec.js` (2 browser scenarios).
- After implementation: original Survivor guards plus new state tests 11/11 PASS.
- Full commercial JS suite: 321/321 PASS (original 314 plus seven new).
- Vite production build: PASS (existing non-fatal bundle-size warning).
- Survivor Playwright: 9/9 PASS after fixing narrow-screen header height and preserving anonymous sign-in guidance.
- Wider premium regression (new Survivor, prior Props/PrizePicks, Best Bets, Betting Odds/Market, Home, Mobile): 30/30 PASS.
- Actual production HTTPS Chromium responsive checks at 320, 390, 430, 768, 1280, 1920: 6/6 HTTP 200, ink background, correct unauthenticated state, zero horizontal overflow, zero JS errors, no private ANNIE G 01 label leaked. 390px screenshot inspected locally, not published.
- Live health HTTP 200; anonymous `/api/survivor/state` remains 401; unauthenticated POST `/api/survivor/save-picks` remains 401. No signed-in browser or real external pool submission was attempted.

## User's original entry and source integrity
Direct private readback at completion: ANNIE G 01 status ALIVE, pool Week 5, current picks [], current pick status OPEN, week_5 submitted=False; five prior teams exactly Chargers, 49ers, Bills, Chiefs, Vikings. Frozen Survivor model forward ledger SHA256 remains `3778bcff7ec9f87f29df739acf1f41dc75c4c7ddfc740c867b9078a51f426f55` during this batch. Private state JSON updates periodically from legitimate cron observation timestamps and therefore its raw SHA can change without a pick mutation; compare semantic pick/used-team fields rather than claiming byte identity.

## Change scope, recovery and caveats
Only `commercial_web/src/App.jsx`, new `commercial_web/src/SurvivorCommandCover.jsx`, new `commercial_web/survivor_cover_state.js`, two new focused tests and this report were changed/staged in this release. Existing unrelated dirty/untracked work left untouched. Pre-change App.jsx backup and matching SHA256 are stored on the SAME VPS at `.deploy_backups/zenith_premium_survivor_cover_before_20261010/` (source file SHA `9ca962c26aed3520fab184198d6cb6a11e2a31da2bd2297595b2d63f849589f8`). These do not demonstrate an offsite disaster recovery restore.

The previously reported 147 Dallas loser entries are user-provided observations pending official Week 5 pool-sheet reconciliation, NOT certified remaining-field counts. No original 147-row source was imported in this build. Original sportsbook source feed still lacks proven fresh paired primary odds/model advantages; this UI update does not repair that independent forecasting issue. Live signed-in iPhone Safari has not been tested; production responsive checks were Chromium.
