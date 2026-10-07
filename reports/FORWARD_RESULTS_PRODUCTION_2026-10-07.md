# Forward results provenance — production release

Date: 2026-10-07 UTC
Live source revision: d0931f3
Environment: /home/ubuntu/sports-hulk
Production state backup: .deploy_backups/forward_results_20261007T210346Z
Rollback branch: backup/pre-forward-results-20261007T210346Z

## Scope
- Corrected prop settlement identity to read frozen market field or original market_subtype.
- Required exact provider-event matching or safely corroborated full game identity; never date alone.
- Added historical source conflict quarantine to Game, Prop and Parlay forward lookups.
- Embedded a per-sport (NFL, CFB, CBB, MLB, NBA, NHL) accountability report in the Brain Record and published its independent JSON snapshot.
- CBB has no forward records and is explicitly displayed as no entries.
- Existing prediction model versions, probabilities, capture timestamps, historical results and unrelated frontend work were preserved.

## Verified live forward results
- 991 newly source-matched prop predictions settled: NFL 25, MLB 514, NHL 452.
- 576 WIN, 415 LOSS and 4,162 still PENDING among 5,153 frozen prop entries.
- All newly settled records matched official graded historical rows by the same provider event ID; no conflicting matched grades were observed.
- No duplicate result on subsequent isolated replay; live set only appended settlement events.
- Cumulative forward-family observations (non-unique, includes overlapping families): 7,417 tracked; 2,009 settled.
- Remaining overdue 12+ hours across families: 2,950; overdue 48+ hours: 390.
- Prop overdue 12+ hours: 2,685; these remain PENDING, never automatically counted as losses.
- This is performance/accountability for recorded predictions, not proof of real-money wagering, betting profit, or a validated winning strategy.
- All model promotion gates remain unchanged and automatic promotion remains false.

## Append-only verification (old bytes -> new bytes)
- Prop ledger 6,802,051 -> 7,223,637 (exact prefix preserved).
- Parlay ledger 5,648,693 -> 5,648,693.
- All-Markets game ledger 622,659 -> 622,659.
- Legacy Betting V2 ledger 82,554 -> 82,554.
- All-Markets price snapshots 1,057,613 -> 1,057,613.
- Frozen pre-release backups include SHA256SUMS.txt; no historical grades were edited.

## API and site
- Commercial /api/health 200
- Brain Performance JSON 200 / READY, new forward_results_accountability object present
- Public /forward_results_accountability.json 200, matches embedded object
- Survivor /_stcore/health 200
- Frontend production build passed; existing pending App.jsx changes preserved.
- No unnecessary commercial restart.

## Post-merge regressions
- 59 Python competition-regime PASS
- 43 Python NBA PASS
- 22 new forward-evidence and backlog-audit PASS
- 8 GitHub deployment safety PASS
- 66 commercial Node PASS
- Vite production build PASS
- No unverified outcome or automatic promotion.

## Next investigation
- Pending-source gaps in MLB and NHL player props; verify official postgame boxes by event and player.
- NFL unresolved prop result coverage; ambiguous player IDs and unsupported markets must remain PENDING.
- NBA prop settlement naturally awaits completed games and graded player outcomes.
- CFB/CBB and additional game-market forward samples require authoritative results; never infer wins from odds or schedules.
- Ensure overdue counts shrink through verified data ingestion, not invented historical wins/losses.
