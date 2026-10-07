# Sports Zenith Ask / Game Scout Acceptance — 2026-10-07

## Result
PASS — core API-level Ask/Game Scout acceptance suite is green.

## Broad live API suite
- 22 / 22 tests passed.
- Covered:
  - Ask evaluation metrics
  - player historical evidence and no-invention career-stat fallback
  - response-state contract
  - schedule/fatigue routing
  - citation click tracking and unsafe URL rejection
  - governed team stats/current-vs-prior labeling
  - exact-match Game Scout routing
  - reporting source conflicts
  - reporting freshness
  - grounded insufficient-evidence fallback
  - multi-word retrieval precision

## Adversarial retrieval
- Prompt-injection fixture: PASS.
- Instruction-like article text is quarantined.
- Exact quarantined subjects do not fall through to unrelated keyword matches.

## Live service
- Commercial service: active on port 8510.
- Health endpoint: HTTP 200.
- Production Vite build: PASS.
- Node syntax check: PASS.

## Current evaluation snapshot
- Tracked Ask responses: 79
- Grounded/current: 57 (72.2%)
- Withheld/flagged: 22 (27.8%)
- Insufficient evidence: 20
- Stale source: 1
- Source conflict: 1
- Unknown: 0
- Errors: 0
- Reporting answers: 11
- Reporting with clickable citation: 6 (54.5%)
- Source clicks: 1
- Average API latency: 112 ms

## Interpretation
The evaluation ledger currently includes regression and adversarial test traffic. The insufficient-evidence count therefore intentionally includes fake-player, missing-context, and safety tests. These percentages should not be treated as real-user answer quality until a separate production-only cohort is accumulated.

## Known test-environment limitation
The VPS does not currently have Playwright Chromium installed, so browser-based UI specs are not included in this acceptance count. API-only Playwright request tests are green. Production assets build successfully and the live HTTP service is healthy.

## Acceptance conclusion
The core Ask/Game Scout architecture, routing, RAG safeguards, schedule/team/player context, feedback/citation telemetry, and response-state contract are ready for the planned external Deep Research review.
