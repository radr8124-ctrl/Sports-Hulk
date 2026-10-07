# MLB Game Master official freshness — isolated acceptance

Date: 2026-10-07 UTC
Branch: feature/mlb-master-freshness
State: production-data replay validated on a separate worktree

## Root cause
- baseball_vault/raw/game_master/mlb_schedule_2026.json was last generated October 3.
- baseball_vault/derived/MLB_GAME_MASTER.csv still listed completed October 5–7 MLB playoff games as Scheduled and omitted their final scores.
- A normal full Game Master rebuild previously reused that same stale current-year cache.
- Live MLB StatsAPI schedule verified current statuses and scores for all recent games.

## Fix
- Add recent status/score refresh based exclusively on the current official MLB StatsAPI schedule, with both numeric MLB team IDs and names, exact gamePk and matching gameType.
- Do not use player prop odds, betting decisions, provider UUIDs or other estimates for game status.
- Preserve the full historical table, every original gamePk and every untouched historical row/feature.
- Guard against a game being downgraded from Final or Live to Scheduled, conflicting preexisting final score, duplicated official game ID, mismatched teams/game type, and kickoff changes greater than two hours.
- Update only status, official first pitch, scores, total runs and home run margin for eligible existing games.
- Write both CSV and parquet data atomically per file, with a recorded official source receipt and source hash before modification; no changes when no results updated.
- Insert the refresh after MLB official core and before markets/fusion in the existing MLB refresh pipeline (55-second budget, safe-run wrapper).
- In a full MLB master rebuild, current year schedules are always fetched live; past-year cached schedules can be reused only after December 15 finalization.

## Real-data isolated replay
- Official league date-window read: 29 games, with 13 status corrections, 0 conflicting games and 0 new game IDs.
- Example official 2026-10-05/06 final games: gamePk 849834, 849839, 849819 and 849826 all correctly became Final with matching official team scores.
- Playoff games on October 7 moved to In Progress/Pre-Game when appropriate, rather than being presented as Scheduled.
- Original row count 7,911 and all gamePk identifiers retained; every non-target row compared equal before and after.
- CSV/parquet rebuilt to the same 7,911-row content.
- No historical game results overwritten, no forward ledgers rewritten and no automatic betting promotion.

## Regression
- New official-master tests: 14 PASS.
- MLB official forward: 26, NHL: 23, NFL: 11, NBA: 43, regime: 59, forward provenance: 22, deployment safety: 8; PASS.
- Commercial Node 66 PASS, Vite production build PASS, bash and Python syntax plus GitHub YAML valid.
- GitHub Actions push is CI-only; old destructive deploy remains disabled.

## Release checklist
- Copy current production master CSV/parquet, cached raw 2026 schedule, status receipts and the source working-state manifest.
- Merge source-only branch with fast forward, preserving uncommitted market collector and UI work.
- Re-run live dry-run and apply recent status sync. Verify 7,911 unique gamePks, four official finals, status idempotence, no previously final score disagreements and all other rows unchanged.
- Verify commercial health and Survivor, and trigger GitHub CI-only sync.
