# Sports Zenith — 70% goal, data integrations and proof-first rollout
Date: 2026-10-09 UTC. Research-only plan. No bet execution, simulated win-rate manipulation, historical result rescoring, sportsbook subscription purchase, or automatic model promotion.

## Live evidence before proposing any new provider
- Original forward scoreboard (2026-10-09 03:56–03:59 UTC): game-lines 174 decisions, 104–70, 59.8%, +3.55 paper units, +2.04% paper ROI, 44 independent game blocks; props and pick'em 2,741 decisions, 1,711–1,030, 62.4%, -41.42 paper units, -1.52% ROI, 70 independent game blocks. Both NOT_PROVEN.
- The prop model's sportsbook Brier baseline (0.19550) outperforms model V2 (0.19963). NBA totals 77–22 (77.8%) on only 19 independent games, paper ROI 30.17% but 90% block-level ROI lower bound -4.45%. MLB props 693–295 (70.1%) yet -9.26 units, 9 independent games. There is no evidence a universal 70% profitable rate exists.
- Current configured vendor key names: SPORTSGAMEODDS_API_KEY, SPORTWIZZARD_API_KEY, PROPLINE_API_KEY, THERUNDOWN_API_KEY, THE_ODDS_API_KEY, ODDSPAPI_API_KEY, BALLDONTLIE_API_KEY, COLLEGEFOOTBALLDATA_API_KEY. These are *configured key names*, not proof every paid quota or endpoint is active. Confirm access and license separately.
- NHL/CFB market source report: SportWizzard and Propline contributing. TheRundown college odds snapshot is intentionally reserved; The Odds API credits intentionally reserved; OddsPAPI intentionally not queried for that CFB build. Avoid billing charges just to duplicate existing lines.
- NHL time-source issue previously stopped five PrizePicks finalists. The current backend honors that protection. NBA PrizePicks likewise retains many SOURCE_TIME_REVIEW rows. Missing matchup/source verification must fail closed.
- Existing Hugging Face account has working authenticated Jobs capability. Public dataset/model discovery tools did not work in this session. It is suitable for a prospective *isolated model experiment* after licensing, privacy, budget and feature timing are reviewed; it is not an odds or starter-data feed.

## Provider shortlist (documentation verified)
1. OpticOdds v3: first prospective primary paid provider to evaluate **only if** current SportWizzard and Propline feeds cannot supply comparable as-of multi-book price histories, exact fixture/athlete identity, line movement, injury/lineup status, and market provenance. Docs: https://developer.opticodds.com/docs/odds-api-getting-started-guide. Sportsbook line alone does not independently confirm starting goalies or PrizePicks payout.
2. SportsDataIO: possible second source for lineup, injury, depth chart and sport-specific feed evidence if existing official/free sources lack verified timestamps. Docs: https://sportsdata.io/developers/available-data-feeds. Depth chart rank is NOT game starter confirmation.
3. The Odds API: first check the *existing* configured subscription and reserved usage instead of buying a replacement; historic event player-prop odds snapshots documented: https://the-odds-api.com/liveapi/guides/v4/index.html. Historical use subject to plan/credit terms.

## Implemented in this research batch
- Added a **strict offline candidate** adapter intelligence_warehouse/provider_integrations/opticodds_research_adapter.py. It requires external fixture ID independently crosswalked to original game, home/away provider team IDs, league ID, start within three minutes, strictly pregame timestamp, quote age within five minutes, exact sportsbook/market/selection/provider player/side/line, and valid price.
- All accepted adapter records remain VERIFIED_SOURCE_RESEARCH_ONLY with automatic_bet_allowed=false. It does not connect or call OpticOdds, spend API credits, replace existing quotes, promote a PLAY, or infer goalie/PrizePicks starter/payout. A real feed subscription and independent fixture crosswalk are still needed.
- Contract tests: 12 passed, including eight-minute discrepancy, false start, stale quote, wrong opponent/player/line, future timestamp and wrong moneyline selection.
- Model features to evaluate once independently captured: (a) pregame price / closing line snapshots, (b) official player availability and game-confirmed starters, (c) minutes or usage projections, (d) travel/rest, (e) sport-specific advanced statistics, (f) source freshness/ disagreement. A feature captured post-event is never eligible in an earlier snapshot.

## Pre-registered goal, not an accuracy claim
- Target >=70% **on future, eligible, frozen high-confidence *research selections***, never by editing or cherry-picking historical picks. Separately report each sport/market and **coverage** (% of events or lines selected); preserve every skipped/lost original row.
- Accept positive simulated EV only using frozen, independently verified execution price and a model calibrated independently against a no-vig sportsbook baseline. 70% winners at -300 would have negative ROI: required break-even at -300 is 75%.
- Require at least 30 independent settled game blocks for initial directional evidence; require more games and formal confidence intervals for public confidence. A game with 25 props is still ONE independent game block.
- Require paired future Brier and log-loss improvement against the book and *positive lower confidence bound* on priced ROI; PrizePicks requires actual entry-level payout terms, not book-leg proxy ROI.
- Register, freeze and evaluate a future challenger against a market-only baseline. Hugging Face jobs could run isolated non-production training after license/compute spend clearance. Never auto-promote a predictor because its in-sample accuracy looks high.
- During pilot: **no betting rule changes and no guaranteed 70% performance.**

## Prioritized next engineering batch
1. Evaluate current source coverage and odds granularity before paying OpticOdds/SportsDataIO.
2. Produce model-ready, *pregame as-of only* features from retained NBA/NHL/NFL/MLB data and independent event IDs.
3. Run blocked rolling-date, nested walk-forward market-vs-model tests, including 70% accuracy **and** priced ROI/coverage.
4. Begin future-only high-confidence shadow trial with immutable experiment ID and compare results after independent games settle. Keep all existing game/props ledgers and operator views.
5. Verify independent off-VPS backups, still outstanding.

## Retrospective 70% probability filter audit (NOT prospective proof)
Read-only reconstruction of existing frozen PROP_V2_PHASE4_SUBTYPE_VETO_2026_10_05 entry/settlement events, selecting p_v2 >= 70%, without altering the records:
- MLB_PROP: 492 settled high-probability selection rows across only **9 independent game blocks**; 86.0% won, **-2.29%** priced paper ROI under the recorded quotes.
- NHL_PROP: 506 settled high-probability selection rows across **25 independent game blocks**; 77.5% won, **-1.97%** priced paper ROI.
- NHL_PRIZEPICKS: 6 high-probability leg rows across 5 games, 33.3% won and -39.98% **book-price proxy** ROI (not an actual pick'em entry payout). The retrospective game/proposition results are heavily correlated and MUST NOT be presented as an independently validated 70% betting strategy.
These results were observed before the next test and cannot count as prospective evidence for the pre-registered future experiment. Key practical finding: 70% (or even >80%) hit rate still need not beat heavy sportsbook vig and execution prices.
The separate future-only goal was immutable-registered in reports/ZENITH_70_PERCENT_FORWARD_TARGET_PREREG_2026-10-09.json at 2026-10-09T04:35:49Z with status PREREGISTERED_UNARMED_RESEARCH_ONLY (not an activated runner). Registration is not permission to place wagers or buy paid provider data.
