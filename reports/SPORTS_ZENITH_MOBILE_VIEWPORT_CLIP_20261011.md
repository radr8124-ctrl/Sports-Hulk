# Sports Zenith — iPhone Page-Panning Containment (2026-10-11)

Scope: Existing website, narrow CSS guard only; no sportsbook, pool, data collector, private account, or prediction change.

## Reported issue
Actual iPhone Safari screenshot showed left-clipped Signal Board heading, game-day deck, Ref stage and **fixed bottom nav**. The page did not visibly move horizontally but was panned/zoomed beyond the usable screen. This is not an acceptable mobile experience. A real iOS visual-viewport zoom offset is one plausible component, **not proven** by desktop Chromium.

## Specific fix
`commercial_web/src/styles.css`: below 768px, page ancestor elements `html,body,#root` use `overflow-x:clip` instead of hidden horizontal scrolling containers, with `touch-action:auto` instead of forcing `pan-y pinch-zoom` on every ancestor. The intention is to prevent programmatic horizontal root panning while preserving horizontal game, news and signal card gestures and user pinch-to-zoom accessibility. Fixed bottom navigation remains full viewport width. Original premium design, full-size The Ref and source-verified game cards are unchanged.

## Tests and limits
- New test `commercial_web/mobile-viewport-clipping.e2e.spec.js` failed RED on original CSS (computed hidden vs clip), passed GREEN after scoped change, checks that all three root scrollLeft offsets remain zero, the signal carousel scrolls, document width matches viewport and fixed mobile nav spans viewport.
- Production Vite build: PASS (nonfatal existing large-chunk warning).
- Focused production browser regressions `mobile-viewport-clipping`, `ref-home-safe-stages`, `home-news-desk`, `retro-wow-ref-cards`: **17/17 PASS**.
- An unfiltered 22-case run passed 18 and failed 4; after the new test was corrected for a source-dependent *single* game tile, the remaining three were old brittle/dated conditions: an exact score-rail width expectation 167 rather than measured 157 at 320px, a first-game 820px threshold measured 831.8px, and an Oct9-time archived Survivor 13-options assertion unavailable in the current data. These remain separate, **not all fixed** by this release.
- Entire JS test suite ran 451; **448 PASS, 3 FAIL** in dated Survivor source/window/field-watch tests. These are not caused by this CSS-only change and remain to be triaged separately.
- Real device Safari zoom/pan position after a previous gesture **cannot be proven fixed by Chromium**. User should pinch zoom back to 100% and reload on iPhone to retest; if screenshot remains left-clipped, inspect Safari Web Inspector visualViewport.offsetLeft/scale and the specific device browser settings rather than suppressing zoom.
- Original CSS backed up and SHA verified on same VPS at `.deploy_backups/zenith_mobile_page_clip_20261011`. Off-VPS recovery not verified.

No native Safari device access, no paid services, no external pool submission or user-account change.

## Follow-up production verification
- Ran expanded mobile-viewport-clipping tests against https://sportszenith.com/ at 320, 360, 390 and 430 pixels: **4/4 PASS** on Chromium.
- Every width checks stationary html/body/root scroll offsets, no document horizontal overflow, full-width fixed bottom navigation, working signal and score rail scrolling, and working vertical page scrolling.
- Test now waits for the asynchronous score rail before checking scrolling and scrolls to the final snap position; immediate 60px scrolling could snap back to zero and an early score-feed arrival could replace the element being measured.
- No further production CSS changes in this follow-up. Published CSS checkpoint remains 4481fe8. Real iPhone Safari touch/zoom behavior remains unverified.

## Continued real-phone failure and gesture guard
- User supplied two 11:33 AM iPhone Safari screenshots after prior width checks. The fixed bottom navigation shifts with the content, so earlier width-only passes did not establish resolution. The paired screenshots are consistent with visual-viewport zoom/pan, but actual device scale/offset were not captured and cause remains an inference.
- Changed mobile root touch-action from auto to manipulation, retaining horizontal carousel gestures and pinch zoom while preventing double-tap smart zoom. WebKit reference: https://webkit.org/blog/5610/more-responsive-tapping-on-ios/. This does not reset an already enlarged Safari viewport.
- Mobile tests now run with isMobile and hasTouch; added gesture policy assertion failed on old CSS, passed after rebuild. Production build PASS; mobile containment and Ref-stage regressions 11/11 PASS in Chromium. Public browser inspected loaded CSS and verified the new mobile gesture declaration is published.
- Downloaded WebKit test binary, but runtime launch failed for missing system libraries. Dependency installation was blocked by the remote command policy; no Safari execution or actual device resolution claimed.
