# Sports Zenith — Proof-first Superdesign & Live-Site Audit
October 9, 2026 — evidence-first game, props, Survivor, and parlays review

## Outcome

The user-provided six website photographs exposed an information-architecture failure: dozens of repetitive PASS/math cards visually dominate, the betting menus hid absent sports/markets, Survivor mystery dashes looked like percentages, and the 'brain' did not distinguish sportsbook probabilities from independent predictive improvement.

The new Best Bets design was revised in the EXISTING Sports HULK Superdesign project, not a fresh ungrounded project. The audit-led draft was fact-checked for fixture name, sportsbook timestamp, and independent-game count hallucinations, and saved as version 4:
- [Sports Zenith proof-first redesign preview](https://p.superdesign.dev/draft/7f42e794-a8f2-49bb-8c3a-7a4ca0653950)
- [Existing Superdesign project canvas](https://superdesign.dev/teams/24871933-d6a3-4740-97e9-f738a14f03a0/projects/144cb851-d868-4d2b-8d78-74ce26fe0ce8)

The preview is not itself the live site's code. Separate tested React changes were deployed for **Best Bets** with no change to sportsbook data, picks, models, rules or balances.

## Verified data and missing NFL / spreads

At source time ~18:04 UTC October 9:
- Current all-markets public feed: **44** research moneyline observations: **39 CFB**, **5 NHL**, **zero verified/shadow plays**, **zero qualified NFL, SPREAD or TOTAL**.
- Upstream October 11 NFL source file `nfl_live/decision/NFL_GAME_DECISIONS.csv`: **13 moneyline** and **13 spread** observations, all **PASS_STALE_MARKET** with **STALE_PRIMARY_MARKET** quality. Do **not** call these fresh odds or winning Best Bets.
- NFL all-markets proof lane: **16 historical independent-game blocks** for moneyline and spread, vs **25-game current threshold**; NFL total **13**. The visible sportsbook market's existence is not proof Zenith improves on it.
- The earlier market board also retains 13 NFL upstream moneylines marked stale. The new public React panel uses ONLY that market-board source to count upstream stale **moneylines**. It does NOT invent fresh spread pricing or reclassify the 13 source NFL spread rows as approved picks.
- All-market feed includes CFB spread history, but no proven independent model edge; therefore presenting zero qualified CFB spreads is correct.

**Root cause:** Best Bets sport and market tabs were dynamically assembled from `data.picks`. As soon as the proof and freshness gates excluded NFL/spreads, the page erased those categories from navigation, leaving the user unable to understand why they were absent. This was a UI limitation on top of a genuine source/proof limitation, NOT evidence that qualified NFL selections were available and suppressed by an erroneous button.

## Live Best Bets corrections

- Permanent sport categories: NFL / CFB / NBA / NHL / MLB / CBB.
- Permanent market categories: All / Moneyline / **Point spreads** / **Totals**.
- Source-grounded `What the brain knows now` status panel: current candidates vs verified plays, freshness/market-source barrier, 25-game sample threshold and current independent-game counts, Brain Record link.
- NFL filter shows only verified official upcoming football fixtures and kickoff times, with **Price pending** where market quotes are stale. This is factual game intelligence and a research navigation aid, not predictions/bets.
- Research watchlist now defaults to **six compact cards**, not a wall of twelve. Detailed stake-price explanations moved beneath expandable View evidence. Initial visible summary distinguishes research from qualified paper tests and labels older source quotes as such.
- Existing uncommitted App/Props/Survivor development changes were preserved. The Best Bets function and its new data helpers were staged as an isolated Git blob and committed at `9da6f68` without committing the unrelated WIP; the saved Superdesign target was updated to version 4.
- A separately reproduced build from `9da6f68` (HEAD-only source checkout) succeeded. The full working-tree current frontend was built and checked separately, then deployed via **atomic live HTML pointer update** with new content-hashed assets; all old chunks remain for rollback. The existing backend data feeds and Python model engines were not modified.

## Sitewide proof/UX priorities from screenshots and source data (additional Superdesign drafts not yet created)

**P0 — NFL market source, not the button.** The current backend's NFL **26 spread/moneyline observations** were all stale. Obtain/verify actual sportsbook provider captured timestamps, exact event identity/side/line, and paired book probability; re-run existing proof gates on independent frozen forward games. Do not force a PLAY to satisfy a UI target, fabricate prices, or claim a 70% winner model.

**P1 — Survivor.** Current screenshot ranks teams with `—%` market and `Strategy 0.0` despite stale prices. Make market freshness a leading honest state (e.g. *Fresh survival probability unavailable*), display current user entry and scoring on the page after sign-in, and visually separate unpriced generic rankings from actionable survivor selections. Do not silently treat a zero placeholder as a real negative signal.

**P1 — Props & PrizePicks.** The current source had **421 candidates and 421 PASS** (zero paper qualifiers). At present too many cards emphasize Under 0.5 and quoted practice-stake arithmetic. Replace repetitive PASS cards with player comparison rows emphasizing actual matchup, verified line/book age, reasons to abstain, official injury/starter status and independent-game evaluation. Keep important data in the first screen; expand price math and developer proof only on demand.

**P1 — Parlays.** The current source had **76 combinations, zero captured multi-leg parlay payout prices, zero proven source legs, and 76 PASS**. A fair independent-leg approximation is **not** a sportsbook parlay offer or measured leg correlation. Present a compact blocked-parlay explanation (missing joint payout/source proof), not dozens of apparent purchasable parlays. Disable expected-profit claims until actual quoted payout, compatible legs and correlation evidence exist.

**P2 — Brain Record.** Historical all-market source-price research had **186 settled positions whose game-model probabilities matched the book**. Show a transparent 'bookmaker baseline only' marker, independent game counts and paired Brier/log-loss comparisons instead of a raw win percentage that misrepresents actual predictive advantage. The earlier NHL adjusted model also had worse Brier than the book across a small 16-game sample. A confidence meter without an independent test does not supply proof.

**P2 — Information density and mobile.** Retain Sports Zenith's existing brand, tabs and PWA. Reduce repetitive boxes; group sports, market, source freshness, game context and expandable research proof. A user should know in 3 seconds: any approved picks? Which games? What is the independent edge? Why no bet? When will the data next refresh? The UI must not promise proof absent in the data.

## Deployment & QA verification

- Specific live 390px browser: `https://sportszenith.com/#best-bets` -> NFL -> Point spreads displays upcoming matchups, 16/25 independent NFL proof, stale primary source and **0 verified plays**; no JS errors and no page overflow.
- Switching NFL Moneyline/Point spreads/Totals retains source/freshness warning and never upgrades research to a shadow play. CFB moneyline research initially displays **six** compact cards; View evidence expands.
- All **26 staged cross-route checks** (13 screens x phone/desktop) passed prior to deploy.
- All **52 post-deployment route checks** (13 screens x 320px/390px/768px/1280px) passed, with no browser page errors or horizontal page overflow. Sign-in modal was tested without OTP or user writes. The PWA service worker caches only offline page/icons; no sportsbook odds or user data.
- **11 pure Bet market/proof tests passed**.
- Cloudflare HTTPS root and health API both HTTP 200 with valid TLS.
- Local rollback: `.deploy_backups/zenith_best_bets_research_coverage_20261009T181500Z/LIVE_INDEX_ROLLBACK_BEFORE_PROOF_UI.html`. Atomic deploy touched content-hashed static JS/CSS and the live HTML index pointer only, did not rewrite existing sources/models or delete old chunks.
- Real native iPhone/Android compiled/signed binary, authenticated user's Survivor save, new NFL fresh bookmaker prices and predictive betting edge remain **UNVERIFIED**; off-VPS independent disaster recovery remains unverified.

**Truthful current status:** Best Bets navigation and proof-first market explanation are now live and materially easier to understand. The underlying inability to produce *verified, fresh NFL spread Best Bets* remains a sports-data/model-validation task. Prioritizing its proof and freshness pipeline is next; simply displaying more PASS lists will not make a winning machine.
