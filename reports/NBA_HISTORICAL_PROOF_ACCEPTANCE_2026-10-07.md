# NBA historical proof integrity — acceptance review

Date: 2026-10-07
Branch: feature/nba-history-proof-integrity
Live service: unchanged in isolated acceptance

## Discovery
- NBA result deduplication previously chose the last completed CSV row by event_id.
- The legacy NBA_RESULTS_HISTORY copy for ESPN event 401902644 had no season_type, while the authoritative NBA_GAME_HISTORY final for the same event had ESPN season_type=1. Duplicate final score and teams matched; a final-but-unlabeled copy incorrectly won.
- That lost PRESEASON metadata on four historical TOTAL recommendation observations and created UNKNOWN evidence in Betting V2.
- The hourly betting proof build could run earlier than the ten-minute NBA grading refresh. File modification time alone incorrectly labels a proof stale after a grader rewrites identical CSV data.

## Fix
- Reconcile duplicated NBA final results by completeness and valid explicit season type instead of last row wins.
- Quarantine final score, team, date, or season contradictions as REVIEW_SOURCE_CONFLICT instead of WIN/LOSS.
- Require a genuine event ID for grading and prevent ambiguous same-day matchups from silently resolving.
- Never infer competition regime from game dates or schedules.
- Write NBA_GRADED_RECOMMENDATIONS.csv atomically, protecting concurrent Betting V2 reads.
- Make grader paths worktree-relative so future isolated validation cannot accidentally modify live NBA state.
- Add a post-grading proof audit with separate NBA proof-cohort counts, result-conflict totals, pregame observation counts, and a strict no-promotion indicator.
- Betting V2 validation records a stable SHA-256 of NBA GAME-grade evidence; the audit compares that instead of raw file modification time. Repeated identical CSV exports do not falsely invalidate proof, while material grade or regime changes do.
- Betting V2 stops without writing output if that source fingerprint changes during its validation build.
- Add the Python audit checks to GitHub read-only CI and manual validation gates.

## Full isolated replay
- Historical recommendations: 936, of which 121 game observations and 815 parlays (not mixed into game betting proof).
- Grade distribution remains 180 WIN, 486 LOSS, 270 PENDING across all observational lanes (primarily historical parlays).
- Recommendation keys preserved, 936/936; no WIN/LOSS/PENDING grade changes versus the frozen input snapshot.
- All 121 game observations now have explicit PRESEASON type 1. Exactly four missing classifications were recovered; remaining prior 1.0 values were canonically normalized to 1.
- Result-source conflicts currently detected: 0.
- Rebuilt isolated NBA proof lanes: MONEYLINE|PRESEASON 5 independent observations, SPREAD|PRESEASON 7, TOTAL|PRESEASON 11.
- Every lane still INSUFFICIENT_HISTORY; zero model promotions.
- Rebuilt source digest matches graded evidence, audit status AUDITED, stale=false. Prior missing/old proof digest correctly fails closed.

## Test suite
- Python competition regime tests: 59 PASS.
- Python NBA tests (official feed, source reconciliation, proof audit): 43 PASS.
- GitHub deployment safety tests: 8 PASS.
- Commercial Node tests: 66 PASS.
- Vite production build: PASS.
- Python compile, Bash syntax and GitHub YAML parse: PASS.
- Source-only change: source code, safety tests and this receipt; no runtime CSVs or immutable ledgers staged/committed.

## Deployment discipline
- Back up graded CSV, result history, Betting V2 validation/model/current artifacts and append-only forward ledgers.
- Integrate with fast-forward only after checking no overlapping live work.
- Regrade NBA history and rebuild dependent all-market proof, forward tracking and Brain Performance; compare recommendation grades to original snapshot and verify both append-only ledger prefixes.
- Do not restart UI merely for backend data; verify commercial and Survivor health.
- GitHub Actions remains CI-only on pushes; manual release workflow remains read-only.
