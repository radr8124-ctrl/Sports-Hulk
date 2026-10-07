# Betting V2 Competition-Regime Isolation Acceptance

Date: 2026-10-07
Branch: feature/betting-v2-regime-isolation
Implementation baseline: 64a9f4a
Latest main reconciled: 9550ed2
Reconciliation merge: 441204c
Spec: docs/superpowers/specs/2026-10-07-betting-v2-competition-regime-design.md
Plan: docs/superpowers/plans/2026-10-07-betting-v2-competition-regime-plan.md

## Decision

**BRANCH ACCEPTED — READY FOR MERGE APPROVAL**

The Betting V2 competition-regime isolation implementation passed its full reconciled branch acceptance checks.

The feature branch has been reconciled with the latest main and revalidated. It has not been merged into main, pushed, or used to restart the production service.

## What changed

- Added canonical competition regimes:
  - PRESEASON
  - REGULAR
  - POSTSEASON
  - UNKNOWN
- Added NBA-only regime enforcement for Betting V2 proof.
- Preserved legacy lane_key = SPORT_MARKET for compatibility/display.
- Added regime-aware proof_lane_key for NBA.
- Added regime-aware proof_version for NBA without restarting non-NBA proof identities.
- Partitioned NBA historical validation/model proof by regime.
- Prevented current NBA candidates from borrowing a model from another regime.
- Made NBA forward, price, settlement, and CLV evidence regime-aware.
- Preserved legacy forward/price/CLV rows without rewriting them.
- Added by_proof_lane forward summaries.
- Added by_regime and by_proof_lane CLV summaries.
- Prevented legacy unlabeled NBA CLV rows from entering authoritative UNKNOWN proof cohorts.
- Added row-level fallback across explicit regime source fields when season_type is blank.
- Updated Brain Record All-Markets presentation to use by_proof_lane when available.
- Preserved by_lane as compatibility-only aggregate display data.
- Preserved legacy payload rendering when proof-lane views are absent.

## Implementation commits

- 6a1843c Add Betting V2 competition regime contract
- 66994bb Partition Betting V2 proof by NBA regime
- 2b1dad2 Match current Betting V2 picks by regime
- 33019cf Isolate NBA forward proof by regime
- 32ca3d4 Separate NBA CLV by competition regime
- af73cf9 Add Betting V2 regime acceptance test
- ef9e2b8 Record Betting V2 regime isolation acceptance
- 04ad512 Harden Betting V2 unknown regime isolation
- c287522 Harden regime proof attribution
- 441204c Merge branch main into feature/betting-v2-regime-isolation

## Final review fixes

The required whole-branch review was performed as a self-review because this harness exposes no subagent dispatcher.

Four findings were fixed and reverified:

1. **UNKNOWN NBA settlement isolation**
   - Before fix: a regime-aware UNKNOWN entry could not settle from explicit UNKNOWN history.
   - RED: test_unknown_regime_nba_entry_settles_only_from_unknown_history failed with settled 0.
   - GREEN: test passed after preserving UNKNOWN history keys.
   - Known PRESEASON/REGULAR/POSTSEASON entries remain unable to cross-settle.

2. **Secondary explicit regime fallback**
   - Before fix: a blank season_type column masked a populated competition_regime field.
   - RED: current row resolved UNKNOWN instead of REGULAR.
   - GREEN: current extraction now chooses the first nonblank explicit regime source field in priority order.
   - No date/week/calendar inference was added.

3. **Legacy CLV proof contamination**
   - Before fix: legacy NBA rows without frozen proof metadata were synthesized into NBA_MONEYLINE|UNKNOWN in authoritative by_proof_lane.
   - RED: UNKNOWN proof tracked 2 instead of 1.
   - GREEN: legacy rows remain visible in aggregate/by_regime UNKNOWN reporting but are excluded from authoritative by_proof_lane unless a proof_lane_key was actually frozen.

4. **Brain Record mixed-lane presentation**
   - Before fix: All-Markets Brain Record joined proof-keyed validation to aggregate by_lane/forward.by_lane, allowing a mixed NBA aggregate to appear beside regime lanes.
   - RED: all-markets-proof-view.test.js failed because no proof-row adapter existed.
   - GREEN: regime-aware payloads render proof lanes only; legacy payloads fall back to by_lane.
   - NBA rows display their competition regime explicitly.

## Final test evidence after latest-main reconciliation

Fresh reconciled run:

- Python regime tests: **42/42 PASS**
- Existing + new commercial_web Node tests: **66/66 PASS**
- Vite production build: **PASS**
- node --check server.js: **PASS**
- Python builder syntax: **PASS**
- focused Brain Record proof-view test: **2/2 PASS**

The production build completed successfully. The earlier chunk-size warning is no longer present in the final captured build tail; the largest reported main bundle was approximately 486.57 kB.

## Runtime regeneration after reconciliation

Regenerated in dependency order inside the isolated worktree:

1. build_betting_v2_all_markets.py
2. build_betting_v2_all_markets_forward.py
3. build_clv_tracker.py
4. build_brain_performance.py

All four builders exited 0.

Generated warehouse/decision artifacts were untracked runtime data at branch baseline. They were verified in place and intentionally excluded from source commits.

## Current NBA regime result

Current explicit upstream future-game data still does not expose a usable NBA season/regime field.

Per the approved design, Sports Zenith does not infer competition regime from date, week, calendar, standings, or game timing.

Reconciled current NBA cohort:

- candidates: **111**
- UNKNOWN: **111**
- PRESEASON: **0**
- REGULAR: **0**
- POSTSEASON: **0**

Current proof-lane candidate counts:

- NBA_MONEYLINE|UNKNOWN: 1
- NBA_SPREAD|UNKNOWN: 19
- NBA_TOTAL|UNKNOWN: 91

All 111 NBA picks have:
- canonical competition_regime
- proof_lane_key ending in the same regime
- NBA-specific proof_version

No current NBA candidate was assigned PRESEASON, REGULAR, or POSTSEASON without explicit source evidence.

## Historical / model proof result

Regenerated NBA validation/model keys are regime-aware:

- NBA_MONEYLINE|UNKNOWN
- NBA_SPREAD|UNKNOWN
- NBA_TOTAL|UNKNOWN

Current unlabeled historical evidence remains UNKNOWN and is not guessed into PRESEASON or REGULAR.

If explicit PRESEASON / REGULAR / POSTSEASON history enters later, it will create separate proof lanes automatically.

## Forward proof result

Regenerated NBA forward proof lanes:

- NBA_MONEYLINE|UNKNOWN: 1 tracked / 0 settled
- NBA_SPREAD|UNKNOWN: 19 tracked / 0 settled
- NBA_TOTAL|UNKNOWN: 91 tracked / 0 settled

All three remain:

- recommendation: HOLD_PROBABILITY_PROOF_REQUIRED
- automatic promotion: false
- proof status: BUILDING_FORWARD_SAMPLE

No cross-regime promotion evidence is available or borrowed.

## CLV result

CLV output now exposes:

- by_regime
- by_proof_lane

Current regenerated CLV regime set:
- UNKNOWN

Authoritative NBA proof CLV:
- NBA_MONEYLINE|UNKNOWN: 1 tracked / 1 open / 0 closed

Legacy unlabeled NBA CLV rows remain in historical aggregate visibility but do not enter authoritative by_proof_lane unless their proof metadata was frozen.

## Brain Record result

Brain Record preserves:

- betting_v2_all_markets.current.by_proof_lane
- betting_v2_all_markets.forward.by_proof_lane
- betting_v2.clv.by_regime
- betting_v2.clv.by_proof_lane

Reconciled artifact counts:
- current proof lanes: 18
- forward proof lanes: 3

The All-Markets Brain Record table now reads proof-lane data when available and displays competition_regime for regime-aware rows.

Compatibility by_lane aggregates remain available to older consumers but are not used as authoritative promotion/readiness rows in the updated Brain Record table.

## Non-NBA continuity

NBA is the only regime-enforced sport in this checkpoint.

Non-enforced sports:
- may carry explicit competition_regime metadata;
- retain existing proof_lane_key shape equal to lane_key;
- retain existing proof_version behavior;
- retain legacy forward/price identity.

CFB behavior was explicitly covered by tests and did not rebaseline.

## Append-only ledger verification

Before reconciled regeneration, byte snapshots were frozen for:

- BETTING_V2_ALL_MARKETS_FORWARD_LEDGER.jsonl
- BETTING_V2_ALL_MARKETS_PRICE_TIMELINE.jsonl
- BETTING_V2_PICK_LEDGER.jsonl
- BETTING_V2_PRICE_TIMELINE.jsonl

Latest reconciliation pass:

- all-markets forward ledger: 732,224 -> 732,224 bytes
- all-markets price timeline: 952,573 -> 956,073 bytes
- Betting V2 pick ledger: 43,704 -> 43,704 bytes
- Betting V2 price timeline: 1,492,888 -> 1,492,888 bytes

Every post-run ledger began with the exact pre-run byte sequence.

Result: **APPEND_ONLY_PREFIX_PASS**

No prior evidence byte was rewritten.

## Isolated reconciled runtime smoke

Commercial server launched from the reconciled worktree on temporary port 8545.

Results:

- GET /api/health -> HTTP 200 / status ok
- GET /brain_performance.json -> HTTP 200 / READY
- Brain current proof lanes -> 18
- Brain forward proof lanes -> 3
- POST /api/ask "What is the best NBA bet right now?" -> HTTP 200
- Ask intent -> best_bet
- Ask status -> RESEARCH_ONLY
- Ask confidence -> WAITING / NO PLAY
- trace_id present -> yes
- take -> "No current NBA bet has cleared the V2 PLAY gate."
- no ERROR
- no OUTPUT_VALIDATION_FAILED

Result: **ISOLATED_SERVER_SMOKE_PASS**

## Latest-main reconciliation

Main advanced during isolated development with:

- ba65dae Add premium Bet Lab learning workflow
- 9550ed2 Simplify parlays with plain English guidance

Actual main-only files did not overlap the Betting V2 regime implementation files.

The feature branch merged latest main at:

- 441204c Merge branch main into feature/betting-v2-regime-isolation

Merge conflicts: **0**

All acceptance tests were rerun after this reconciliation.

## Recorded rulings

1. **CLV regime bridge**
   - When legacy BETTING_V2_CURRENT lacks regime metadata, BETTING_V2_ALL_MARKETS_CURRENT may provide normalized regime only through exact sport + game_key matching.
   - Missing/conflicting evidence becomes UNKNOWN.
   - No date inference.

2. **Live verification**
   - Production service was not restarted from the isolated worktree.
   - Isolated HTTP verification was used.
   - Production restart remains a post-merge verification.

3. **Current NBA unlabeled games**
   - Current NBA games remain UNKNOWN until explicit upstream regime metadata survives into the current decision feed.
   - Reduced model coverage is preferred to proof contamination.

4. **Generated runtime artifacts**
   - Untracked runtime warehouse files are verified but not committed as source.

5. **Main drift**
   - Latest main was reconciled into the feature branch before final acceptance.
   - No overlap/conflict occurred.

## Remaining action

The branch is technically ready.

The only remaining action is a user-approved integration step:

1. merge feature/betting-v2-regime-isolation into main;
2. regenerate affected artifacts from main;
3. restart sports-hulk-commercial.service;
4. verify live /api/health HTTP 200;
5. run one live Game Scout Best Bets smoke query;
6. record the production merge/health result.

No production merge or restart is performed by this receipt.
