# Sports Zenith / Game Scout — Deep Research Re-Audit Handoff

Date: 2026-10-07
Baseline commit: c2b9dff
Project root: /home/ubuntu/sports-hulk
Commercial app: /home/ubuntu/sports-hulk/commercial_web

## Purpose

This handoff is for the planned Deep Research review after the Sports Zenith / Game Scout core upgrade.

The core architecture has already been built, regression-tested, live-smoke-tested, and accepted. The Deep Research task is now to challenge **decision quality, model blind spots, calibration, UX usefulness, and competitive differentiation**.

Do not spend the audit simply rediscovering features that already exist.

## Accepted baseline

Primary acceptance report:
- reports/SPORTS_ZENITH_CORE_ACCEPTANCE_2026-10-07.md

Ask / Game Scout architecture:
- reports/ASK_SPORTS_HULK_AGENT_ARCHITECTURE.md

Retrieval benchmark:
- reports/ASK_RETRIEVAL_GOLDEN_CURRENT.json

Semantic-answer benchmark:
- reports/ASK_SEMANTIC_ANSWER_GOLDEN_CURRENT.json

Latest acceptance baseline:
- 64/64 Node/unit/regression tests PASS
- 21/21 broad live API tests PASS
- deterministic safety/evidence suite PASS
- retrieval golden set 5/5 PASS
- semantic answer golden set 5/5 PASS
- retrieval recall 100% on deterministic golden set
- retrieval precision 100% on deterministic golden set
- answer relevance 100% on deterministic golden set
- semantic answer pass rate 100% on deterministic golden set
- live /api/health HTTP 200
- direct DraftKings optimizer READY with legal lineups
- live ESPN box score endpoint READY
- private Fantasy auth boundaries PASS

These are code/acceptance benchmarks, not claims of future gambling profitability.

## Current product structure

Main product surfaces:
- Scores
- Best Bets
- Props
- PrizePicks
- Parlays
- Fantasy
- Survivor
- News & Insights
- Brain Record
- Practice
- Research
- Ask / Game Scout

Fantasy includes:
- Start/Sit
- Waivers
- FAAB context
- IR stash
- Defense streaming
- IDP
- DFS optimizer
- account-linked roster/scoring context where available

Survivor includes:
- linked private entries
- multiple entries per account
- entry-specific used teams
- current-week rule gate
- multi-entry diversification
- same-team concentration protection
- same-game concentration protection
- future-value / save-for-later research
- buyback/re-entry evidence gate
- pool survival dynamics
- entry switching
- diversified plan on Survivor page
- multi-entry home summary

Game Center includes:
- Overview
- Box Score
- Odds
- Props
- Zenith
- News

Game Scout includes:
- exact-match game context
- current scores
- structured reporting
- fantasy routing
- Survivor routing
- betting / props
- schedule / fatigue
- team stats
- player historical evidence
- session reference memory
- preference-aware presentation
- account-linked context where authorized

## Guardrails already built

Do not recommend these as if they are missing unless Deep Research finds a concrete defect:

- PASS / WAITING / insufficient-evidence behavior
- exact-game isolation
- no cross-matchup market borrowing
- no cross-matchup prop borrowing
- insufficient-information fallback
- stale reporting gate
- source-conflict gate
- prompt-injection quarantine
- source freshness thresholds
- groundedness checks
- exact claim-to-source mapping
- clickable citations
- claim-level evidence UI
- source-click telemetry
- helpful / needs-work feedback
- failed-question queue
- unsupported-claim measurement
- trusted multi-source consensus
- deterministic retrieval benchmark
- semantic answer benchmark
- final output validation gate
- privacy-safe structured tracing
- GET timeout/retry behavior
- circuit breaker
- Python bridge hard timeouts
- bridge output-size caps
- private-data auth boundaries

## Recent key commits

- c2b9dff Record Sports Zenith core acceptance
- d321536 Add dependency failure resilience
- afc456c Add privacy-safe Ask tracing
- d5435be Add final Ask output validation gate
- cae2d8c Add semantic Ask answer benchmark
- cc1115a Add retrieval golden benchmark
- e9cc9c7 Add trusted multi-source reporting consensus
- 5eb9490 Track Ask claim evidence coverage
- 9e5e109 Show claim-level evidence in Ask
- f48bcc4 Align reporting claims with exact sources
- 825db89 Add Survivor pool survival dynamics
- 132763a Add Survivor concentration safeguards
- 215c1ed Add Survivor buyback evidence gate
- 3e9c1b1 Add Survivor future value guidance
- 0f9eeff Diversify multi-entry Survivor picks
- 18d51a3 Support multiple linked Survivor entries

## Deep Research priority questions

### 1. Betting model quality

Audit Best Bets and game-market decision logic for ways to improve **forward hit rate and calibration**, not merely produce more picks.

Investigate:
- whether current probability thresholds are too loose/tight
- whether market-type thresholds should differ by sport
- whether favorite/underdog, home/away, spread size, total band, rest, travel, injury uncertainty, line movement, market disagreement, and price quality should create distinct cohorts
- whether stronger no-play gates would improve expected value
- whether current de-vig / fair-probability treatment is adequate
- whether closing-line value should be used more strongly in model promotion decisions
- whether observed edge should be shrunk more aggressively by sample size
- whether challenger models should be segmented more deeply before promotion
- whether calibration curves / Brier score / log loss should supplement hit rate

Deliver:
- highest-value changes ranked by likely impact
- changes that improve selection quality vs changes that merely increase volume
- exact additional fields or calculations required
- which ideas can be tested with current data vs require new data

### 2. Prop / PrizePicks quality

Audit Props V2 and PrizePicks separately.

Investigate:
- stat-family-specific models
- role/usage volatility
- injury replacement effects
- pace / matchup / defensive pressure
- line quality and alt-line structure
- sportsbook vs pick'em economics
- correlation / duplicate exposure
- injury/practice uncertainty penalties
- opponent scheme and player archetype effects
- whether different sports need separate proof thresholds
- whether PrizePicks payout economics justify different probability cutoffs

Deliver:
- specific calibration improvements
- strongest missing variables
- where the system should remain PASS more often
- what would most likely increase forward win rate

### 3. DFS optimizer quality

Audit:
- Best Overall
- Cash Safe
- Tournament Upside
- Contrarian

Investigate:
- lineup correlation
- stacking
- bring-backs
- ownership leverage
- late-swap readiness
- duplication risk
- ceiling/floor modeling
- salary allocation
- injury news handling
- contest-size strategy
- portfolio diversification across multiple generated lineups
- whether current optimizer objective is too projection-heavy
- whether lineup evaluation should compare against random/baseline/median constructions

Deliver:
- specific changes that can be paper-tested
- success metrics for each DFS mode
- recommended forward-sample gates before trusting strategy changes

### 4. Survivor intelligence

Current system already has:
- used-team eligibility
- future value
- multi-entry diversification
- same-game concentration protection
- buyback evidence gate
- historical/current pool dynamics separation

Audit whether Survivor can improve further through:
- opponent future schedule path
- leverage vs public pick concentration
- survivor-specific expected value
- correlated pool elimination risk
- strategic preservation of elite teams
- different policy when user has 1 vs many entries
- pool-size-aware aggressiveness
- endgame strategy

Do not recommend fabricated ownership if pool ownership is not verified.

### 5. Fantasy decision quality

Audit whether Start/Sit, Waivers, FAAB, IR stash, Defense streaming and IDP use enough of:
- scoring format
- roster construction
- bench depth
- replacement value
- opponent context
- schedule strength
- rest/fatigue
- injury lifecycle
- expected role
- historical player evidence
- current reporting
- league-specific constraints

Focus on decision usefulness, not adding decorative data.

### 6. Game Scout answer quality

The retrieval and semantic guardrails are built.

Now evaluate:
- whether answers are concise enough
- whether recommendation / why / risk / what-changes-it is the right hierarchy
- whether confidence language is understandable
- whether Game Scout should surface fewer or more cards
- whether exact evidence is shown at the right level
- whether user follow-ups feel natural
- whether session memory creates ambiguity
- whether personalization is useful without changing model truth
- whether Ask duplicates content already visible elsewhere in the app

Deliver UX changes only if they reduce decision friction.

### 7. Brain Record / accountability

Audit whether "How Good Is The Brain?" measures the right things.

Current philosophy:
- permanent forward record
- no cherry-picking
- betting and props judged by settled outcomes
- DFS judged by lineup results
- Survivor judged by survival
- Ask judged by grounding / citations / traceability / golden benchmarks

Investigate:
- calibration metrics
- benchmark baselines
- rolling vs lifetime views
- sample-size confidence
- Wilson intervals
- Brier/log-loss
- CLV
- strategy-specific DFS comparisons
- sport-specific splits
- whether model upgrades should require statistically meaningful forward evidence

### 8. Data blind spots

Look for the biggest *decision-relevant* gaps, such as:
- verified ownership
- sharper closing lines
- more complete historical player game logs
- advanced matchup context
- weather
- officiating
- travel / altitude
- lineup confirmation
- snap/usage trends
- depth-chart changes
- contest ownership
- injuries/practice feeds
- market movement history

Rank by likely value vs integration cost.

Do not recommend paid feeds generically. Explain what exact data would improve what exact decision.

### 9. Competitive product audit

Compare Sports Zenith conceptually against leading:
- score apps
- betting analytics tools
- fantasy tools
- DFS optimizers
- Survivor tools
- sports AI/chat products

Focus on:
- what users repeatedly value
- what users complain about
- information overload
- trust/transparency
- latency
- stale information
- hidden assumptions
- personalization
- workflow fragmentation

Identify:
- true differentiators already present
- missing table-stakes features
- features that should be removed or simplified
- features that should be emphasized commercially

## Required output format from Deep Research

Return findings in this order:

1. **Executive verdict**
   - what is genuinely strong
   - what is still weak
   - what is most likely to improve real decision quality

2. **Priority 0 fixes**
   - only issues that can materially hurt correctness, safety, or decision quality

3. **Priority 1 model improvements**
   - ranked by likely impact

4. **Priority 2 product / UX improvements**

5. **Data gaps ranked by ROI**

6. **What NOT to build**
   - ideas that add complexity without likely performance benefit

7. **Recommended experiments**
   - hypothesis
   - exact implementation change
   - cohort
   - success metric
   - minimum forward sample
   - promotion / rollback rule

8. **Revised roadmap**
   - smallest useful build order
   - one checkpoint at a time

## Audit rules

- Do not assume more picks = better.
- Treat PASS as a valid decision.
- Prefer forward proof over backfit claims.
- Separate betting hit rate from profitability.
- Separate sportsbook betting from PrizePicks/pick'em economics.
- Separate DFS modes.
- Do not mix user preference memory with sports truth.
- Do not invent current data that is missing.
- Do not downgrade stale/conflicting guardrails just to answer more questions.
- Do not recommend a wholesale framework rewrite unless there is concrete evidence the current architecture cannot support the improvement.
- Do not recommend LangGraph/FastAPI/pgvector merely because they are fashionable; explain the actual bottleneck first.
- Keep Sports Zenith's structured sports truth outside generic vector memory.
- Preserve the exact-game no-borrowing guarantee.
- Preserve private-data boundaries.
- Preserve append-only performance accountability.

## Known non-blocking limitations

1. Browser-only Playwright visual tests have not been run because the VPS does not currently have the required Chromium binary.
2. Vite reports a main-bundle chunk-size warning above 500 kB. Build succeeds; this is a code-splitting/performance optimization opportunity.
3. Current deterministic golden benchmarks are intentionally small and synthetic. Recommend expansion if useful, but do not confuse benchmark size with live sports accuracy.
4. Some private personalization paths require a real authenticated saved league/account to exercise fully end-to-end.

## Desired outcome

The audit should answer:

**Given the system that exists today, what are the few highest-impact changes most likely to make Sports Zenith materially better at sports decisions—not merely bigger, busier, or more complicated?**

The output should be specific enough that each recommendation can become a focused implementation checkpoint with a measurable forward test.
