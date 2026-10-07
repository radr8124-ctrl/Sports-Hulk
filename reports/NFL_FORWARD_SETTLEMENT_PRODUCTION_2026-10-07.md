# Sports HULK forward-source investigation and NFL production correction

Date: 2026-10-07 UTC
Source revision: 774551c
Production: /home/ubuntu/sports-hulk
Backup: .deploy_backups/nfl_exact_grading_20261007T212432Z
Recovery branch: backup/pre-nfl-identity-20261007T212432Z
Investigation: reports/FORWARD_SETTLEMENT_SOURCE_INVESTIGATION_2026-10-07.md

## Live NFL correction
- Graded sportsbook PROP snapshots contain nflverse player identity with optional team, e.g. 00-0038997|IND. Prior grader treated the ID as a player name.
- New grader matches the explicit nflverse player ID or genuine player name, exact NFL week, verified team/opponent pair, and exactly one statistical result.
- No fallback to a previous week's boxscore or a mismatching opponent; malformed/duplicate identities remain unresolved.
- Performed regrading against the already-saved official ESPN NFL game-result snapshot, with no extra provider fetch.
- Saved live pre-release source and outcome backups, fast-forwarded source branch only, and published atomic grade CSVs.
- 3,659 archived ledger rows, 712 unique latest recommendations.
- 117 previously unresolved NFL sportsbook PROP episodes now graded: 62 WIN, 55 LOSS.
- The five remaining unresolved official player results stay unresolved; unsupported props and unplayed games remain unresolved/pending.
- Zero prior settled grade changes; no PRIZEPICKS, GAME or PARLAY grade changes.
- Frozen prop forward ledger gained 28 verified NFL SETTLED events: 22 WIN, 6 LOSS, all with exact event match.
- NFL frozen forward prop record: 95 tracked, 42 WIN, 11 LOSS, 42 PENDING. 12 are overdue by 12+ hours.
- Live historical forward ledger bytes 7,223,637 -> 7,235,589, byte-prefix preserved; all 28 append events were verified. No other sport forward grade was changed.
- A repeat settlement scan added zero duplicate outcomes.
- All-model automatic promotion remains disabled.

## Cross-sport root cause
- MLB: 1,979 pending; 904 lack an exact matching frozen market side/line despite related historical observations; 766 absent historical market subtype; 192 missing graded player episode; 113 historical episodes still PENDING; 4 DNP. Date-only grading prohibited without a verified provider-event to official gamePk/player crosswalk.
- NHL: 1,152 pending predictions have uniquely matched official completed game, player ID, supported boxscore stat, and frozen pregame start. 447 already settled predictions independently agree with the official box stat; zero contradictions observed. The remaining 300 pending are not yet source-verifiable: 271 games not final, 19 roster-ID gaps, and 10 player-box gaps. They remain pending. An additional 5 already settled NHL predictions could not be independently rechecked from this roster/box snapshot, so no reconciliation change was made to them.
- The NHL sample Darnell Nurse is recorded under SJS in the current NHL roster; no mislink conclusion is supported by that sample.
- NHL source-ready records are NOT settled by this NFL-focused release. They require a dedicated immutable-proof market-line settlement builder and safety tests.

## Live accountability
- Rebuilt Brain Performance and independent FORWARD_RESULTS_ACCOUNTABILITY snapshot.
- Cross-family forward tracked 7,417, settled 2,037, overdue 12+ hours 2,922; different families can overlap and are not unique wagers.
- Commercial /api/health 200 and Survivor /_stcore/health 200.
- Existing unrelated dirty worktree edits preserved; no commercial UI restart required.
- Previous isolated regression: 11 NFL identity, 59 regime, 43 NBA, 22 forward provenance, 8 deployment safety, 66 JavaScript tests, production Vite build all PASS.
- GitHub pushes run read-only CI; no automatic deployment.

## Next step
Controlled, isolated NHL official-box result replay (unique final game + player + verified stat + frozen market/line/side + pregame capture, with no contradiction to already settled outcomes). Separately build MLB provider event/gamePk identity reconciliation; do not guess from the date alone.
