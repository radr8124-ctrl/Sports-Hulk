# Sports Zenith — NHL goalie source truth and college readiness
Audit: 2026-10-09 04:14–04:18 UTC. Research/paper mode; no real wagers. No previous frozen predictions, user picks, market odds or model coefficients edited by this batch.

## NHL source depth / integrity
- Original history: 1,592 distinct completed NHL games (2025–26: 1,528; 2026–27: 64), 57,427 player-game records, 6,367 goalie-game records, 3,184 team-game blocks.
- Exactly 2,820 team-game blocks carry one explicit starter=True official goalie flag, matching all 2,820 pre-repair derived goalie IDs. The other 364 blocks had no true flag (208 season 2025–26/type 1; 60 type 9; 96 season 2026–27/type 2).
- The old source builder substituted the highest postgame ice-time goalie and falsely labeled all 364 as historical starters. Corrected nhl_live/build_nhl_data.py to require a literal boolean true source flag; string values do not count.
- Repaired only the five starter-dependent columns for those 364 rows in team-game CSV and Parquet with scripts/nhl_starter_source_truth_reconcile.py. Original official goalie-game file hash unchanged; all other team-game fields, verified starter labels and row identities unchanged. CSV/Parquet checks passed and repeat audit found zero remaining mislabeled rows.
- Provenance receipt: reports/NHL_HISTORICAL_GOALIE_STARTER_SOURCE_AUDIT_LATEST.json; local pre-change backups: .deploy_backups/nhl_historical_starter_source_guard_20261009T041800Z and .deploy_backups/nhl_starter_derived_reconcile_20261009T041415Z. These are VPS-local, not offsite proof.
- Test: 40 NHL regression tests and 15 NFL/NHL source tests passed. Compile/diff whitespace checks passed.
- Current goalie listings: 14 players for four ESPN events; every listing is LISTED_NOT_CONFIRMED. No pregame starting-goalie confirmation inferred.
- Decision board: zero NHL PrizePicks finalists; 20 standard sportsbook prop finalists and one moneyline research finalist. No claim of validated betting edge.

## College football / basketball
- College football current 2026 game history: 397 completed games. Legacy research has 8,643 historical games, 8,052 nearest-neighbor walkforward cases and 3,948 games with old paired two-sided provider lines. Historical winner accuracy (70.65%) is not real priced/prospective profitability proof.
- CFB forward-shadow moneylines: 44 tracked, zero settled; 20 current research finalists. Probabilities/markets unproven.
- Current CFB scheduled refresh **failed with oom-kill at 04:12Z** after core, markets, fusion and decision building passed; last recorded stage was research grading. Automatic production refresh is not accepted until a normal timed run passes. The cause of memory pressure is not yet isolated.
- CBB: 6,300 completed 2025–26 games; 727 prior-season efficiency team baselines for upcoming 2026–27; no current 2026–27 completed games, no live betting decisions or finalists. Preseason efficiency numbers are not betting probabilities. Do not claim college PrizePicks/DFS data is fully supported.

## Saved paper performance, 2026-10-08 23:56–23:59 Eastern
- Game lines: 174 settled, 104 wins/70 losses (59.8%), +3.5499 units, +2.04% ROI, 44 independent games. Model and bookmaker Brier tie; status NOT_PROVEN.
- Props/pick'em research: 2,741 settled, 1,711 wins/1,030 losses (62.4%), -41.415 units, -1.52% ROI, 70 independent games. Book Brier 0.19550 vs model Brier 0.19963; status NOT_PROVEN.
- NBA totals +29.8718 simulated units on only 19 games; NBA spread -21.4595 units on only eight games. NHL sportsbook props -48.4650 units on 25 games.
- Confidence-label warning for separate audit: overall prop ROI is row-weighted -1.52%, while the reported game-block-aggregated lower confidence metric is -1.12%. These are different estimands; do not advertise the latter as the conventional bound for the displayed row-weighted ROI.
- All odds-related profitability is forward-shadow or a proxy, not real customer gambling returns.

## Next bounded batch
1. Investigate CFB grade-stage OOM and ordinary systemd timer stability.
2. Verify independently confirmed pregame NHL starters using exact time/game/player evidence, never historical starter guesswork.
3. Continue college true forward-market proof; CBB live decisions only after official current games.
4. Establish and test independent off-VPS recovery; current backups are local only.

## Verified scheduled-run follow-up (2026-10-09 04:20–04:22 UTC)
- The ordinary NHL scheduled refresh completed and retained zero NHL PrizePicks finalists, 20 sportsbook prop research finalists, one game-line research finalist. Its automatically rebuilt original/derived NHL team history was audited again: **2,820 explicit-source starter blocks, 364 source-unconfirmed blocks, zero inferred/falsely filled starters**. Pandas serializes some valid player IDs as a numeric string ending in .0; the reconciliation audit now normalizes only integer-equivalent IDs and still rejects truly conflicting IDs. **41 NHL and 15 NHL/NFL source regression tests passed.**
- CFB's exact failure was identified: **CFB_RECOMMENDATION_LEDGER.csv was 8,322,069,816 bytes**, and the prior grader attempted to load its entire contents as a pandas DataFrame on a 7.6 GiB RAM VPS without swap, resulting in an OOM kill. No prior records were deleted or rebuilt.
- A bounded fail-closed guard was placed in **cfb_live/decision/run_cfb_learning_postrefresh.sh**. When its ledger is more than 512 MiB, it archives current research normally, logs `OVERSIZE_SOURCE_LEDGER`, deliberately defers the RAM-intensive grader with return code 85, and leaves CFB current core, odds fusion and decision boards available. This is not a restored grading pipeline.
- The **ordinary 04:20:14 UTC CFB systemd timer completed with Result=success at 04:21:28**, after market fusion and decision brain succeeded (20 research finalists). Its separate learning log showed archive success, `GRADE DEFERRED: OVERSIZE_SOURCE_LEDGER bytes=8336145161`, and `CFB LEARNING INCOMPLETE`; the parent reported a learning warning but did not suffer another OOM. Ledger size still grows rapidly and the prior graded summary dates from October 6, so grading and incremental archive growth require a separate dedicated repair before claiming complete readiness.
- Site check at 04:22 UTC: HTTP 200. Independent offsite backup/recovery remains unverified. All forward shadow statistics remain unproven; no real betting profit implied.
