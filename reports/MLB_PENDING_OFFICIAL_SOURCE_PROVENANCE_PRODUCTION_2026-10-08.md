# MLB pending official-source accountability — live production acceptance

Date: 2026-10-08 UTC
Deployed source revision: 9385eb3
Backup/recovery: .deploy_backups/mlb_pending_truth_20261008T003732Z and backup/pre-mlb-pending-truth-20261008T003732Z

## Live changes
- MLB official prop forward catch-up now records the exact SHA-256 and byte length of the frozen append-only ledger at the conclusion of official source verification.
- Public Brain Record includes a read-only MLB pending breakdown, but trusts official reason buckets ONLY when the latest source receipt is READY, totals and last-batch settlements reconcile, no prior grade contradiction exists, and the current ledger matches both stored SHA-256 and byte length.
- Missing, stale, mutated or partial source receipts keep the breakdown unverified rather than guessing result reasons or marking a player as sportsbook-void.
- Existing age-based pending-overdue counts/status remain for compatibility, but are explicitly distinguished from an officially gradeable source backlog.
- No underlying frozen market/line/pick/probability is changed. Official WIN/LOSS data still requires league Final boxscores, exact player/game ID and pregame provenance; no automatic model promotion.

## Live status and verification
- The scheduled hourly model run finished before deploying. No live collector or result writer was active at merge.
- Backed up all current forward, Brain and league provenance sources with a SHA-256 manifest, then fast-forward merged code/tests/report only; unrelated dirty frontend and market collector work was preserved.
- Three live postmerge test suites PASS: 15 new pending source proof tests, 22 forward provenance tests, 7 automatic batch-size catch-up tests.
- The live Prop V2 forward builder rechecked 2,090 previously settled MLB results with zero conflicts and zero newly eligible official game outcomes at that time. Frozen ledger byte prefix preserved completely.
- The hourly collector had added 26 new pregame research ENTRY events before deployment, bringing the live MLB record to 2,524 tracked, 1,467 WIN, 623 LOSS, and 434 PENDING.
- Current validated official-source reasons across the 434: 394 NO_OFFICIAL_FINAL_BOX, 37 PLAYER_NOT_VERIFIED_PLAYED, 3 NOT_VERIFIED_PREGAME_OR_START. These are NOT sportsbook voids or actual wager losses. Zero verified outcomes were waiting to be appended in the source receipt.
- Receipt SHA-256 digest and file length matched the live frozen ledger exactly; public Brain Performance and public/embedded forward results accountability were all READY and matched each other.
- Site endpoints: commercial API 200, Survivor 200, Brain JSON 200, forward_results_accountability JSON 200.
- The result batch controller remains up to four sequential source-verified batches of no more than 100 per scheduled hourly run.

## Tests and safeguards
- 15 new pending proof tests, 22 generic forward tests, 7 automatic catch-up tests, 26 original MLB official box tests, 16 MLB numeric ID crosswalk tests, 10 MLB schedule rolling tests, 10 frozen provider identity tests, 17 MLB player-ID capture tests, 14 MLB master freshness tests, 23 NHL, 11 NFL, 43 NBA, 59 regime and 8 workflow safety tests: PASS.
- Commercial Node/API/UI 66 tests PASS, frontend Vite production build PASS, Python syntax and both GitHub workflow YAMLs PASS.
- No UI App.jsx changes were overwritten, no platform payout was claimed, and no betting model was automatically promoted.

## Next check
- Await MLB StatsAPI's strict Final status and completed participated player boxes for Dodgers–Braves, Rays–Yankees and Brewers–Padres. The hourly catch-up then grades at most 400 verified new results per cycle in 100-outcome batches.
- Historical player-participation and pregame-time holds remain separate from live games awaiting finals.
