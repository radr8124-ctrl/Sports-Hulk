# Betting V2 Competition-Regime Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make NBA Betting V2 proof regime-aware so preseason, regular-season, postseason, and unknown evidence cannot contaminate each other, while preserving non-NBA proof continuity.

**Architecture:** Add a small shared regime-contract module, propagate canonical regime metadata through Betting V2, and introduce NBA-only proof identities/versioning. Keep public `lane_key` backward compatible, keep non-NBA forward keys stable, and preserve all legacy ledgers append-only.

**Tech Stack:** Python 3, pandas, numpy, standard-library `unittest`, JSON/JSONL artifacts, existing Sports Zenith build scripts.

**Spec:** `docs/superpowers/specs/2026-10-07-betting-v2-competition-regime-design.md`

## Global Constraints

- Canonical regimes are exactly `PRESEASON`, `REGULAR`, `POSTSEASON`, `UNKNOWN`.
- Explicit ESPN-compatible numeric season types map `1 -> PRESEASON`, `2 -> REGULAR`, `3 -> POSTSEASON`; missing/unrecognized values become `UNKNOWN`.
- No date/week/month inference may convert `UNKNOWN` into a known regime.
- Existing public/display `lane_key = SPORT_MARKET` remains backward compatible.
- NBA is the only regime-enforced sport in this checkpoint.
- Non-enforced sports propagate regime metadata but retain their existing proof and forward identity.
- Existing forward, price, pick, and CLV ledger rows are never rewritten.
- No betting threshold or promotion gate is weakened.
- No model from a different NBA regime may be borrowed.
- Exact-file staging only; do not commit unrelated generated/live warehouse noise.

## Review Focus

1. **Numeric/text source variants:** `1`, `1.0`, `"1"`, `"1.0"`, and explicit aliases must normalize identically; test in Task 1.
2. **Unknown NBA regime:** a current NBA row with missing/invalid regime must remain `UNKNOWN` and cannot borrow PRESEASON/REGULAR/POSTSEASON proof; test in Task 3.
3. **Non-NBA continuity:** CFB receives `competition_regime=REGULAR` metadata but keeps its old proof/forward identity; tests in Tasks 1, 2, and 4.
4. **Legacy ledger readability:** old rows without regime/proof_version must remain readable and must not be rewritten; tests in Tasks 4 and 5.
5. **Settlement mismatch:** an NBA forward entry may settle only from a matching-regime historical outcome when explicit regime is available; test in Task 4.

---

### Task 1: Shared Competition-Regime Contract

**Files:**
- Create: `intelligence_warehouse/betting_v2/competition_regime.py`
- Create: `tests/test_competition_regime.py`

**Interfaces:**
- Produces: `normalize_competition_regime(value, sport=None) -> str`
- Produces: `regime_enforced(sport) -> bool`
- Produces: `proof_lane_key(sport, market, regime) -> str`
- Produces: `proof_version(model_version, sport, regime) -> str`
- Initial enforced-sport set: `{"NBA"}`

- [ ] **Step 1: Write failing normalization and identity tests**

In `tests/test_competition_regime.py`, add `unittest.TestCase` tests asserting:
- numeric/string 1 variants and explicit preseason aliases -> `PRESEASON`
- numeric/string 2 variants and explicit regular aliases -> `REGULAR`
- numeric/string 3 variants and explicit postseason aliases -> `POSTSEASON`
- missing, date-like, week-like, and unrecognized values -> `UNKNOWN`
- NBA TOTAL proof keys differ for PRESEASON vs REGULAR
- CFB TOTAL proof key remains `CFB_TOTAL`
- NBA proof versions differ by regime; CFB proof version equals the raw model version.

- [ ] **Step 2: Run the test and verify RED**

Run: `python3 -m unittest tests.test_competition_regime -v`

Expected: FAIL because the module/functions do not exist.

- [ ] **Step 3: Implement the shared contract**

Create `competition_regime.py` with the four exact interfaces above. Use explicit numeric/text maps only; do not inspect dates or weeks.

- [ ] **Step 4: Run the test and verify GREEN**

Run: `python3 -m unittest tests.test_competition_regime -v`

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add intelligence_warehouse/betting_v2/competition_regime.py tests/test_competition_regime.py
git commit -m "Add Betting V2 competition regime contract"
```

---

### Task 2: Partition Historical Validation and Models by NBA Regime

**Files:**
- Modify: `intelligence_warehouse/betting_v2/build_betting_v2_all_markets.py:1-52,314-439,692-754,1238-1338`
- Create: `tests/test_betting_v2_regime_history.py`

**Interfaces:**
- Consumes: Task 1 helpers
- Produces: history rows with `competition_regime`, `lane_key`, `proof_lane_key`
- Produces: proof-keyed validation/models and compatibility `by_lane` plus authoritative `by_proof_lane`.

- [ ] **Step 1: Write failing historical partition tests**

Use temporary CSV fixtures and patch `HISTORY_FILES`. Assert:
- NBA TOTAL season type 1 -> PRESEASON and proof key `NBA_TOTAL|PRESEASON`
- NBA TOTAL season type 2 -> REGULAR and proof key `NBA_TOTAL|REGULAR`
- both retain `lane_key == "NBA_TOTAL"`
- missing NBA season type -> UNKNOWN / `NBA_TOTAL|UNKNOWN`
- CFB season type 2 -> REGULAR metadata but proof key `CFB_TOTAL`.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m unittest tests.test_betting_v2_regime_history -v`

Expected: FAIL because history rows lack regime/proof keys.

- [ ] **Step 3: Propagate regime into `build_history(sport, market)`**

Import Task 1 helpers. Read explicit upstream `season_type` first; accept another explicitly named regime source only when present. Add the three identity fields. Do not infer from `event_start`.

- [ ] **Step 4: Run history tests and verify GREEN**

Run: `python3 -m unittest tests.test_betting_v2_regime_history -v`

Expected: PASS.

- [ ] **Step 5: Add failing proof-partition test**

Expose a focused grouping helper if needed, then assert NBA PRESEASON and REGULAR become separate proof frames while CFB remains one compatibility proof frame.

- [ ] **Step 6: Run the new test and verify RED**

Run: `python3 -m unittest tests.test_betting_v2_regime_history -v`

Expected: partition assertion FAILS against sport+market-only grouping.

- [ ] **Step 7: Make validation/model storage proof-keyed**

Modify training so NBA groups by `proof_lane_key`; non-enforced sports keep existing proof identity. Stored validation/model rows carry `competition_regime`, `lane_key`, `proof_lane_key`, `proof_version`. Add authoritative `by_proof_lane`; keep compatibility `by_lane`. Do not change scoring or thresholds.

- [ ] **Step 8: Verify Task 2**

Run:
```bash
python3 -m unittest tests.test_competition_regime tests.test_betting_v2_regime_history -v
python3 -m py_compile intelligence_warehouse/betting_v2/build_betting_v2_all_markets.py
```

Expected: PASS.

- [ ] **Step 9: Commit Task 2**

```bash
git add intelligence_warehouse/betting_v2/build_betting_v2_all_markets.py tests/test_betting_v2_regime_history.py
git commit -m "Partition Betting V2 proof by NBA regime"
```

---

### Task 3: Make Current NBA Candidates Use Matching-Regime Proof Only

**Files:**
- Modify: `intelligence_warehouse/betting_v2/build_betting_v2_all_markets.py:755-1237`
- Create: `tests/test_betting_v2_regime_current.py`

**Interfaces:**
- Consumes: Task 1 helpers and Task 2 proof-keyed models/validations
- Produces: current rows with `competition_regime`, `proof_lane_key`, `proof_version`
- Guarantees: NBA lookup uses matching proof only; non-enforced lookup stays backward compatible.

- [ ] **Step 1: Write failing current-candidate tests**

Using temporary current CSVs/models/validations, assert:
- NBA preseason candidate looks up `NBA_MONEYLINE|PRESEASON`
- NBA regular candidate cannot use a PRESEASON model
- NBA UNKNOWN cannot borrow a known-regime model
- missing matching NBA model falls back to `MARKET_REFERENCE_INSUFFICIENT_HISTORY`
- CFB regular candidate continues to use `CFB_MONEYLINE`
- output rows include regime/proof metadata.

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m unittest tests.test_betting_v2_regime_current -v`

Expected: FAIL because current lookup uses only `SPORT_MARKET`.

- [ ] **Step 3: Extend current schema/extraction**

Add explicit season/regime source-column discovery. Normalize only explicit values.

- [ ] **Step 4: Switch lookup to `proof_lane_key`**

Derive canonical regime/proof metadata before lookup. NBA uses proof key; non-enforced sports keep legacy proof key. Preserve market-reference fallback for UNKNOWN/missing NBA proof.

- [ ] **Step 5: Emit regime metadata and `by_proof_lane`**

Keep existing `by_lane`; add authoritative proof-lane summary. Do not change selection thresholds.

- [ ] **Step 6: Verify Task 3**

Run:
```bash
python3 -m unittest tests.test_competition_regime tests.test_betting_v2_regime_history tests.test_betting_v2_regime_current -v
python3 -m py_compile intelligence_warehouse/betting_v2/build_betting_v2_all_markets.py
```

Expected: PASS.

- [ ] **Step 7: Commit Task 3**

```bash
git add intelligence_warehouse/betting_v2/build_betting_v2_all_markets.py tests/test_betting_v2_regime_current.py
git commit -m "Match current Betting V2 picks by regime"
```

---

### Task 4: Make NBA Forward and Price Evidence Regime-Aware

**Files:**
- Modify: `intelligence_warehouse/betting_v2/build_betting_v2_all_markets_forward.py:102-707`
- Create: `tests/test_betting_v2_regime_forward.py`

**Interfaces:**
- Consumes: current rows with regime/proof metadata
- Produces: NBA regime-aware forward/price identities
- Guarantees: non-enforced forward/price identities remain legacy-compatible.

- [ ] **Step 1: Write failing identity/legacy tests**

Assert:
- identical NBA PRESEASON vs REGULAR rows produce different forward keys and price identities
- CFB forward key equals legacy `model_version|identity(row)`
- CFB price identity equals legacy `identity(row)`
- `canonical()` still reads a legacy row without regime/proof_version.

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m unittest tests.test_betting_v2_regime_forward -v`

Expected: FAIL because keys ignore regime/proof version.

- [ ] **Step 3: Add focused identity helpers**

Keep `identity(row)` as legacy identity. Add:
- `forward_identity(row, model_version) -> str`
- `price_identity(row) -> str`

NBA uses proof version/regime; non-enforced sports return legacy identities.

- [ ] **Step 4: Freeze metadata into new events**

ENTRY, SHADOW_TRIGGER, and MARKET_PRICE events carry `competition_regime`, `proof_lane_key`, `proof_version`. Never rewrite old rows.

- [ ] **Step 5: Write failing settlement-regime test**

Synthetic NBA PRESEASON entry + PRESEASON/REGULAR historical outcomes for the same market. Assert only matching PRESEASON outcome can settle the regime-aware entry. Assert a legacy no-regime entry retains legacy settlement behavior.

- [ ] **Step 6: Make NBA settlement regime-aware**

Include canonical regime in NBA settlement matching. A regime-aware NBA entry must never settle from a conflicting known regime.

- [ ] **Step 7: Add `by_proof_lane` forward summary**

Keep `by_lane`; add authoritative proof-lane summary.

- [ ] **Step 8: Verify Task 4**

Run:
```bash
python3 -m unittest tests.test_betting_v2_regime_forward -v
python3 -m py_compile intelligence_warehouse/betting_v2/build_betting_v2_all_markets_forward.py
```

Expected: PASS.

- [ ] **Step 9: Commit Task 4**

```bash
git add intelligence_warehouse/betting_v2/build_betting_v2_all_markets_forward.py tests/test_betting_v2_regime_forward.py
git commit -m "Isolate NBA forward proof by regime"
```

---

### Task 5: Preserve Regime Through Global CLV Tracking

**Files:**
- Modify: `intelligence_warehouse/betting_v2/build_clv_tracker.py:98-452`
- Create: `tests/test_betting_v2_regime_clv.py`

**Interfaces:**
- Consumes: Betting V2 current picks/market board carrying regime metadata when available
- Produces: new CLV ENTRY/MARKET_PRICE/CLOSE rows with `competition_regime`, `proof_lane_key`, `proof_version`
- Produces: `by_regime` and `by_proof_lane` CLV summaries
- Guarantees: non-NBA and legacy key behavior remains compatible.

- [ ] **Step 1: Write failing CLV key/metadata tests**

Assert:
- NBA PRESEASON and REGULAR picks for the same game/side do not share the new CLV pick/market key
- CFB key remains equal to legacy `row_key(row)`
- ENTRY freezes regime/proof metadata
- MARKET_PRICE freezes regime/proof metadata
- legacy entries without regime remain readable.

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m unittest tests.test_betting_v2_regime_clv -v`

Expected: FAIL because CLV keys/rows ignore regime.

- [ ] **Step 3: Add regime-aware CLV key helper**

Keep `row_key(row)` as the legacy key. Add `regime_clv_key(row) -> str`:
- NBA regime-aware rows append/use proof version + regime
- non-enforced or legacy rows return the legacy key.

Use the same helper for matching picks to market-price history.

- [ ] **Step 4: Freeze regime/proof metadata through ENTRY, MARKET_PRICE, and CLOSE**

New events carry canonical regime/proof fields. CLOSE inherits the entry's frozen regime; it must not be re-derived from current time or another row.

- [ ] **Step 5: Add failing summary-separation test**

Create closed synthetic NBA PRESEASON and REGULAR entries and assert:
- top-level legacy summary may include both for historical visibility
- `by_regime.PRESEASON` and `by_regime.REGULAR` are separate
- `by_proof_lane` separates the two proof cohorts
- no regime-aware promotion consumer needs the mixed aggregate.

- [ ] **Step 6: Implement `by_regime` and `by_proof_lane` summaries**

Reuse `summarize_group(rows)`; do not change CLV math.

- [ ] **Step 7: Verify Task 5**

Run:
```bash
python3 -m unittest tests.test_betting_v2_regime_clv -v
python3 -m py_compile intelligence_warehouse/betting_v2/build_clv_tracker.py
```

Expected: PASS.

- [ ] **Step 8: Commit Task 5**

```bash
git add intelligence_warehouse/betting_v2/build_clv_tracker.py tests/test_betting_v2_regime_clv.py
git commit -m "Separate NBA CLV by competition regime"
```

---

### Task 6: Brain Record Exposure, Regeneration, and Acceptance

**Files:**
- Modify only if required for defaults/exposure: `intelligence_warehouse/brain_performance/build_brain_performance.py:347-536`
- Create: `tests/test_betting_v2_regime_acceptance.py`
- Regenerate as required:
  - `intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_MODELS.json`
  - `intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_VALIDATION.json`
  - `intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_CURRENT.json`
  - `intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_FORWARD_SUMMARY.json`
  - `intelligence_warehouse/betting_v2/BETTING_V2_CLV.json`
  - `intelligence_warehouse/brain_performance/BRAIN_PERFORMANCE.json`
  - matching `commercial_web/public` / `commercial_web/dist` generated artifacts written by the existing builders.

**Interfaces:**
- Consumes: regime-aware Betting V2/forward/CLV artifacts
- Produces: Brain Record preserving authoritative regime proof metadata
- Guarantees: accepted live system remains conservative and healthy.

- [ ] **Step 1: Write failing Brain Record/acceptance fixture test**

In `tests/test_betting_v2_regime_acceptance.py`, use small synthetic payloads or temporary path patching to assert:
- Brain Record's `betting_v2_all_markets.current` preserves `by_proof_lane`
- forward section preserves `by_proof_lane`
- CLV section exposes `by_regime` / `by_proof_lane` if included in the all-markets/Betting V2 display path
- NBA PRESEASON proof is labeled PRESEASON
- no synthetic REGULAR proof count is created from PRESEASON data.

- [ ] **Step 2: Run test and verify RED if Brain defaults/exposure are incomplete**

Run: `python3 -m unittest tests.test_betting_v2_regime_acceptance -v`

Expected: either RED on missing defaults/exposure or GREEN if the aggregator already preserves the new fields unchanged. If GREEN, do not add unnecessary Brain Record code.

- [ ] **Step 3: Make the minimum Brain Record change only if Step 2 proves it is needed**

If defaults are required, add `by_proof_lane` / regime-aware empty defaults. Do not restructure unrelated Brain Record sections.

- [ ] **Step 4: Run all focused regime tests**

Run:
```bash
python3 -m unittest \
  tests.test_competition_regime \
  tests.test_betting_v2_regime_history \
  tests.test_betting_v2_regime_current \
  tests.test_betting_v2_regime_forward \
  tests.test_betting_v2_regime_clv \
  tests.test_betting_v2_regime_acceptance -v
```

Expected: PASS.

- [ ] **Step 5: Snapshot immutable legacy ledgers before regeneration**

Record hashes for:
- `BETTING_V2_ALL_MARKETS_FORWARD_LEDGER.jsonl`
- `BETTING_V2_ALL_MARKETS_PRICE_TIMELINE.jsonl`
- `BETTING_V2_PICK_LEDGER.jsonl`
- `BETTING_V2_PRICE_TIMELINE.jsonl`

Do not require hashes to remain unchanged after new append-only capture; instead preserve copies of pre-run content and verify the post-run files start with the exact pre-run bytes.

- [ ] **Step 6: Regenerate the regime-aware artifacts**

Run the active builders in dependency order:
```bash
python3 intelligence_warehouse/betting_v2/build_betting_v2_all_markets.py
python3 intelligence_warehouse/betting_v2/build_betting_v2_all_markets_forward.py
python3 intelligence_warehouse/betting_v2/build_clv_tracker.py
python3 intelligence_warehouse/brain_performance/build_brain_performance.py
```

Expected:
- builders exit 0
- NBA current candidates with explicit current preseason source data are `PRESEASON`
- NBA `by_proof_lane` contains PRESEASON proof only unless explicit other-regime data exists
- CFB proof keys remain compatibility keys.

- [ ] **Step 7: Verify append-only immutability**

Compare each post-run ledger prefix with its pre-run snapshot.

Expected: every original byte remains unchanged; any differences are append-only new lines.

- [ ] **Step 8: Run artifact assertions**

Use a one-shot Python assertion script or the acceptance test to verify:
- all NBA current picks have canonical `competition_regime`
- no NBA PRESEASON row reports a REGULAR proof key
- non-enforced sport proof keys remain legacy-shaped
- forward/CLV regime summaries exist
- Brain Record preserves regime-aware proof
- no promotion threshold values changed.

- [ ] **Step 9: Run full relevant regression suite**

Run:
```bash
python3 -m unittest discover -s tests -p 'test_*regime*.py' -v
cd commercial_web
node --test *.test.js
npm run build
node --check server.js
```

Expected:
- all regime tests PASS
- existing Node suite PASS
- production build PASS
- server syntax PASS.

- [ ] **Step 10: Restart and verify live health**

Run the existing user service restart, then:
`curl -sS -o /tmp/zenith_regime_health.json -w 'HTTP %{http_code}\n' http://127.0.0.1:8510/api/health`

Expected: `HTTP 200`.

Also smoke-check `/api/ask` for one Best Bets query and ensure it does not return `ERROR` or `OUTPUT_VALIDATION_FAILED`.

- [ ] **Step 11: Inspect exact Git diff before staging**

Run:
```bash
git status --short
git diff -- intelligence_warehouse/betting_v2 intelligence_warehouse/brain_performance tests commercial_web/public commercial_web/dist
```

Exclude unrelated live/generated noise. Stage only files required by this checkpoint.

- [ ] **Step 12: Commit Task 6**

Commit implementation/tests and intentional regenerated artifacts with:
```bash
git commit -m "Isolate Betting V2 NBA proof by regime"
```

- [ ] **Step 13: Write checkpoint receipt**

Create:
`reports/BETTING_V2_REGIME_ISOLATION_ACCEPTANCE_2026-10-07.md`

Record:
- tests run/pass counts
- NBA current regime counts
- proof-lane counts
- legacy ledger prefix verification
- CFB continuity result
- build/health result
- exact implementation commit.

Commit the receipt separately:
```bash
git add reports/BETTING_V2_REGIME_ISOLATION_ACCEPTANCE_2026-10-07.md
git commit -m "Record Betting V2 regime isolation acceptance"
```

---

## Execution Notes

- Execute tasks in order; Tasks 2-6 depend on Task 1 interfaces.
- Do not combine commits across task boundaries unless a test proves the boundary cannot stand independently.
- If a test exposes an upstream source that lacks explicit regime data, keep it `UNKNOWN`; do not invent a heuristic.
- If generated artifacts show unexpected cross-sport proof resets, stop before commit and investigate.
- If current NBA source data is no longer preseason when this plan is executed, acceptance should assert the explicit current regime actually present rather than hard-code PRESEASON; the core invariant is same-regime proof only.
