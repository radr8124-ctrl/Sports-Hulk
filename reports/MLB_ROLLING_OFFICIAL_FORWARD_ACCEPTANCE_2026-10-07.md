# MLB rolling official results and frozen-event fallback — isolated acceptance

Date: 2026-10-07 UTC
Branch: feature/mlb-rolling-official-windows
State: isolated acceptance PASS. No production ledger modified yet.

## Two root causes addressed
- The official MLB forward settlement planner previously halted every MLB result check once the earliest and latest frozen provider events spanned more than 31 days, even if many older outcomes were already verified. That would make multi-month performance accountability stop progressing.
- Original frozen MLB forward entries now store official numeric player ID, exact away/home club names and original first pitch. However, the settlement planner still required a separate archived research snapshot to associate sportsbook event UUID with an official MLB gamePk. If an archive snapshot was absent for a valid frozen event, the original capture proof was unused.

## Fix and integrity
- Group archived/frozen original game starts into UTC-date windows of <=31 calendar days inclusive, with one date of timezone margin each side. Only fetch windows around actual frozen event dates, not intervening empty months.
- Bound calls to 48 schedule windows; too many windows fail closed. All windows must succeed before the planner can append any forward result.
- Deduplicate identical official gamePk entries across overlapping windows. Contradictory duplicate official game identities are a batch-wide source-validation failure.
- Reconcile provider UUID, original game clock and exact away/home club evidence from BOTH archived snapshots and immutable original captured MLB forward entries. When an archived snapshot is absent, the immutable original capture may associate a sportsbook UUID with an official gamePk only after a unique official team/start match.
- Conflicting snapshot and frozen club/time evidence poison the provider event mapping instead of choosing whichever source happens to be last.
- Settlement of an individual player still requires the identical numeric player ID, original name/club, official Final game feed, actual played box-stat and original pregame market/side/line.
- Existing settled grade contradictions stop the whole batch; DNP and unfounded results remain PENDING. All frozen probabilities, model versions, previous ledger entries and automatic model-promotion gates are untouched.
- Official analytical grades do not establish real-money bets or realized payouts.

## Acceptance
- New rolling-window and overlapping-source tests: 10 PASS, covering cross-calendar years, leap day, 140 continuous daily events, duplicate/conflicting official gamePks, <=31-day API bounds, source budget, and multi-month partial-source failure.
- New missing-archive frozen-event tests: 10 PASS. Complete frozen original player/game metadata and official Final box can be graded, but missing/invalid IDs, conflicting archived club, changed time, post-first-pitch capture, DNP and prior-result conflict cannot.
- Prior MLB official-box 26, historic ID crosswalk 15, original capture 17 and Game Master 14 tests PASS.
- NHL 23, NFL 11, NBA 43, regime proof 59, forward provenance 22 and deployment safety 8 PASS.
- Commercial Node suite 66 PASS and Vite frontend build PASS. Workflow YAML + Python compile PASS.
- Real production-data read-only source replay: 8 archived UUIDs, one October schedule window, four finalized MLB boxes, 1,943 existing official box-confirmed results, zero mismatches, zero new eligible outcomes.
- Full isolated copy of source histories and frozen forward ledger: 5,199 frozen entries preserved; MLB 1,369 WIN, 574 LOSS, 554 PENDING unchanged. Second replay added zero duplicate outcomes. Full ledger byte prefix and all other-sport grades preserved.

## Release
- Commit only source code, tests and this report; exclude copied runtime ledgers, archived source data and output JSONs.
- Before production merge back up frozen prop forward ledger, independent grade/source receipts and current Brain Record, while preserving uncommitted market and UI work.
- Fast-forward checked source-only commit, rerun official planner and scheduled forward summary, confirm zero previous grade rewrites and no model promotion, and keep both sites healthy.
- Push main to read-only GitHub CI for final Python/UI/deployment safety validation.
