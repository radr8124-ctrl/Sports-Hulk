# Sports Zenith — accuracy-only reference audit: Rithmm, PropsBot and connected DraftKings
Reviewed October 9, 2026 America/New_York; source observations Oct 10 UTC.
**Scope:** Strengthen actual predictive accuracy and source quality. NO dashboard redesign, arbitrary new predictions, live model weight changes, new wagers or unlicensed third-party feed.

## Rithmm — useful, with an important caveat
- https://www.rithmm.com/post/how-rithmm-mlb-backtesting-works describes about 3,000 historical MLB games split *before strategy tuning*: half to calibrate recommendation windows; approximately 1,450 separate games to calculate published win rates/ROI. They explicitly state the halves sample across multiple seasons; this is a separation of tuning/testing, not necessarily chronological future replay. Sports Zenith should retain the stricter time-ordered evaluation, game-block separation and untouched future freeze.
- https://www.rithmm.com/ai-sports-betting describes pregame sport-specific model probabilities, opponent/context/player factors, line shopping, dynamic injury and market-movement downgrades, and Scout model explanations. Product claims do not verify proprietary model skill.

## PropsBot — useful source-method ideas, not verified profitability
- https://propsbot.ai/performance-methodology/ describes independent model ensembles, 5/10/20-game player trends, home/away and season baseline, snap/minutes/usage, opponent defensive efficiency and pace, goalie/pitcher matchups, quoted sportsbook lines and no-vig, and line movement.
- Its **self-reported** MLB July 12 study reports Brier 0.1903 vs Vegas 0.1947 over 101,881 graded props. No original complete pregame ledger/independent reproduction was performed here. Its high-hit-rate NFL category reports 74.4% wins on 22,210 selections **with -5.0% ROI**, whereas separately selected high-ROI NFL plays report 51.7% wins and +16.8% ROI. Source date September 29, 2026. These are not externally audited figures: win-rate increase and +EV are different goals.

## Connected DraftKings — live checks actually performed
- The user's connected DraftKings ChatGPT app responded successfully to ping, active 2026 NFL league/team configurations, current Raiders/Patriots team statistics, official-style Oct 4 Chiefs/Raiders final, and upcoming Oct 11 Raiders/Patriots fixture. Ping time 2026-10-10T02:25:08Z. Competition IDs: Oct 4 974082; Oct 11 974090. Raiders/Patriots kickoff 2026-10-11T17:00Z.
- This connected app supports informational game/team stats, schedules and results. It DOES NOT provide sportsbook wagering/account access or a licensing entitlement to stream bookmaker prices into the independent Zenith VPS. Treat these as independent scouting/corroboration, not price data.
- **Statistic definition mismatch:** DraftKings Oct 4 reports 218 Chiefs passing + 189 rushing = 407 total yards. NFL-hosted official team sites report **399 Chiefs TOTAL NET yards**, Raiders 437. Both match final KC 30, LV 27. Official:
  https://www.chiefs.com/game-day/2026/reg-week4/chiefs-at-raiders/
  https://www.raiders.com/game-day/2026/reg-week4/chiefs-at-raiders/
  The eight-yard difference is consistent with gross vs net after sacks; game score is not wrong. DO NOT merge under one feature heading.
- DK team offense points/game LV 28.2 and NE 14.8 do NOT arithmetically match *official scoreboard* four-week means (LV 28.75; NE 16.25). Their source window or meaning may differ and is not necessarily wrong. Official season scoreboard:
  https://www.raiders.com/schedule/2026/
  https://www.patriots.com/schedule/2026/
  The mismatch must be resolved before assuming this is a like-for-like model feature. Connected app result generated ~2026-10-10T02:25Z.

## Current Sports Zenith predictive proof — no inflated win percentage
- Existing NFL original nine-feature market-assisted model was trained on **2,465** distinct 2016–2024 games. Already inspected 2025 secondary diagnostic on **284** games: bookmaker no-vig Brier **0.210906373**, enhanced model **0.212617338**, i.e. the model was **0.001710965 WORSE**, with week-block bootstrap interval for advantage crossing zero. Source: reports/NFL_2016_2024_SCORE_FORM_HOLDOUT_2025_CHECKPOINT_20261009.json.
- The original 13 prospective 2026 NFL Week 5 model predictions are frozen before kickoff; 0 officially settled at review time. Don't use tomorrow's outcomes to retrain them after the fact.
- Existing game-market research forward audit: 198 settled selections across 52 games; all 198 copy sportsbook market reference probability. Not independent model advantage.
- Props V2 snapshot: **602** candidates, **zero** proven qualified plays, including 26 NFL prop and 14 NFL PrizePicks candidates. Source modeled probability unavailable/untrained for these.
- Original compiled NFL 2016–25 bookmaker price history lacks some original book-specific timestamps; replayable per-play EPA archive is not currently mounted. Sourcing that additional data and reproducing true as-of feature clocks matters more than adding odds calculators or more chatbot copy.

## Exact next accuracy experiment — preregister, don't promote
1. With original historic as-of data only, build rolling prior-only 5/10/20 player form, minutes/snaps, usage, opponent-adjusted matchup, lineup availability, location, travel, and price movement with explicit data and original timestamp definitions. Do not use current stats from AFTER a historical game's kickoff.
2. Freeze one independent model challenger with declared sport/market/feature list and untouched strictly later game-blocked holdout; evaluate Brier and log loss versus original same-book no-vig market. Evaluate 2026 *future* after kickoff only. Do NOT tune using the already inspected 2025 diagnostic then claim that same 2025 is out-of-sample.
3. Track actual win rate and real stake-weighted ROI independently. High win rate alone is not profitable value. Require original executable price and genuine bookmaker close before calculating true CLV.
4. If the independent challenger doesn't outperform the baseline, keep the original system unchanged. No fake 'locked in' model upgrade or invented accuracy %.

## Isolated source-admission gate implemented
- New pure code: intelligence_warehouse/historical_recovery/draftkings_stat_definition_gate.py. New unit tests: tests/test_draftkings_stat_definition_gate.py.
- Nine tests passed. They quarantine the DK 407 vs official 399 metric-definition mismatch, conflicting teams/scores/time, ambiguous offensive PPG, missing yardage, game-future time travel, unknown competition regime, and insufficient previous games for rolling windows.
- This is a **read-only potential source-admission gate NOT wired to the production training pipeline**. No DK data entered model weights or original feature files, and not one new wager or bet recommendation was placed.
- Concurrent model work is underway in other filenames; this scoped change must not overwrite their work. Independent off-VPS raw-data recovery remains unverified.
