# NBA historical proof integrity — production release

Date: 2026-10-07 UTC
Live repository: /home/ubuntu/sports-hulk
Source commit: a09491a Harden NBA historical grading and proof provenance
Backup directory: .deploy_backups/nba_history_proof_20261007T204630Z
Rollback code reference: backup/pre-nba-history-20261007T204630Z

## Live outcome
- Merged isolated source-only branch into main with fast-forward and no conflicts.
- Preserved existing unrelated in-progress commercial UI and NBA market collector edits.
- Regraded historical NBA recommendations from live source ledger: 13,179 archive entries, 936 unique recommendations, 666 settled observations across all lanes including research parlays.
- Prior 936/936 recommendation grades unchanged. Four previously blank NBA GAME season types recovered as PRESEASON. All 121 GAME observations now have explicit source type 1.
- No changes to result scores or WIN/LOSS/PENDING classification.
- Rebuilt all-market model validation, forward proof, CLV tracking and Brain Performance.
- NBA proof now correctly partitions: 5 preseason MONEYLINE, 7 preseason SPREAD, 11 preseason TOTAL.
- All three lanes remain INSUFFICIENT_HISTORY; model promotion prohibited.
- NBA proof integrity receipt status AUDITED; stale=false using canonical game evidence digest; conflicting result count=0.
- All-market forward ledger retained original 622,659 bytes exactly; price snapshot ledger retained original 1,054,975 bytes before appending (1,057,613 after).
- No original immutable ledger rows were overwritten.
- No front-end service restart was necessary for source/data updates.

## Live health and safety
- Commercial API /api/health: HTTP 200 / status ok.
- Brain Performance JSON: HTTP 200 / READY; correct preseason proof lanes with source digest present.
- Survivor service (8502): HTTP 200.
- Ask NBA best bet: intent best_bet, status WAITING, confidence WAITING, 0 suggested plays.
- Production code remains on main; GitHub Actions push triggers CI tests only, not an automatic live deployment.

## Production regression checks
- Competition regime tests: 59 PASS.
- NBA tests including historical integrity, official data mapping and audit: 43 PASS.
- Deployment safety tests: 8 PASS.
- Commercial Node: 66 PASS.
- Vite production build: PASS.
- Builder Python compile and NBA learning shell syntax: PASS.

## Next research
- Continue accumulating genuine forward outcomes and paired market pricing before any strategy promotion.
- Keep preseason, regular season and playoffs separated in proof and in the public Brain Record.
- Continue explicit NBA source conflict and proof freshness auditing each scheduled NBA learning cycle.
