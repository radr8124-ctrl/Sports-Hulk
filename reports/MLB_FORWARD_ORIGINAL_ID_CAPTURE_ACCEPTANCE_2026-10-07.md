# MLB original player identity retention — isolated acceptance

Date: 2026-10-07 UTC
Branch: feature/mlb-forward-id-capture
Status: isolated acceptance pass

## Finding and fix
- The MLB_PROP_DECISIONS and MLB_PRIZEPICKS_DECISIONS feeds already contain a numeric MLB player ID, the player's canonical full name/key, home/away clubs, current club and official start time.
- The existing Prop V2 compiler discarded these identity fields before writing PROP_V2_CURRENT, and the forward capture stored no IDs. This made retrospective MLB event/player proof unnecessarily difficult.
- Prop V2 now carries original source identity in its MLB picks only when the numeric ID, full name/key, player club/opponent pair, start and event ID are mutually consistent.
- The append-only forward capture now freezes these original ID and team fields in every NEW eligible MLB prediction at the same time as the original probability/line/model. No existing frozen key or ledger ENTRY is rewritten.
- ID label: MLB_DECISION_EXPLICIT_PLAYER_ID_TEAM. Final-box verification flag is explicitly *at capture*, false, and platform payout claim is false. The ID alone is never a WIN/LOSS.
- MLB official final-box settlement may use this exact original forward-ID source if the original archive lacks a numeric ID. Both clubs and official gamePk must match, the player name/team must match the actual participated MLB box, and any existing original archived player ID or corroborated historical ID disagreement causes a hold.
- Prior captured MLB entries without the new ID keep using the previously verified official historical crosswalk. No retroactive changes to captured fields, outcomes, model scores, odds, ROI or picks.

## Real source acceptance
- Source decision checks: 1,411/1,411 current sportsbook PROP and 112/112 PrizePicks decision rows contain internally consistent numeric IDs and club pairs.
- Isolated Prop V2 build on latest copies of actual MLB decisions and validation artifacts: 233/233 eligible sportsbook PROP candidates and 13/13 PrizePicks candidates kept exact IDs, home/away teams and first pitch. All 246 remained PASS_NO_PROVEN_MODEL_EDGE, with model version and probability gates unchanged.
- The real official-box settlement backend regression (including previous missing-ID and DNP cases) remained unchanged in the isolated test suite.
- No actual user wagers, winnings or payout claims are fabricated; historical status stays PENDING until official final evidence is available.

## Safety tests
- 17 new source/capture/forward/frozen-ID tests PASS; including actual Prop V2 build behavior, invalid IDs, mismatched teams, altered original start, forged provenance, append-only idempotence, missing source history, official box and prior-grade conflicts.
- Existing MLB official grading 26, MLB historical crosswalk 15, Game Master status 14, NHL 23, NFL 11, NBA 43, competition regimes 59, forward evidence 22, deployment 8: PASS.
- Commercial Node suite 66 PASS, Vite production build PASS, Python compile and GitHub workflow YAML PASS.
- GitHub CI push remains non-destructive/read-only and deployment workflow remains manual review only.

## Deployment
- Keep all unrelated uncommitted frontend and market collector work untouched.
- Preserve original Prop V2 output, frozen forward ledger and brain report in a dated backup.
- Integrate source-only fast-forward and re-run metadata compile with no changes to existing probabilities; then capture new future MLB predictions with source IDs.
- Verify old ledger byte-prefix, existing grades/keys, zero automatic promotions, and both app health endpoints.
