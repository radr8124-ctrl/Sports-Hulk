# Betting V2 Competition-Regime Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve explicit competition regime through the Betting V2 all-markets proof pipeline so NBA preseason evidence can never qualify NBA regular-season promotion.

**Architecture:** Repair the NBA ESPN season-type source first, then introduce a small shared regime/proof-identity module. Keep public `lane_key` backward compatible, make `by_proof_lane` authoritative for proof, and use row-level `proof_version` so NBA starts a clean regime-aware cohort without restarting non-NBA forward evidence.

**Tech Stack:** Python 3, pandas, numpy, built-in `unittest`, existing JSON/CSV/JSONL builders, Vite commercial dashboard.

**Spec:** `docs/superpowers/specs/2026-10-07-betting-v2-competition-regime-design.md`

## Global Constraints

- Canonical `competition_regime` values are exactly `PRESEASON`, `REGULAR`, `POSTSEASON`, `UNKNOWN`.
- ESPN numeric season types map exactly: `1 -> PRESEASON`, `2 -> REGULAR`, `3 -> POSTSEASON`.
- Missing or unrecognized regime evidence becomes `UNKNOWN`; never infer regime from dates, weeks, standings, or game labels.
- NBA is the only regime-enforced sport in this checkpoint.
- Non-enforced sports keep their existing proof identity and forward-key continuity.
- Public/display `lane_key = SPORT_MARKET` remains backward compatible.
- Authoritative proof identity is `proof_lane_key`; authoritative proof summaries use `by_proof_lane`.
- Existing immutable forward, price, and CLV history is never rewritten or relabeled.
- No betting threshold, probability formula, or PLAY gate is loosened.
- No new Python dependency is added; tests use built-in `unittest`.
- Exact-file staging only; never `git add .`.
- The legacy `build_clv_tracker.py` is out of scope.

## Review Focus

1. **Malformed or unavailable ESPN `seasonType` reference** — NBA core must emit a blank/unknown upstream value without crashing or guessing; pinned in Task 1 tests.
2. **NBA market row cannot be matched to current-game metadata** — decision output must leave `season_type` blank so Betting V2 normalizes it to `UNKNOWN`; pinned in Task 1 and Task 2 tests.
3. **Legacy NBA forward row has no `proof_version`** — it remains readable but cannot enter the new NBA regime-aware active proof cohort; pinned in Task 3 tests.
4. **Non-NBA row after the migration** — CFB/NFL/MLB/NHL/CBB forward identity must remain byte-compatible with the old `model_version|identity` scheme; pinned in Task 2 and Task 3 tests.
5. **NBA `UNKNOWN` has a large historical sample** — it still cannot become promotion-authoritative or lend a model to PRESEASON/REGULAR/POSTSEASON; pinned in Task 2 tests.

---

### Task 1: Repair explicit NBA season metadata at the source

**Files:**
- Modify: `nba_live/build_nba_core.py:328-365`
- Modify: `nba_live/decision/build_nba_decision_brain.py:20-70,590-930`
- Create: `tests/__init__.py`
- Create: `tests/betting_v2/__init__.py`
- Create: `tests/betting_v2/test_nba_regime_source.py`

**Interfaces:**
- Consumes: ESPN Core event dictionaries containing `season` and `seasonType` references.
- Produces: `season_info(event: dict) -> tuple[object | None, object | None]`, where season year is explicit and season type prefers the explicit numeric `type` value, then explicit name as fallback.
- Produces: `build_current_game_metadata(games: pandas.DataFrame) -> dict[str, dict]`, keyed by canonical `YYYY-MM-DD|AWAY|HOME`, with values `{"season": ..., "season_type": ...}`.
- Produces: `NBA_GAME_DECISIONS.csv` rows containing `season` and `season_type` copied only from matched explicit current-game metadata.

- [ ] **Step 1: Create unittest package markers and write failing ESPN season/seasonType tests**

Create empty `tests/__init__.py` and `tests/betting_v2/__init__.py` so package-style unittest commands work.

In `tests/betting_v2/test_nba_regime_source.py`, dynamically import `nba_live/build_nba_core.py` and use `unittest.mock.patch.object` on `ref_json`.

Tests:

```python
def test_season_info_uses_explicit_season_type_reference(self):
    event = {
        "season": {"$ref": "season-ref"},
        "seasonType": {"$ref": "type-ref"},
    }
    resolved = {
        "season-ref": {"year": 2027},
        "type-ref": {"type": 1, "name": "Preseason"},
    }
    # patched ref_json returns resolved[$ref]
    self.assertEqual(core.season_info(event), (2027, 1))
```

```python
def test_season_info_missing_type_does_not_guess(self):
    event = {"date": "2026-10-07T23:00Z", "season": {"$ref": "season-ref"}}
    # season resolves to {"year": 2027}; no seasonType
    self.assertEqual(core.season_info(event), (2027, None))
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m unittest tests.betting_v2.test_nba_regime_source.NbaCoreSeasonInfoTests -v
```

Expected: FAIL because current `season_info()` does not dereference `seasonType` and returns no explicit type for the ESPN reference shape.

- [ ] **Step 3: Implement the minimal NBA core parser repair**

Modify `season_info(event)` in `nba_live/build_nba_core.py`.

Required behavior:
- dereference `event["season"]` through existing `ref_json`;
- dereference `event["seasonType"]` through existing `ref_json`;
- year comes from resolved season `year`;
- season type prefers resolved seasonType `type`;
- if numeric type is absent, explicit seasonType `name` is allowed;
- if no explicit type/name exists, return `None`;
- no date inference.

- [ ] **Step 4: Run season-info tests and verify GREEN**

Run the Step 2 command.

Expected: 2 tests PASS.

- [ ] **Step 5: Write failing tests for current-game metadata lookup**

In the same test file, dynamically import `nba_live/decision/build_nba_decision_brain.py`.

Tests:

```python
def test_current_game_metadata_keys_explicit_regime_by_game_key(self):
    games = pd.DataFrame([{
        "start": "2026-10-07T23:00Z",
        "away_team": "MIN",
        "home_team": "IND",
        "season": 2027,
        "season_type": 1,
    }])
    lookup = decision.build_current_game_metadata(games)
    self.assertEqual(
        lookup["2026-10-07|MIN|IND"],
        {"season": 2027, "season_type": 1},
    )
```

```python
def test_unmatched_game_has_no_synthetic_regime(self):
    games = pd.DataFrame([])
    lookup = decision.build_current_game_metadata(games)
    self.assertNotIn("2026-10-07|MIN|IND", lookup)
```

- [ ] **Step 6: Run metadata tests and verify RED**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m unittest tests.betting_v2.test_nba_regime_source.NbaDecisionRegimeTests -v
```

Expected: FAIL because `build_current_game_metadata` does not exist.

- [ ] **Step 7: Implement current-game metadata propagation**

In `nba_live/decision/build_nba_decision_brain.py`:
- add `CURRENT_GAMES = DERIVED / "NBA_GAMES_CURRENT.csv"`;
- add `build_current_game_metadata(games: pd.DataFrame) -> dict[str, dict]`;
- canonical key uses UTC date from `start` plus canonical away/home abbreviations;
- in `build_game_decisions(forms)`, load `CURRENT_GAMES` once and build the lookup;
- for each fusion row, read metadata by its existing `game_key`;
- append `season` and `season_type` into each decision row;
- unmatched rows get blank/`None`, never an inferred value.

- [ ] **Step 8: Run Task 1 tests**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m unittest tests.betting_v2.test_nba_regime_source -v
```

Expected: all Task 1 tests PASS.

- [ ] **Step 9: Syntax-check both modified modules**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m py_compile nba_live/build_nba_core.py nba_live/decision/build_nba_decision_brain.py
```

Expected: exit 0.

- [ ] **Step 10: Commit Task 1**

```bash
git add nba_live/build_nba_core.py nba_live/decision/build_nba_decision_brain.py tests/__init__.py tests/betting_v2/__init__.py tests/betting_v2/test_nba_regime_source.py
git commit -m "Preserve explicit NBA season type"
```

---

### Task 2: Add canonical regime identity and partition Betting V2 proof

**Files:**
- Create: `intelligence_warehouse/betting_v2/competition_regime.py`
- Modify: `intelligence_warehouse/betting_v2/build_betting_v2_all_markets.py:1-45,314-438,692-754,899-1135,1238-1415`
- Create: `tests/betting_v2/test_competition_regime.py`
- Create: `tests/betting_v2/test_all_markets_regime.py`

**Interfaces:**
- Produces: `normalize_competition_regime(value: object) -> str`.
- Produces: `lane_key(sport: str, market: str) -> str`.
- Produces: `proof_lane_key(sport: str, market: str, regime: str) -> str`.
- Produces: `proof_version(sport: str) -> str`.
- Produces: `regime_proof_allowed(sport: str, regime: str) -> bool`.
- Constants:
  - `REGIME_ENFORCED_SPORTS = frozenset({"NBA"})`
  - `REGIME_PROOF_VERSION = "BETTING_V2_REGIME_V1_2026_10_07"`
  - `LEGACY_PROOF_VERSION = "BETTING_V2_ALL_MARKETS_2026_10_05"`
- `proof_lane_key("NBA","TOTAL","PRESEASON") == "NBA_TOTAL|PRESEASON"`.
- `proof_lane_key("CFB","TOTAL","REGULAR") == "CFB_TOTAL"`.
- `proof_version("NBA") == REGIME_PROOF_VERSION`.
- `proof_version("CFB") == LEGACY_PROOF_VERSION`.

- [ ] **Step 1: Write failing normalization and identity tests**

In `tests/betting_v2/test_competition_regime.py`:

```python
def test_numeric_espn_types(self):
    self.assertEqual(regime.normalize_competition_regime(1), "PRESEASON")
    self.assertEqual(regime.normalize_competition_regime("2.0"), "REGULAR")
    self.assertEqual(regime.normalize_competition_regime(3.0), "POSTSEASON")

def test_explicit_text_aliases(self):
    self.assertEqual(regime.normalize_competition_regime("Pre-Season"), "PRESEASON")
    self.assertEqual(regime.normalize_competition_regime("Regular Season"), "REGULAR")
    self.assertEqual(regime.normalize_competition_regime("Playoffs"), "POSTSEASON")

def test_unknown_never_guessed(self):
    for value in (None, "", "2026-10-07", "Week 5", "4"):
        self.assertEqual(regime.normalize_competition_regime(value), "UNKNOWN")

def test_proof_identity_is_only_enforced_for_nba(self):
    self.assertEqual(regime.lane_key("NBA", "TOTAL"), "NBA_TOTAL")
    self.assertEqual(
        regime.proof_lane_key("NBA", "TOTAL", "PRESEASON"),
        "NBA_TOTAL|PRESEASON",
    )
    self.assertEqual(
        regime.proof_lane_key("CFB", "TOTAL", "REGULAR"),
        "CFB_TOTAL",
    )

def test_unknown_nba_is_not_proof_allowed(self):
    self.assertFalse(regime.regime_proof_allowed("NBA", "UNKNOWN"))
    self.assertTrue(regime.regime_proof_allowed("NBA", "PRESEASON"))
    self.assertTrue(regime.regime_proof_allowed("CFB", "UNKNOWN"))
```

- [ ] **Step 2: Run helper tests and verify RED**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m unittest tests.betting_v2.test_competition_regime -v
```

Expected: import/module failure because `competition_regime.py` does not exist.

- [ ] **Step 3: Implement the canonical regime helper**

Create `competition_regime.py` with the interfaces and constants above.

Normalization rules are exactly the spec values; no time/date inference.

- [ ] **Step 4: Run helper tests and verify GREEN**

Run the Step 2 command.

Expected: all helper tests PASS.

- [ ] **Step 5: Write failing all-markets history/proof tests**

In `tests/betting_v2/test_all_markets_regime.py`, dynamically import `build_betting_v2_all_markets.py`.

Use a temporary CSV and temporarily replace `HISTORY_FILES["NBA"]`; set module `_DEVIG` to an empty deterministic structure so the test uses payload American odds.

Synthetic rows must include:
- `lane=GAME`
- `market=TOTAL`
- `grade=WIN/LOSS`
- `score`
- `game_key`
- `selection`
- `snapshot_at`
- `start`
- `season_type`
- `payload_json={"american_odds": -110, "line": 220.5}`

Tests:

```python
def test_history_rows_partition_preseason_and_regular(self):
    frame = game.build_history("NBA", "TOTAL")
    self.assertEqual(
        set(frame["proof_lane_key"]),
        {"NBA_TOTAL|PRESEASON", "NBA_TOTAL|REGULAR"},
    )

def test_history_unknown_is_separate(self):
    frame = game.build_history("NBA", "TOTAL")
    unknown = frame[frame["competition_regime"] == "UNKNOWN"]
    self.assertTrue(all(unknown["proof_lane_key"] == "NBA_TOTAL|UNKNOWN"))
```

- [ ] **Step 6: Write failing proof-selection tests**

The all-markets module must expose:

`select_proof_model(models: dict, validations: dict, sport: str, market: str, regime: str) -> tuple[str, dict, dict]`

Tests:

```python
def test_preseason_cannot_borrow_regular_model(self):
    models = {
        "NBA_TOTAL|REGULAR": {"coefficients": {"market_calibrated": [0, 1]}},
    }
    validations = {"NBA_TOTAL|REGULAR": {"status": "READY"}}
    key, validation, model = game.select_proof_model(
        models, validations, "NBA", "TOTAL", "PRESEASON"
    )
    self.assertEqual(key, "NBA_TOTAL|PRESEASON")
    self.assertEqual(validation, {})
    self.assertEqual(model, {})

def test_unknown_nba_cannot_be_promotion_authoritative(self):
    self.assertFalse(regime.regime_proof_allowed("NBA", "UNKNOWN"))
```

- [ ] **Step 7: Run all-markets tests and verify RED**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m unittest tests.betting_v2.test_all_markets_regime -v
```

Expected: FAIL because history rows have no regime fields and `select_proof_model` does not exist.

- [ ] **Step 8: Integrate regime fields into historical/current all-markets data**

Modify `build_betting_v2_all_markets.py`:

- import the new regime helper;
- `build_history()` assigns:
  - `competition_regime`
  - compatibility `lane_key`
  - authoritative `proof_lane_key`;
- current candidates normalize explicit `season_type` from the decision row;
- current candidates include:
  - `competition_regime`
  - `proof_lane_key`
  - `proof_version`;
- add `select_proof_model(...)` and make current lookup use only matching proof identity;
- NBA `UNKNOWN` receives market-reference fallback and cannot use a known-regime model.

Keep existing `MODEL_VERSION` unchanged; this checkpoint changes proof schema, not the probability formula.

- [ ] **Step 9: Partition validation/model construction by proof lane**

In `main()`:
- group each sport/market history frame by `proof_lane_key`;
- non-enforced sports still produce one proof lane equal to `lane_key`;
- known NBA regimes can run existing `walk_forward()`;
- NBA `UNKNOWN` produces a non-promotable validation envelope:
  - `status="UNKNOWN_REGIME_RESEARCH_ONLY"`
  - counts only
  - no fitted model coefficients;
- authoritative outputs add `by_proof_lane`;
- every compatibility lane summary includes `proof_authority`;
- compatibility `lanes/by_lane` remains:
  - for non-enforced sports, `proof_authority=True` and the same proof result as before;
  - for NBA, `proof_authority=False` plus a non-authoritative `REGIME_PARTITIONED` envelope listing proof lanes and aggregate counts, with no deployable coefficients or promotion metrics.

Model output should expose authoritative models through `by_proof_lane`; compatibility NBA model entries must not contain coefficients that could be mistaken for an aggregate deployable model.

- [ ] **Step 10: Add failing non-NBA compatibility test**

In `test_competition_regime.py`:

```python
def test_cfb_proof_version_stays_legacy(self):
    self.assertEqual(
        regime.proof_version("CFB"),
        "BETTING_V2_ALL_MARKETS_2026_10_05",
    )
```

In `test_all_markets_regime.py` add:

```python
def test_cfb_proof_key_is_unchanged(self):
    self.assertEqual(
        regime.proof_lane_key("CFB", "MONEYLINE", "REGULAR"),
        "CFB_MONEYLINE",
    )
```

- [ ] **Step 11: Run Task 2 tests**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m unittest   tests.betting_v2.test_competition_regime   tests.betting_v2.test_all_markets_regime -v
```

Expected: all Task 2 tests PASS.

- [ ] **Step 12: Syntax-check Task 2 modules**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m py_compile   intelligence_warehouse/betting_v2/competition_regime.py   intelligence_warehouse/betting_v2/build_betting_v2_all_markets.py
```

Expected: exit 0.

- [ ] **Step 13: Commit Task 2**

```bash
git add   intelligence_warehouse/betting_v2/competition_regime.py   intelligence_warehouse/betting_v2/build_betting_v2_all_markets.py   tests/betting_v2/test_competition_regime.py   tests/betting_v2/test_all_markets_regime.py
git commit -m "Partition Betting V2 proof by competition regime"
```

---

### Task 3: Make forward and price evidence regime-aware without restarting other sports

**Files:**
- Modify: `intelligence_warehouse/betting_v2/build_betting_v2_all_markets_forward.py:102-315,474-788`
- Create: `tests/betting_v2/test_all_markets_forward_regime.py`

**Interfaces:**
- Consumes from Task 2: current rows with `competition_regime`, `proof_lane_key`, `proof_version`.
- Produces: `effective_proof_version(row: dict) -> str`, using explicit row `proof_version` and legacy `model_version` fallback for old rows.
- Produces: `proof_cohort_key(row: dict) -> str`, exactly `SPORT|PROOF_VERSION`.
- Existing `forward_key(version, row)` remains callable but must use regime-aware identity only when the row's sport is regime-enforced.
- Produces forward/price events with `competition_regime`, `proof_lane_key`, `proof_version`.
- Produces authoritative `by_proof_lane` summary; `by_lane` is compatibility only.

- [ ] **Step 1: Write failing forward-key compatibility tests**

In `tests/betting_v2/test_all_markets_forward_regime.py`:

```python
def test_nba_forward_keys_differ_by_regime(self):
    base = {
        "sport": "NBA",
        "game_key": "2026-10-20|BOS|NYK",
        "market": "TOTAL",
        "selection_key": "OVER",
        "line": 225.5,
        "proof_version": regime.REGIME_PROOF_VERSION,
    }
    pre = {**base, "competition_regime": "PRESEASON"}
    reg = {**base, "competition_regime": "REGULAR"}
    self.assertNotEqual(
        forward.forward_key("BETTING_V2_ALL_MARKETS_2026_10_05", pre),
        forward.forward_key("BETTING_V2_ALL_MARKETS_2026_10_05", reg),
    )

def test_cfb_forward_key_remains_legacy_format(self):
    row = {
        "sport": "CFB",
        "game_key": "2026-10-10|A|B",
        "market": "MONEYLINE",
        "selection_key": "A",
        "line": None,
        "competition_regime": "REGULAR",
        "proof_version": regime.LEGACY_PROOF_VERSION,
    }
    self.assertEqual(
        forward.forward_key(regime.LEGACY_PROOF_VERSION, row),
        "BETTING_V2_ALL_MARKETS_2026_10_05|CFB|2026-10-10|A|B|MONEYLINE|A|",
    )
```

- [ ] **Step 2: Write failing legacy-row isolation test**

```python
def test_legacy_nba_row_is_readable_but_not_active_new_proof(self):
    legacy = {
        "sport": "NBA",
        "model_version": regime.LEGACY_PROOF_VERSION,
        "forward_key": "legacy",
    }
    self.assertEqual(
        forward.effective_proof_version(legacy),
        regime.LEGACY_PROOF_VERSION,
    )
    self.assertNotEqual(
        forward.proof_cohort_key(legacy),
        f"NBA|{regime.REGIME_PROOF_VERSION}",
    )
```

- [ ] **Step 3: Run forward tests and verify RED**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m unittest tests.betting_v2.test_all_markets_forward_regime -v
```

Expected: FAIL because proof helpers and NBA regime identity do not exist.

- [ ] **Step 4: Implement regime-aware forward/price identity**

Modify the forward builder:

- add `effective_proof_version(row)`;
- add `proof_cohort_key(row)`;
- keep non-enforced `identity(row)` output byte-compatible;
- append `competition_regime` to NBA identity only;
- `forward_key(version,row)` prefixes `effective_proof_version(row)`;
- price `market_key` uses the same regime-aware identity rule;
- price events copy:
  - competition_regime
  - proof_lane_key
  - proof_version;
- entry and shadow-trigger events copy proof fields.

- [ ] **Step 5: Make active cohort filtering sport + proof-version aware**

Current global-model-version filtering must be replaced.

`capture()` should return an `active_proof_cohorts` list derived from current picks, where each cohort is `SPORT|PROOF_VERSION`.

`main()` filters canonical rows by `proof_cohort_key(row)` membership in that active set.

This must:
- retain legacy CFB/NFL/MLB/NHL/CBB rows whose proof version is the legacy model version;
- exclude legacy NBA rows from the new NBA regime-proof cohort;
- retain old rows as readable history on disk.

- [ ] **Step 6: Write failing summary partition test**

Add a pure helper:

`build_proof_summaries(rows: list[dict], prices: dict) -> tuple[dict, dict]`

It returns `by_lane, by_proof_lane`.

Test with two NBA synthetic cohorts and one CFB cohort:
- `by_proof_lane` contains separate NBA PRESEASON/REGULAR entries;
- NBA `by_lane["NBA_TOTAL"]["promotion"]["recommendation"] == "USE_BY_PROOF_LANE"`;
- CFB `by_lane["CFB_MONEYLINE"]` is the same proof result as its sole authoritative proof lane.

- [ ] **Step 7: Run the new summary test and verify RED**

Run Task 3 unittest command.

Expected: FAIL because `build_proof_summaries` does not exist.

- [ ] **Step 8: Implement authoritative forward summaries**

Use `proof_lane_key` to group authoritative promotion proof.

Rules:
- `by_proof_lane` contains all promotion gates and statistics and marks `proof_authority=True`;
- non-enforced `by_lane` mirrors its sole proof lane and marks `proof_authority=True`;
- NBA `by_lane` is compatibility-only, marks `proof_authority=False`, and sets recommendation `USE_BY_PROOF_LANE` with `automatic_promotion=False`;
- no NBA aggregate promotion gate can pass.

Update rules text to state regime-aware proof.

- [ ] **Step 9: Run Task 3 tests**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m unittest tests.betting_v2.test_all_markets_forward_regime -v
```

Expected: all PASS.

- [ ] **Step 10: Syntax-check and commit Task 3**

Run:

```bash
.venv/bin/python -m py_compile intelligence_warehouse/betting_v2/build_betting_v2_all_markets_forward.py
```

Expected: exit 0.

Commit:

```bash
git add   intelligence_warehouse/betting_v2/build_betting_v2_all_markets_forward.py   tests/betting_v2/test_all_markets_forward_regime.py
git commit -m "Isolate Betting V2 forward proof by regime"
```

---

### Task 4: Propagate regime through line CLV and Brain Record

**Files:**
- Modify: `intelligence_warehouse/betting_v2/build_betting_v2_line_clv.py:268-333,864-1138`
- Modify: `intelligence_warehouse/brain_performance/build_brain_performance.py:20-65,347-584`
- Create: `tests/betting_v2/test_line_clv_regime.py`
- Create: `tests/betting_v2/test_brain_regime.py`

**Interfaces:**
- Consumes Task 3 forward entries containing regime/proof metadata.
- `timeline_event(...)` copies `competition_regime`, `proof_lane_key`, `proof_version`.
- `build_output(run)` returns both compatibility `by_lane` and authoritative `by_proof_lane`.
- Brain Record adds `BETTING_V2_LINE_CLV` source and exposes it under `betting_v2_all_markets["line_clv"]`.

- [ ] **Step 1: Write failing line-CLV metadata test**

In `tests/betting_v2/test_line_clv_regime.py`, construct an entry with:
- `competition_regime="PRESEASON"`
- `proof_lane_key="NBA_TOTAL|PRESEASON"`
- `proof_version=REGIME_PROOF_VERSION`

Give `timeline_event()` a minimal quote record.

Assertions:

```python
self.assertEqual(event["competition_regime"], "PRESEASON")
self.assertEqual(event["proof_lane_key"], "NBA_TOTAL|PRESEASON")
self.assertEqual(event["proof_version"], regime.REGIME_PROOF_VERSION)
```

- [ ] **Step 2: Run line-CLV test and verify RED**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m unittest tests.betting_v2.test_line_clv_regime -v
```

Expected: FAIL because timeline events do not carry regime/proof fields.

- [ ] **Step 3: Implement line-CLV regime propagation**

Modify `timeline_event()` to copy proof fields from entry.

Because `closed_rows()` already spreads `**entry`, closed records retain those fields automatically.

Modify `build_output(run)`:
- existing `by_lane` remains compatibility and carries `proof_authority`;
- add authoritative `by_proof_lane`, grouping only rows that have explicit `proof_lane_key` and `proof_version`;
- NBA lane aggregate is diagnostic only and marks `proof_authority=False`;
- non-enforced lanes may mark `proof_authority=True` when they map one-to-one to their proof lane;
- legacy/unlabeled rows that lack explicit proof metadata are summarized separately under `legacy_unlabeled` and are never reassigned into `UNKNOWN` or any known proof lane;
- exact close/LCB proof used for promotion must come from the same proof lane.

- [ ] **Step 4: Add failing line-CLV summary partition test**

Patch `canonical_forward()` and `closed_rows()` with synthetic PRESEASON and REGULAR NBA rows.

Assert:
- `by_proof_lane` has two NBA proof lanes;
- each proof lane count uses only its regime;
- `by_lane["NBA_TOTAL"]["proof_authority"] is False`;
- a synthetic legacy NBA row lacking proof metadata appears only in `legacy_unlabeled`, not in either proof lane.

- [ ] **Step 5: Run line-CLV tests and verify GREEN**

Run Step 2 command.

Expected: all line-CLV tests PASS.

- [ ] **Step 6: Write failing Brain Record passthrough test**

In `tests/betting_v2/test_brain_regime.py`, import `build_brain_performance.py`.

Patch `read_json` or its source constants so a synthetic all-markets validation/forward/line-CLV payload is returned.

Test the helper introduced for this task:

`betting_v2_all_markets_payload() -> dict`

Assertions:
- returned payload includes `line_clv`;
- validation retains `by_proof_lane`;
- forward retains `by_proof_lane`;
- current candidate metadata is not stripped.

- [ ] **Step 7: Run Brain Record test and verify RED**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m unittest tests.betting_v2.test_brain_regime -v
```

Expected: FAIL because `BETTING_V2_LINE_CLV` and `betting_v2_all_markets_payload()` do not exist.

- [ ] **Step 8: Refactor Brain Record source assembly into a focused helper**

In `build_brain_performance.py`:
- add constant path `BETTING_V2_LINE_CLV`;
- extract current inline all-markets source assembly into `betting_v2_all_markets_payload() -> dict`;
- include `line_clv` with a WAITING fallback;
- do not recompute proof;
- preserve authoritative `by_proof_lane` from source artifacts.

`main()` calls this helper.

- [ ] **Step 9: Run Task 4 tests**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m unittest   tests.betting_v2.test_line_clv_regime   tests.betting_v2.test_brain_regime -v
```

Expected: all PASS.

- [ ] **Step 10: Syntax-check and commit Task 4**

Run:

```bash
.venv/bin/python -m py_compile   intelligence_warehouse/betting_v2/build_betting_v2_line_clv.py   intelligence_warehouse/brain_performance/build_brain_performance.py
```

Expected: exit 0.

Commit:

```bash
git add   intelligence_warehouse/betting_v2/build_betting_v2_line_clv.py   intelligence_warehouse/brain_performance/build_brain_performance.py   tests/betting_v2/test_line_clv_regime.py   tests/betting_v2/test_brain_regime.py
git commit -m "Expose regime-aware Betting V2 execution proof"
```

---

### Task 5: Regenerate NBA-first proof and run acceptance verification

**Files:**
- Generated/modified by builders as required:
  - `nba_live/derived/NBA_GAMES_CURRENT.csv`
  - `nba_live/decision/NBA_GAME_DECISIONS.csv`
  - `intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_MODELS.json`
  - `intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_VALIDATION.json`
  - `intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_CURRENT.json`
  - `intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_FORWARD_SUMMARY.json`
  - `intelligence_warehouse/betting_v2/BETTING_V2_LINE_CLV.json`
  - `intelligence_warehouse/brain_performance/BRAIN_PERFORMANCE.json`
  - corresponding `commercial_web/public` / `dist` published JSONs
- Append-only files that may grow but whose old prefix must not change:
  - `intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_FORWARD_LEDGER.jsonl`
  - `intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_PRICE_TIMELINE.jsonl`
  - `intelligence_warehouse/betting_v2/BETTING_V2_LINE_CLV_TIMELINE.jsonl`

**Interfaces:**
- Consumes all prior task changes.
- Produces a live NBA PRESEASON regime-aware proof cohort plus unchanged non-NBA proof continuity.

- [ ] **Step 1: Record immutable-prefix baselines before regeneration**

Create a temporary verification record outside git, e.g. `/tmp/sports-zenith-regime-prefixes.json`.

For each append-only JSONL above, record:
- line count;
- SHA-256 of the exact first N lines where N is the pre-run line count.

Also record the current CFB proof version constant for the acceptance script.

Expected: baseline file written; no repository files changed.

- [ ] **Step 2: Run the complete unit suite**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m unittest discover -s tests/betting_v2 -p 'test_*.py' -v
```

Expected: all regime-isolation tests PASS.

- [ ] **Step 3: Rebuild explicit NBA source metadata**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python nba_live/build_nba_core.py
.venv/bin/python nba_live/decision/build_nba_decision_brain.py
```

Expected:
- NBA core reports READY;
- current Oct. 7/8 preseason events carry explicit season type `1`;
- `NBA_GAME_DECISIONS.csv` contains `season` and `season_type`.

- [ ] **Step 4: Rebuild all-markets de-vig and regime-aware Betting V2**

Run:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python intelligence_warehouse/betting_v2/build_betting_v2_all_market_devig.py
.venv/bin/python intelligence_warehouse/betting_v2/build_betting_v2_all_markets.py
.venv/bin/python intelligence_warehouse/betting_v2/build_betting_v2_all_markets_forward.py
.venv/bin/python intelligence_warehouse/betting_v2/build_betting_v2_line_clv.py
.venv/bin/python intelligence_warehouse/brain_performance/build_brain_performance.py
```

Expected: each builder exits 0 and writes READY outputs.

- [ ] **Step 5: Verify NBA current regime is explicit and isolated**

Run a Python acceptance script that asserts:

```python
# NBA current candidates
nba = [r for r in current["picks"] if r["sport"] == "NBA"]
assert nba
assert {r["competition_regime"] for r in nba} == {"PRESEASON"}
assert all(r["proof_lane_key"].endswith("|PRESEASON") for r in nba)
assert all(r["proof_version"] == REGIME_PROOF_VERSION for r in nba)

# No preseason evidence creates regular-season proof
regular_keys = [
    k for k in validation["by_proof_lane"]
    if k.startswith("NBA_") and k.endswith("|REGULAR")
]
assert not regular_keys

# NBA compatibility lanes are not promotion-authoritative
for lane, row in current["by_lane"].items():
    if lane.startswith("NBA_"):
        assert row.get("proof_authority") is False
```

Expected: `NBA_REGIME_ACCEPTANCE_PASS`.

If an ESPN event truly lacks explicit seasonType, the acceptance script may allow that specific row only as `UNKNOWN`, but it must then assert:
- no known-regime model is used;
- no REGULAR proof credit is created;
- the row remains PASS/market-reference.

Do not convert that case to PRESEASON from date.

- [ ] **Step 6: Verify non-NBA proof continuity**

Acceptance script asserts for all current CFB rows:
- `proof_lane_key == lane_key`;
- `proof_version == LEGACY_PROOF_VERSION`;
- forward identity for a fixed synthetic CFB row equals the pre-migration expected string.

Also assert non-NBA compatibility `by_lane` remains promotion-authoritative for its single proof lane.

Expected: `NON_NBA_PROOF_CONTINUITY_PASS`.

- [ ] **Step 7: Verify append-only history prefixes are unchanged**

Using the pre-run `/tmp/sports-zenith-regime-prefixes.json`:
- for each JSONL, hash the first original N lines;
- assert the hash equals the pre-run hash;
- permit only appended lines after N.

Expected: `IMMUTABLE_PREFIX_PASS`.

- [ ] **Step 8: Verify line CLV and Brain Record expose regime-aware proof**

Acceptance script asserts:
- `BETTING_V2_LINE_CLV.json["by_proof_lane"]` exists;
- NBA proof rows are regime-specific;
- `BRAIN_PERFORMANCE.json["betting_v2_all_markets"]["validation"]["by_proof_lane"]` exists;
- `["forward"]["by_proof_lane"]` exists;
- `["line_clv"]["by_proof_lane"]` exists.

Expected: `BRAIN_REGIME_PROOF_PASS`.

- [ ] **Step 9: Run existing commercial/unit regression suite**

Run:

```bash
cd /home/ubuntu/sports-hulk/commercial_web
node --test *.test.js
```

Expected: existing Node suite passes with 0 failures.

- [ ] **Step 10: Build commercial app and syntax-check server**

Run:

```bash
cd /home/ubuntu/sports-hulk/commercial_web
npm run build
node --check server.js
```

Expected: exit 0; Vite chunk-size warning may remain non-blocking.

- [ ] **Step 11: Restart live commercial service and verify health**

Run:

```bash
cd /home/ubuntu/sports-hulk/commercial_web
export XDG_RUNTIME_DIR=/run/user/1000
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
systemctl --user restart sports-hulk-commercial.service
sleep 1
curl -sS -o /tmp/zenith_regime_health.json -w 'HTTP %{http_code}\n' http://127.0.0.1:8510/api/health
cat /tmp/zenith_regime_health.json
```

Expected:
- `HTTP 200`;
- all required source booleans remain true.

- [ ] **Step 12: Inspect exact changed-file set**

Run:

```bash
cd /home/ubuntu/sports-hulk
git status --short
```

Do not stage unrelated generated warehouse/history noise.

Stage only:
- source files from Tasks 1-4;
- tests;
- the specific regime-aware generated artifacts needed for the accepted baseline;
- no unrelated live refresh outputs.

- [ ] **Step 13: Commit the accepted regenerated baseline**

Use exact-file `git add` paths from Step 12.

Commit message:

```bash
git commit -m "Rebaseline NBA Betting V2 by competition regime"
```

- [ ] **Step 14: Fresh verification after the final commit**

Run again:

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m unittest discover -s tests/betting_v2 -p 'test_*.py' -v
cd commercial_web
node --test *.test.js
npm run build
curl -sS -o /tmp/zenith_regime_final_health.json -w 'HTTP %{http_code}\n' http://127.0.0.1:8510/api/health
```

Expected:
- Python tests: 0 failures;
- Node tests: 0 failures;
- build: exit 0;
- health: HTTP 200.

Only after this fresh run may the checkpoint be called complete.
