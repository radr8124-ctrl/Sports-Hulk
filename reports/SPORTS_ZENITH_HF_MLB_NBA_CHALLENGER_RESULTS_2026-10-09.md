# Zenith — Hugging Face challenger research acceptance (October 9, 2026)

**Status: DATA VERIFICATION PASS; predictive advantage NOT PROVEN; live betting deployment DENIED.**

This continuation reused the previously authenticated Hugging Face integration and official Sports Zenith data. The historical Hugging Face studies ran on the existing VPS with CPU NumPy models; Hugging Face Jobs did not run, charge, or store any project data. None of the app's current predictions, models, settlement ledgers, bankroll settings, PrizePicks calculations, survivor selections or sportsbook prices were changed.

## 1. Previous Hugging Face pilot protected

- Earlier SmartStake MLB player-prop research remained on server, including 101 official MLB games with verified paired lines and a locked July holdout containing 46 independent hits games.
- The previously frozen market-only model performed better than the previous advanced model on the original July hits holdout, 0.252171 versus 0.254329 Brier. This confirmed a failed improvement, not a working production model.
- 60 existing historical Hugging Face regression tests passed and the original locked hits-model SHA-256 matched its saved acceptance receipt. The new lineup-reaction source guard's 10 tests also passed.
- New SmartStake lineup-reaction dataset screened: 85,030,536 *quote rows*; twelve deterministically spaced source events, 24 price snapshots. Zero valid fully independently game+player+main-line verified quotes. This does not imply the entire data source lacks useful information; new independent crosswalks are required. No live ingestion attempted.

## 2. Fixed historical multi-market MLB test (previously inspected July)

Preregistration: `reports/HF_ZENITH_MULTI_MARKET_SECONDARY_JULY_PREREG_2026-10-09.json`, committed **before** running the four-market model. Locked input SHA manifests and fixed ridge penalty 16, selection filter 70% probability +3% predicted paper value. Source: Hugging Face `SmartStake/mlb-player-props`, exact same-book/timestamp opposing priced pairs, unique official event/player/stat matching, strictly earlier actual player-form stats and official analytic outcomes. External research, not genuine 2026 contemporaneous Zenith forward picks.

| Market | Earlier games used for fit | July test games | Raw fair sportsbook Brier | Market-only calibrated Brier | Market + prior player stat Brier | Market-only vs advanced gain |
|---|---:|---:|---:|---:|---:|---:|
| Player hits | 94 | 46 | 0.258127 | 0.254916 | 0.254513 | +0.000402 |
| Total bases | 92 | 44 | 0.264673 | 0.287647 | 0.289934 | -0.002288 |
| RBIs | 94 | 46 | 0.190172 | 0.192604 | 0.192450 | +0.000154 |
| Strikeouts | 37 | 15 | 0.261969 | 0.324767 | 0.323424 | +0.001344 |

Brier: lower is better; positive gain means the advanced model marginally beat its *fitted market-only comparator*, not necessarily the raw source sportsbook. Every game and calendar-day bootstrap interval included zero. Only **five distinct July calendar days** were represented. Combined 70%-probability and +3%-paper-EV screen produced no advanced-model qualifiers across the four markets. The only two historical market-only strikeout qualifiers won 1/2 for -28.5% quoted-price paper ROI; neither is meaningful performance proof. No live training or model promotion occurred.

Reproducible code/test: `intelligence_warehouse/betting_v2/hf_multimarket_secondary.py`, `tests/test_hf_multimarket_secondary.py` (13 passed). Original frozen historical comparison: `reports/hf_mlb_multimarket_secondary_20261009/secondary_comparison_summary.json`. Individual original-game prediction research remains on the VPS/private local backup and must not be committed to a public repository or the commercial site. Preregistration original SHA: `da5418a2b55a6a72521ccdc92940e98b40c6c604183f6409b492666914eeaf40`.

## 3. Newly discovered HF NBA historical odds-and-results source

Hub dataset: `minmaxxxer/nba-closing-lines-ats-2025-26` (updated October 5, 2026). Source card claims CC-BY-4.0 and bookmaker-consensus closing prices, but its underlying sportsbook records, bookmaker price timestamps, upstream redistribution rights and executable offered prices are **not independently verified**.

- Public HF dataset had **1,315 source NBA games** (1224 regular, 91 postseason including six play-in games).
- Joined by original NBA home/away names, exact independently recorded ESPN start time within three minutes, unique matchup and independently official Final score. **1,305 of 1,315 games** matched genuine official event/time/final scores and independent ATS + total result calculation.
- Of these, **1,214 were verified regular-season games** eligible for the fixed study. The 91 postseason games and ten unmatched game identities were excluded, not guessed or relabeled.
- Original Hugging Face sample is **101,323 bytes compressed**; saved privately as `reports/hf_nba_closinglines_audit_20261009/SOURCE_original_hf_nba_2025_26.parquet` with SHA-256 `6364a163288e10b207d694043c0f11802737a1b5571b4604d274c9cc883974e6`. Frozen official comparison source is also retained privately.
- No current 2026–27 NBA preseason results were silently mixed with the historic 2025–26 regular-season sample.

### Frozen NBA baseline-vs-challenger evaluation

Preregistration before new predictions: `reports/HF_ZENITH_NBA_REGULAR_SEASON_MODEL_PREREG_2026-10-09.json` with SHA-256 `d90dc358c4f5a01c9340beede23348dc0b760d1827c014d04a0e47ad76cd25de`. Fixed formula and same regularization 25 for three market types. Earlier 711 independently verified regular-season games, Oct 2025–Jan 2026, train. Later **503 distinct** February–April 2026 regular-season games are the historic test. Dates and market separation fixed *before fitting*. Closing-line source lacks original bookmakers' capture times, so this is **a retrospective as-of-unverified diagnostic**, not a backtest using guaranteed historical executable snapshots.

| 2025–26 NBA market | Raw publisher sportsbook Brier | Earlier-trained market-calibrated Brier | Frozen expanded model Brier | Independent held-out games | Statistical advantage proven |
|---|---:|---:|---:|---:|---|
| Total over/under | **0.250004** | 0.252564 | 0.254588 | 503 | NO |
| Home spread cover | 0.249909 | 0.249456 | **0.248672** | 503 | NO |
| Home moneyline | **0.164504** | 0.166583 | 0.167687 | 503 | NO |

The expanded spread model's 0.000785 Brier improvement vs trained market-only did not survive either game or 65-calendar-day bootstrap uncertainty. The totals and moneyline models were **worse** than the publisher's raw sportsbook probabilities. There is **no verified predictive edge**, just a much larger historical test.

A 70%-probability conditional market favorite selection from the publisher's original close home-win probabilities yielded **225/257 wins = 87.55%** on 51.09% of available holdout games. This is the **sportsbook's favorite probability, not the Zenith model's proprietary accuracy or profit**. The market-only fitted model selected 245 of 503 games and won 215 (87.76%); the advanced model 247 and won 215 (87.04%). None had original timestamped executable odds or confirmed payout, so **profit/ROI is unavailable**, not positive. Totals and spreads produced zero 70%-probability high-confidence qualifiers. This illustrates why a universal 70% hit rate is not a useful proof of beating bookmaker vig.

Source verification and model code: `intelligence_warehouse/betting_v2/hf_nba_market_challenger.py`. Test suite: `tests/test_hf_nba_market_challenger.py` (12 passed). Both independent NBA source-audit and private per-game prediction outputs replayed **byte-for-byte identically**, and all saved aggregate model metrics matched on rerun. Results: `reports/hf_nba_closinglines_audit_20261009/nba_research_comparison_summary.json`; original score/review receipts and source protected locally.

## 4. No accidental model promotion, sensible next stage

Do NOT train one generic NBA+MLB+NHL+NFL pick model to chase 70%. Separate preseason/regular/playoff regimes, player/game/betting-market types and source as-of timestamps. Best work next:
1. Collect **authentic source-timestamped prior-to-tipoff** NBA and NHL book odds with independent ESPN/NHL event and player IDs from the existing paid providers (SportWizzard, Propline), before purchasing any extra provider.
2. Add independent verified pregame lineup, minutes/usage, injuries, starters and availability *only where source time predates the quoted line*. No retrospective game stat leakage or false confirmation.
3. Freeze a selective challenger on games that **have not occurred yet**; compare future, one-game-block outcome and priced unit ROI to a verified no-vig source bookmaker, not win rate alone.
4. Preserve matched IDs, bookmaker, line/price, source time, last pregame update, model version, frozen prediction, official Final grade and model-vs-market Brier/CLV in durable versioned records.
5. Require an independent off-VPS backup restore. Local checksums alone do not prove independent disaster recovery.

**No Hugging Face paid Jobs were created**, no API subscription purchased, no public sportsbook original price history redistributed, no wager placed or current live model altered.
