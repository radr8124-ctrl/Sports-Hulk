# Sports Zenith — Four-Sport Official Learning and Missing-Grade Recovery (2026-10-10)

## User intent
Use NHL regular season, college football, NBA preseason, and MLB playoffs **today** to improve the existing Sports Zenith learning engine. Preserve the original freeze, do not restart the project, do not invent validated positive-EV model edge, and do not combine unrelated competitions. The project had useful data, but the existing forward settlement was missing exact NBA alternate lines.

## Actual source-backed outcome audit

| Competition | Original SETTLED research lines independently cross-checked with official Final | Different finished games | Official league stage |
|---|---:|---:|---|
| NHL regular season | 17 | 17 | NHL game_type=2 |
| College football | 5 | 5 | ESPN CFB season_type=2 |
| NBA preseason | 167 | 22 | ESPN NBA season_type=1 |
| MLB postseason | 12 | 9 | MLB StatsAPI gameType=D (Division Series) |
| **Total** | **201** | **53** | Four strictly separate cohorts |

Official phase/game identity requires exact team IDs/names and kickoff within 30 minutes; qualifying SETTLED results additionally require the exact official Final scores. No postgame data becomes a retroactively declared pregame input. For NBA the ESPN-vs-market franchise aliases were explicitly reconciled (NY/NYK, NO/NOP, GS/GSW, UTAH/UTA, SA/SAS, WSH/WAS); there is no score-only/fuzzy matching. Repeated identical NBA official fixture rows do not inflate sample sizes and contradictory duplicates fail closed.

MLB's unmodified official public schedule capture `intelligence_warehouse/sport_cohorts/sources/MLB_STATSAPI_POSTSEASON_SCHEDULE_20261010.raw.json` is a 22,264-byte original MLB StatsAPI source. SHA256 `8560faa66e10928b7c4583375270a8d2a0dba1bf80f5adb45c3098aea8cf29e6`. It includes separately identified Division Series (D) and upcoming League Championship Series (L) matches, with real official gamePk. Future playoff events are **not** presented as final before the league does so.

## Major error found: 550 historical market research outcomes still pending

The original `BETTING_V2_ALL_MARKETS_FORWARD_LEDGER.jsonl` had **549 NBA preseason lines from 22 completed games** and **one NHL game-side record** still showing PENDING despite the independently source-verified final score. The NHL case was already flagged as an opposite-side market conflict.

In the NBA original `NBA_GRADED_RECOMMENDATIONS.csv`, all **549** overdue exact game/market/selection/line combinations are **absent from the qualified GAME recommendation grading index**. The existing forward settlement program depends on this exact qualified historic index to append SETTLED events, explaining the uncovered alternative-market lines. Original index SHA256 as of audit `92d98961861d3153700dfcd5e4de44bd6294cd6227f3d790c8ba42c2299ce5f7`. No postgame grade was selected based on outcome or a new line; outcome was recomputed from each original frozen side/line and the official final score.

A separate immutable-source-linked audit receipt `intelligence_warehouse/sport_cohorts/SPORT_COHORT_OFFICIAL_FINAL_SHADOW_GRADES.json` now contains **550 grade-only research observations**. The 549 NBA records break down:
- 200 NBA spreads: 87 result WIN, 112 LOSS, 1 PUSH
- 349 NBA game totals: 281 result WIN, 68 LOSS
- **538/549** were flagged as duplicate or alternative line variants in the ORIGINAL captured record, and **549/549** copied the sportsbook reference probability instead of proving independent model edge
- NHL shadow: one losing market side previously flagged contradictory

These are **not 550 new independent games**: the NBA recoveries come from the same 22 games already present, with one additional distinct NHL game. Across original audited plus recovered records, there are just **54 distinct official finished game IDs**. None proves model betting profit; a high hit percentage on alternate lines has no meaning without original odds, payoff and independent calibrated probability. The original forward ledger remains unchanged/PENDING; the new shadow receipt does not append retroactive SETTLED rows or modify historical scores/picks. Original attempted betting decision was PASS throughout.

An immutable compressed initial recovery snapshot was versioned into Git as `reports/SPORTS_ZENITH_FOUR_SPORT_FROZEN_SHADOW_GRADE_RECEIPT_20261010.json.gz` (18,231 bytes vs 884,231 original JSON bytes). Original receipt SHA256 `9898ef035872f613126ef458ed70ce15ea688a9d9e952e3a136edf0f8c0d866c`; gzip archive SHA256 `0e1bc1eb5fa4b43b5f4772c3677b9a3c25eac3a517afb4031d1fa9f42187554a`. Original data/model source SHAs are also in the JSON receipt. This is versioned on the VPS; a full **off-server restoration has NOT been tested**.

## Implemented continuing pipeline

- New `intelligence_warehouse/sport_cohorts/build_sport_cohort_readiness.py`: hashes source files; keeps NHL/CFB/NBA/MLB by official phase; independently recomputes grades; writes a small public proof summary, full locally preserved shadow receipt and cross-linked hashes; deliberately sets all MODEL_TRAINING/REAL_WAGERS flags false.
- New `intelligence_warehouse/sport_cohorts/update_mlb_postseason_schedule.py`: bounded public StatsAPI schedule (no account, no paid odds) request, immutable date-stamped original raw snapshots, fail-closed duplicate/malformed event validation, never overwrites an earlier daily file. Latest official snapshot is selected by date for subsequent validation.
- Existing hourly `SPORTSZENITH_OUTCOME_LEARNING_SHADOW_V1` builder now also publishes new sport cohorts, without replacing the original learning or Survivor pipelines.
- New daily `SPORTSZENITH_MLB_OFFICIAL_POSTSEASON_PHASE_DAILY_V1` source capture at **10:15 UTC** (06:15 EDT during current daylight time). The schedule was installed and read-back verified with all prior crontab entries unchanged. **The next scheduled daily run has not yet occurred**, so no claim of verified next-day refresh. Existing hourly audit at :22 UTC will incorporate that new snapshot afterward.
- New `commercial_web/src/SportLearningReview.jsx` under **Brain Record**: clear four-sport game counts, phase names, 550 overdue shadow result warning, 549 missing exact grading index proof, and examples of actual final-score prediction misses without made-up causal injury/explanation.
- New strict tests `tests/test_sport_cohort_official_replay.py`, `tests/test_mlb_postseason_schedule_source.py` and `commercial_web/four-sport-learning.e2e.spec.js` validate fixture/event identity, team aliases, league phase, original game score, forward capture time, exact line, grader omissions, append-only separation, source status and mobile layout.
- **Final acceptance:** 86/86 Python source/governance tests; 221/221 Node website tests (after replacing an obsolete hardcoded 2,843-result expectation with checked actual win/loss/push accounting); 47/47 responsive browser tests. React production build PASS. Real HTTPS 390px iPhone-width browser returned HTTP 200, loaded all four competition panels, showed the true 201/53/550 observations and zero horizontal overflow, with no anonymous Survivor identity leak. Existing `/api/health` healthy.
- The initial source-only cohort build and repeated manual hourly learning publisher runs succeeded, but **the first newly installed 10:15 UTC scheduled MLB capture has not been observed yet**.

## Critical next model-science requirements

NHL 17 independent games, CFB 5, NBA preseason 22, MLB Division Series 9 **cannot be combined** to claim 53 sport-homogeneous training examples or to train an NFL winner model. Sport/regime-specific features must be independently as-of captured: hockey goalie confirmation, opponent quality, rest/back-to-back; CFB QB/roster strength and mismatch depth; NBA preseason starter minutes, bench rotations and coach roles (never mix with regular-season minute projections); MLB starter/lineup/bullpen availability and playoff series/rest. Frozen model-vs-book scores, true offered timestamped prices, and substantial *future* holdout groups are needed before a production model or sportsbook-play gate changes. The present V2 still uses copied sportsbook probabilities.

**Decision:** data/source verification repaired for research, error cause recorded, original ledger protected, **zero independent betting advantage proven, zero live weights or wages changed**.
