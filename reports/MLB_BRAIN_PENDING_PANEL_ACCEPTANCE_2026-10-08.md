# MLB pending progress — compact Brain Record panel acceptance

Date: 2026-10-08 UTC
Branch: feature/mlb-brain-pending-panel
Status: isolated verified, source-only release candidate

## Purpose
- Surface official-source verified progress of the append-only MLB research Prop V2 forward ledger directly on the existing Brain Record main tab, beneath the separately labeled official published picks record.
- The block is intentionally compact and uses the existing design system, with 4 headline totals (pending, settled, wins, losses) and 3 source reason counts (awaiting official Final, player appearance unverified, invalid pregame capture).
- Generic overdue is not conflated with officially gradeable outcomes.
- Research results remain separate from actually published picks, sportsbook voids or real-money payouts.

## Validation
- Read from the existing Brain Performance JSON forward_results_accountability.mlb_official_pending_breakdown; no new external API, source or grade.
- Show source reason counts only if the official-source receipt is SOURCE_RECONCILED, ledger numbers are internally consistent, every reason is a nonnegative safe integer, and reasons sum to the pending count.
- If a receipt is stale or new predictions have been frozen, show actual ledger totals with Source proof pending but hide all reason counts.
- Display the verified gradeable queue and other source holds when nonzero, without claiming payments.
- Existing Brain Record endpoint polling remains once per 60 seconds.

## Acceptance
- 7 new Node tests: correct live counts, stale source, mismatched buckets, newly frozen predictions, waiting queue, invalid ledger, and invalid source reason — PASS.
- 73 commercial Node/API/UI tests PASS including all previous 66.
- Vite React production build PASS.
- Real Brain payload mapped correctly: 2,524 frozen, 1,467 WIN, 623 LOSS, 2,090 settled, 434 PENDING, including 394 official-game waits, 37 participation holds, 3 original pregame timing holds.
- No model promotion, settlement changes, published-wager claims, or other sports affected.

## Deployment safeguards
- Production commercial_web/src/App.jsx has intentional unrelated uncommitted work; leave untouched and preserve its behavior.
- Commit only PerformancePanel.jsx, mlbPendingProgress.js, its Node tests, and this acceptance report.
- Before serving changes, back up entire previously published commercial dist, and preserve original source/status.
- Build live site with the existing live App.jsx and new PerformancePanel module; avoid copying an isolated bundle that would revert earlier user UI work.
- Verify Brain Record static bundle, commercial API, Survivor and GitHub CI-only.
