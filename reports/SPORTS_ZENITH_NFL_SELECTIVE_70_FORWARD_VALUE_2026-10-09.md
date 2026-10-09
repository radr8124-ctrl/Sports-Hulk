# Sports Zenith — NFL 70% forward-selection/value checkpoint

2026-10-09 UTC. Research only; no approved plays, real wagers, or proven profitability.

## Pre-registered criteria and source

Original parent selection registration: reports/ZENITH_70_PERCENT_FORWARD_TARGET_PREREG_2026-10-09.json, created before all games. The NFL-specific registration was created October 9 at 06:19:35 UTC in reports/ZENITH_NFL_70_TRUE_FORWARD_PRICE_EXPERIMENT_PREREG_2026-10-09.json. Original thirteen ESPN-event NFL forecasts had previously been genuinely frozen at approximately 01:41:55 UTC.

The first original source SHA-256 remains b74351d24c0cf591624a74c8dc2d33f84ea34f1374c65d782219bc5d95b60602. No earlier game results were used in the nine-feature model. Its 2025 diagnostic was worse than the sportsbook baseline.

The fixed research-only screen chooses at most one side per independently identified game, requiring ALL: original model chosen-team win probability at least 70%, advantage at least 3 percentage points over the original same-book no-vig price, paper EV at least +3% against the original source American odds, and a bookmaker quote captured after original team context and within five minutes of prediction freeze, before game start.

## Actual future research results (not selected winning bets)

- Original source-time future NFL games evaluated: **13**.
- Probability at least 70%: **4**.
- Book probability advantage at least three percentage points: **1**.
- Quoted-price paper EV at least three percent: **0**.
- **Passed every fixed research filter: 0**.
- Permanently recorded ABSTAIN decisions: **13**.
- Independent official Final outcomes known: **0**.
- New real-money NFL selections: **0**.

Blockers can overlap: 12 insufficient model-vs-book edge, 13 insufficient price-EV, 9 below 70% probability. Maximum original quote age at model freeze was 147.4 seconds. All original model and price coefficients stayed unchanged. The fixed screen did not invent a bet to chase a hit-rate goal.

Research-only append ledger: intelligence_warehouse/selective_forward/NFL_70_FIXED_VALUE_SHADOW.jsonl. Initial 13-row SHA-256 **1f9b4410644217ffdc5fb26dfe44a801d3a4cd08153dbe8bea83b91da14393a6**. The file is privately excluded from Git. Each row keeps the original source game, home/away, model probability, no-vig reference, source bookmaker/price, timestamp, pass/fail reason and whether independently executable (currently false).

## Source-verified future grading and automation

Research implementation: intelligence_warehouse/selective_forward/nfl_70_forward_evidence.py. Selection capture requires original first-13 model source SHA, before-kickoff registration and quote chronology, source-priced moneyline pair verification, and immutable append-only per-game records. Past/kicked-off events cannot be retrospectively captured as new forward selections.

Later official results are accepted only from the existing independent first ESPN Final source/scorer, with original event, teams, frozen model SHA/time, postgame verified final score and source hash. Source-quote paper units are NEVER real sportsbook settlement or executed-bet ROI.

Research-only capture/grade was added after the original official Final source and scorer in nfl_live/decision/run_nfl_learning_postrefresh.sh, the existing hourly systemd NFL refresh post-step. It uses governed scripts/sports-safe-run.sh with a 15-second limit and does not block commercial NFL, Survivor, fantasy, props or DFS decisions. A manual governed stage returned rc=0 with 13 earlier source records retained and 0 duplicate records. The first normal scheduled hourly service after wiring remains to be observed before calling automatic integration accepted.

## Persistence and tests

The pre-existing previously uncommitted six NFL forward source/model/Final modules and ten suites were preserved under local Git commit **77b098a**. The new runner and tests passed **75 regressions** including contradictory official source scores, original bookmaker odds math, source changes and append-only idempotency. Original source recovery: 22 files preserved and verified by restoration under .deploy_backups/zenith_nfl_70_forward_SOURCE_BEFORE_INTEGRATION_20261009T062600Z.

The insurer caveat: sportsbook prices come from an aggregator, not independently confirmed as executable original book offers. Future paper EV is only an unproven research hypothesis. There is no statistical or profit edge yet, no artificial rate increase, no paid dataset subscription, and independent off-VPS recovery is still unverified.
