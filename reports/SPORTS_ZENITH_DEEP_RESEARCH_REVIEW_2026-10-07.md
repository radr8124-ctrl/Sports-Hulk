# Sports Zenith / Game Scout — Deep Research Re-Audit

Date: 2026-10-07
Audit baseline: 8eab734 / c2b9dff
Project root: /home/ubuntu/sports-hulk

## Executive verdict

Sports Zenith is architecturally strong, unusually disciplined, and not yet proven to have a broad independent predictive edge over the betting market.

That is not a failure. The most important thing the current system is doing correctly is refusing to turn historical noise, high hit-rate cohorts, or market-reference probability into fake HULK edge.

Core recommendation: do not make Sports Zenith less selective. Make the proof cleaner, the regimes cleaner, the price layer better, and the challengers more targeted.

The strongest parts today are governed PASS/WAITING behavior, exact-game isolation, market/reference benchmarking, block-aware validation, immutable forward ledgers, CLV tracking, claim/source grounding, private-context boundaries, Survivor multi-entry logic, a unified cross-sports assistant, and permanent Brain Record accountability.

The weakest part is not the UI or chatbot plumbing. It is that the learned betting/prop layers still mostly fail to beat a strong de-vigged market baseline out of sample.

Next development cycle: cleaner regimes and attribution; better price/execution measurement; market-residual challengers; entry-level PrizePicks economics; contest-level DFS simulation; decision-delta fantasy improvements.

## 1. Current evidence

### Betting V2

Current mode is SHADOW_ONLY: 129 candidates, 0 shadow plays, 129 passes.

CFB has the most meaningful game-market historical samples (moneyline 80, spread 107, total 108) but no independent HULK edge. The de-vigged/reference market remains the stronger probability model in current validation, so the current MARKET_REFERENCE/PASS fallback is correct.

### Props V2

Current: 640 candidates, 0 shadow plays, 0 shadow monitors, 640 passes.

Broad learned prop models generally underperform the market baseline. Old HULK-score ordering is negative in several major lanes and is correctly vetoed.

### Prop subtype evidence

NHL sportsbook assists: 136 rows; market reference Brier 0.22684 vs core 0.24967; paired advantage -0.02284; reject.
NHL sportsbook points: 124 rows; market reference 0.23604 vs core 0.25196; paired advantage -0.01592; reject.
NHL sportsbook shots: 127 rows; reference 0.25371 vs core 0.25207; mean advantage +0.00164 but LCB95 -0.01624; PROMISING_BUT_UNCERTAIN.
NHL PrizePicks points: 67 rows; reference 0.24889 vs core 0.24642; mean advantage +0.00247 but LCB95 -0.03372; PROMISING_BUT_UNCERTAIN.
NHL PrizePicks shots: core worse than market; do not promote.

### DFS

Replay proof is tiny: DraftKings has 2 slates per mode; FanDuel 1 slate per mode. DK random-baseline percentiles are 69.2 (Best Overall), 70.2 (Cash Safe), 74.4 (Tournament Upside), but DK Top-10%-vs-random is 0% in that tiny sample and no strategy is promotion eligible.

Current DFS is a strategy-aware lineup optimizer, not a contest EV simulator.

### CLV / execution

Current CLV tracker: 38 tracked, 21 closed, positive CLV rate 47.6%, average fair CLV -0.3611 probability points, average entry-price closing-EV -4.3162%. Samples are small but the process signal needs attention.

By sport fair CLV: MLB +0.21 pp; NHL +1.28 pp; NBA -3.58 pp; NFL -1.71 pp; CFB -1.04 pp.

## 2. Priority 0 fixes

### P0.1 — Preserve season / competition regime through Betting V2

NBA upstream history contains season_type and the NBA decision layer explicitly keeps season types separate. The all-markets Betting V2 builder and forward tracker do not carry or split on season_type.

The current NBA betting sample is preseason. Mixing preseason/exhibition and regular-season proof can contaminate calibration, ROI and CLV promotion evidence.

Required: propagate a normalized regime through source decision row, training row, validation lane, current pick, forward key, price timeline, CLV and Brain Record. At minimum PRESEASON, REGULAR, POSTSEASON. Preserve CFB/CBB phase where available.

Migration: do not rewrite immutable history. Version the model/ledger and start a regime-aware forward cohort. Existing mixed NBA results stay research-only and do not qualify regular-season promotion.

### P0.2 — Split selection performance, model skill, and execution

Brain Record must explicitly separate:
1. selection cohort W-L / ROI;
2. HULK incremental probability skill vs de-vigged market;
3. execution/price quality via CLV.

A winning market-reference cohort is not proof of HULK model edge.

Recommended lane labels: MARKET-REFERENCE COHORT, HULK CHALLENGER, HULK EDGE PROVEN, UNPROVEN.

### P0.3 — Upgrade price / CLV proof before promotion

At signal time capture: best executable price, median/consensus price, worst reasonable price, book for best price, book count, time-to-start, line dispersion, price dispersion, and recent price movement.

At close capture: best close, consensus close, no-vig close and quote timestamp.

Probability proof, selection proof, ROI proof and CLV proof remain independent gates.

## 3. Priority 1 model improvements

### P1.1 — Model the residual around the market

The market is currently the best predictor in most developed lanes. HULK should predict when/how the de-vigged market is wrong instead of reconstructing outcome probability from scratch.

Use market logit as a base/offset and learn a residual from line movement, book dispersion, availability, lineup certainty, rest/travel, opponent pressure/style, role/snap/minutes changes, weather/venue where relevant, subtype and time-to-game.

Evaluate market reference vs market+residual challenger using paired Brier/log-loss and the existing forward block gates.

### P1.2 — Regime-aware hierarchical shrinkage / calibration

Test partial pooling across sport/market/subtype/regime instead of unstable small-sample lane calibrators. Candidate methods: conservative logistic scaling, beta calibration, hierarchical/Bayesian shrinkage; use isotonic only with genuinely large data.

Do not select on hit rate alone.

### P1.3 — Line movement and market disagreement features

Derive opening-to-current movement, 6h/3h/1h movement, book-direction agreement, consensus dispersion, best-vs-median gap, stale-book flag and time-to-start.

Treat these as challenger features, not assumed sharp-money labels.

### P1.4 — Join existing internal intelligence before buying feeds

Use already-built availability lifecycle, schedule/fatigue, defensive pressure, decision readiness, roster continuity, team style and market context. Enforce strict pre-prediction timestamps to prevent leakage.

### P1.5 — Focus prop research on subtypes

Best current sportsbook prop challenger: NHL PLAYER_TOTAL_SHOTS. It has a small positive mean Brier signal but uncertainty crosses zero. Freeze forward; do not promote.

Second research candidate: NHL PrizePicks PLAYER_TOTAL_POINTS, but only after entry-level payout economics is implemented.

Do not spend the next cycle rescuing NHL assists, broad NHL props, broad MLB props, or old HULK-score ordering unless new feature families materially change out-of-sample results.

## 4. PrizePicks / pick'em

### P1.6 — Build an entry-economics engine

PrizePicks is an entry-level payout problem, not just a leg-ranking problem. Actual payout can vary by lineup and is disclosed before submission. DNPs, ties and reboots can change/revert the structure.

Inputs: actual offered payout, lineup type, leg probabilities, projection type, same-game/same-player relationships, team constraints, DNP/reboot/tie rules, correlation estimate/confidence.

Outputs: joint probability, payout distribution, expected return, conservative return, correlation state, uncertainty, and PASS when payout is unverified.

Use actual displayed payout, not a hard-coded standard payout table.

## 5. DFS

### P1.7 — Add contest simulation before more GPP weight tuning

Current optimizer uses projection, value, context/role, ownership, stack bonuses and overlap constraints. Leading serious DFS products simulate opponent fields and payout ladders and rank by contest ROI.

Build a replay/paper contest simulator with lineup outcome distributions, opponent field, contest size, entry fee, payout ladder, duplication estimate and stack/correlation state.

Outputs: cash probability, Top 10%, Top 1%, first-place probability, expected duplicates and expected ROI.

Mode objectives: Cash Safe -> cash probability/floor; Tournament -> expected ROI/Top1%; Contrarian -> expected ROI with exposure/ownership constraints; Best Overall -> balanced ranking when contest context is absent.

### P1.8 — Add duplication penalty

For tournament modes estimate duplication from ownership product, salary left, common stack patterns, chalk combinations, then actual replay fields when available.

### P1.9 — Late swap only after contest simulation

Sequence: contest simulation -> duplication/field modeling -> late swap -> alerts.

## 6. Survivor

Current Survivor is already strong. Highest-value next signal is verified pick popularity / field leverage.

Add only when verified or explicitly modeled: win probability, future value, pick popularity, elimination leverage, pool size and number of user's alive entries.

Do not fabricate popularity.

## 7. Fantasy

FantasyPros-level features such as league sync, Start/Sit, waiver advice, roster comparison, strength of schedule and news are table stakes and largely already present.

Differentiation should be replacement-value decision deltas, not more rankings.

Start/Sit: selected player vs best alternative, expected points delta, floor delta, availability delta.
Waivers: add/drop pair, weekly gain, rest-of-season gain, positional scarcity, roster-fit delta.
FAAB: value gain, budget remaining, urgency, scarcity and opportunity cost.

Keep weekly, rest-of-season and roster-construction grades separate and coherent.

## 8. Game Scout / UX

Game Scout is a real differentiator because it combines exact context, no borrowed markets/props, evidence, session continuity, personalization and traceability.

Do not add more answer sections. Preferred hierarchy: Decision -> Why -> Risk -> What changes it -> Evidence.

For bets add a price ceiling (e.g. playable -115 or better; PASS at -125). For props show exact line threshold. For DFS show contest assumption. For Survivor show current-week vs future-value tradeoff.

## 9. Brain Record

Per lane, foreground: forward decisions, independent blocks, W-L, ROI + confidence bound, Brier delta vs market, log-loss delta vs market, ECE, CLV + confidence bound, probability source, regime and model version.

Promotion dashboard should show four independent gates: probability, selection, economics, execution/CLV. Never hide a failed gate behind a composite score.

## 10. Data gaps ranked by ROI

Tier A — high ROI / mostly existing data:
- season/competition regime;
- price timeline movement/dispersion/best price;
- injury uncertainty / lineup confirmation;
- rest/travel/fatigue;
- opponent defensive pressure/style.

Tier B — high ROI but needs stronger external/current data:
- verified DFS ownership;
- DFS contest files/payout ladders;
- actual PrizePicks entry payout;
- verified Survivor pick popularity.

Tier C — test before paying:
- officiating/referee tendencies;
- niche weather derivatives;
- social sentiment;
- vendor 'sharp money' labels;
- generic AI projections.

## 11. Competitive product verdict

Action Network / odds tools: line movement, real-time odds, target-line alerts and bet analytics are table stakes. Sports Zenith needs a user-facing price-threshold/alert layer, while its proof + cross-domain intelligence is differentiated.

SaberSim / DFS Hero: serious GPP tooling uses field simulation, payout simulation, ROI ranking, ownership, duplication and late swap. Sports Zenith's largest DFS gap is contest simulation/duplication-aware EV.

FantasyPros: league sync, Start/Sit, waiver and roster-specific tools are table stakes. Sports Zenith should differentiate with transparent evidence, coherent grades, decision deltas and cross-domain Game Scout.

Survivor products: used-team tracking, multiple entries, elimination/mulligans and standings are table stakes. Sports Zenith's next differentiator is verified popularity/leverage plus future-value portfolio strategy.

## 12. What NOT to build next

Do not build more generic pick cards; more main tabs; a framework rewrite; generic multi-agent orchestration; a large vector DB for structured sports truth; deep neural networks before regime/calibration/data issues; automatic bet placement; automatic waiver transactions; unverified DFS ownership; unverified Survivor popularity; more parlays before component legs prove edge; hard-coded PrizePicks entry EV; stale semantic caching of live sports answers; or a blog-generation factory before model quality work.

## 13. Recommended experiments

### Experiment 1 — Regime-aware Betting V2
Hypothesis: separating preseason/regular/postseason removes volatility contamination.
Change: carry regime into all records/keys and version a new forward ledger.
Cohort: NBA first.
Metrics: Brier vs market, log loss, ECE, CLV, ROI.
Review after 30 independent regular-season blocks; promotion uses existing probability/ROI/CLV gates.

### Experiment 2 — Market-residual challenger
Hypothesis: governed context predicts market error better than raw outcomes.
Change: market logit offset + feature groups added one at a time.
Cohort: CFB ML/SPREAD/TOTAL first.
Success: paired Brier/log-loss LCB95 > 0, no worse CLV, existing block gate.

### Experiment 3 — NHL shots subtype
Cohort: NHL sportsbook PLAYER_TOTAL_SHOTS.
Forward gate: >=50 settled, >=30 independent blocks, Brier LCB95 >0, log-loss LCB95 >0, priced ROI LCB90 >0, non-negative CLV.

### Experiment 4 — Price timing / best price
Record first signal, 6h, 3h, 1h, 30m, last prestart best/median prices.
Segment by sport/market/regime/probability band.
Success: repeatable capture window with positive CLV lower bound.

### Experiment 5 — PrizePicks entry economics
Freeze actual offered payout and entry EV; settle entry-level ROI.
Review after >=50 entries and >=30 independent event blocks.

### Experiment 6 — DFS contest simulation
Replay current Tournament Upside vs Sim-ROI challenger.
Initial directional review: 20 independent slates.
Promotion review: >=50 slates.
Metrics: contest ROI, cash rate, Top1%, first-place probability, duplication and drawdown.

### Experiment 7 — Fantasy replacement-value delta
Add start/sit and waiver replacement deltas.
Measure helpfulness, reversal rate after news and settled lineup point delta.

## 14. Revised roadmap

Build 1: Priority-0 Betting V2 regime isolation.
Build 2: Brain Record attribution split.
Build 3: Best-price + CLV timing features.
Build 4: CFB market-residual challenger.
Build 5: NHL shots subtype forward challenger.
Build 6: PrizePicks entry economics.
Build 7: DFS contest simulation replay.
Build 8: Fantasy replacement-value deltas.
Build 9: Survivor verified popularity/leverage.

## 15. Final recommendation

Sports Zenith should not chase a higher displayed betting percentage by relaxing gates.

The next breakthrough should come from better experiment design, not more confidence.

If one item is started next: Betting V2 competition-regime isolation, followed by a clean rebaseline.

If one modeling experiment follows: market-residual modeling with line movement + governed context, evaluated by paired Brier/log-loss and forward CLV.

If one major product-model feature follows: contest/entry economics — PrizePicks payout EV and DFS contest simulation.

## External research reviewed

1. Machine learning for sports betting: Should model selection be based on accuracy or calibration? Machine Learning with Applications, 2024. https://www.sciencedirect.com/science/article/pii/S266682702400015X
2. Comparing two methods for testing the efficiency of sports betting markets. Sports Economics Review, 2024. https://www.sciencedirect.com/science/article/pii/S2773161824000193
3. Classifier calibration: a survey on how to assess and improve predicted class probabilities. Machine Learning. https://link.springer.com/article/10.1007/s10994-023-06336-7
4. PrizePicks Payouts. Updated September 9, 2026. https://www.prizepicks.com/help-center/payouts
5. PrizePicks Player Picks. Updated September 9, 2026. https://www.prizepicks.com/help-center/player-picks
6. PrizePicks DNPs, Reboots, and Ties. Updated August 11, 2026. https://www.prizepicks.com/help-center/dnps-reboots-and-ties
7. SaberSim NFL/DraftKings optimizer and contest simulations. https://www.sabersim.com/nfl/optimizer
8. DFS Hero contest simulator methodology. https://dfshero.com/help/simulate/how-the-simulator-works
9. FantasyPros My Playbook / Start-Sit / Waiver Assistant. https://www.fantasypros.com/nfl/myplaybook/intro.php
10. Action Network app / line alerts. https://www.actionnetwork.com/app
11. TeamRankings Survivor strategy ecosystem. https://www2.teamrankings.com/
12. RunYourPool NFL Survivor. https://dev.runyourpool.com/nfl-survivor-pools.cfm

Community discussions were sampled for UX sentiment only and were not treated as authoritative evidence.