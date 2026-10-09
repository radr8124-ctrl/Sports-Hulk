# Sports Zenith — Hugging Face dataset feasibility (read-only)

Date: 2026-10-08. Scope: potential historical sports odds and player-prop training data, **not** Sports HULK official forward picks. No external datasets imported, no paid archives purchased, no private Sports Zenith records uploaded, no model rules modified.

## Integration status
- Hugging Face was authenticated to the ChatGPT connector for user account Radr8124, with read-repo permissions. Hugging Face connector `dataset_search` was disabled by server configuration; repo details were accessible.
- Followed the official Hugging Face Dataset Viewer read-only workflow using `https://datasets-server.huggingface.co/splits`, `/first-rows`, `/size`, and limited `/rows` API queries against verified public repos.

## Candidate 1: SmartStake/mlb-player-props — pilot-worthy with limitations
- URL: https://huggingface.co/datasets/SmartStake/mlb-player-props
- Dataset card claims CC-BY-4.0. Independently reported Viewer: **621,391,637 rows**, 11 fields; ~901 MB compressed parquet, ~83.7 GB expanded memory. Full raw ingest could exceed reasonable memory. Use filtered/chunked queries only; review third-party sportsbook terms and attribution before product use.
- Schema inspected: `game_id`, `start_time`, `player`, `market`, `line`, `side`, `book`, `ts`, `odds`, `result`, `won`.
- Sampled 300 rows across offsets 0/100/10000. All 300 had timestamp before game start; **all 300 were the same event/player/market/book**. Repeated minute snapshots do not create independent proof games.
- Sampled sparse positions 1M, 100M, 300M, 600M: other dated games/players exist, with both graded and NULL `won` values. Coverage roughly March–July 2026. Some records have no result and must be excluded from win/loss model validation.
- **Limitations:** opaque `game_id` like `m~1371d3f8` is not MLB gamePk; no official MLB team identifier, player ID, or stated timezone offset in columns. Must map identity to official MLB fixtures/box scores, verify outcome and player-market semantics, and confirm local UTC assumptions before training.
- Status: CONDITIONAL RESEARCH DATASET. Good pilot candidate for historical prop odds and separate backtests, NOT automatically accepted for live official forward performance.

## Candidate 2: oliviersportsdata/NFL-Multi-Market-Timestamped-Odds-Team-Stats — demo only
- URL: https://huggingface.co/datasets/oliviersportsdata/NFL-Multi-Market-Timestamped-Odds-Team-Stats
- Downloaded only the free 5,410,794-byte `NFL_SAMPLE.csv` to memory (no persisted source files). Verified **26,169 rows** across **18 unique NFL Game_IDs**, 2 books, 3 markets.
- `Is_Live=0`, `Is_Suspended=0`: **8,884 pre-match non-suspended snapshots** from 18 games. ML rows with both sides priced: **3,819 rows from 18 independent games**. Games, not odds snapshots, determine validation sample size; 18 < 25-event minimum. Provider's pregame flags need independent kickoff-time audit because schema has `Date` but no explicit kickoff timestamp.
- Hub license is `other` / described as single-user-commercial; the provider markets the full archive separately for money. Do not purchase or import until commercial terms are reviewed and user explicitly approves any payment.
- Status: SCHEMA DEMONSTRATION, not enough games in the free sample to validate Sports Zenith's independent model.

## Candidate 3: edushinka/market-calibration — advertised only, viewer blocked
- URL: https://huggingface.co/datasets/edushinka/market-calibration
- Repository description claims 36,476 fair-probability/outcome observations across five sports; metadata states CC-BY-4.0.
- Read-only Dataset Viewer `/splits` returned HTTP 500, `/first-rows` HTTP 404. No trustworthy schema/sample data was accessed; cannot count as ready-to-use training data.
- Status: DEFER pending working accessible raw files and provenance.

## Other lower-priority findings
- `Oronto/mlb-game-prediction-data`: small mixed CSV repository, not a verified timestamped pregame probability archive; postgame statistics invite temporal leakage. Avoid as pregame model training source until audited.
- `edushinka/line-movement`: small aggregate league-level measurement dataset, not individual settled game selections. Useful as market research, not individual grade history.

## Required next read-only validation pilot
1. For SmartStake, sample a *bounded*, representative number of distinct games, not consecutive adjacent rows; pull only needed fields through parquet/Dataset Viewer.
2. Verify `ts < start_time`, timestamp timezone, valid/paired odds, game and player identity, real official box scores, market settlement, and what missing `won` means.
3. Join at least 25 unique event IDs with actual official MLB gamePk and test a **chronological out-of-sample split**. Data provider IDs alone do not establish official matching.
4. Keep externally reconstructed historical *backtests* separate from Sports Zenith's frozen *forward* predictions. No artificial promotion to PLAY and no changes to live models before passing validation and user approval.
5. If a paid dataset/API is needed, check entitlement, license and total cost first; do not auto-purchase.

This document records the authenticated HF app discovery and direct public viewer sample checks; no site deployment was necessary.
