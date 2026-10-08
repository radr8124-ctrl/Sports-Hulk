# MLB pending progress in Brain Record — production release

UTC date: 2026-10-08
Feature revision: 566e77c
Backup: .deploy_backups/mlb_brain_panel_20261008T005412Z
Recovery branch: backup/pre-mlb-brain-panel-20261008T005412Z

## Live delivery
- Added a compact MLB Props research-progress section near the top of the existing Brain Record tab, just beneath the separately labeled official published picks record.
- Shows totals (frozen pending, settled, wins, losses) and only proof-backed reason counts from the league-verified source receipt (awaiting official Final, player appearance not proven, invalid pregame capture). Additional source holds or a verified gradeable queue display only when they exist.
- Makes clear frozen research entries are not proof of an officially published selection, actual sportsbook wager, sportsbook void or realized payout.
- On stale/invalid/mismatched official receipts, the panel shows ledger headline totals with Source proof pending but hides all causal counts.
- Reads only the existing public Brain Performance source and updates on its existing 60-second polling; no extra upstream API, model change or result settlement.

## Source, test, and live review
- Only PerformancePanel.jsx, mlbPendingProgress.js and a 7-case pure Node validation suite were committed; production App.jsx and unrelated unfinished market changes were preserved exactly.
- Production sourced build used live App.jsx (which included previous intentional uncommitted UI changes), not the committed-branch worktree's older App.jsx.
- The live static dist was staged separately, built and tested before swapping. Entire prior 21 MB dist was moved to the dated rollback location.
- New published lazy chunk was PerformancePanel-zHTkRY_3.js; contains the precise MLB pending progress section. HTTP 200 for root, commercial API, Brain JSON, lazy-loaded component and Survivor health.
- 73 Node/API/UI tests passed (7 additional checks atop all 66 existing); Vite production compile passed.
- Production live App.jsx SHA-256 before and after build was identical; no unrelated source code overwritten.

## Current official MLB research state at publish
- 2,524 frozen MLB predictions; 1,467 WIN, 623 LOSS, 2,090 settled and 434 PENDING.
- Source-reconciled holds: 394 waiting for strict MLB official Final game boxes, 37 lacking verified player appearance, and three captured after the actual original first pitch. Zero currently gradeable results were awaiting processing.
- During the latest official schedule query at around 00:55 UTC, Dodgers–Braves was still live in the ninth inning, Rays–Yankees live in the third inning and Brewers–Padres pregame. None can be settled without official Final and player stats.
- An existing hourly Sports HULK forward refresh is already configured to clear up to four sets of 100 verified results per hourly run.

## Next
- Keep tracking official Finals and append no more than 100 verified analytical grade events per batch, with immutable source proof and zero model promotion.
- When official games finish, the Brain Record source breakdown updates automatically from the already existing server refresh and public JSON.
