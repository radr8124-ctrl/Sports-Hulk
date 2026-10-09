# Sports Zenith — Hugging Face continuity, source evaluation, and safe restart

**UTC October 9, 2026.** Research only. No live betting decisions changed, no historical picks or model versions rewritten, and no paid Hugging Face Jobs submitted.

## What survived from prior Hugging Face work

- The authenticated Hugging Face plugin is connected. The Jobs account returned **zero historic or running HF cloud jobs** in its Jobs list during this audit. Prior HF experiments did not require a continuously hosted cloud job; research pulled public datasets and ran local Sports Zenith Python experiments on the VPS.
- Existing research using public dataset **SmartStake/mlb-player-props** remains present under `reports/hf_mlb_pilot_20261008/`, `reports/hf_mlb_expanded_20261008/`, and `reports/hf_mlb_unseen_0017_20261008/` with `hf_mlb_prop_*.py` research modules and tests. HF confirms the dataset was last updated July 9, 2026, and it contains **March–early July**, not today's October fixture feed.
- Previous source verification: 318 vendor-graded and independently source-matched historical selections on 101 official MLB games; the source held many repeated minute-by-minute sportsbook quotes, **not 621M independent training games**.
- The original *untouched July shard* contains 46 official hits-game outcomes. Its frozen odds-only model Brier was **0.252171**; frozen market+prior-player-stat Brier **0.254329** (worse). Frozen model file rechecked against original SHA-256 `2efee022990b0a9d7f0f9be06c7767ab99f04a841bb1dbde8ef57a5e2b3826a6`; grade report still says `production_play_approved=false`. No experimental edge was carried into live betting.
- Existing HF researcher regression: **60 tests pass**, no errors (October 9).

## New Hugging Face dataset source screened

- Public dataset **SmartStake/mlb-lineup-reactions**, last updated July 23, 2026 (Hub metadata); Dataset Viewer reports **85,030,536 time/price rows**, not independent games. This could be useful for historical lineup announcement and sportsbook reprice behavior, but it has *no attached betting outcome* and is **not current live lineup news**. Dataset license card is CC-BY-4.0; upstream sportsbook commercial rights are not independently verified.
- In a bounded, predetermined **12-offset x 2 rows** stratified source-screening sample, queried via public HF Viewer, **24 original records represented 12 source event IDs and 12 provider game IDs**.
- Strict import review (new `intelligence_warehouse/provider_integrations/hf_lineup_research.py`) requires exact independently mapped official MLB event AND matched player, non-suspended mainline quote, as-of pregame source time, sensible odds and correct quote-vs-announcement time. **No sample record met that bar**: 12 were alternative-line prices, 12 lacked uniquely verified official game crosswalk. Two sampled rows did match a previously verified provider game but were alternate lines. This is a thin convenience sample, not a claim that the whole HF source is unusable.
- Public sample and source hash persisted (PRIVATE local research only): `reports/hf_mlb_lineup_reactions_20261009/original_public_sample.json`, source manifest digest `d615a6a42a08c08446ae7252bd8d08738e0a69aa087a9d8de48ed58789f221a6`. Original sample file SHA-256 `9ee10df7f714a1a1ec545d127014df2a0f0855ec459fc2664367e1787f974ce2`.
- Receipt with source-to-official reason codes: `reports/hf_mlb_lineup_reactions_20261009/research_audit_d615a6a42a08.json`. A separate **no-network replay** matched all original row decisions, event counts, game counts, missing reasons and both source/checkpoint hashes.
- New source guard tests: **10 passed**; original HF work tests: **60 passed**.
- The HF public Dataset Viewer /filter did not accept the tested query syntax (HTTP 422), and free-text search for a known source ID timed out. No bulk archive was downloaded. Those endpoints are not certified as a dependable exact-event ingestion mechanism.

## Reality check for the 70% goal

Hugging Face is genuinely useful for training/research, **not a magic new current sportsbook feed**. Additional historical data is valuable only with original event/player crosswalk, legally usable sources, pregame timestamps, independent train/holdout games, and bookmaker price and payout proof. Fancy modeling on correlated line snapshots does not turn an unproven edge into one.

The pre-registered `reports/ZENITH_70_PERCENT_FORWARD_TARGET_PREREG_2026-10-09.json` remains **UNARMED**, never rewritten. No predictor automatically promoted from this retrospective screening. Follow-up should prioritize a validated, *recent* pregame features source and unseen future settlement blocks, then HF-assisted isolated, cost-capped challenger training and blocked calibration/ROI tests against verified market odds. Do not purchase cloud compute without approval; Hugging Face Jobs uses paid compute with a positive credit balance.

## Persistence

- Code and tests go into source-controlled research-only paths, **not** live decision import paths.
- Preserve the existing historical HF scripts, old experimental output hashes, newly sampled raw public HF rows and reason-code receipt with local checksum verified recovery archive. Original dataset raw source samples must NOT be committed to a public code repository.
- The VPS-local archive is not independent off-VPS recovery. An off-server restore test remains outstanding.

## Reproduce

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m unittest tests.test_hf_lineup_research -q
.venv/bin/python -m intelligence_warehouse.provider_integrations.hf_lineup_research --manifest reports/hf_mlb_lineup_reactions_20261009/original_public_sample.json --out-dir reports/hf_mlb_lineup_reactions_20261009/<new_unique_replay_dir>
```

Do not replay into the original receipt directory: its reports have exclusive-create behavior to prevent overwriting the original source evidence.
