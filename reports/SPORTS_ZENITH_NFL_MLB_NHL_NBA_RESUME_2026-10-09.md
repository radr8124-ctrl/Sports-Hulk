# Sports Zenith — resumed NFL/MLB/NHL/NBA proof work, October 9, 2026

**Completed, not restarted.** The earlier MLB 14-day offseason lookback bug had already been fixed by the production refresh pipeline in commits `3641d9b` and `7e038d8` when this audit resumed. The postseason window is now **28 days**, while hitters still require **4 recent games** and pitchers **2**. No gate was lowered to force a selection.

## Second defect found and repaired

In the first pinned public sample, **246 MLB props/PrizePicks research records** existed. **18** shared a provider event UUID for the White Sox–Guardians postseason matchup but had a source kickoff **three hours different** from official MLB StatsAPI's scheduled first pitch. Keeping those apparently qualified entries on the site could confuse a user and make result identity unreliable.

We preregistered the strict clock test before changing source code, preserving file hashes in `reports/ZENITH_MLB_POSTSEASON_OFFICIAL_GAME_CLOCK_GATE_PREREG_2026-10-09.json` and local immutable source copies under `.deploy_backups/zenith_mlb_official_fixture_clock_gate_20261009T201600Z/`. The dedicated read-only verifier `intelligence_warehouse/betting_v2/mlb_official_fixture_clock.py` requires *all*: original explicit player ID/name/team, player team in the actual fixture, exact official away/home pair, unique official MLB `gamePk`, and provider start no more than **180 seconds** from the official MLB schedule. Malformed, missing, duplicated or conflicting events are excluded from the **current research feed only**; original provider snapshots, historical results and frozen forward ledgers are never rewritten. The public feed carries the official gamePk and postseason competition regime plus candid `official roster lineup NOT confirmed` and `executable odds NOT confirmed` labels.

The original pinned sample produced **228 accepted / 18 held**, agreeing with the preregistered audit. The **updated live feed snapshot** after normal MLB refresh and the strict game clock check contains **228 MLB props and 22 MLB PrizePicks research records** across **two uniquely verified official MLB games** (gamePk 849831 Division Series and 849809 League Championship Series). The 3-hour variants no longer appear. The source market probabilities and old bet decisions were not changed; all **250 remain PASS_NO_PROVEN_MODEL_EDGE**, with **zero verified PLAYs**. Testing the mobile and desktop website confirmed the MLB tabs and cards appear.

Source tests: **15 Python unit/regression checks passed**, including the original 28-day lookback tests and new fail-closed team/clock/doubleheader source tests. User-facing public website API healthy (HTTPS HTTP 200). Pre- and post-fix public feed, code, source registry and full audit reports have SHA-backed VPS-local copies. Off-server restoration **is not verified**.

## Remaining blockers and next sequence

**NFL:** Existing thirteen nine-feature frozen games, plus 26 unique player prop opportunities across 11 upcoming games (40 prop+PrizePicks feed records contain 14 overlaps), are preserved. The NFL source may still have stale original moneyline/spread prices, and our independent player-form experiment has not yet beaten the bookmaker on future graded games. Don't promote historical market-mirror predictions.

**NHL:** 290 current upstream PrizePicks decision records, but zero published candidates. They include **80 SOURCE_TIME_REVIEW**, **192 HIGH_JUICE_WATCH**, **10 GOALIE_START_REVIEW**, with the rest other review conditions. Next check the exact player, line, odds, provider kickoff and source-priced payout; don't remove the confirmed goalie or timestamp quality guards to make cards appear.

**NBA preseason:** Today's NBA is preseason; the current **166** NBA player prop and PrizePicks records are for upcoming **regular-season** games later in October. They are not evidence of current preseason props. Keep competition regimes and official season types separate before producing any preseason model.

**MLB remaining:** All live MLB prop/PrizePicks market probabilities still mirror the sportsbook references, and the 28-day trailing form uses some late regular-season games. NBA/NHL/MLB still need independent forward-calibrated models, quoted and source-verified prices, game-level outcome settlement, independent same-book Brier/EV evaluation, and appropriate separate PrizePicks payout economics. **No wagers or real PrizePicks entries were submitted.**

The official machine receipt, keyed by source SHA and constraints, is `reports/SPORTS_ZENITH_MLB_POSTSEASON_CLOCK_PROOF_AND_NEXT_LANES_2026-10-09.json`. No code, picks or datasets outside Sports Zenith were modified.
