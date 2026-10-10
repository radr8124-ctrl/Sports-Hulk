# Sports Zenith — NFL 5/10/20 Scoring History Accuracy Diagnostic (2026-10-10 UTC)

## Objective / decision

The user sent Rithmm + PropsBot public methodology links and connected DraftKings, explicitly asking for **increased prediction accuracy**, not more dashboard features or forced bet approvals. This is an **isolated, read-only, pre-declared historical diagnostic** to test if opponent-adjusted 5-, 10-, and 20-game team score windows improve Zenith's NFL model compared with the sportsbook's fair no-vig home-win probability. **Decision: not promoted.** The effect is small, unstable, and fails the latest inspected year.

## Original empirical source and limitations

- Historical input `data_vault/derived/NFL_GAME_MASTER.csv`, unique NFL game IDs, seasons 2016–2025, original source SHA-256 `35a23b30de0b91666f2a452d7f36df1b8fc3959a27989492e10965794c655190`.
- 2,749 completed games with plausible paired moneylines and binary outcomes; two source games with invalid markets and 10 ties quarantined. All training predictors are formed from **prior full NFL weeks only**; no current-week game result or current-season future data enters a feature vector.
- Opponent-adjusted scoring margin approximates half of (home recent PF + away recent PA − away recent PF − home recent PA). Also contains relative offense/defense, prior-window coverage, scheduled rest, neutral field, and **the same historical market probability**. Three pseudo-form windows are shrunk to a fixed prior of 22 points using three pseudo-games. Fixed ridge logistic L2 penalty 20.
- **Critical coverage discovery:** Full 5-game past histories exist for both teams in 1,941/2,749 cases; full 10-game histories in 1,139; **true full 20-game same-season history for both teams in only ONE game** (and none in 2022–2025 test folds). The 20-game feature nearly always uses fewer prior games. It is *not* evidence that 20 full games produce better models. Cross-season 20-game trends may need recency/coach/QB/roster normalization and were NOT silently fabricated.
- Original bookmaker moneylines in historical master were compiled **retrospectively**, without a verified specific book and pregame capture timestamp. This is a rough historical benchmark, **not an executable sportsbook betting return or original closing-line audit**.
- The 2025 season has previously been examined in the older nine-feature study; it is a diagnostic only, not pristine forward holdout. All results are strictly **shadow research**, no new bet/ROI/profit prediction or model weights changed.

## Genuine expanding-year historical comparison, **1,136 independent games**

The script `intelligence_warehouse/historical_recovery/nfl_rolling_score_form_diagnostic.py` fits with calendar seasons earlier than each test year. For 2022, 2016–2021 are training, 2022 separate; for 2023, train through 2022; for 2024, train through 2023; for 2025, train through 2024. One unique game yields at most one binary home-win evaluation. Comparison: raw paired no-vig bookmaker, retrained market-only ridge, and pre-specified 5/10/20 score-form ridge. No post-hoc hyperparameter or feature search.

| Historical season | Unique games | Market Brier | Rolling Brier | Market winner % | Rolling winner % | Market minus rolling Brier; 95% paired-week bootstrap |
|---|---:|---:|---:|---:|---:|---|
| 2022 | 282 | 0.20928694 | 0.207349293 | 65.60% | 68.44% | +0.00193765; [-0.00004281, +0.00369968] |
| 2023 | 285 | 0.218638336 | 0.216730981 | 67.02% | 67.72% | +0.00190735; [-0.00020768, +0.00422016] |
| 2024 | 285 | 0.200974786 | 0.201587648 | 70.88% | 70.88% | −0.00061286; [-0.00372939, +0.00225240] |
| 2025 | 284 | 0.210906373 | 0.213005732 | 65.85% | 64.79% | −0.00209936; [-0.00466920, +0.00080206] |

Pooled equally per individual game over all four folds: market Brier 0.20995252, longer-form model 0.20967160; tiny improvement **0.00028092**, but the challenger only beat the raw book in **2 of 4** individual seasons. **Every individual season's 95% week-block bootstrap interval crossed zero**. The latest inspected year was **worse**, with about 1.06 percentage points *lower* correct-winner rate. These data do not justify claiming an accuracy advantage, +EV betting strategy, or model promotion.

## Connected DraftKings scope and source gate

Connected first-party DraftKings ChatGPT plugin responded OK on October 10, 02:35 UTC and returned official-grade Oct 4 Chiefs@Raiders final (KC 30, LV 27) and an Upcoming Oct 11 Raiders@Patriots scheduled for 17:00Z. DK uses separate `competitionId` values (974082/974090); Zenith's source uses official ESPN event IDs and must match by teams, status and kickoff before enriching.
- DK Oct 4 Chiefs Total Yards 407 = displayed Passing Yards 218 + Rushing 189, whereas official NFL team **net** yardage is 399. These are **different possible metric semantics**, not 8 free extra yards for training.
- DK current-season offense scoring averages 28.2 LV/14.8 NE, while the same teams' four official 2026 *scoreboard points* averages 28.75/16.25; source definition/denominator/time remains unverified.
- Isolated safety gate `intelligence_warehouse/historical_recovery/draftkings_stat_definition_gate.py` rejects incorrect event IDs, outcome mismatches, post-kickoff stats, unknown competition phase and insufficient prior games. Nine focused tests passed. **This gate is not yet wired to Zenith's production predictor**, and the plugin is not a licensed sportsbook odds API or an automated direct VPS feed.

## Rithmm / PropsBot ideas investigated, restricted by evidence

- Rithmm's documented MLB ~3,000-game split reserves ~1,450 for measurement separate from window calibration. Beneficial: never use the games that selected the strategy to report its win rate/ROI. Their published sampling across years is not strict prospective as-of holdout; Zenith's chronological game-block separation is stronger.
  https://www.rithmm.com/post/how-rithmm-mlb-backtesting-works
- Rithmm's MLB pitch/park/bullpen/opponent adjustment concept is relevant to MLB, **not a directly transplantable NFL player-prop model**. License/data quality and original captured pregame line are prerequisites.
  https://www.rithmm.com/post/rithmm-mlb-2026-full-release
- PropsBot's published rolling 5/10/20 recent-form, opponent adjustments, line movements and confidence/Brier methods are useful **hypotheses**; the self-reported accuracy/ROI cannot substitute for original independently replayable picks at given sportsbook prices.
  https://propsbot.ai/performance-methodology/
  https://propsbot.ai/chatgpt-sports-betting-bot/

## Implementation and verification

- New isolated historical diagnostic `intelligence_warehouse/historical_recovery/nfl_rolling_score_form_diagnostic.py` and source-linked output `reports/NFL_ROLLING_5_10_20_WALK_FORWARD_DIAGNOSTIC_20261010.json`.
- Safety regression `tests/test_nfl_rolling_score_form_diagnostic.py` checks historical source SHA, unique game IDs, no 2026 game results, current-week perturbation invariance, ability to learn from *later* weeks, source recency and four strict calendar splits. **6 new tests passed**.
- Independent DraftKings source-quality check **9 tests passed**, total **15 focused tests passed**.
- The prior 2016–2024 trained nine-feature NFL frozen model and its 2025 diagnostic (model Brier **0.212617338** vs original bookmaker **0.210906373**) remain untouched and its 13 first Week 5 future predictions cannot be replaced.
- **No live model code/weight, frozen prediction ledger, actual user Survivor pick, sportsbook bankroll, paid API request or website UI was changed.**
- Next meaningful stage: obtain independently timestamped pregame source values and definitions for 5/10/20 NFL player/team stats; freeze **one** model hypothesis and compare it against same-book prices on later 2026 games, with Brier, log loss, correct-side rate and independently verified quote-to-close/ROI analyzed separately.

**Decision: no validated increase in winning percentage yet; future model improvement must be earned on forward games.**
