# MLB 100-result automatic multi-batch catch-up — verified production

Date: 2026-10-08 UTC
Live source code revision: 64d2597
Environment: /home/ubuntu/sports-hulk
Recovery branch: backup/pre-mlb-auto-catchup-20261008T001923Z
Backup with SHA256 source manifest: .deploy_backups/mlb_auto_catchup_20261008T001923Z

## Production result
- Automatic official MLB prop settlement now loops over up to four separately VERIFIED batches in each scheduled hourly Prop V2 refresh; at most 100 graded results may be appended in any batch, up to 400 in a single refresh.
- Source verification and concurrent frozen-ledger checks run separately for each batch, and the next batch stops when no new verified results remain or the source is unavailable.
- A partial source outage after one successful batch preserves that first independently verified batch but sets PARTIAL_SOURCE_HOLD and reports the unsettled verified count as unknown, never falsely zero.
- The official MLB receipt and public forward summary expose each batch's status and count, the total appended in that hourly run, how many verified were left, the four-batch cap, and the model-promotion flag.
- Frozen model probabilities/identities, previous settlement grades and all unrelated sports remain untouched. No platform wager, payout or betting profitability is claimed.

## Live deployment and verification
- Source-only fast-forward merged while MLB collectors and hourly writer were inactive. Unrelated modified App.jsx and other sport/market work were preserved.
- Original immutable forward ledger, official historic MLB player-ID sources, archived snapshots, forward receipt/summary and Brain Record were backed up with SHA256 hashes and recovery branch.
- Immediate production postmerge: 7 new automatic catch-up safety tests PASS, immutable ledger exact byte-equality to premerge.
- Live Prop V2 forward builder ran successfully with automatic catch-up: READY, one 0-result batch because there were no new independently confirmed official-final played markets. Actual source receipt batch_limit=100 and max_batches_per_refresh=4; 0 grade contradictions.
- Before/after production source upgrade, all 9,440,517 original ledger bytes were retained exactly; no events appended and no frozen keys rewritten.
- Current MLB frozen forward: 2,498 predictions, 1,467 WIN, 623 LOSS, 2,090 settled, 408 PENDING.
- The pending MLB categories remain 368 without official Final game, 37 not verified as having played and 3 originally captured after official first pitch.
- Brain Performance existing public/embedded accountability matched the canonical ledger (READY), with 35 MLB pending overdue 12h and zero automatic model promotions. Separate MLB user wagers/payouts were NOT created.
- Public Sports API, Survivor page and Brain API each returned HTTP 200.

## Isolated acceptance and CI
- 7 new automated catch-up tests PASS:
  - 350 source-proven outcomes in one run as 100+100+100+50
  - 405 verified outcomes halted at 100+100+100+100 then resumed with 5 next run and 0 duplicates
  - fail-closed after 100 when the league feed is unavailable on the next batch
  - unverified live games never grade, prior grades remain intact, invalid cap inputs rejected, and main() includes 250 settled in its published summary.
- All related sport and release safety suites passed: crosswalk 16, MLB official 26, rolling schedule 10, frozen source 10, MLB capture 17, MLB master 14, NHL 23, NFL 11, NBA 43, regime proof 59, forward provenance 22 and release workflow 8.
- Commercial Node/API/UI suite 66 PASS; production Vite build and CI workflow YAML validity PASS.
- Isolated real-data replay on the 5,200-entry frozen ledger matched existing 2,090 MLB official graded results, produced one READY zero-result batch and an identical ledger byte prefix; second pass appended zero duplicates.
- This release only changes verified-result catch-up. No model promotions or destructive automated deployment.
