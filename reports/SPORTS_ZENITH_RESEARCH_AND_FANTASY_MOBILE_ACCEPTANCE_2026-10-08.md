# Sports Zenith Research Lab and Fantasy mobile width acceptance — 2026-10-08

## Reason for repair

An actual Chromium audit of all 13 top-level commercial pages at 1365x768, 390x844 and 320x568 found 12 correctly populated pages with no JavaScript exceptions or HTTP 5xx responses, one Research placeholder (no page heading or actual research content), and a 26-pixel horizontal document overflow at 320px on Fantasy caused by the unwrappable two-button Season-Long/DFS mode chooser.

## Fix

- Replace the Research placeholder with a real, responsive, standalone Research Lab that reads the existing public `performance_snapshot.json`, `forward_results_accountability.json`, `selectivity_analysis.json`, `fantasy_v2_forward.json`, the `/api/ask/evaluation-summary`, and `/api/health`. No private user data, manual interventions, or new source collectors are required. New first-class links lead to the existing Brain Record, Best Bets and Ask.
- Show actual official published-settled-wins-losses-units independently from *aggregated* forward research counts. Clearly label threshold experiments retrospective diagnostics, small Ask claim/fixture samples as limited tests (not betting accuracy), and source existence as **not** proof of freshness. Never convert research candidates, replay, shadow predictions or pending records into official picks.
- Research handles missing snapshots as UNKNOWN / `—` with an explicit warning, not invented zeros. Fetch six compact source payloads rather than including the heavyweight 5MB Brain Record file in the additional Research route.
- Fix the small-screen Fantasy mode chooser so two tabs can share available width, without interfering with the separately scrollable lane navigation or altering any Fantasy models.

## Acceptance

- 4 new Research view-model tests pass covering strict official/research separation, no invented data, no automatic promotion when missing and no private field leakage.
- All 110 commercial Node tests pass with pre-existing uncommitted Props V2 refactor intact in the isolated hybrid Vite production build.
- Real Chromium browser at 1365x768, 390x844 and **320x568** shows the complete actual-data Research page with all six public production data sources successfully loaded via safe local API forwarding, working hash deep links, no React errors, and **no document overflow**. Fantasy no longer overflows on these viewports.
- Feature changes only `commercial_web/src/App.jsx`, new `ResearchLab.jsx`, `researchSummary.js`, and `research-summary.test.js`. Previous user App.jsx/PropsV2Panel.jsx work retained separately and test-built intact.
