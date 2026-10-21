# Sports Zenith Broadcast Homepage — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a substantially improved consumer-facing Sports Zenith homepage and 40–50px auto-scrolling broadcast ticker, as a tested preview on the existing React application without changing sports engines.

**Architecture:** Retain the current `commercial_web/src/App.jsx` app and route/state mechanism. Extract score normalization into a pure helper, replace the oversized home score cards with a nonduplicating six-feed ticker, and compose a premium homepage around existing panels. Preserve other pages and data behavior.

**Tech Stack:** React 18, Vite 6, Tailwind 3, lucide-react; Node built-in test runner for pure helpers.

**Spec:** `docs/superpowers/specs/2026-10-21-zenith-hybrid-destination-design.md`

## Global Constraints

- Existing `commercial_web` only; no replacement application, backend rewrites, extra cron jobs or service installations on shared VPS.
- Visual direction: midnight navy, champagne gold, teal status, bright/default editorial surface with Light/Dark/System design goal.
- Broadcast ticker must be ~40–50px high with continuous right-to-left scrolling, pause on hover/focus/touch, reduced-motion fallback, clickable game links, and no fake scores.
- Data comes from the existing NFL, MLB, NBA, NHL, CFB, CBB JSON feeds already consumed by `HomeScoreRail`.
- Existing `ScoresHub`, `ScoreGameCenter`, `PersonalStartSitPanel`, Props, Parlays, Survivor, DFS and auth remain operational.
- Production unchanged until desktop/mobile screenshots, build verification and owner signoff.
- No MagicPath dependency; Onlook/21st.dev can supply reference components but are not runtime prerequisites.

## Review Focus

1. No games or malformed feeds: render an honest compact empty state, never fictional matchups.
2. Null scores/pre-game: display start time/status rather than `0–0` or fabricated finals.
3. Extremely long team labels: preserve ticker height and avoid overflows.
4. Reduced-motion user: animation disabled and content remains keyboard/manual scrollable.
5. Clicking any game or navigation item: route still works, preserves existing authentication and Game Center behavior.

---

### Task 1: Normalize and test existing score data

**Files:**
- Create: `commercial_web/src/site/scoreTickerModel.mjs`
- Create: `commercial_web/tests/scoreTickerModel.test.mjs`
- Modify: `commercial_web/package.json` (add `test:unit` script only)

**Interfaces:**
- Produces: `normalizeTickerGames(feeds: Record<string, unknown>, limit?: number): Array<{id:string,league:string,away:string,home:string,awayScore:string,homeScore:string,status:string,startTime:string|null}>`.
- Feed keys `nfl`, `mlb`, `nba`, `nhl`, `cfb`, `cbb`. Prefer MLB `today_games` when present; other leagues `games`.
- `formatTickerLabel(game): string` formats status and available real score/time.

- [ ] Write tests `emptyFeedsReturnsEmpty`, `liveBeforeUpcomingBeforeFinal`, `pregameHasNoInventedScores`, `malformedGamesIgnored`, `mlbTodayGamesIncluded` asserting exact normalized fields.
- [ ] Run `node --test tests/scoreTickerModel.test.mjs`; expect failure before helper exists.
- [ ] Implement the pure normalization helpers (defensive shape check, preserve `event_id`/`gamePk`, stable fallback identity, status rank, max 12).
- [ ] Run `npm run test:unit`; expect all cases pass.
- [ ] Commit `test/scoreTickerModel.test.mjs`, `src/site/scoreTickerModel.mjs`, `package.json`.

### Task 2: Build the premium continuous ticker

**Files:**
- Create: `commercial_web/src/site/BroadcastTicker.jsx`
- Create: `commercial_web/src/site/broadcastTicker.css`

**Interfaces:**
- Consumes: `BroadcastTicker({games, onNavigate, onSelectGame})`, normalized games from Task 1.
- Produces: fixed Zenith Live label + two repeated sequences of real game entries (for seamless CSS marquee), keyboard accessible and reduced-motion fallback. Callback `onSelectGame(game)` optional; use `onNavigate('Scores')` when deep-link selection cannot be supported safely.

- [ ] Add focused render inspection/test harness assertions for empty list, real game labels, link/button semantics, and no duplicate tab stops in cloned decorative sequence.
- [ ] Verify red/initial render failure.
- [ ] Implement semantic HTML; one announced sequence, aria-hidden non-interactive duplicate; ticker 40–50px; hover, focus-within and pointer/touch pause; user controlled horizontal scroll under reduced motion.
- [ ] Run unit tests and `npm run build`; expect pass.
- [ ] Commit new component and CSS.

### Task 3: Replace oversized home rail without multiplying fetch jobs

**Files:**
- Modify: `commercial_web/src/App.jsx` (existing `HomeScoreRail`, header/home render)
- Modify: `commercial_web/src/styles.css` (scoped site theme tokens and layout)

**Interfaces:**
- Preserve `HomeScoreRail({onNavigate})` public API; reuse its six existing `useJsonEndpoint` results, pass normalized results to `BroadcastTicker`.
- No additional intervals, polling loops, or background tasks.

- [ ] Add regression check that `HomeScoreRail` still references exactly six existing score hooks, all six leagues, and the `Scores` navigation.
- [ ] Verify existing oversized 230px cards and default stacked home appearance against baseline screenshots.
- [ ] Replace the 230px card markup with ticker and move it to directly below header/navigation (not inside full-width padded editorial main).
- [ ] Refine existing hero, compact news, Top Picks and feature links to broadcast/editorial hierarchy; do not remove actual content or mark unapproved items approved.
- [ ] Run `npm run test:unit` and `npm run build` and inspect layout at 1440px, 768px, 390px.
- [ ] Commit homepage integration.

### Task 4: Visual, navigation and release validation

**Files:**
- Create: `docs/reports/zenith-home-phase1-qa.md`
- Potential targeted fixes to site files from prior tasks.

**Interfaces:** Runs locally, does not deploy.

- [ ] Capture desktop, tablet, and mobile screenshots; compare ticker height, no overflow, editorial hierarchy, scroll behavior and hover/focus pause.
- [ ] Confirm keyboard navigation, reduced motion, empty score feed, non-current score handling and Light/Dark/System expectations; if theme toggle is deferred, explicitly mark it incomplete and do not claim acceptance.
- [ ] Smoke-test navigation through Scores, Picks, Props, PrizePicks, Parlays, Fantasy, Survivor and research. Confirm authenticated components still render.
- [ ] Run `npm run test:unit`, `npm run build`, inspect diffs; record results, screenshot paths, branch SHA and rollback.
- [ ] Commit QA report and fixes; request owner visual approval before PR merge/deployment.

## Later phases (separate plans)

- Dedicated Fantasy Start/Sit premium side-by-side redesign using current `PersonalStartSitPanel` and verified projections.
- Editorial content management and premium membership conversion measurements.
- Data-quality remediation for stale parlays/props and approvals, independent of homepage UI.
