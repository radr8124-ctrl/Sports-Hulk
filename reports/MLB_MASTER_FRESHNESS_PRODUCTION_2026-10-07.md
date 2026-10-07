# MLB master score/status freshness — production release

Date: 2026-10-07 UTC
Source revision: 3882a5d
Production: /home/ubuntu/sports-hulk
Backup: .deploy_backups/mlb_master_live_20261007T222802Z
Code recovery branch: backup/pre-mlb-master-20261007T222802Z

## Why this needed repair
- The Game Master 2026 raw cached schedule and derived CSV had been built on October 3.
- Thirteen October playoff games were still recorded as older Scheduled/Pre-Game/In Progress statuses, even after the current official MLB StatsAPI feed showed completed or live.
- The previous full-season builder blindly reused the current-year cached schedule, risking later regression of completed scores.

## What changed
- Introduced a strict recent MLB StatsAPI schedule status/score refresher after official core collection and before market fusion in the recurring MLB refresh pipeline.
- It matches numeric official gamePk, team names and MLB team IDs, season game type, and kickoff within two hours.
- It never downgrades an already-final or live game to an earlier lifecycle phase or silently overwrites a different previously-final score.
- A duplicate official gamePk, changed source file, unsupported status or new game absent from the original master is flagged for review.
- Updates are restricted to current official status, first pitch and score-derived values on already-existing games. No historical game rows, betting results, frozen probabilities or unrelated columns are intentionally modified.
- Full-season rebuilds now bypass the cached raw schedule for the active MLB season, and only reuse prior seasons once the season has finalized.

## Official real-data production acceptance
- Live official date-window queried 29 games.
- Safely corrected 13 recent game lifecycle records with 0 source conflicts and 0 missing-new-game exceptions.
- MLB official playoff finals for gamePk 849834, 849839, 849819 and 849826 are now all Final with correct MLB team scores.
- Existing cached Game Master had 7,911 rows. The live source was already modified versus Git HEAD in several independent market-count columns and contained 3 fewer game keys than tracked HEAD; the full byte copy was preserved BEFORE integration.
- Code integration did not modify the dirty master. The source refresh then preserved all 7,911 gamePk values and every non-target row including its unrelated market columns.
- Both derived CSV and parquet retain 7,911 rows after official refresh.
- Previous master CSV, parquet, cached raw 2026 schedule and worktree manifest were backed up together with SHA256 receipts.
- Commercial API and Survivor health checks returned HTTP 200.
- No UI restart, historical-grade rewrite or automatic betting model promotion.

## Validation
- New official Game Master tests: 14 PASS (final-status monotonicity, score contradictions, double gamePk, no missing historical rows, source outages, dry-run and idempotence).
- Previous regression pass: MLB official prop forward 26, NHL 23, NFL 11, NBA 43, regime 59, forward provenance 22, deployment safety 8; all PASS.
- Commercial Node tests 66 PASS; Vite production build PASS, Python and Bash syntax plus GitHub workflow YAML valid.
- GitHub CI now includes the parquet engine (pyarrow) required by these Game Master tests, with CI-only push and no destructive automatic deployment.

## Current tracked MLB forward outcomes (unchanged by this master refresh)
- Frozen MLB prop predictions: 2,495.
- Official-source confirmed: 1,222 WIN, 505 LOSS, 768 PENDING.
- Model auto-promotion remains disabled. These are analytical predictions, not verified real-money placed wagers.

## Next
- Improve official player ID capture in frozen MLB research outputs for the 221 predictions that cannot yet be independently verified; do not infer a player ID by a fuzzy-name or date-only match.
- Extend forward official schedule requests to rolling windows as futures accumulate beyond the current 31-day verification range.
