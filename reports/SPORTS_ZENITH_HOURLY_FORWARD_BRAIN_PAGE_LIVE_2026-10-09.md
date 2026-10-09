# Sports Zenith — hourly forward proof is visible in Brain Record

**2026-10-09 UTC. User-facing research-only integration complete; no betting engine changes.**

## Live verified workflow

The installed existing hourly `sports-hulk-intelligence-archive.service` already runs the hash-chained source performance builder successfully every hour. The original private `intelligence_warehouse/brain_performance/FORWARD_PROOF_TREND_APPEND_ONLY.jsonl` has **4 locally verified original checksummed checkpoints**; original game/proposition source models and settled results remain unchanged.

Added a **strict whitelisted** 2.5KB aggregate static data feed at `/forward_proof_current.json`, rewritten hourly from the most recent readback-verified private SHA-256 chain. Original private source paths, player identities, bookmaker line rows, APIs and vendor event UUIDs are explicitly excluded. Source reports can fail closed without clearing old settled records.

The active Brain Record route in `commercial_web/src/App.jsx` loads `PerformancePanel.jsx` (not the legacy unused BrainPerformance.jsx). A compact `ForwardProofPanel.jsx` is now embedded immediately after the original official record, leaving the whole official record and other DFS, Survivor, fantasy, sportsbook dashboards intact. It fetches a tiny new feed independently of the historical 5MB brain bundle, validates the strict research-only contract, displays the source checkpoint with ET clock and warns if the feed is more than 95 minutes old.

Live content, as of 2026-10-09T09:39:24.590481+00:00, explicitly distinguishes:
- **Game lines:** 115–71 (61.8% hit), **+4.98% source-priced paper ROI**, original model-vs-book Brier included; no proven ROI.
- **Props:** 1763–1080 (62.0%), **-1.79% paper ROI**. Its model Brier is worse than sportsbook, no edge.
- **MLB Full16:** only one independent previously completed game; **29** genuinely frozen source move quotes across **two** upcoming games, zero official outcomes.
- **NFL:** thirteen original frozen pregame game forecasts, no profitable 70%+value qualifiers, zero official grades.
- **CFB:** historical *research recommendation* grades, explicitly not independently executed wagers.

## Deploy and tests

- Built Vite frontend into an isolated candidate directory, **without deleting or overwriting any original compiled live assets**. Copied only new content-hashed JS/CSS chunks, atomically replaced `commercial_web/dist/index.html`; all old chunks retained for rollback. Original HTML backup: `.deploy_backups/zenith_forward_proof_actual_web_PREDPLOY_20261009T094800Z/index.html`. Current live HTML SHA-256: `596940a26edce7acbbf2bc0886894fce0fb594653f8a42e3557d65b584b5265a`.
- Production localhost static index, main JS, stylesheet, Brain Record lazy-loaded chunk and sanitized data feed returned **HTTP 200**. Existing API health HTTP 200. **An interactive browser screenshot/user login test was not completed**; compilation, source routing and HTTP-level production checks passed.
- Public/backend regression: **23 Python tests**, **11 Node tests**, candidate Vite build PASS. Tests reject fake profits/70% claims, changed loss counts, future source timestamps, altered checksum history, duplicate append, source tampering, invalid original official-game blocks and inconsistent paper ROI.
- Hourly automatic public feed regeneration is part of the existing safe, nonblocking intelligence-archive systemd poststep; no duplicate timer or paid plugin service.
- Source control covers only code, tests, whitelisted presentation and this receipt. Generated private ledger/current view/public dynamic proof JSON and original paid vendor book quotes are excluded. The unrelated pre-existing dirty `App.jsx`, Survivor editor and Props panel worktree files were deliberately **NOT STAGED**.

**Constraints:** neither 61.8% game-line hit rate nor +4.98% paper ROI establishes independently executable real-money profit or statistical model edge; 62% props win rate coexists with negative price-adjusted paper ROI. The first Full16 game and 29 correlated MLB book observations are not generalizable market evidence. **Independent off-VPS restore is still unverified.**
