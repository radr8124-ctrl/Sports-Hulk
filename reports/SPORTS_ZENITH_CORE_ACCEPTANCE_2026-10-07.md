# Sports Zenith Core Acceptance — 2026-10-07

## Decision

**CORE UPGRADE ACCEPTED FOR DEEP RESEARCH RE-AUDIT**

The Sports Zenith / Game Scout core upgrade is functionally complete against the current architecture roadmap. The remaining items are optional Phase 3 enhancements or browser-environment validation, not blockers to the Deep Research review.

## Final acceptance results

### Unit / local regression layer

- Node test files: 19
- Total tests: **64**
- Passed: **64**
- Failed: **0**

Coverage includes:
- account preferences
- personalization presentation
- FAAB presentation
- claim evidence
- claim evidence coverage
- output validation
- privacy-safe tracing
- resilient dependency fetch behavior
- trusted multi-source consensus
- Survivor personalization
- multi-entry linking and diversification
- Survivor future value
- Survivor buyback gate
- Survivor concentration risk
- Survivor pool survival dynamics

### Live API regression layer

- API tests: **21**
- Passed: **21**
- Failed: **0**

Coverage includes:
- governed player history
- response-state contract
- schedule / fatigue intelligence
- session reference memory
- safer-option continuation
- roster follow-up continuity
- governed team stats
- exact-game market isolation
- exact-game prop isolation
- Game Scout context escape for Survivor
- Survivor buyback guardrail
- Survivor future-value routing
- Survivor pool-dynamics privacy boundary

### Deterministic safety / evidence API layer

All fixture-driven API checks completed with exit code 0.

- stale vs fresh reporting: PASS
- source disagreement: PASS
- trusted multi-source consensus: PASS
- final output validation: PASS
- privacy-safe trace correlation: PASS
- claim-evidence coverage telemetry: PASS
- golden benchmark summary exposure: PASS
- prompt-injection quarantine: PASS
- exact fact-to-source alignment: PASS

### Retrieval golden benchmark

- Cases: **5/5 PASS**
- Retrieval recall: **100%**
- Retrieval precision: **100%**
- Answer relevance: **100%**
- Expected evidence records: 5
- Recovered expected records: 5
- Unrelated positive evidence returned: 0

### Semantic answer benchmark

- Cases: **5/5 PASS**
- Semantic answer pass rate: **100%**

The benchmark verifies final-answer behavior for:
- current structured fact
- multi-source agreement
- stale evidence withholding
- source-conflict withholding
- insufficient-evidence refusal

### Live product smoke

Eight major Ask lanes returned valid governed responses with trace IDs:
- Best Bets
- Props
- PrizePicks
- DFS
- Waivers
- Start/Sit
- Survivor
- Live Scores

No smoke response returned ERROR or OUTPUT_VALIDATION_FAILED.

### Game Center / live data

- /api/health: **HTTP 200**
- NBA real ESPN box score through resilient fetch: **HTTP 200 / READY**
- Ask evaluation summary: **HTTP 200 / READY**
- Ask trace summary: **HTTP 200 / READY**

Final health snapshot confirmed all required sources present:
- NFL scores
- MLB scores
- NBA scores
- NHL scores
- CFB scores
- CBB scores
- Best Bets V2
- Props V2
- Parlays V2
- Survivor V2
- Fantasy news
- Ask context
- Ask retrieval

### DFS / Fantasy

- Direct DraftKings BEST_OVERALL optimizer: **HTTP 200 / READY**
- Legal lineups returned: **2**
- Private Fantasy unsigned boundaries:
  - Start/Sit: 401 AUTH_REQUIRED
  - Waivers: 401 AUTH_REQUIRED
  - IR stash: 401 AUTH_REQUIRED
  - Defense streaming: 401 AUTH_REQUIRED
  - IDP: 401 AUTH_REQUIRED

### Production safeguards accepted

- prompt-injection quarantine
- stale-source gate
- source-conflict gate
- insufficient-evidence fallback
- exact-match Game Center routing
- claim-to-source alignment
- claim-level evidence UI
- unsupported-claim measurement
- trusted multi-source consensus
- final Ask output validation
- failed-question review queue
- append-only Ask evaluation
- thumbs-up/down feedback
- source-click tracking
- privacy-safe structured tracing
- dependency timeout
- transient GET retry
- circuit breaker
- Python bridge hard timeouts
- Python bridge output-size caps
- private-data authentication boundaries

## Browser-only validation limitation

Browser-only Playwright suites were **not claimed as passing** because the VPS does not currently have the required Chromium binary installed.

This affects visual/browser automation only. API-only Playwright request tests, Node tests, production build, live endpoints, real ESPN box-score retrieval, DFS bridge execution and health checks all passed.

Browser suites remain a separate environment-validation task if Chromium is installed later.

## Non-blocking build note

Vite reports a chunk-size warning for the main bundle above 500 kB. The production build succeeds. This is a performance/code-splitting optimization opportunity, not a functional acceptance failure.

## Deep Research handoff

Recommended next action: run the planned Deep Research audit against the completed Sports Zenith / Game Scout architecture, with particular attention to:
- decision-quality improvements
- remaining model blind spots
- betting/prop calibration opportunities
- DFS strategy quality
- production UX refinements
- optional Phase 3 features

Optional Phase 3 work should not be mixed into the acceptance baseline before that audit.
