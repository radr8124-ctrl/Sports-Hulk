# Sports Zenith — Full-Size Mobile Ref Sideline / Clear Scorecard Release
Date: 2026-10-10 (America/New_York)
Status: LIVE VERIFIED, SMALL-SCOPE UI RELEASE
Project: existing `/home/ubuntu/sports-hulk`, production `https://sportszenith.com`

## Why
The user wants Sports Zenith Home to give a memorable premium sports-magazine first impression and wants The Ref's full-body, occasional spontaneous sports gestures preserved. On the live 390px iPhone-sized page, the fixed 113px-wide original mascot previously intersected the first scorecard by approximately **5,333 square pixels**, hiding part of the original verified score/data. The assistant proposed a mobile "proper Ref stage" beside the scores, and the user approved continuing.

## Scoped UI change
- Only `commercial_web/src/HomeGameDayDeck.jsx` and one new browser test were changed for runtime/test behavior.
- The scorecard carousel has a mobile **Ref sideline**: first game cards/empty states occupy a dedicated left lane, while the decorative right lane reserves room visually for the original animated Ref. The stage is intentionally light-mint/ink/coral/gold and belongs to the existing approved 1980s sports magazine identity.
- At mobile viewports 320-767px, the scorecard lane and each card have a width of `calc(100vw - 153px)`. The 87px decorative right lane is noninteractive and `aria-hidden`, with no separate identity tracking, animations, odds, opinions or source information.
- The Ref **itself is unchanged**: retains full-body 113px figure on phones, spontaneous silent flag/strike/whistle performances, manual sound-only whistle, manual control panel, reduced-motion support, ability to shrink/move when user requests, and desktop 150px figure. We did NOT shrink the Ref, hide him on mobile, or replace the mascot with a generic chip.
- Swipe functionality and all existing five original score sources are preserved. Desktop 768+/1280 widths remain full-size horizontal/game-card grid as before. `GameTile` title abbreviation and source metadata remain unchanged.
- The same mobile side lane applies to verified no-games/source-failure/stale-feed messages, so the fixed Ref cannot cover those longer status descriptions in the first score section.
- Original headings, source timestamps, verified scores, six-sport navigation, Brain Record, News Desk, private Survivor and Fantasy integrations, model/odds/decision code remain untouched.

## Proof and TDD
- Original `HomeGameDayDeck.jsx` was SHA-verified before editing in `.deploy_backups/zenith_mobile_ref_score_sidestage_before_20261010/SOURCE_SHA256.txt`. The prior 28 MB compiled frontend `dist` was separately backed up under the same VPS-local backup directory ahead of production build.
- `ref-mobile-sideline-scorecard.e2e.spec.js` was written first and failed against pre-change Home due to missing stage. Four tests passed after minimal implementation; the added fifth test initially failed for a no-games state lacking the safe lane, then passed after sharing the RefSideline presentation between real game tiles and the honest empty states. A viewport resize timing flake was addressed using Playwright's observable width poll, not hidden by suppressing the assertion.
- **5/5 new Playwright browser tests PASS** for 320,360,390,430 mobile + 1280 desktop, synthetic public game scores, swipe, original Ref size, no overlay, honest no-games state, private identity exclusion.
- **314/314 Node JS suite PASS**.
- **33/33 combined Home, News Desk, scores, mobile and Ref regression Playwright tests PASS** (includes the new 5).
- **6/6 separate serial spontaneous Ref animation browser tests PASS**.
- Production Vite build wrote current frontend successfully (`npm run build` printed `BUILD_EXIT=0` and `built in 6.83s`; pre-existing nonfatal large-bundle warning).
- Real HTTPS Playwright at widths **320, 360, 390, 430, 768, 1280px** with a *synthetic browser-only injected public score fixture* (never written to website data) confirmed HTTP 200, exact first scorecard/Ref overlap **0 px²**, original phone Ref **113px** wide, original desktop Ref **150px**, every team-score element present, no horizontal page overflow, no JS errors, no anonymous private Survivor name leaked.
- Separate real HTTPS **without test fixtures** checked 390px and 1280px production: live page HTTP 200, five real sourced game tiles in the window, ESPN / MLB StatsAPI attribution present, premium News Desk retained, no JS errors and no overflow.
- `https://sportszenith.com/api/health` HTTP 200; anonymous `/api/survivor/state` HTTP **401**.

## What this does NOT claim
- The full-size floating Ref **may still cover other full-width Home content at certain mobile scroll positions**, notably the News Desk and decision cards. This release solves the specific score-carousel and no-games/source-status overlap without shrinking him; a separate layout pass should inspect each full-width destination or provide a context-aware safe stage. Do not claim the entire Home is immune to collisions yet.
- The fixed Ref's occasional flag/whistle/strike is theatrical, never a real penalty, verified injury, sports result or betting pick.
- Browser checks emulate phone and desktop viewports; physical iOS Safari / Android hardware QA remains outstanding.
- Backups and Git readback on OVH are **same-server only**. Off-server recovery has not been independently verified.

## Source and reproducibility
- Runtime code: `commercial_web/src/HomeGameDayDeck.jsx`.
- New e2e: `commercial_web/ref-mobile-sideline-scorecard.e2e.spec.js`.
- To rerun: `cd /home/ubuntu/sports-hulk/commercial_web && node --test *.test.js && npm run build && npx --no-install playwright test ref-mobile-sideline-scorecard.e2e.spec.js retro-wow-ref-cards.e2e.spec.js home-theme-continuity.e2e.spec.js home-news-desk.e2e.spec.js site-clean-mobile.e2e.spec.js command-center-home.e2e.spec.js score-game-center.e2e.spec.js --workers=2 --reporter=dot`. Run `ref-spontaneous-calls.e2e.spec.js` serially with `--workers=1` to avoid virtual clock/background-tab conflation.
- No secret keys, paid APIs, official bets, injury inference, survivor pick submissions or forward performance records modified.
