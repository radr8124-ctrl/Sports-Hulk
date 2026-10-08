# MLB official pending attribution — isolated acceptance

Date: 2026-10-08 UTC
Branch: feature/mlb-pending-source-truth
Status: isolated code/tests/real-ledger replay PASS, no production changes yet

## Why
- Sports HULK's generic Brain Record counts pending predictions as "overdue" 12 hours after scheduled first pitch. That age metric alone does not distinguish a game still awaiting official Final from a verified unplayed-player hold, an invalid post-first-pitch capture or a genuinely gradeable, unprocessed result.
- The official MLB Props settlement receipt already retains the precise failed verification reason for EVERY still-pending frozen prediction, but this information was not exposed in the public Brain Record.
- This caused the MLB Sports Intelligence dashboard to call 35 historical MLB research observations a generic settlement backlog when the actual official source had zero currently verifiable waiting picks.

## Improvement
- The official MLB forward catch-up receipt now stores the exact SHA-256 digest and byte length of the append-only frozen Prop V2 ledger it has just verified.
- Brain's forward accountability includes "mlb_official_pending_breakdown" in its root and MLB Props fields, with verified buckets for NO_OFFICIAL_FINAL_BOX, PLAYER_NOT_VERIFIED_PLAYED, NOT_VERIFIED_PREGAME_OR_START, other source holds, and verified gradeable queue.
- A classification is labeled SOURCE_RECONCILED ONLY when the official receipt is READY, prior grades are non-contradictory, settled totals and outstanding reason totals match the ledger, the last batch's newly appended settlements are properly counted, and both ledger SHA-256 plus file size match exactly.
- Otherwise the report explicitly flags UNVERIFIED_OFFICIAL_RECEIPT, STALE_OFFICIAL_RECEIPT, NO_EXACT_FROZEN_LEDGER_SOURCE_PROOF, INVALID_OFFICIAL_RECEIPT or OFFICIAL_SOURCE_NOT_READY with no invented bucket counts.
- Unverified player participation is NOT classified as a verified sportsbook void, nor as a WIN/LOSS. Invalid original pregame research is NOT classified as a betting loss.
- Original generic overdue counts and status remain for backward compatibility, and the new source explanation says age-based overdue is NOT proof of an eligible grade. This is evidence transparency, not model or pick promotion.
- Every other sport/forward family remains untouched. All frozen predicted probabilities and ledger outcomes remain immutable.

## Verified evidence
- Before release, the production MLB ledger contained 2,498 frozen predictions: 1,467 WIN, 623 LOSS and 408 PENDING.
- The official MLB receipt reported 368 NO_OFFICIAL_FINAL_BOX, 37 PLAYER_NOT_VERIFIED_PLAYED, 3 NOT_VERIFIED_PREGAME_OR_START and zero gradeable backlog from the official games currently Final.
- On a fully isolated current-ledger/source copy, a live official source replay made no settlement change. Its newly stored exact ledger SHA-256 matched the current frozen ledger, and Brain's audit verified all pending reasons together with 2,090 prior settled grades.
- A second replay settled zero duplicate outcomes, unchanged ledger byte prefix preserved.

## Acceptance coverage
- 15 new pending-attribution tests PASS: correct buckets, stale totals, partial source failures, corrupted source receipt, negative/boolean/noninteger counts, unexpected holds, missing receipt and no-loss/no-void assertion, and exact ledger SHA-256 and file size mismatch even when counts still agree.
- Existing automatic 100-result catch-up 7 PASS; generic cross-sport forward evidence 22 PASS; original official MLB 26, numeric-ID crosswalk 16, rolling event windows 10, frozen-source events 10, original player-ID capture 17, official MLB Master 14 PASS.
- NHL 23, NFL 11, NBA 43, regime model controls 59, release workflow safety 8 PASS.
- Commercial Node/API UI 66 PASS and Vite production build PASS. Workflow YAML and Python compile PASS.

## Live release controls
- Snapshot and hash existing frozen ledger, league-source receipts, official source archives and current Brain Record.
- Fast-forward merge scoped source/test/report changes with no overlap on uncommitted market, frontend or collector work.
- Run live forward receipt (source read-only if no new Final) and rebuild Brain with verified official source breakdown, then verify public Brain endpoint, accountability JSON, Survivor and commercial health routes.
- GitHub main CI-only push; no model rule promotion, guessed outcomes or simulated payout claims.
