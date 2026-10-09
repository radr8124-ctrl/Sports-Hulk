# Sports Zenith — Hugging Face MLB historical player-prop pilot

**Date:** October 8, 2026 · **Stage:** read-only source and model feasibility · **Outcome:** bounded 25-independent-game milestone met with 54 verified games. **Production authorization:** NOT GRANTED. No current bets, props, results, model thresholds, forward ledgers or user picks were modified.

## Objective and evidence source

The user authorized the next step from `reports/HUGGING_FACE_BETTING_DATA_READ_ONLY_FEASIBILITY_2026-10-08.md`: validate at least 25 distinct external MLB games, match provider identities to official game/player results and pre-kickoff odds, then conduct a *strictly chronological* out-of-sample baseline vs pregame-feature experiment, keeping it separate from forward records.

Public Hugging Face dataset: [SmartStake/mlb-player-props](https://huggingface.co/datasets/SmartStake/mlb-player-props). Dataset card advertises **CC-BY-4.0**. That does not automatically establish the publisher's right to resell, redistribute or use underlying sportsbook data commercially. No bulk data was downloaded and no paid action taken.

Dataset Viewer reports **621,391,637** rows. To avoid equating book/minute snapshots with independent events, **72 equally spaced row offsets** were sampled read-only with `length=1` per request, spanning March–July 2026. This is an **offset-stratified convenience sample**, not an unbiased random sample by game, sportsbook or proposition type.

Original provider columns: `game_id`, `start_time`, `player`, `market`, `line`, `side`, `book`, `ts`, `odds` (decimal), `result`, `won`. Provider's `m~...` game IDs are opaque and have no implicit MLB `gamePk` meaning. Odds are one-side decimal prices, not de-vigged fair market probabilities.

## Official identity, timing and grading audit

Every sampled provider row was independently matched to Sports Zenith's existing `intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_HISTORY.csv`, sourced from official MLB StatsAPI boxscores. The validator requires the *unique* official same-player regular-season game within **3 minutes of provider start**, handles accented names (e.g. **Suárez, Herrera, Narváez**), checks the odds timestamp is **strictly before official game start**, checks the official per-player count for the *precise prop market*, and verifies the over/under/push logic and vendor `won` flag against that count. Naive provider timestamps were assumed UTC ONLY when the official kickoff match validated the assumption.

| Evidence status | Rows | Treatment |
| --- | ---: | --- |
| **VERIFIED_HISTORICAL** | **54** | One distinct MLB official gamePk each; accepted for bounded research only |
| Missing source outcome (`won`/`result`) | 6 | Excluded |
| Unmatched or nonunique official player/game start | 9 | Excluded |
| Provider result disagreed with MLB official stat | 3 | Excluded |
| **Total sampled** | **72** | 72 distinct provider IDs; 54 distinct verified official game IDs |

All 54 accepted quotes preceded official kickoff. Maximum source-start vs official-start mismatch was **one minute**. Validated rows included **27 sportsbooks**, six prop types: hits 17, total bases 13, RBIs 10, home runs 7, strikeouts 5, batting walks 2. Accepted game dates span March 28–June 18, 2026.

Three explicit conflicts excluded: **Nick Kurtz** (provider 2 hits vs official 0, gamePk 822910), **Garrett Mitchell** (provider 5 total bases vs official 0, gamePk 824998), **Shea Langeliers** (provider 0 total bases vs official 1, gamePk 824991). A separate live read-only MLB StatsAPI boxscore call returned HTTP 200 for six sampled games and independently corroborated these conflicting official counts as well as three accepted player outcomes.

## Pre-game player features, reconstructed without leakage

The generated pregame player feature CSV available on the server covered only **August–October**, later than the provider sample. Instead of using future statistics, the pilot reconstructed just one narrowly defined historical feature from the complete official MLB game history: last-five *completed* game mean for the matching player and stat, compared with the quoted prop line/direction. Every input was from an **official game dated strictly before the source bet quote's UTC date**. Same-day, target-game and subsequent game outcomes were excluded. Current-game official data was used only to resolve player identity and validate the eventual grade, never to construct input features.

**54/54** already-validated selections had at least five strictly prior eligible game statistics. Separate `asof_audit.json` records the latest allowed prior date and the exact evidence fields. This historical feature is an **experimental replacement from existing MLB archives**, not the original Sports HULK pregame model score at the time.

## Chronological experiment — not independent profit proof

Train: **32** independent, time-ordered games ending May 17. Holdout: **22** distinct later games starting May 18. No overlap in games or timestamps. Comparison used fixed 2026 source odds and pregame features and evaluated against *held-out official grades* only; regularized logistic calibration was trained on training outcomes only.

| Holdout approach | Brier error (lower is better) | Log loss |
| --- | ---: | ---: |
| Raw one-sided market-implied odds | 0.153030 | 0.470053 |
| Training-only recalibrated odds | 0.143443 | 0.443426 |
| Market odds + strictly earlier player-stat trend | **0.139954** | **0.436577** |

The augmented model's Brier error was **0.003489** lower than recalibrated market odds on these 22 games. This is a tiny and nonrepresentative research sample, not a demonstrated edge. It evaluates a newly created toy historical model, **not** Sports Zenith's existing HULK model. Across different *overlapping, not independent* chronological 50–80% train splits, the augmented model improved on recalibrated odds in 6 of 7 splits; at 80/20 it **worsened** (0.153744 vs 0.150975), indicating instability. Nothing here supports a claims-based winner percentage, expected value, approved PLAY or deployed change.

## Hard limitations and next gates

1. **Paired prices only partially confirmed:** A read-only 40 MB first-parquet-shard spot-check found a rigorously matched **Riley Greene player-hits** quote at the same book/time/market/line: Fanatics UNDER 0.5 at decimal 2.3 and OVER 0.5 at decimal 1.588235294; de-vigged UNDER probability **0.40847201**, raw UNDER probability **0.43478261**, same-book overround **0.06441224** (6.44%). Another verified **Matt Olson player-bases** offer had only OVER at its exact book/line/time and was correctly blocked from de-vigging. These **2 spot checks** do not establish paired-price coverage for the other 52 verified games. The larger Dataset Viewer `/filter` lookup timed out. The 40 MB parquet scratch file was removed after analysis; all 18 shards were NOT downloaded. Pairing requires exact timestamp, book, game, player, market, and line, with one nonconflicting valid price per side. Need per-game paired prices across a representative set before claiming fair-market proof.
2. **Source selection bias:** The 72 offsets are not randomized by event/market/side/price; multiple player markets were pooled. Need larger independently matched datasets, market-by-market tests, provider stratification, independent chronological seasons and uncertainty intervals.
3. **Commercial rights:** CC-BY-4.0 is the repository card label, not confirmed upstream sportsbook distribution rights. Before product use, verify the publisher's terms, third-party data licensing and attribution.
4. **Model identity:** Existing HULK pre-kickoff predictions for these exact March–July outcomes were not recorded. This experiment must remain separate from frozen forward-record ledger and cannot rewrite historical HULK picks or qualify old current plays.
5. **Independent source validation:** Continue spot-checking official MLB box scores and rejecting discrepancies; never count a repeated minute quote as another prediction/game.

**Next controlled stage** (NOT yet run): obtain timestamp-matched opposite-side sportsbook prices for a stratified independent set of distinct games; test fair-price calculations and the per-market chronological walk-forward benchmark; separately compare *actual* contemporaneous HULK snapshots if found. Larger independent holdouts and explicit safety/provenance acceptance are required before any production consideration.

## Reproducible outputs and commands

No live Sports Zenith frontend, current prop engine, betting rule, settlement ledger, or API endpoints were changed.

Code:
- `intelligence_warehouse/betting_v2/hf_mlb_prop_pilot.py` — source row + official game/player/grade validator.
- `intelligence_warehouse/betting_v2/hf_mlb_prop_asof.py` — leak-free pregame feature reconstruction and ridge-logistic **research-only** historical test.
- `intelligence_warehouse/betting_v2/hf_mlb_prop_pairing.py` — exact book, player, game, line and timestamp opposite-side odds validator (research only).
- `tests/test_hf_mlb_prop_pilot.py`, `tests/test_hf_mlb_prop_asof.py` and `tests/test_hf_mlb_prop_pairing.py` — red/green coverage for identity, grade, timestamp, future-data leakage, duplicate games, exact pairing and chronological splitting.

Frozen research output (not ingested into production):
- `reports/hf_mlb_pilot_20261008/sample_manifest.json` — the 72 bounded public source observations and offsets; repeatable without relying on a temporary `/tmp` file.
- `reports/hf_mlb_pilot_20261008/audit.json` and `summary.json` — official per-row matching decisions and counts.
- `reports/hf_mlb_pilot_20261008/asof_audit.json` and `asof_experiment.json` — feature provenance and market comparisons.
- `reports/hf_mlb_pilot_20261008/split_sensitivity.json` — seven overlapping train/holdout diagnostic splits.
- `reports/hf_mlb_pilot_20261008/paired_spotcheck.json` — two exact-book/time example checks, including one defensible fair odds pair and one one-sided rejection.

From `/home/ubuntu/sports-hulk`:

```bash
.venv/bin/python -m unittest tests.test_hf_mlb_prop_pilot tests.test_hf_mlb_prop_asof tests.test_hf_mlb_prop_pairing -q
.venv/bin/python intelligence_warehouse/betting_v2/hf_mlb_prop_pilot.py --input-samples reports/hf_mlb_pilot_20261008/sample_manifest.json --output-dir reports/hf_mlb_pilot_20261008
.venv/bin/python -m intelligence_warehouse.betting_v2.hf_mlb_prop_asof --verified-audit reports/hf_mlb_pilot_20261008/audit.json --output-dir reports/hf_mlb_pilot_20261008
```

Official MLB history provenance SHA-256 at audit time: `6d462e6f70d0eddbe1aa4dd583d41090324f681cd8f7046fc58b24050bfd3e24` (85,212,455 bytes). External verified-row audit SHA-256: `2f29a07a037557dc9f8901838424866a9f431f69aecd20ce3a3ffad30971e7f7` before any reproducibility rerun.

**Research acceptance: PASS** (independent game count and as-of checks). **Production/forward betting approval: NOT CLAIMED.**

## Final repeatability and service checks

- Unit/related regime tests: `.venv/bin/python -m unittest tests.test_hf_mlb_prop_pilot tests.test_hf_mlb_prop_asof tests.test_hf_mlb_prop_pairing tests.test_betting_v2_regime_current tests.test_betting_v2_regime_history -q` → **27 passed**, zero failures.
- All three new research-only Python modules compiled successfully.
- Replaying the source samples from the *persisted* `sample_manifest.json` reproduced exactly **54** accepted independent games and **0.139954** holdout augmented Brier. Replayed `audit.json` bytes matched the original SHA-256 exactly; temporary replay files removed.
- Downloaded/inspected exactly one 40,343,480-byte external parquet shard containing 26,223,713 timestamp observations across 213 row groups. It was **removed from `/tmp`** after selecting two bounded odds-pair spot checks. The much larger source archive was not copied onto production storage.
- Public commercial Sports Zenith health endpoint responded **HTTP 200** after pilot verification. No production website or recommendation logic was changed.
