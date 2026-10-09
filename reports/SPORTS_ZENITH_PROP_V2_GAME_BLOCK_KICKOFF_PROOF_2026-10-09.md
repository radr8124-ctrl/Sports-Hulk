# Sports Zenith — Prop V2 independent-game holdout and original kickoff conflicts

**Verified October 9, 2026 UTC on existing Sports Zenith VPS.** Quant model data/validation fix, not a website redesign or betting selection promotion.

## Live, reproducible diagnostic BEFORE repair

The original `intelligence_warehouse/betting_v2/build_prop_v2.py` sorted graded props by source snapshot time, but then created walk-forward train/test sets by individual prediction **row** rather than game group. `block_key` was used only after fitting, for bootstrap metrics. In six existing settled-history lanes there were **552 test rows out of 823** whose exact game block also appeared in that fold's training set. This is actual **same-game train/test outcome contamination**, but does not independently prove individual input-feature values were captured after the event.

By lane (raw historical pre-fix): NFL PrizePicks 42/46 overlapping test rows; NFL sportsbook props 65/71; NHL props 203/317; NHL PrizePicks 97/150; MLB props 102/175; MLB PrizePicks 43/64. NBA prop lanes had zero validated graded training history.

## Surgical fix (no real wagers, no confidence reductions)

- Retain existing graded/raw history files and frozen forward ledger. Require an actual source event/game identifier, valid original event start, and a prediction captured strictly before start to enter model history. Do not create row-based pseudo-independent games when event identity is missing.
- New `game_blocked_rolling_origin_folds` holds **entire games**, with deterministic chronological first-prediction ordering. No game can appear in both training and testing in any fold.
- A historical training game must start **at least 24 hours before** the earliest prediction in the later test fold; every train prediction must predate that cutoff. This is a conservative assumed postkickoff result-availability **proxy**, NOT independent evidence of the original official Final publication time.
- Reject model validation if fewer than **30 independent historical games** or fewer than **15 independent available training games**. Unqualified lanes are labeled insufficient/untrained and fall back to the sportsbook market baseline.
- Explicit source conflict quarantine: for any source game whose original kickoff times disagree by more than **three minutes**, exclude **the entire game** from training, calibration, metrics, confidence and final model coefficient fitting. Original graded source rows remain unchanged. Real NHL prop history had 18 such games (347 prediction rows) and NHL PrizePicks history six games (40 rows). These are an honest source ambiguity, not zero-value historical game results.
- In the generated validation receipt, report the historical original eligible rows, whole-game kickoff-conflict count/rows, retained model rows/independent games, test fold source-time provenance and zero game overlaps. Existing model proof/expected-value/promotion cutoffs unchanged.

## Production test and result

- Focused validation/source/odds regression suite: **37 tests passed**. Ten directly address strict game-block independence, result-age embargo, small independent game counts, conflicting source kickoffs, missing clocks, and original-data preservation.
- Full bounded real Prop V2 production rebuild: exit **0**. Website HTTPS health HTTP **200**, public and built V2 research JSON byte-equal to generated current payload. Original `PROP_V2_FORWARD_LEDGER.jsonl` **SHA256 byte-for-byte unchanged** against the pre-edit backup.
- Latest current V2: **756** research candidates; **0 SHADOW PLAY**, **0 MONITOR**, **756 PASS**.
- After kickoff conflicts quarantined: NHL props **287 model-history rows / 31 games**, 3 clean test folds with 12 distinct test game blocks, market-reference deployment, **no demonstrated model edge**. NHL PrizePicks **260 rows / 43 games**, 4 clean folds with 17 distinct test game blocks, market-reference deployment, **no demonstrated edge**.
- NFL prop/PrizePicks histories: 15 distinct games each; MLB props 16 and MLB PrizePicks 14; all remain insufficient for trustworthy block-independent model validation. NBA player-lane histories still missing. Candidate availability does not equal proof of a positive edge.

## Explicit limitations and recovery

- The original source data does NOT establish the official historic Final-publication timestamp or every original feature's as-of availability. The 24-hour postkickoff cutoff is a conservative research proxy, not a claim of fully prospective outcome/data provenance.
- Secondary read-only CLV audit: 46 closed game-market observations currently use `LAST_PRESTART_MARKET_SNAPSHOT`; 11 of their "close" source quotes were captured over six hours before kickoff and four were before the recorded selection entry. These must be isolated by source quality before interpreting CLV as true close execution evidence.
- A separate pre-existing `tests.test_mlb_forward_id_capture` fixture expects a fictional year-2099 source row to pass the official MLB schedule gate. That specific test returned zero candidate rows on **both the original pre-edit module and the revised module**, so its one failing expectation is pre-existing and unrelated to this game-blocked validation patch. Do not misreport it as a new regression or as a passing test.
- Originals and the forward ledger were SHA256 copied before modification to `.deploy_backups/prop_v2_game_block_holdout_before_20261009T2130Z/` on the same VPS and readback verified. Git versioning of new code, tests and this report is separate from runtime model state. **Independent off-VPS raw-data recovery remains unverified.**
- No user Survivor picks, fantasy/DFS entries, actual wagers, or historical graded outcomes were written by this validation fix.

## Follow-up actions

Audit all feature-publication clocks vs the frozen pregame snapshot, qualify genuine closing-line sources (not any older prestart price) for CLV, and re-establish a prospective market-beating benchmark only after 30+ independent completed test games in a homogeneous sport/market/competition context. A power/Shin devig alternative or correlated-entry payout model must be held in shadow research until source odds and payout calibration prove improvement.
