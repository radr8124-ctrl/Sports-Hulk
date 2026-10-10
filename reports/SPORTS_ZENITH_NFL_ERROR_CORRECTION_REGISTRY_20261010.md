# Sports Zenith — Error-Recovery Correction Trials (Oct 10, 2026 UTC)

## What the user asked
Continue building a betting/fantasy intelligence system that **learns from why predictions were wrong**, rather than merely displaying the final hit rate. Keep exact original sportsbook baselines, don't erase frozen predictions, and don't promote fake winning percentages.

## What was actually found
- The prior 2025 NFL nine-feature diagnostic (284 completed NFL games) produced **Brier 0.212617338** versus sportsbook no-vig **0.210906373** (lower is better): the experimental model was WORSE.
- Among those 284, the model reversed the sportsbook's favored winner **six times**; four reversals selected the wrong winner where the book's original favorite was correct, and two reversals selected the correct winner where the book was wrong.
- Source-time 2025 error autopsy distinguishes (i) original bookmaker fair probability, (ii) frozen research model probability, (iii) final winner, (iv) strongest signed *logit coefficient terms*, and (v) uncertainty about actual cause. A feature's mathematical contribution does **not** prove weather, injuries, QB or coaching caused a loss.

## Hypotheses tested — and deliberately rejected
A fixed historical comparison was performed using unique games with full expanding **past-season-only** training (2016–2021 train / 2022 test, then train through 2022 / 2023 test, etc.), repeatable ridge L2=20, no result from the target or same NFL week in the inputs. Original 2016–24 frozen model coefficients were reproduced in the 2025 fold.

| Strictly historical approach | Pooled Brier (1,136 independent games) | Market improvement | Action |
|---|---:|---:|---|
| Original paired sportsbook no-vig | **0.2099525** | Benchmark | Keep as reference |
| Existing nine-feature experimental model | 0.2105144 | −0.0005619 | Reject vs market |
| Fall back to bookmaker if either team has fewer than three previous current-season games | 0.2109040 | −0.0009515 | **Reject** |
| Fall back to bookmaker when model reverses market favorite | 0.2105822 | −0.0006297 | **Reject** |
| Both experimental safeguards combined | 0.2109388 | −0.0009863 | **Reject** |

The winner-disagreement fallback improved over the unmodified experimental model **within 2025**, but it still failed to beat the bookmaker then, and failed the pooled 2022–2025 benchmark. All four original/corrective model approaches are weaker than the market over this particular inspected historical dataset. **Three proposed corrections were rejected.**

Important scientific limitation: the 2025 season and historical context had already been seen in prior Zenith research. These trials are exploratory diagnostics, not a newly frozen clean prospective test. Historical moneylines were retrospectively compiled without independently timestamped original book/line availability. This analysis does not establish true closing prices, executable +EV or historical ROI, regardless of Brier comparison.

## Software implementation
- Isolated source-only historical challenger: `intelligence_warehouse/historical_recovery/nfl_error_recovery_shadow.py`.
- Complete original game-block results and misfire audit: `reports/NFL_ERROR_RECOVERY_SHADOW_DIAGNOSTIC_20261010.json`.
- SHA256-verified candidate evaluation and fail-closed outcome gate: `intelligence_warehouse/outcome_learning/error_trial_registry.py`. It checks original historical-source and immutable frozen model hashes, all four seasonal folds, prior-year train chronology, test count arithmetic and recomputes pooled Brier from season metrics before accepting a candidate record.
- Wired to existing **hourly** `intelligence_warehouse/outcome_learning/build_outcome_learning.py` source-readback and published `zenith_learning_review.json`. If evidence is missing/invalid, only an explicit BLOCKED verdict appears; the existing NFL/Basketball/NHL learning pipelines remain operational and no invalid candidate is approved.
- `commercial_web/src/BrainLearningPanel.jsx` now displays **Corrections tested: 3 · rejected: 3** on the existing Brain Record page, with one-tap details including the original model baseline and compared Brier scores. Does not change the main navigation, betting models, odds, Ref assistant or private Survivor picks.
- Updated earlier brittle `commercial_web/brain-learning-review.e2e.spec.js` to bind the live settled-pick counts and prospective original NFL scorer counts from the actual source file rather than assuming 197 rows forever. Removed hardcoded win-rate text on the page.

## Outcome / safeguards
- The original production model coefficients, same-book bookmaker sources, thirteen frozen future NFL predictions, Survivor saves and historical forward ledger were neither modified nor backfilled.
- **Zero new approved bets, zero model promotions, zero verified new accuracy gain.** Rejecting failed interventions is a valid learning outcome.
- Existing `SPORTSZENITH_OUTCOME_LEARNING_SHADOW_V1` hourly source-only review continues. Did not increase paid API usage or add another cron.
- Original before-change publisher/UI files were copied and SHA256-verified under `.deploy_backups/zenith_error_trial_registry_before_20261010T0300Z`, on the VPS; **off-server recovery remains separately unverified**.
- The crucial next scorecard is the genuinely frozen original **13 NFL Week 5 predictions** after their games finish. The separate official ESPN scorer must verify final event IDs and game outcomes before any change can be evaluated prospectively.
- New registry tests exercise tamper cases (promotion flag, fake Brier gain, wrong source hash, future-year contamination, conflicting year count, unauthorized model update) and the existing forward-data source contracts. All summaries carry a blocked/research-only designation; no positive EV or winning promise is made.
- **Completed acceptance:** **42/42 Python** unit/source tests covering original frozen game history and candidate gates; **221/221 website JavaScript** tests; **43/43 responsive browser tests** across Brain Record, Bets odds, tools, Ref, Props and Survivor. Build PASS, live website health HTTP 200, public/dist learning JSON byte-identical, original historical source/model/NFL future ledger SHA readback confirmed.
- New research files are committed only as an isolated versioned Git checkpoint on the original VPS. No change to unrelated currently modified sports source services. No claim that a fresh forward profit or accuracy increase has been established.
