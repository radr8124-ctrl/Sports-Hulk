# Sports Zenith Fantasy Trades and missing data responses — acceptance 2026-10-08

## Previously incomplete work

- The user-facing Fantasy navigation omitted the Trades function defined in Sports Zenith's product North Star. Users could not compare give/get players in the main Fantasy page without external tools.
- The commercial backend returned `index.html` with **HTTP 200** for a nonexistent `.json` URL or missing static JS asset. This could hide collector failures or make the browser report JSON parse errors instead of a clear missing-data state.

## Feature delivered and guardrails

- Added a visible **Trades** lane to the existing Fantasy Season-Long dashboard, reusing the same published NFL weekly research data already shown elsewhere. The tool permits up to 4 players on each side, shows rest-of-season and weekly research indices with source generation date, and uses a limited one-to-one/same-position evidence comparison.
- A directional ROS index change is displayed only for equal player counts, matched same-position groups, unique unambiguous player identities, valid numeric scores and a timestamp no older than seven days. This is **not** trade fairness, projected fantasy points, or a recommendation. Missing coverage, conflicting identities, stale data, different positions, uneven player counts, and duplicate/same-player comparisons are explicitly held as insufficient or incomparable. No transactions or private provider permissions are simulated.
- The selected user-owned saved team is used only for a roster-membership warning; there are no Fantasy DB writes or external fantasy-site credentials used by this analysis.
- Missing static `.json`, `.js`, `.css`, `.ico` and any unknown `/api/...` paths now use an actual `404` JSON response instead of falsely serving the SPA HTML. Real existing resources and extensionless SPA navigation routes retain prior behavior; static directory containment now uses a path-delimiter check.

## Test evidence

- 9 new trade research safety tests passed (valid comparisons, different positions, uneven 2-for-1 trades, ambiguity, unknown names, stale dates, duplicate players, saved-roster context, missing inputs).
- 4 new static route tests passed (SPA fallback, genuine missing `.json`/JS assets, unknown API, directory containment).
- All 123 Node tests and Vite production build pass against preserved live user App.jsx and Props V2 UI sources.
- Playwright interactive preview tests at 1365x768, 390x844, 320x568 passed using **real** public NFL research rows (Quinshon Judkins and Kyren Williams for a valid same-position test; Trey McBride for blocked cross-position comparison). No React errors, no document overflow.
- Existing frozen betting research, saved Fantasy leagues and private Survivor state remain unchanged. No authenticated trade or account mutation occurs.
