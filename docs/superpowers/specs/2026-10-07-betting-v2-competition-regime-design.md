# Betting V2 Competition-Regime Isolation Design

Date: 2026-10-07
Status: Approved design awaiting implementation plan
Project: Sports Zenith / Game Scout
Scope: Betting V2 all-markets proof pipeline, generic framework with NBA-first rebaseline

## 1. Problem

Sports Zenith upstream sports pipelines can preserve competition-phase information such as NBA and CFB season type, but Betting V2 all-markets currently collapses proof into sport + market lanes.

That creates a proof-contamination risk. NBA preseason, regular season, and postseason differ materially in rotation stability, lineup certainty, market liquidity, and late price movement. A preseason result must not count toward regular-season model promotion.

The current accepted Betting V2 architecture is intentionally proof-gated and append-only. This change must strengthen those guarantees without rewriting historical evidence or breaking existing UI consumers.

## 2. Goals

1. Introduce one canonical field: `competition_regime`.
2. Normalize only explicit upstream regime evidence.
3. Preserve regime through training, validation, current candidates, forward ledgers, price timelines, CLV, and Brain Record.
4. Keep public/display `lane_key` backward compatible.
5. Separate proof with a new regime-aware identity.
6. Start a clean NBA regime-aware forward cohort without rewriting prior immutable rows.
7. Make UNKNOWN explicit and non-promotable where a regime is required for proof.

## 3. Non-goals

This checkpoint does not:
- change betting thresholds;
- create more PLAYs;
- change probability models beyond proof partitioning;
- add new paid data;
- backfill guessed regimes from dates;
- rewrite existing forward or CLV history;
- alter Props V2, PrizePicks, DFS, Fantasy, or Survivor;
- redesign the Brain Record UI beyond exposing regime metadata needed for proof clarity.

## 4. Canonical regime contract

Canonical values:

- PRESEASON
- REGULAR
- POSTSEASON
- UNKNOWN

Normalization accepts explicit upstream values only.

For ESPN-derived numeric season types:
- 1 / 1.0 -> PRESEASON
- 2 / 2.0 -> REGULAR
- 3 / 3.0 -> POSTSEASON

Accepted text aliases may include explicit names such as:
- PRESEASON, PRE-SEASON
- REGULAR, REGULAR SEASON
- POSTSEASON, POST-SEASON, PLAYOFF, PLAYOFFS

Any missing, blank, malformed, or unrecognized value becomes UNKNOWN.

No date, week number, month, standings state, or game label may silently convert UNKNOWN into a known regime.

The normalizer should accept sport as context for future source-specific mappings, but the first implementation should use the explicit ESPN-compatible contract above plus text aliases.

## 5. Compatibility model

Existing consumer-facing lane identity remains stable:

`lane_key = SPORT_MARKET`

Examples:
- NBA_MONEYLINE
- NBA_SPREAD
- NBA_TOTAL

A new proof identity is introduced behind an explicit activation policy.

For regime-enforced sports:

`proof_lane_key = SPORT_MARKET|COMPETITION_REGIME`

Examples:
- NBA_MONEYLINE|PRESEASON
- NBA_MONEYLINE|REGULAR
- NBA_TOTAL|POSTSEASON

For sports not yet regime-enforced, `proof_lane_key` remains equal to the existing `lane_key` even though `competition_regime` metadata is still propagated. This prevents an NBA-first cleanup from silently rebaselining CFB, NFL, MLB, NHL, or CBB.

The initial activation set is:
- NBA

Adding another sport to regime enforcement is a future explicit rebaseline decision, not an automatic side effect.

Where summaries need both views:
- `by_lane` remains the compatibility/display view;
- authoritative regime-aware proof is exposed through `by_proof_lane`;
- promotion decisions must read regime-aware proof, never the aggregate compatibility view.

## 6. Data flow

### 6.1 Historical training rows

The all-markets history builder reads explicit upstream season/phase fields from graded recommendation history.

Each row receives:
- competition_regime
- lane_key
- proof_lane_key

Walk-forward validation groups by proof_lane_key. For NBA, that key is regime-specific. For non-enforced sports, proof identity remains backward compatible during this checkpoint.

Historical NBA rows with UNKNOWN remain visible for research counts but must not be merged into a known-regime proof lane.

NBA-first policy:
- PRESEASON NBA rows train/validate only PRESEASON proof lanes;
- future REGULAR NBA rows start independent REGULAR proof lanes;
- PRESEASON proof never satisfies REGULAR promotion gates.

### 6.2 Final fitted models

Model storage is keyed by proof_lane_key. In this checkpoint, NBA is the only regime-enforced sport; non-enforced sports retain their current proof key.

Every stored model carries:
- sport
- market
- lane_key
- proof_lane_key
- competition_regime
- history_n
- independent_blocks
- probability source
- proof status

Compatibility summaries may aggregate model inventory by lane_key, but no aggregate is promotion-authoritative.

### 6.3 Current candidates

Current decision rows receive competition_regime from explicit upstream game/decision data.

Every current candidate carries:
- lane_key
- proof_lane_key
- competition_regime

The model lookup uses proof_lane_key.

If the matching proof lane does not exist or lacks enough history:
- probability falls back to the existing market-reference behavior;
- selection_rule_status remains insufficient-history/research-only;
- no model from a different regime may be borrowed.

UNKNOWN must never borrow PRESEASON, REGULAR, or POSTSEASON proof.

### 6.4 Forward ledger

The immutable forward identity becomes regime-aware only for regime-enforced sports.

Introduce a row-level `proof_version` separate from the existing global probability-model version:
- NBA: `proof_version` includes a regime-schema version and starts a new regime-aware proof cohort;
- non-enforced sports: `proof_version` remains the existing model version so their forward identity does not restart.

For NBA, new forward keys include `proof_version` and competition_regime in addition to the existing market identity.

For non-enforced sports, forward-key behavior remains unchanged in this checkpoint.

Two otherwise identical synthetic NBA picks with different regimes must produce different forward keys.

New forward entries carry:
- competition_regime
- proof_lane_key
- proof_version

Existing ledger rows are not edited.

A top-level schema/version marker may identify the new regime-aware pipeline, but it must not by itself re-key non-NBA forward evidence.

### 6.5 Price timeline

New price snapshots carry competition_regime, proof_lane_key, and proof_version.

For NBA, the price identity is regime-aware so derived execution metrics remain in the same proof cohort. For non-enforced sports, price identity remains backward compatible in this checkpoint.

No historical price row is rewritten.

### 6.6 CLV

CLV rows and summaries must preserve competition_regime.

Regime-aware CLV summaries should be available at least by:
- sport
- market/lane
- competition_regime

Promotion logic may use only CLV from the same proof regime.

Existing mixed/legacy CLV remains historical evidence and is labeled legacy/mixed rather than reassigned.

### 6.7 Brain Record

Brain Record must expose the regime attached to each regime-aware Betting V2 proof cohort.

Minimum fields:
- competition_regime
- proof_lane_key
- model_version
- proof_version
- independent_blocks
- forward decisions
- probability source
- proof status

Existing aggregate cards may remain, but any promotion/readiness presentation must make clear which regime is being judged.

A legacy mixed-regime cohort must not be displayed as regular-season proof.

## 7. NBA-first rollout

The framework is generic, but the first clean rebaseline is NBA.

Rollout sequence:

1. Add regime normalizer and tests.
2. Propagate regime through all-markets historical/current outputs.
3. Partition NBA proof lanes by regime.
4. Add a regime-schema/proof version without globally restarting non-NBA evidence.
5. Version NBA forward evidence so new regime-aware rows cannot merge with legacy rows while non-NBA forward keys remain stable.
6. Propagate regime and proof version into price/CLV records.
7. Regenerate Betting V2 artifacts.
8. Verify current NBA preseason candidates are PRESEASON.
9. Verify regular-season proof count is zero until explicit REGULAR rows arrive.
10. Verify CFB REGULAR behavior remains functionally unchanged apart from new metadata.
11. Rebuild Brain Record and commercial artifacts.
12. Run focused and full regression checks.

## 8. Migration and immutability

Historical ledgers are append-only evidence.

The implementation must not:
- edit old forward entries;
- mutate old price snapshots;
- relabel old CLV rows;
- copy legacy NBA outcomes into REGULAR proof.

Instead:
- old model version stays historical;
- new model version creates new regime-aware keys;
- legacy mixed results remain visible but excluded from regime-aware promotion.

If a legacy row lacks an explicit regime, its canonical competition_regime is UNKNOWN and it may carry a separate legacy/unlabeled reporting flag. LEGACY is not a canonical competition_regime value.

## 9. Promotion rules

No promotion threshold is weakened.

A known-regime model may be reviewed only against evidence from the same regime.

For NBA REGULAR:
- PRESEASON decisions = zero contribution;
- POSTSEASON decisions = zero contribution;
- UNKNOWN decisions = zero contribution.

Existing probability, economics, ROI, CLV, independent-block, and manual-review gates remain unchanged unless a later approved checkpoint changes them.

## 10. Failure behavior

If regime extraction fails:
- row receives UNKNOWN;
- pipeline continues;
- row cannot borrow a model from another regime;
- current recommendation remains conservative/market-reference where appropriate.

If a downstream artifact receives an invalid regime:
- normalize to UNKNOWN;
- do not crash the live site;
- surface diagnostics in generated receipts/logging where available.

If a current NBA game has UNKNOWN regime:
- no NBA regime-specific learned model may be treated as valid proof for it.

## 11. Testing strategy

Implementation is test-driven.

### Unit tests

Regime normalization:
- numeric 1 -> PRESEASON
- numeric 2 -> REGULAR
- numeric 3 -> POSTSEASON
- string numeric forms map identically
- explicit text aliases map correctly
- missing/unrecognized -> UNKNOWN
- dates/weeks are not used to guess regime

Identity:
- lane_key remains NBA_TOTAL
- proof_lane_key differs for NBA_TOTAL|PRESEASON and NBA_TOTAL|REGULAR

### Builder tests

Historical:
- PRESEASON and REGULAR rows for the same sport/market are validated separately
- UNKNOWN rows do not enter either known regime cohort

Current:
- candidate carries competition_regime and proof_lane_key
- current candidate uses only matching-regime model
- missing matching model falls back to market reference

### Forward tests

- otherwise identical synthetic picks in PRESEASON and REGULAR have different forward keys
- new ledger entry freezes regime
- old ledger fixture remains readable

### CLV tests

- price snapshots carry regime
- close/CLV event preserves entry regime
- summaries do not combine PRESEASON and REGULAR for promotion evidence

### End-to-end regression

Run the NBA all-markets pipeline from explicit preseason source data and assert:
- current NBA candidates are PRESEASON;
- no REGULAR NBA proof is created from preseason rows;
- forward rows preserve PRESEASON;
- CLV/price records preserve PRESEASON;
- Brain Record reflects PRESEASON proof status.

Run a CFB regular-season fixture and assert:
- competition_regime = REGULAR;
- proof_lane_key remains the existing CFB lane key because CFB is not regime-enforced in this checkpoint;
- existing conservative decisions remain unchanged.

## 12. Acceptance criteria

This checkpoint is accepted only when all are true:

1. Canonical regime helper is covered by tests.
2. Betting V2 training and validation are proof-partitioned by regime for regime-enforced sports.
3. Current NBA candidates expose regime and use matching proof only; non-enforced sports retain existing proof behavior.
4. NBA forward identity is regime-aware while non-enforced forward identities remain stable.
5. Price timeline and CLV preserve regime, and NBA execution proof is regime-separated.
6. Brain Record exposes regime-aware proof.
7. Old ledgers remain unmodified by migration logic.
8. NBA preseason evidence cannot count toward NBA regular-season promotion.
9. Existing CFB regular-season behavior does not regress, including its forward-key/proof continuity.
10. Focused tests pass.
11. Full relevant regression suite passes.
12. Production build and /api/health pass after regeneration.
13. Changes are committed with exact-file staging only.

## 13. Expected files touched during implementation

Likely core files:
- intelligence_warehouse/betting_v2/build_betting_v2_all_markets.py
- intelligence_warehouse/betting_v2/build_betting_v2_all_markets_forward.py
- intelligence_warehouse/betting_v2/build_betting_v2_line_clv.py and/or the active CLV tracker
- intelligence_warehouse/brain_performance builder(s)
- focused new regime helper module
- focused unit/regression tests
- generated current/validation/model/forward-summary/Brain Record artifacts as required

The implementation plan must inspect the active CLV and Brain Record builders before naming their exact write targets.

## 14. Design decisions

### Chosen
Generic regime framework with NBA-first rebaseline.

### Rejected
NBA-only hard-coded patch: faster but creates duplicated logic and guarantees future cleanup.

### Rejected
Immediate cross-sport historical backfill: too broad, risks guessing missing regimes, and is unnecessary for fixing the proof path.

### Rejected
Changing public lane_key everywhere: high compatibility cost with no proof benefit.

## 15. Success definition

After this change, Sports Zenith can truthfully say:

NBA preseason evidence, regular-season evidence, and postseason evidence are separate proof cohorts. A model can only earn promotion from evidence generated in the same competition regime it will be used in.

That guarantee is more important than producing more picks.
