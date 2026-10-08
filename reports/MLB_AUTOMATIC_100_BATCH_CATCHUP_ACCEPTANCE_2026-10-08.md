# Sports HULK MLB automatic verified result catch-up — isolated acceptance

Date: 2026-10-08 UTC
Branch: feature/mlb-100-automatic-catchup
Release status: tested in isolated worktree; not yet deployed when authored

## Goal
- The existing MLB forward settlement safely graded up to 100 official Final box-score predictions per *hourly run*, but once 300+ results from a final game were verified it could take four hours to clear them all.
- Keep each batch no larger than 100, but automatically work through up to four separately verified batches in the SAME scheduled run. Maximum 400 per hourly cycle.

## Source integrity and accountability
- Each of the maximum four batches runs the existing unique MLB gamePk, numeric player ID, archived/frozen opponent and pregame timing, official final box, actual played stat, frozen side/line and previous grade-conflict checks *again*, not a single unverified bulk write.
- Each batch enforces old byte-preserving append-only entries, source-content fingerprints and concurrent ledger writer checks.
- Stop on an official source error, source mutation, ambiguous original identity, prior-grade conflict, no new settled entries or empty verified backlog.
- Partial official-source failure after one successful batch leaves that independently verified batch in the ledger, marks source status PARTIAL_SOURCE_HOLD, and reports remaining count as unknown (not zero).
- The receipt now has batch_results, batches_executed, batch_limit=100, max_batches_per_refresh=4, and verified_remaining_for_future_refresh. The public forward summary exposes the batch result metadata.
- All models remain unpromoted; official analytical result receipts never claim actual sportsbook bets or realized payouts.

## Isolated source/regression proof
- 350 synthetic fully official-game-and-player verified results cleared in one hourly-style run as [100, 100, 100, 50], preserving original immutable byte prefix and 350 original frozen keys.
- 405 qualified cases stopped safely at [100,100,100,100], retained five verified for next run, then settled [5] and added zero on a third idempotence pass.
- Simulated official source outage after 100 verified results: only first 100 appended, 20 remained pending, status PARTIAL_SOURCE_HOLD, last_batch_status OFFICIAL_API_UNAVAILABLE, future-ready count UNKNOWN.
- Nonfinal schedule had one READY zero-result batch and did not loop.
- Previously settled WIN grades preserved; invalid batch_size/max_batches values rejected.
- Direct hourly main() integration mock confirmed 250 official MLB results are counted once in the overall forward summary while auto-promotion remains false.
- New isolated tests: 7 PASS.
- Existing MLB ID crosswalk: 16 PASS, official box: 26, rolling windows: 10, missing snapshot: 10, player ID capture: 17, MLB master: 14.
- NHL: 23, NFL: 11, NBA: 43, regime proof: 59, forward provenance: 22, deployment safety: 8 — all PASS.
- Commercial Node/API/UI: 66 PASS; Vite production build, Python compilation, GitHub CI and manual review workflow YAML PASS.

## Existing real ledger source replay
- Live immutable ledger copied; 5,200 frozen total sport entries, including MLB 2,498 predictions with 1,467 WIN, 623 LOSS and 408 PENDING.
- Current official MLB result source confirmed five finals and 2,090 existing settled results, with zero new qualified grades, zero grade contradictions and no source changes.
- New automatic runner on copied ledger produced READY, one bounded zero-settlement batch and an identical ledger byte-prefix. Second pass appended zero duplicates.
- The remaining MLB pending categories were 368 without official Final, 37 without verified player appearance and three originally captured after first pitch.
- Other sports and frozen probabilities left unchanged. No model promotion, sportsbook payouts or guaranteed profitability.

## Controlled live release
- Source-only fast-forward after existing dirty path check. Back up frozen ledger, official source snapshots, summary/receipt and Brain Performance before any live builder call.
- Verify scheduled hourly job executes auto catch-up without source race. Check live receipt and public forward summary and healthy Sports/Survivor endpoints.
- Push GitHub main to run read-only CI, not automatic destructive deployment.
