# Sports Zenith — MLB as-of context, leakage fix and secondary holdout

**Date:** October 8, 2026 UTC. **Verdict: research pipeline improved; model edge NOT PROVEN.** Existing Sports Zenith PLAY/PASS logic, moneyline/prop model versions, priced forward selections, official game outcomes, website, and commercial licensing were not modified in this work.

## Why this pass happened

User requested continued improvement after the Hugging Face historical player-prop pilot had recovered verified sportsbook quotes and official MLB results but found that a simple prior-five-game player trend did not improve the subsequent July sealed test. Target: add opposing pitching/team context, park environments, player role and previous matchup while proving every feature existed **before the quoted bet**. Historical probable starting pitchers, confirmed lineups, and quote-time weather were investigated but no authentic timestamped March–July archives were identified on this server. The experiment **does not invent them**. Prediction approvals still require genuine forward evidence and commercial source rights.

## Historical source and time safeguards

- Original external odds: [SmartStake MLB Player Props on Hugging Face](https://huggingface.co/datasets/SmartStake/mlb-player-props) — timestamped prices with paired offers from exactly the same book/market/line/game/minute, side chosen by fixed outcome-blind hash, and distinct officially matched MLB game IDs.
- Training evidence: `reports/hf_mlb_expanded_20261008/asof_audit.json` (vendor grades crosschecked against MLB StatsAPI), 94 original player-hits games across March–June. July evidence: `reports/hf_mlb_unseen_0017_20261008/unseen_asof_audit.json` (46 analytically officially derived result games across July 1–5). The July outcomes had **already been looked at earlier in the conversation**. Therefore all July results here are **secondary retrospective diagnostics, not a new blind holdout**, even if model coefficients were frozen before this particular pass.
- Official MLB historical player-by-game input: `intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_HISTORY.csv`. Fixture/venue/game final history: `baseball_vault/derived/MLB_GAME_MASTER.csv`. No source file was rewritten.
- Added `intelligence_warehouse/betting_v2/hf_mlb_prop_context.py` requiring strict as-of evidence: player and opponent games must be **from dates earlier than the quote's UTC date**, with a conservative 12-hour age gap; same-day, current-game and future outcomes never enter predictors. Unique current fixture verification includes official game ID, teams and first pitch within three minutes of the earlier identity proof. Player's most recent prior verified team must match the fixture; cases with trades or uncertain team are rejected rather than imputed. No contemporaneous probable starter or lineup is inferred from the eventual boxscore.
- Park factor is computed from **completed 2025 regular-season games**, prior to the 2026 quote, by venue ID with **at least 40** prior-year completed games. Full-season 2026 park factors are expressly rejected. Source price, team/venue and player provenance is preserved per row.

## Preregistered single-model experiment and exclusions

The **fixed 8-feature, ridge-logistic** full-context specification was written before fitting/evaluating this pass in `reports/HF_MLB_CONTEXT_MODEL_PREREGISTRATION_2026-10-08.md` (SHA-256 `7b877c0f5811a594c066443e59bccb3cc5a75b1537f9ddef0f1b589d8db25674`). Its eight extra features, with prespecified scaling and fixed **lambda 16** penalty, are: prior-five player stat vs line, opposing-team historical pitchers' hits-allowed per nine, opposing-team last-ten runs allowed, **prior-season-only** park factor, prior-ten hitter plate-appearance average (historical role proxy; not today's confirmed lineup), prior-player rest, earlier hitter-vs-opponent hit history (missing handled by zero only with explicit count), and fixture home flag. Market reference is always the exact same-book/minute over/under de-vigged probability. No post-outcome feature search or hyperparameter tuning was run against July.

- Original training player-hits vendor-verified rows: **94**.
- Accepted full-context training rows: **90**; four rejected: 2 player prior team not matching later-game roster, 1 missing minimum prior-season venue data, 1 conflicting fixture start time.
- Accepted July analytical holdout rows: **46/46**, 46 independent game IDs. No historical confirmed starter, confirmed lineup or weather-at-quote timestamp was verifiable for any of these 46; those predictor fields remain unavailable, not fabricated.
- Pre-July fit from 90 vendor-verified March–June games ended at **2026-06-18T18:10:00Z** and was saved *before* evaluating the July outcomes to `reports/hf_mlb_expanded_20261008/frozen_full_context_v1_research_only.json`, frozen SHA-256 **`dd056d1f0b9ec0ade58b6c1366de46631602835088dbcaf8384b3bbc0d091f88`**. The model was re-fitted using only the same 90 training rows as a reproducibility check and yielded exactly the same coefficients; the frozen file stayed byte-identical. This sequence is an internal process safeguard, **not** proof that previously known July results are newly unseen.

## July five-calendar-day secondary comparison

| Approach | 46-game July Brier error ↓ | Log loss ↓ |
| --- | ---: | ---: |
| Raw de-vigged book prices | 0.258127 | 0.710573 |
| Market-only calibration **trained on same 90 records** | 0.254972 | 0.703659 |
| Market + eight fixed as-of features **trained on same 90** | **0.252535** | **0.699411** |
| **Earlier** market-only model trained on **94** records | **0.252171** | From prior locked run |

The full-context experiment improves Brier versus its identically sourced 90-game market-only control by **0.002437**, but is worse by **0.000364** than the earlier 94-game market-only calibration previously tested on these very same 46 games. The game-bootstrap 95% improvement interval is **[-0.009112, +0.014403]** and the five-calendar-day cluster-bootstrap 95% interval is **[-0.009706, +0.015331]**, both containing zero. Among a post-hoc 23-quote established-book subset, Brier values are calibrated market **0.257226**, augmented **0.256171**, difference only **0.001055** and too small for a reliable claim. Day-by-day results alternate signs. **No robust independent predictive advantage, positive ROI or qualified PLAY follows.** Do not publish these Brier metrics as a winning-percentage claim.

## Separate real Sports Zenith forward record — why PASS remains rational

Read-only inspection of `intelligence_warehouse/betting_v2/PROP_V2_FORWARD_SUMMARY.json` (October 8 snapshot) shows **2,118 settled prop entries across all sports**, with overall V2 Brier **0.20050 vs market 0.19522** (higher/worse for V2). In the **MLB_PROP** lane there were **944 settled prop observations but only 8 independent game blocks**, with current V2 and market probabilities identical (Brier **0.17326** each). That is insufficient independent forward game evidence to approve an MLB betting signal; multiple player selections from a single game cannot become hundreds of independent verification blocks. The game-moneyline forward ledger had **131 settled** market selections but not proven independent probability edge. These forward facts must be kept separate from the research-only historical Hugging Face dataset. Model selection/status safeguards remain unchanged.

## Real backtest leakage repair — code tested, live generated data not republished

The *original* `baseball_vault/park_factors.py` computed season-level park factors with no regular-season filter and `baseball_vault/historical_pregame_features.py` merged them into game histories for the **same season**, which leaks future 2026 results into earlier 2026 backtests. Both generators were patched (source code only) under TDD: park factor source now accepts final **regular-season games only**, and historical features attach only a park reference from **the prior completed season** for the identical venue ID. Missing prior-season references stay NULL, with explicit `park_factor_reference_season` and `park_factor_reference_games` fields. No current betting threshold or active model changed.

A **temporary staged build** using the actual 7,911-game master passed invariants: 2024 historical rows 2,652 with no invented 2023 reference; 2025 historical rows 2,639 with 2,326 2024-park-covered rows; 2026 historical rows 2,620 with 2,387 2025-park-covered rows. Not one staged 2026 game used a 2026 park factor. Production `MLB_PARK_RUN_FACTORS.csv`, `MLB_HISTORICAL_PREGAME_FEATURES.csv`, and `MLB_GAME_MASTER.csv` were SHA-verified unchanged during this stage. **Existing generated production artifacts may still contain the old same-season park data until their dependent historical-model/comps consumers are audited and an authorized, backed-up rebuild runs.** Do not treat code patch/staging as evidence that all published historical metrics were recalibrated.

## External dataset boundaries

HF dataset cards for `canesyrup/mlb-player-props` and `Neonlightzz/mlb-player-props` repeat the same SmartStake March–July dataset description; they are **not established independent later-season validation data**. Source cards' CC-BY-4.0 labels do not independently prove upstream sportsbook redistribution or commercial model-use rights. No external historical lines were published to the commercial website and no paid data was purchased. Historical MLB pregame probable pitchers, confirmed lineups and quote-time weather require new genuinely timestamped sources and rights checks before being added to a commercial model.

## Reproducible files and next steps

Code: `intelligence_warehouse/betting_v2/hf_mlb_prop_context.py`, `hf_mlb_prop_context_model.py`, the prior `hf_mlb_prop_pilot*.py` research components, plus the patched `baseball_vault/park_factors.py` and `baseball_vault/historical_pregame_features.py`. Tests: `tests/test_hf_mlb_prop_context.py`, `tests/test_hf_mlb_prop_context_model.py`, `tests/test_mlb_park_asof_provenance.py`. All written with red/green checks against missing functionality and before final verification; results recorded in final audit.

Research-only evidence under `reports/hf_mlb_expanded_20261008/`: `context_train_research_only.json` (94 rows with statuses), `context_july_research_only.json` (46), `frozen_full_context_v1_research_only.json` (source checksum-locked model), `full_context_v1_secondary_july_result.json` and `context_secondary_posthoc_descriptive.json`. No model or evidence was uploaded to Hugging Face.

**Next work:** protect and collect genuine independently timestamped pregame features alongside the existing forward ledger; verify commercially authorized live opponent probable pitcher, confirmed lineup and weather captures; complete dependent park-feature rebuild review; wait for sufficient different future games/seasons before any promotion. Do not call the current model proven or lower independent history requirements to remove PASS statuses.

## Persisted as-of park regeneration candidate (research only)

A complete **research-only** staged generator run was saved under `reports/hf_mlb_staged_park_20261008/`. It includes a copy of the source MLB game master, derived park factors for completed regular seasons, the corrected historical pregame CSV/Parquet features, and `MANIFEST.json` with per-file SHA-256. The manifest documents precisely **7,911** staged historical games and the year-by-year prior-season coverage (2024: 0, 2025: 2,326, 2026: 2,387). The generator's original live master/park/history CSVs were individually SHA-verified **unchanged** after the staged run. This staged file is not part of the live betting feeds; dependent calibration and comparison-model rebuilds have not been authorized or run against it in production. **Do not silently replace published historical metrics** until those consumers are audited and backups verified.

## Extra read-only forward proof check

The current forward-prop summary provides useful but not qualifying sample evidence: across MLB_PROP there are **944 settled forward prop selections tied to only eight independent game blocks**, with baseline and V2 probability both equal to market reference (Brier 0.17326). Current NBA prop forwards remain mostly pending (not a comparable sample); NHL_PROP has 987 settled predictions over 16 independent game blocks, with V2 worse than market. The user-facing PASS is therefore a legitimate per-lane uncertainty conclusion, not simply a missing local file. These numbers were read from existing live summary data and NOT revised by this context research.

## Fresh regression verification

`.venv/bin/python -m unittest tests.test_hf_mlb_prop_pilot tests.test_hf_mlb_prop_asof tests.test_hf_mlb_prop_pairing tests.test_hf_mlb_prop_expansion tests.test_hf_mlb_prop_expanded_analysis tests.test_hf_mlb_prop_fair_lane tests.test_hf_mlb_prop_locked_holdout tests.test_hf_mlb_prop_official_derived tests.test_hf_mlb_prop_unseen_shard tests.test_hf_mlb_prop_context tests.test_hf_mlb_prop_context_model tests.test_mlb_park_asof_provenance tests.test_betting_v2_regime_history tests.test_betting_v2_regime_current tests.test_nfl_grading_game_identity -q` → **76 passed, zero failures**. Python modules compiled, targeted `git diff --check` passed and source history/park staging invariants passed. The research-only full-context model re-fitted from the saved 90 games with **identical frozen coefficients** and its secondary July evaluation replayed identically without changing the original frozen artifact. The live website remained available with HTTP 200 during this pass.
