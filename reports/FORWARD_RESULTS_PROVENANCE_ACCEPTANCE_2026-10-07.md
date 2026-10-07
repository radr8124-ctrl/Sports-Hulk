# Sports HULK forward-result provenance — isolated acceptance

Date: 2026-10-07
Branch: feature/forward-results-provenance
Mode: forward accountability and verified research-only settlement

## Root cause and corrections
- Prop V2 froze market_subtype as the ledger field market, but its settlement identity looked only for market_subtype. That mismatch prevented all 5,153 frozen prop entries from matching source grades.
- Fixed the identity round-trip without replacing frozen forward keys or changing prediction probabilities.
- Settlement now uses matching explicit event ID, or complete game key when event identity evidence does not conflict. Date-only fallback cannot settle a prediction, preventing same-date/doubleheader errors.
- Repeated historical source observations must agree on grade, scores, value, event identity, game identity, and parlay leg grades. Contradictory evidence quarantines the key, rather than overwriting a WIN/LOSS.
- Applied consistent collision protection to All-Markets Game, Props, and Parlay forward result lookups.
- All unresolved/future/unverified records remain PENDING. No automatic model promotions, no fabricated payouts or recorded real-money wagers.

## Independent replay
- Copied immutable ledgers and historical grading sources into the isolated worktree.
- Prop forward ledger before: 5,153 distinct predictions, 0 settled.
- Exact source-verified settlement of 991 predictions: NFL 25, MLB 514, NHL 452. NBA 0 settled because no prop history is yet graded.
- Replay result: 576 WIN, 415 LOSS, 4,162 PENDING, 0 duplicate settlements on subsequent runs.
- All 991 matched the same provider event identifier. No source grade conflicts among matched entries.
- Frozen ledger bytes remained an exact prefix of the replay output (append-only).
- 2,685 prop predictions still overdue by 12 hours and remain visibly PENDING; not assumed losses.
- Across four forward tracking families (nonunique predictions), snapshot after replay reported 7,417 tracked and 2,009 settled. Cohorts are explicitly not counted as unique wagers.
- All six sports are represented (NFL, CFB, CBB, MLB, NBA, NHL). CBB is marked without available forward entries, not invented results.
- Parlay backlog uses the latest confirmed leg start, not the first leg alone.

## Brain Record integration
- Automatic Brain Performance refresh writes FORWARD_RESULTS_ACCOUNTABILITY.json, a public equivalent and embeds forward_results_accountability in the Brain JSON.
- Complete isolated Brain Performance run finished READY and reproduced the separate receipt as parsed JSON.

## Tests
- Python regime: 59 PASS
- Python NBA: 43 PASS
- New forward provenance: 22 PASS
- Deployment safety: 8 PASS
- Commercial Node: 66 PASS
- Vite production build: PASS
- Python source compilation and GitHub workflow YAML parse: PASS

## Deployment conditions
- Do not stage copied runtime ledgers or historical CSVs.
- Back up live prop, game, parlay and legacy forward ledgers, Brain snapshot and historical grades before merge.
- Fast-forward source code after confirming no overlap with live pending edits and no active performance/refresh job.
- Replay on live only after backup; verify exact source matches, no grade rewrites, idempotence, and ledger prefix preservation.
- Rebuild Brain Performance and validate both API and Survivor health.
- GitHub CI stays read-only and cannot trigger an automatic live deployment.
