# Betting V2 Competition-Regime Isolation Acceptance

Date: 2026-10-07
Branch: feature/betting-v2-regime-isolation
Implementation baseline: 64a9f4a
Implementation head before receipt: af73cf9
Spec: docs/superpowers/specs/2026-10-07-betting-v2-competition-regime-design.md
Plan: docs/superpowers/plans/2026-10-07-betting-v2-competition-regime-plan.md

## Decision

The Betting V2 competition-regime isolation implementation passed its isolated acceptance checks.

This receipt records branch-level acceptance only. The branch has not been merged into main and production was not restarted from the worktree.

## What changed

- Added canonical competition regimes:
  - PRESEASON
  - REGULAR
  - POSTSEASON
  - UNKNOWN
- Added NBA-only regime enforcement for Betting V2 proof.
- Preserved legacy lane_key = SPORT_MARKET for UI/display compatibility.
- Added regime-aware proof_lane_key for NBA.
- Added regime-aware proof_version for NBA without restarting non-NBA proof identities.
- Partitioned NBA historical model/validation proof by regime.
- Prevented current NBA candidates from borrowing a model from another known regime.
- Made all-markets NBA forward and price identities regime-aware.
- Made NBA settlement regime-aware when explicit regime exists.
- Added by_proof_lane forward summaries.
- Added regime-aware CLV keys/metadata and by_regime/by_proof_lane summaries.
- Confirmed Brain Record preserves the new proof structures without requiring a Brain builder redesign.
- Preserved append-only historical ledgers.

## Task commits

- 6a1843c Add Betting V2 competition regime contract
- 66994bb Partition Betting V2 proof by NBA regime
- 2b1dad2 Match current Betting V2 picks by regime
- 33019cf Isolate NBA forward proof by regime
- 32ca3d4 Separate NBA CLV by competition regime
- af73cf9 Add Betting V2 regime acceptance test

## TDD / regression evidence

Final fresh post-commit run:

- Python regime tests: 38/38 PASS
- Existing commercial_web Node tests: 64/64 PASS
- Vite production build: PASS
- node --check server.js: PASS
- git diff --check: PASS

The production build retained the pre-existing Vite chunk-size warning for a bundle slightly above 500 kB. Build exit code remained 0.

The isolated npm install reported 7 dependency-audit findings in the existing lockfile (2 moderate, 5 high). Dependency upgrades were not part of this regime-isolation checkpoint.

## Runtime regeneration

Regenerated inside the isolated worktree:

1. build_betting_v2_all_markets.py
2. build_betting_v2_all_markets_forward.py
3. build_clv_tracker.py
4. build_brain_performance.py

All builders exited 0.

Generated warehouse/decision artifacts were untracked runtime data at branch baseline. They were verified in place and intentionally not added to Git.

## Current NBA regime result

The current NBA future-game decision and market-fusion sources do not expose explicit season/regime metadata.

Per the approved spec, Sports Zenith does not infer regime from date, week, or calendar.

Therefore the regenerated current NBA cohort is:

- candidates: 111
- UNKNOWN: 111
- PRESEASON: 0
- REGULAR: 0
- POSTSEASON: 0

Current NBA proof lanes:

- NBA_MONEYLINE|UNKNOWN
- NBA_SPREAD|UNKNOWN
- NBA_TOTAL|UNKNOWN

No current NBA candidate was assigned a REGULAR proof lane without explicit source evidence.

This intentionally reduces model coverage until the upstream current feed preserves explicit regime metadata, but prevents preseason/regular/postseason proof contamination.

## Historical NBA proof result

Settled historical rows with explicit regime are partitioned when available.

Historical rows lacking explicit regime remain UNKNOWN; they are not guessed into PRESEASON or REGULAR.

The regenerated current model/validation inventory therefore does not manufacture a REGULAR proof cohort from unlabeled history.

## Non-NBA continuity

CFB remained non-regime-enforced in this checkpoint.

Acceptance assertion:

- CFB current candidates checked: 5
- every CFB proof_lane_key remained equal to its existing lane_key
- no CFB forward-key reset was introduced by NBA regime isolation

Other non-enforced sports retain legacy proof identity behavior while being able to carry regime metadata when explicitly available.

## Append-only ledger verification

Pre-run byte snapshots were frozen for:

- BETTING_V2_ALL_MARKETS_FORWARD_LEDGER.jsonl
- BETTING_V2_ALL_MARKETS_PRICE_TIMELINE.jsonl
- BETTING_V2_PICK_LEDGER.jsonl
- BETTING_V2_PRICE_TIMELINE.jsonl

After regeneration, every post-run file began with the exact original byte sequence.

Observed append sizes:

- all-markets forward ledger: +153,253 bytes
- all-markets price timeline: +71,368 bytes
- Betting V2 pick ledger: +1,210 bytes
- Betting V2 price timeline: +80,863 bytes

No pre-existing ledger byte was rewritten.

## Forward / CLV / Brain proof checks

Forward NBA proof summary contained:

- NBA_MONEYLINE|UNKNOWN
- NBA_SPREAD|UNKNOWN
- NBA_TOTAL|UNKNOWN

No NBA REGULAR forward proof lane was created.

CLV output exposed:

- by_regime
- by_proof_lane

Current regenerated CLV regime set was UNKNOWN for newly bridged unlabeled current NBA evidence.

Brain Record preserved:

- current.by_proof_lane
- forward.by_proof_lane
- betting_v2.clv.by_regime
- betting_v2.clv.by_proof_lane

No synthetic NBA REGULAR proof appeared in Brain Record.

## Isolated runtime smoke

Worktree commercial server launched on temporary port 8544.

Results:

- GET /api/health -> HTTP 200 / status ok
- POST /api/ask, Best Bets query -> HTTP 200
- Ask intent -> best_bet
- Ask status -> WAITING
- trace_id present -> yes
- no ERROR
- no OUTPUT_VALIDATION_FAILED

The isolated worktree intentionally lacked many ignored live score/news artifacts, so health source flags for those feeds were false and Game Scout correctly returned WAITING instead of inventing an answer.

Production service on main was not restarted.

## Main-branch drift discovered during isolated execution

While this feature branch was running, main independently advanced with unrelated work including:

- ba65dae Add premium Bet Lab learning workflow
- 9550ed2 Simplify parlays with plain English guidance

Those commits are not part of feature/betting-v2-regime-isolation.

The regime branch must be reconciled against the latest main only after whole-branch review, followed by fresh integration tests before any merge.

## Recorded rulings

1. CLV regime bridge:
   when legacy BETTING_V2_CURRENT lacks regime metadata, the normalized all-markets current artifact may supply regime only through exact sport + game_key matching; missing/conflicting evidence becomes UNKNOWN.

2. Live verification:
   production service was not restarted from the isolated worktree; isolated HTTP verification was used instead.

3. Current NBA unlabeled games:
   current future NBA games remain UNKNOWN because no explicit current regime survives upstream; no calendar/date inference is permitted.

4. Generated runtime artifacts:
   untracked runtime warehouse files are verified but not committed as source.

5. Main drift:
   unrelated main commits stay outside this feature branch and must be reconciled only after feature review.

## Remaining merge-time checks

Before this branch can be merged to main:

- perform the required whole-branch code review;
- reconcile the feature branch with latest main;
- rerun 38/38 regime tests;
- rerun the existing Node suite;
- rerun production build/server syntax;
- regenerate affected Betting V2 artifacts on the reconciled code;
- restart the production service only after merge/integration approval;
- verify live /api/health HTTP 200 and one Game Scout smoke query.

