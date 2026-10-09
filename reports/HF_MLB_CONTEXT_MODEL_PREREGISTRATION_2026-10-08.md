# Sports Zenith — preregistered exploratory MLB player-hits context model

## Scope and timing

**Only retrospective historical research.** The original official Sports Zenith betting proof and frozen forward ledger remain unchanged. The 46 July game outcomes have ALREADY BEEN OBSERVED during the previous single-signal experiment; a model evaluated on July now must be labeled **SECONDARY HISTORICAL RECHECK, NOT NEW SEALED OUT-OF-SAMPLE DISCOVERY**. No cherry-picking, hyperparameter search, deciding feature weights from this July set or creating PLAYs from the experiment.

Data previously verified in `/home/ubuntu/sports-hulk/reports/hf_mlb_expanded_20261008/` and `/home/ubuntu/sports-hulk/reports/hf_mlb_unseen_0017_20261008/`: 94 earlier 2026 vendor-graded paired-price player-hits research games and 46 later July official-analytic-grade player-hits research games. New strictly as-of context builder conservatively excludes four of 94 original training games due to missing 2025 venue samples, disagreement in historical player team, or fixture timestamp discrepancy. **90 prior-only context-complete historical training games and 46 July analytical test games** are eligible for the fixed experiment.

## Source-time and leakage invariants

Pregame input features must use only: (a) target game's *known fixture metadata* (venue ID and home/away fixture position, never its outcome), (b) 2025 completed MLB *regular-season* venue totals to define previous-year park factor (at least 40 completed games at venue), (c) prior regular-season MLB player boxscores, strictly before quote UTC calendar day and at least 12 hours older than quote start, to estimate existing player role and rest and previous head-to-head results, (d) opposing team's prior ten completed games and aggregated historical pitcher hits allowed; **never the current game's starting pitcher inferred from a postgame boxscore**. Current confirmed lineup and pregame weather have no verifiable historical capture as-of and are deliberately marked unavailable. Do not use same-season-full-season `MLB_PARK_RUN_FACTORS.csv` or 2026 `park_run_factor` from `MLB_HISTORICAL_PREGAME_FEATURES.csv`, both of which can leak 2026 future outcomes. The actual player ID and fixture are used only to resolve archival identity, not to infer a supposedly pre-announced lineup.

## Fixed feature set — ONE regression specification, no retrospective changes

Use ridge-logistic market-fair baseline (two-sided de-vigged same-book/time probability), with fixed quadratic penalty **lambda 16** on all non-intercept terms relative to prior market-only logit coefficient 1, zero on new features. Additional columns, in this exact order:

1. Existing verified prior-player hits vs line side-adjusted `pregame_context_signal`, clamp [-3,3].
2. Opposing team last-ten completed-game aggregate pitching hits allowed per 9 innings, `(value-8.5)/3`, clip [-2,2].
3. Opposing team last-ten completed-game runs allowed, `(value-4.5)/2.5`, clip [-2,2].
4. Previous-season-only venue run factor, `(factor-1)/0.2`, clip [-1.5,1.5].
5. Prior ten hitter appearances' average plate appearances, `(average-4.2)/1.4`, clip [-2,2]. This is NOT a confirmed current lineup.
6. Rest days since last *prior* completed game, `(min(rest_days,14)-2)/5`, clip [-1.5,2.5].
7. Previous head-to-head player hits per game relative to prior-five hits average, clipped [-1.5,1.5], or `0` when less than two prior matchup games. Never use target-game matchup results.
8. Player's fixture home flag `home_flag-0.5`.

The full model includes the baseline two columns (intercept and market logit) plus eight specified context columns. Regularized fit uses only the 90 pre-July training rows. The matching market-only *control* model must be trained on the same 90. No fit or coefficient search on July values. Freeze both models and the training/input checksums before running a July evaluation. JSON source files used as input to the model must be independently checked against official MLB gamePk and as-of context during feature construction.

## Evaluation and rejection rules

Compare raw book fair probability, a market-only ridge-logistic calibrator, the previous 94-game one-signal benchmark, and the new **single fixed context-augmented model** on all 46 July games. Evaluate Brier and log loss, game-bootstrapped 95% interval of relative Brier improvement and **calendar-day-clustered** 95% interval (only 5 distinct July dates). Do not exclude losing outcomes or restrict operator after seeing results. Compare market-only and augmented using identical heldout games with no overlaps. July results are not pristine unused validation because earlier work inspected their grades. More truly unseen months/seasons and commercial source rights are required for claims of a robust edge; even improvement here must not be promoted to a current PLAY.

## Key source audits

- The venue-based park source generator `baseball_vault/park_factors.py` groups by whole season and would reveal future 2026 outcomes if used retrospectively on 2026 games. It is prohibited as such; compute 2025 park factor directly from 2025 regular-season final source games only.
- No historically timestamped probable opposing starters, confirmed lineups or weather archives established in the current Sports Zenith data warehouse. These data lanes remain **not available for this experiment** until contemporaneous historical captures are proven.

**Approval gate:** RESEARCH-ONLY; any failure, ambiguous identity, missing as-of source, contradictory data, or insufficient independent sample remains a HOLD. No production model edits or bankroll simulation should be derived from these outputs.
