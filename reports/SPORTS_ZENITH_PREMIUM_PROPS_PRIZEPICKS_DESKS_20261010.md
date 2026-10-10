# Sports Zenith — Premium Props and PrizePicks Editorial Research Desks
Date: 2026-10-10 (America/New_York)
Status: LIVE HTTPS VERIFIED / SOURCE-SAFE UI RELEASE / CODE VERSIONED IN GIT

## User goal
Continue the approved premium sports-magazine UI across Sports Zenith. The user specifically wants the existing Props and PrizePicks sections polished now, with Survivor revisited after this market UI work. Retain the $0 commitment, existing page routing, date-scoped source data, model proof restrictions and original full-size animated Ref identity.

## Exactly what changed
- Only `commercial_web/src/PropsV2Panel.jsx` changed for live behavior; one new target browser suite `commercial_web/premium-props-prizepicks-cover.e2e.spec.js` was added.
- Both `#props` and `#prizepicks` use a distinct premium **THE PLAYER LINEUP** / **THE PICK-EM DESK** header, deep ink `#173E52`, aqua/coral/gold top stripe, warm ivory count panels and compact mobile typography.
- The three header counters are calculated **per original lane**, not from global totals: `allRows.length` as **Saved lines**, `SHADOW_MONITOR` count as **Monitors**, and `SHADOW_PLAY` count as **Paper plays**. They have explicit unique `data-prop-cover-metric` IDs. Source snapshot at verification: **1,075 PROP** lines, **100 PRIZEPICKS** lines, **0 monitors** and **0 paper plays** in both. All 1,175 saved candidates are PASS states. These are NOT approved sports wagers and not verified live/available current price offers.
- The header explicitly says **Research only**. Props: dated player lines and independent prediction proof. PrizePicks: **Entry payout is not proven** and cannot be inferred from an individual leg. A context strip dynamically reflects the selected sport/NBA phase, without altering any filtered candidates.
- Original source-backed individual player cards now use warm magazine-paper `#FFF8ED` surfaces and consistent aqua Props / coral PrizePicks accents. The same model, player/line, last bookmaker price, future kickoff gate, fair/book-based and experimental probabilities, historical-form label, source/quality proof and `View evidence` detail stay intact.
- Original sport and NBA competition-phase filters, exact player search, recent-form watch, historical research toggle and Show 12 more control are preserved. Historical form remains explicitly research only, not an independent model forecast.
- Research-only monitor alert text now states that monitoring **does not clear** the independent prediction/payout gate; no sportsbook line, official bet, forward ledger, pricing model, eligibility state, account/Survivor data or statistical algorithm was changed.

## Test-first process
- New Playwright suite written and run BEFORE implementation. The existing site failed as expected because `[data-premium-player-cover]` did not exist.
- First preview: **3/4** passed; the 320px header was 355px tall due to a side badge squeezing the explanatory copy. We removed the redundant mobile badge (still visible on desktop), widened the text column and shortened the explanation. Retest: **4/4** passed.
- Actual preview cover measured **214px** on 320–430px phones, 226px at 768px, 235px at 1280px. This is a compact editorial cover, not a lengthy unsupported marketing block.
- Full JavaScript Node test suite: **314/314 PASS**.
- Frontend production `npm run build`: **PASS** with pre-existing nonfatal large-bundle warning.
- Combined production Playwright suite of 39 tests (new premium desks + original Odds, Market Board, Tools, Game Props, Mobile Betting, Parlays and Home theme): **39/39 PASS**.
- Actual production HTTPS Chrome at **320/390/430/768/1280/1920px**, each on `#props` and `#prizepicks`: **12/12 PASS**. All HTTP 200, correct source totals 1075/100 at inspection, 0 monitor/play counts, ink masthead, correct independent model/payout caveats, mobile cover under 236px, **zero horizontal overflow**, zero browser JS errors, and no leaked private user pool labels.
- Actual `/api/health` HTTP **200**; unauthenticated `/api/survivor/state` HTTP **401**.
- The last verified counts describe the saved model file at the time of this release; they can change when the collector updates. Zero qualified plays is not predictive evidence of future sports results.

## Provenance and limits
- SHA256-verified prechange original component backup at `.deploy_backups/zenith_premium_player_desks_before_20261010/` plus before-build `dist` backup; **same VPS only**, not an independently restored offsite recovery.
- Browser screenshots inspected in VPS-local `/tmp/zenith_player_desks_preview_20261010/`; not uploaded or published to users.
- All pre-existing unrelated dirty files were left unchanged and unstaged: `commercial_web/props-premium.e2e.spec.js`, `commercial_web/bet-meaning.e2e.spec.js`, `commercial_web/src/SurvivorPickEditor.jsx`.
- Physical iPhone Safari not directly tested; viewport checks were done in Chromium against actual production HTTPS.
- This completes **Props and PrizePicks premium visual presentation**, not the full Sports Zenith site and not a claim of improved model win rate. Some PrizePicks evidence cards remain a swipeable row beneath the first phone viewport by design, so no approved payout is implied.

## Next step — Survivor
The user specifically wants to return to Survivor **after** this upgrade. Verify the authenticated `ANNIE G 01` entry and Week 5 pool status, rules, eligible picks, and separate **external Scott OK** before discussing any official submission. An on-site save never substitutes for an organizer's acknowledgement; do not create/change/submit a pick without the user's explicit selection and approval.

## Repeat
```bash
cd /home/ubuntu/sports-hulk/commercial_web
node --test *.test.js
npm run build
npx --no-install playwright test premium-props-prizepicks-cover.e2e.spec.js mobile-betting-side-and-form.e2e.spec.js betting-odds-first.e2e.spec.js betting-market-board-premium.e2e.spec.js betting-tools.e2e.spec.js game-props.e2e.spec.js parlays-premium.e2e.spec.js home-theme-continuity.e2e.spec.js --workers=2 --reporter=dot
```
