# Sports Zenith — Full-Body Ref Safe News/Signal Sidelines
Date: 2026-10-10 (America/New_York)
Release status: **LIVE HTTPS VERIFIED, VERSIONED AFTER TESTING**
Baseline commit: `5421596`; production site: `https://sportszenith.com/`

## Why
The user's priority is a premium, unforgettable sports-magazine homepage with an original **full-size, animated, spontaneous Ref**, not a generic AI icon. The approved mobile scorecard side lane already protects real scores, but the fixed 113px Ref still obscured Signal Board buttons, News Desk article links, the Home Brain Record shortcut and some Learning Loop controls while scrolling.

## Bounded UX fix
This release gives the existing Ref an **in-page editorial sideline** when a phone visitor enters two Home sections: Signal Board and Zenith News Desk. Each mobile stage uses the accepted coral/ink/mint/gold palette and reserves 158px of vertical space with a dedicated **113px full-body animated Ref** to its right. Signal cards and source-linked newsroom articles remain full width and tappable below. It is the **same original Ref**, not a duplicated SVG mascot.

The existing `ZenithRefCompanion.jsx` uses a React portal into `data-ref-safe-stage="signals|news"` only under 768px on Home with its control panel closed. Opening manual controls temporarily undocks to the original fixed placement so the Flag, Strikeout, Whistle, Ask The Ref, Brain Record, move/shrink buttons and saved Surprise calls switch all remain usable. Closed controls redock into the page stage. The Ref's automatic animations are unchanged; they remain silent and follow reduced-motion/visibility preferences.

At 768px and wider, the unchanged fixed desktop Ref stays within the reserved editorial gutter; no second mascot is created. On the full News & Insights route (not the Home newsroom preview), the original Ref position is retained. Source selection, stories/attribution, original game scores and official probability/odds systems are unchanged.

## Precisely scoped files
- `commercial_web/src/HomeRefStage.jsx`: one reusable in-page stage, with distinct Signal and News copy, no private data.
- `commercial_web/src/App.jsx`: render mobile stage before the existing five-card Signal Board carousel.
- `commercial_web/src/HomeTopNews.jsx`: render matching mobile stage before the original sourced lead + 3 brief stories.
- `commercial_web/src/ZenithRefCompanion.jsx`: keep original animation/control state while conditionally portalling the Ref into a stage.
- `commercial_web/src/ZenithRefCompanion.css`: position the docked Ref within stage, without shrinking or forced sound.
- `commercial_web/ref-home-safe-stages.e2e.spec.js`: five new browser tests (320 and 390 phone, manual controls, desktop unchanged, deep-linked news fallback).

## Evidence, with honest limitations
- Measured BEFORE: phone Home fixed Ref overlapped multiple signal buttons and source-linked news article links. At 390px centered News scroll, visible article/link rectangles were intersected by thousands of pixels². Picks and Learning sections also had collisions and remain next-pass work.
- Test-first: new browser scenario failed as expected (missing `data-mobile-docked=true`); after implementation preview **5/5** PASS.
- Full production Node test suite: **314/314 PASS**.
- Production Vite build: **PASS**; existing nonfatal large-bundle advisory remains.
- Production browser checks: **44/44** PASS, covering this stage plus Home, News Desk, original mascot controls, scorecard lane, responsive navigation and News Hub.
- Serial automatic referee tests: **6/6** PASS; original silent surprises, motion opt-out and manual sound-only whistle remain.
- Actual HTTPS at 320, 360, 390, 430px: both mobile stages present, mascot width **113px**, overlap with their visible articles/links/buttons **0px²**, all pages HTTP 200, no horizontal document overflow, no browser JS errors or anonymous private-entry leakage.
- At 1280/1920 desktop, mascot width 150/170px, original fixed sideline, no visible article/action overlap. A raw 768px card-rectangle check initially appeared to overlap the Ref; we independently verified the third signal card is **clipped by the overflowing swipe rail**: raw overlap ~20kpx² but visible overlap **0px²**. This is a false positive, not a UI regression.
- Home /api/health remained HTTP 200; anonymous `/api/survivor/state` remained **401**.
- Scoped original source and frontend assets were backed up on the existing OVH VPS at `.deploy_backups/zenith_ref_safe_stages_before_20261010/` and source checksums verified. This is not independent off-server restore proof.

## Known remaining work
1. **The Ref can still overlay the Home Survivor/Fantasy/Brain shortcut cards and Learning Loop while browsing on a phone.** Include their safe treatment in the next Home premium first-fold/final layout pass; don't silently shrink/hide the original full-body figure.
2. The two extra in-page mobile stages increase vertical scrolling by about 316px total. That's an intentional non-overlap and recognizability tradeoff; follow-up Home polish should balance page length and first-view impact.
3. Signed-in Survivor UI, Bets/Props/PrizePicks, Brain Record, Fantasy/DFS and physical iPhone Safari testing are distinct future batches. No private picks or model weights were changed.
4. No Groq/Claude paid API calls, inference keys, subscriptions, betting actions or account data were touched.

## Repeat verification
```bash
cd /home/ubuntu/sports-hulk/commercial_web
node --test *.test.js
npm run build
npx --no-install playwright test ref-home-safe-stages.e2e.spec.js retro-wow-ref-cards.e2e.spec.js home-theme-continuity.e2e.spec.js home-news-desk.e2e.spec.js sports-news-hub.e2e.spec.js ref-mobile-sideline-scorecard.e2e.spec.js site-clean-mobile.e2e.spec.js command-center-home.e2e.spec.js --workers=2 --reporter=dot
npx --no-install playwright test ref-spontaneous-calls.e2e.spec.js --workers=1 --reporter=dot
```
