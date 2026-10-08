# Sports Zenith Research Lab and narrow Fantasy viewport — live verified 2026-10-08

Feature commit: `5302960`. Source/main-site backup: `.deploy_backups/zenith_research_mobile_20261008T055202Z`. Recovery branch: `backup/pre-zenith-research-mobile-20261008T055202Z`.

- Research was previously a placeholder. Live `/research` now shows source-backed official published betting history; separate aggregate forward research settlement records; historical calibration and threshold tests; Ask answer-quality evidence; real Fantasy forward settlement by lane; and source-availability checks explicitly **not** claiming freshness.
- Live Research page reads six production endpoints successfully. A Playwright live browser run at 1365×768, 390×844 and 320×568 verified real research values displayed (including aggregate forward research counts), real-data states rather than placeholder, no JS errors or HTTP 5xx and no document overflow.
- Same live browser run confirmed Fantasy mode tab overflow previously 26 px on 320-wide viewport is now **0** at every tested breakpoint.
- Existing uncommitted user App.jsx/PropsV2Panel.jsx code preserved; Survivor pool and frozen forward ledger untouched. All 110 Node API/UI tests and production Vite build passed with user WIP on the live site, and the prior full frontend distribution was backed up before the static-asset swap.
- Source-only route and responsive layout changes require no new cloud credentials, no external provider sign-in, and do not promote research-only conclusions into official picks.
