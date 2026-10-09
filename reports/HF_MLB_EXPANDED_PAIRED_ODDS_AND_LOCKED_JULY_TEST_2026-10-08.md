# Sports Zenith — Hugging Face MLB historical paired-price expansion and untouched July holdout

Date: October 8, 2026 (UTC). Stage: external historical research only. **No Sports Zenith live model, UI, forward ledger, probability-qualification thresholds, original graded pick history or sportsbook wager was modified or submitted.**

## Executive result

External sports betting data is no longer an unexplored source: a bounded sample of 3 archived Hugging Face parquet shards identified **411 exact timestamp/book paired-odds research candidates from 125 source game IDs**. Official MLB StatsAPI game/player/stat verification accepted **318 vendor-graded research selections (101 unique MLB official games)**; **317** of those also had strictly prior eligible player-form evidence. **This is not Sports Zenith's original forward-performance record**. A player-hits trend improvement on an internal 38-game historical holdout *failed to repeat* on a new pre-sealed July 46-game test. The market-only calibrated model outperformed the frozen market-plus-player-trend model on the July test. **No selection is promoted to PLAY.**

## Frozen outcome-blind sampling protocol

Source: https://huggingface.co/datasets/SmartStake/mlb-player-props (HF dataset card CC-BY-4.0; downstream sportsbook rights unverified). The archive has 621,391,637 minute/book observations, **not** as many independent games. Sampled only archive parquet shards `0000` (March), `0008` (May), and `0015` (June), ~135 MB compressed. Exactly 36 evenly spaced parquet row groups per shard (108 groups). For each source game ID and each market, choose a same-book, same-timestamp, same-player, same-line, simultaneous OVER+UNDER quote closest to **six hours before scheduled first pitch**, requiring at least two hours pregame. Selection side is from fixed SHA-256 of source game ID+market; *no outcome grade, odds edge, winning bet, or future statistic is used for quote selection*. Reject conflicting duplicate prices, unpaired prices, invalid American/decimal transformations, or implausible overround. There is only one research candidate per source game and market. The original source candidates and selection manifest are preserved under `reports/hf_mlb_expanded_20261008/` for reproducibility.

## First source audit (vendor outcome present)

| Check | Result |
| --- | ---: |
| Distinct provider game IDs | 125 |
| Paired candidate selections | 411 |
| Unique official MLB gamePk with accepted vendor grade/identity/price | **101** |
| Exact book/time/line two-sided odds pairs plus official matching | **318** records |
| With strictly prior official player context | **317** records |
| Source-game IDs mapped to conflicting official games | 35 records, rejected |
| No unique official matching player and fixture | 30 records, rejected |
| Vendor outcome missing | 8 records, rejected in the **vendor-graded** audit |
| Provider stat/result disagreed with official MLB boxscore | 20 records, rejected |

Per-market independent official games with every required field: **hits 94, total bases 92, RBIs 94, strikeouts 37**. Only **29 of the 94 hits games** came from the small established sportsbook subset (`bet365`, `BetMGM`, `Caesars`, `DraftKings`, `Fanatics`, `FanDuel`, `Hard Rock`, `Pinnacle`). This post-hoc source-quality subset has insufficient size for a confident model claim. Source prices include unfamiliar/secondary operators, another reason not to deploy results as commercially executable recommendations.

Official identity requires unique MLB gamePk, diacritic-insensitive **exact player name**, season/game start within **3 minutes** of provider start, trusted boxscore, verified exact-market result vs declared line, and a quote before the official first pitch. Player model uses only official *previous* completed games dated strictly before quote UTC date; no target-game or future stats are used as predictive features.

## Three-month per-market chronological holdouts

Research-only ridge-logistic test against de-vigged, **same-book/time** market prices. These are retrospective external source results, not an official prediction sequence from Sports Zenith.

| Market | Verified games | Chronological training / holdout | Paired fair-market Brier | Calibrated market Brier | Market + pregame form Brier |
| --- | ---: | --- | ---: | ---: | ---: |
| Player hits | 94 | 56 / 38 | 0.254043 | **0.252692** | **0.246543** |
| Total bases | 92 | 55 / 37 | **0.205075** | 0.228008 | 0.222613 |
| RBIs | 94 | 56 / 38 | 0.219771 | 0.218995 | 0.218678 |
| Strikeouts | 37 | 22 / 15 | 0.232115 | **0.224857** | 0.225195 |

For hits, the observed gain over calibrated market was 0.006149 Brier units. Its **game-resampled 95% confidence interval for improvement includes zero**, [-0.000721, 0.013341]; the simultaneous four-market 98.75% interval includes zero, [-0.002824, 0.014587]. For all lanes, 95% intervals included zero. Earlier 90% hit interval alone was not strong enough to make a proof claim. Seven overlapping chronological train/holdout fraction probes were evaluated as **descriptive sensitivity only**, not seven independent replications. Because results varied and most records were not from large established books, *no profitable or independent betting edge is established*.

## Additional independent-shard check — frozen BEFORE looking at July outcomes

Before opening or sampling previously untouched `0017.parquet`, a separate **research-only hits model** was fitted on **all 94 earlier vendor-graded official games through 2026-06-18T18:10Z**. It was sealed to `reports/hf_mlb_expanded_20261008/frozen_hits_before_0017.json` with SHA-256 `2efee022990b0a9d7f0f9be06c7767ab99f04a841bb1dbde8ef57a5e2b3826a6`; frozen calibration/augmented coefficients were never modified during evaluation.

Unseen HF shard `0017` contained ~51.8 MB compressed and ~39.0 million snapshots, of which **60 evenly spaced row groups** were inspected with the same outcome-blind source selection rule (170 exact paired-price candidates, 51 provider game IDs). Initial publisher-grade audit found **zero provided WIN/LOSS grades**: the source's `result`/`won` columns were missing from all 170 selected cases, although source prices and many official MLB boxscores were present.

A separate, **opt-in, research-only** adjudicator now analytically grades ONLY rows with **both vendor outcome fields blank** AND unique verified official game/player/participation/statistics. It requires at least one plate appearance for hitter props (or recorded pitching outs for a pitcher), an exact official stat, a non-push over/under line, a verified pregame source timestamp, and a unique official fixture. It NEVER rewrites a conflicting vendor grade, fixes ambiguous multi-game IDs by guessing, or claims sportsbook/DFS platform settlement. Every such row is tagged **`OFFICIAL_DERIVED_HISTORICAL`**, `platform_settlement_claim=false` and `grade_source=OFFICIAL_MLB_STATSAPI_BOXSCORE_ANALYTIC_ONLY`. It cannot enter Sports Zenith's official performance/forward ledgers.

- **152 July source candidates** received independently official-derived analytic outcomes (not publisher settlements); **18 rejected**: 14 unmatched games/players, four conflicting provider game IDs.
- **49 unique official July MLB games** had valid game/grade and paired odds; **151** rows had prior-only player features.
- July supported per-market independent-game counts: hits **46**, total bases **44**, RBIs **46**, strikeouts **15**.
- The frozen hits experiment evaluated **46 newly observed July games** from **July 1–5**, strictly later than the June 18 training cutoff and disjoint from all earlier training games. **No refit** of frozen market or player-stat model was allowed.

### Locked July test: harder evidence

| July heldout hits model / baseline | 46-game Brier (lower is better) |
| --- | ---: |
| Exact paired-book fair market probability | 0.258127 |
| **Frozen calibrated market** | **0.252171** |
| **Frozen calibrated market + previous player stats** | 0.254329 |

The previously promising player-stat addition is **worse by 0.002159 Brier** relative to the frozen market-only calibration on this new source shard. The 95% game bootstrap interval for improvement was [-0.013888, 0.009127], spanning zero. The 46 separate official games occurred on only **five calendar days** (8/8/9/14/7 games); a 95% *calendar-day clustered* bootstrap on those dates was [-0.010882, 0.006292], also spanning zero. On the exploratory 23-quote subset from the established book list, market calibration Brier was 0.252494 versus **0.263030** for augmented player form (worse). The subset is too small to generalize.

Five live MLB StatsAPI read-only boxscore confirmations, one from each July day, returned HTTP 200 and matched accepted analytic hits results: Josh Naylor (823122), Sal Stewart (823767), Alejandro Osuna (822884), Rafael Devers (824336), and A.J. Ewing (824903). This supports independent official outcome integrity but **not** bookmaker platform settlement or commercial redistribution rights.

## Conclusions, gates and next steps

- **Data acquisition/validation: PASS.** Public historical quote archive, official identity/time, exact same-book two-sided odds, pregame features, and independent official analytic outcomes are now real and reproducible for a narrow bounded sample. This directly addresses data availability, but not profit proof.
- **Player-form signal: FAIL TO VALIDATE ON SEALED JULY HOLDOUT.** It must not replace live models or enter best-bet/shadow PLAY qualification. More volume of that same unvalidated feature does not create a proven edge.
- **Source licensing: NOT VERIFIED.** Dataset card says CC-BY-4.0, which does not independently settle original bookmaker redistribution/use restrictions; no public resyndication or product deployment authorized.
- **Future predictive research:** Pre-register improved, truly pregame feature sets (opposing pitcher quality, lineup eligibility, park/weather, player fatigue, role and recent matchup), book-approved source subset and odds decision timestamp; test on months/seasons and unseen source shards/dates with independent holdouts. Freeze entire model *before* seeing test outcomes; evaluate separate prop markets, game/day blocked uncertainty, calibration and executable paired prices.
- **True forward validation:** Only pre-kickoff captured live model decisions and verifiable odds belong in official Sports Zenith Brain Record. Historical reconstructed predictions must remain clearly labeled backtests.

## Research-only code, reports and verified safeguards

New source/analysis components under `intelligence_warehouse/betting_v2/`:
- `hf_mlb_prop_expansion.py` (result-blind multi-shard exact-book-time quote selection)
- `hf_mlb_prop_expanded_analysis.py` (official identity/grade/paired odds/strict-asof audit)
- `hf_mlb_prop_fair_lane.py` (separate per-market chronological holdouts with 90/95/98.75% game-bootstrap intervals)
- `hf_mlb_prop_locked_holdout.py` (immutable historic external market and market-plus-trend coefficients)
- `hf_mlb_prop_official_derived.py` (strict analytic outcome recovery **only** where publisher provided no grade)
- `hf_mlb_prop_unseen_shard.py` (July shard validation and locked-fit evaluation with frozen SHA checks)

Tests include `tests/test_hf_mlb_prop_expansion.py`, `test_hf_mlb_prop_expanded_analysis.py`, `test_hf_mlb_prop_fair_lane.py`, `test_hf_mlb_prop_locked_holdout.py`, `test_hf_mlb_prop_official_derived.py`, `test_hf_mlb_prop_unseen_shard.py`, plus original audit, as-of and pairing tests. All were written with red/green checks and must pass before future reuse.

Frozen evidence under `reports/hf_mlb_expanded_20261008/` and `reports/hf_mlb_unseen_0017_20261008/` includes source candidates/selection manifest, official audit, as-of audit, fair-market Brier comparisons, SHA-backed frozen model and untouched July result. No new frontend deployment required.

**The next work should focus on discovering a genuine, robust independent market edge — not removing proof gates to force picks.**

## Final verification and server cleanup

- **60 Python unit/regression tests passed** (`tests.test_hf_mlb_prop_pilot`, `test_hf_mlb_prop_asof`, `test_hf_mlb_prop_pairing`, `test_hf_mlb_prop_expansion`, `test_hf_mlb_prop_expanded_analysis`, `test_hf_mlb_prop_fair_lane`, `test_hf_mlb_prop_locked_holdout`, `test_hf_mlb_prop_official_derived`, `test_hf_mlb_prop_unseen_shard`, `test_betting_v2_regime_history`, and `test_betting_v2_regime_current`). Research Python modules compiled without errors.
- Fresh independent replay from the persisted 0017 source-candidate manifest and **original SHA-256 sealed hits model** produced **byte-for-byte identical** full July `unseen_official_audit.json` and `unseen_asof_audit.json`, and identical frozen holdout metrics. Temporary replay artifacts were removed. These tests validate implementation repeatability, **not** betting profitability.
- Five direct, read-only official MLB StatsAPI boxscore spotchecks across the five July dates matched the analytic results (5/5 HTTP 200 and exact player hits count).
- Four **explicitly temporary** parquet shard files under `/tmp/hf_mlb_cohort20261008/` were removed after processing, freeing **186,721,986 bytes**. All source-candidate manifests, official audit reports, frozen model and result evidence in permanent Sports HULK `reports/` were verified present. No historic Sports HULK source/graded/forward data was deleted.
- The Sports Zenith production API health endpoint returned **HTTP 200**. No live UI restart or betting model deployment occurred because no edge was validated.
