# Sports Zenith — Survivor Risk Lens and Verified Full Player Box Scores
**Date:** 2026-10-10 (UTC), actual existing Sports Zenith production on OVH VPS.

## User-directed goals
Continue building the existing website, without new branding or a restart. Improve Survivor selection beyond choosing the largest spread, because the user finds Jacksonville inconsistent and prioritizes dependable decisions, lower crowd exposure and preserving two unused teams for Week 6. Restore actual player-by-player game box scores.

## Release A — Risk-first Survivor comparison (deployed)
- Scoped signed-in Survivor component `commercial_web/src/SurvivorRiskLens.jsx` between the private pick editor and current-week general candidates.
- Four distinct fields: source-backed risk flags, prior verified pick usage, future schedule/value, and an explicit zero-live-price/model-proof warning. Temporary user concern toggle **does not save, submit or alter pool picks**.
- Previously imported **Week 4** official pool metadata independently checked (364 entry rows, exactly 360 ACTIVE_OR_UNCONFIRMED; 4 eliminated excluded). Anonymous per-team previous usage for 360 entries: Jacksonville 102, Houston 1, Cincinnati 10, LA Rams 9, NE Patriots 9. These are teams USED PRIOR to Week 5, **not confirmed Week 5 popularity or expected picks**.
- New `survivor_pool_leverage.js` validates original official imported file name, provenance hash metadata, week, counts, CSV integrity, row statuses, and returns aggregate team counts; no participant names or entry IDs in the authenticated response. Missing, stale, malformed or mismatched input does not invent prior team ownership.
- Server's existing authenticated linked-entry `GET /api/survivor/state` gains `historical_pool_availability`; anonymous 401 unchanged. Only the linked entry receives this aggregate section, and model/pick state remains governed by original 2026 pool rules and separate sportsbook freshness.
- `commercial_web/survivor_pool_leverage.test.js`: 5/5; actual imported Week 4 readback: 360 valid rows.
- Related **pre-existing frozen Friday source replay test failures** (4) were brought current without editing historical sportsbook files: replay only the SHA-linked archived Friday fixture array at its actual Oct9 capture clock; Saturday primary feed must remain unavailable. Updated `nfl_research_source_display.test.js` and `survivor_source_review.test.js`.
- Dedicated private React SSR render with real 2026 readback proved correct totals, blank model edge, Week 6 double-pick banner, and no user identity leak. Not a real signed-in browser acceptance.

## Release B — Full official player box scores (deployed)
- ESPN summary `GET /api/boxscore` for NBA, NHL, CFB and CBB now independently verifies exact ESPN event ID, **both competition team IDs**, and the provider Final/Live state before using player stats; unknown/pregame are never called final.
- Source data maps full `boxscore.players[*].statistics[*].athletes[*]` by team and category, retains exact labels/values, excludes did-not-play player lines, refuses bad player IDs, misaligned stats, duplicate athletes and team conflicts. A missing statistic is not inferred as a zero.
- `verified_player_boxscore.js`: pure verification contract and `verified_player_boxscore.test.js` 8/8 including game identity, DNP, mismatched provider starts/teams, unverified pregame and category separation.
- `src/PlayerBoxScoreTables.jsx` adds expanding team/category player tables, sticky player names, horizontally scrollable stat columns, actual Final/Live labels, counts of DNPs and excluded incomplete rows. Integrated into `src/ScoreGameCenter.jsx`'s Box Score tab; existing separate NFL/MLB components untouched.
- Real *public official ESPN Final* provider readback, also independently live through Sports Zenith HTTPS `/api/boxscore`:
  - NBA 401898395 Dallas–Houston: 29 verified player-stat rows; nine provider-reported DNP rows excluded, zero malformed rows.
  - NHL 401892465 Seattle–Detroit: 39 player-stat rows across forwards, defense, goalies; zero malformed rows.
  - CFB 401858254 Florida State–Louisville: 74 player-category stat lines; one malformed/unverified row rejected. **Stat lines are not unique athletes** because passing/rushing etc can repeat.
- Three real official-source iPhone 390px headless browser checks displayed both teams' player tables, source final badge, with **zero document horizontal overflow** for NBA/NHL/CFB. Source scoreboard route was test-isolated per event but player-stat API responses came from the live production server, not test mocks.
- New deterministic browser `player-box-score.e2e.spec.js`: NBA viewport 390px and 1280px; real-rendered NBA test still covers same Game Center existing tabs.

## Regression and production proof
- Full `commercial_web/node --test *.test.js`: **257/257 passing** after legitimate archived quote replay fixes.
- `npm run build`: PASS, production Vite chunks created and served from original `commercial_web/dist`.
- Game Center targeted browser: **5/5 passing**; Survivor/mobile/Home browser earlier in same change set: **17/17 passing**.
- Systemd `sports-hulk-commercial.service`: restarted with user D-Bus and active; live `/api/health` 200; anonymous `/api/survivor/state` 401. Immediate 502 while the server restarted was transient; second live and local health readbacks 200.
- Private source files `nfl_live/derived/SURVIVOR_ENTRIES.json` and `intelligence_warehouse/survivor_accountability/SURVIVOR_V2_FORWARD_LEDGER.jsonl` retained same SHA-256 before/after both deployments. No pool picks saved/submitted, no real wager, model correction or DFS lineup placed.
- Pre-edits SHA-verified **local VPS** copies at `.deploy_backups/survivor_risk_lens_before_20261010T0800Z/` and `.deploy_backups/zenith_full_player_box_before_20261010T0820Z/`.
- Version control should stage ONLY reviewed source/test/report files due separate other-project dirty working tree. Off-server raw-data restoration is **NOT VERIFIED**. A Git commit on VPS is not proof of offsite recovery.

## Limitations / next phase
- No authenticated real-user private browser login/OTP or third-party official pool acknowledgement was performed. The user must still pick and externally text/email the organizer and receive an "OK" response before Saturday 6 PM ET.
- No verified new live sportsbook primary quotes or proven independent Survivor outcome advantage. Risk flags are existing source observations, not consistency-trained statistical claims.
- Real native iPhone Safari and Android device builds/login remain unverified; Playwright Chromium 390px simulation is not a signed native device test.
- ESPN provider may temporarily fail or omit player stats in a new Final game; show an honest unavailable state rather than a synthetic box score.
- CBB table parser implemented but no relevant actual completed CBB game was available in this release's source window.

## Release C — Live box-score refresh and official-source protection
- `commercial_web/boxscore_source_cache.js` adds bounded (150 max, adjustable up to 500) in-process, per-game in-flight request deduplication. Cached source retains *original* `generated_at` and cannot become a falsely new live observation. TTL is 45 sec LIVE, five minutes FINAL, two minutes PREGAME, 30 sec UNKNOWN. Failed/upstream-invalid reads never stay cached.
- Boxscore HTTP route now uses this wrapper and a bounded 80-request/min per-IP throttle. Upstream ESPN event/participant/state validators remain mandatory before adding verified player rows. No paid odds source usage.
- While an official game is live, and *only while Game Center's Box Score tab is mounted*, client refreshes at 60-sec intervals. Hidden tabs skip polling; changing tabs cancels the interval; returning to visible checks immediately. The old verified data stays visible during refresh. A failed refresh displays a stale-data warning and source checked time rather than blanking it or pretending it updated.
- Six pure cache tests verified simultaneous request dedup, source expiry across all stages, request rejection, bounded memory and retry after source errors. The full `node --test *.test.js` suite is **263/263 PASS**.
- Game Center targeted tests: **6/6 PASS**, including a Playwright clock-accelerated live game with stats 15→25 after 60 sec, subsequent HTTP 503 with retained last verified 25 and visible error, and zero polling after leaving the box-score tab.
- Production Vite build PASS, systemd restarted and active; local & HTTPS /api/health both HTTP 200, anonymous private Survivor HTTP 401, unchanged checksums for private Survivor entries and forward ledger.
- Local pre-change SHA verified at `.deploy_backups/zenith_live_player_refresh_before_20261010T0830Z/`. No signed-in real user browser or native iPhone acceptance and no off-VPS full restore verified.
