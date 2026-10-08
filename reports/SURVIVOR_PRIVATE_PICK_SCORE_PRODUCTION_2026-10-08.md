# Survivor private score cards — production acceptance

UTC date: 2026-10-08
Source commit: bac5ffc
Rollback: .deploy_backups/survivor_private_scores_20261008T021744Z

## Delivered
- A compact My Pick Score section on the main Survivor tab displays the latest saved week picks of the authenticated, linked Survivor entry. Each team has its own card with Week, Pick, saved pool result, and league score/clock where verified and available.
- Saved historical outcomes are taken only from the private entry's week pick records; current ESPN game leads are never silently promoted to settled pool entry results. NFL team/clock matching is confined to the current week near kickoff.
- Private backend only adds pick_scores to an already authenticated, linked-entry-specific API response. Unauthenticated /api/survivor/state continues to return HTTP 401. No anonymous entry detail was released.
- Live original Survivor data remains unmodified. Read-only fixture of ANNIE G 01 showed Week 4 Minnesota Vikings SURVIVED 15-10 against Miami and both saved Week 3 survived selections.

## Safety and verification
- 8 new Survivor score regressions and all 81 commercial Node tests PASS, and an isolated Vite build PASS with the user-modified PropsV2Panel UI included.
- The existing unrelated App.jsx patch and untracked PropsV2Panel module were preserved exactly (the combined App.jsx SHA-256 matches the independently built/tested hybrid source); no partial or blanket cleanup was used.
- Prior production 21 MB dist and full Survivor entry state backed up; source feature merged fast-forward; user app delta reapplied after a targeted, one-path git stash. Preserved staged sources and verified saved Survivor entries byte-for-byte.
- Deployed a staged full live-source frontend build with lazy SurvivorScoreCards bundle; restarted commercial Node service to load private API. HTTP 200 for root, health, public NFL scores, Survivor current and score component asset; legacy Survivor Streamlit HTTP 200; private state without bearer HTTP 401.
- The local fallback file has zero linked Survivor accounts. Remote Insforge linkage has not been user-authenticated in this test. The personal scorecard is visible only after linking an existing Survivor entry to an authenticated account; this was not tested with an actual member token.

## Remaining Survivor functionality
- Main commercial Survivor page still lacks the PDF/XLSX/CSV upload and confirmation flow available on legacy Streamlit. A read-only parse of the saved 9-page Week 4 PDF returned 364 unique entries and 1,811 weekly picks, with no input edits.
- Main commercial Survivor also does not yet allow a signed-in member to save their Week 5 pick; this should use an authenticated linked-entry endpoint and enforce the current pool week's team reuse and eliminated/settled rules.
- The saved Week 4 Vikings result must never be overwritten by future imports. The official pool week is now 5; Week 5 pick-count rules await a new pool sheet.
