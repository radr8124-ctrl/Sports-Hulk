# Sports Zenith — Game Day Command Center Visual Phase 1
**Applied:** 2026-10-10 UTC | **Scope:** existing Sports Zenith live web UI, not new website

## User request
Continue building the verified mistake-learning platform **and explain what the sports website will look like** using previously reviewed PolyPredictr, Stat Sniper, OddsJam, Rithmm and PropsBot as conceptual references. The user prioritizes reliable predictions, exact sportsbook prices, actual results, explanations, DFS/fantasy/Survivor, and visually polished iPhone UX. Preserve the existing application, all verified source ledgers, private Survivor entries and The Ref bot.

## Visual direction adopted
**Sports Zenith: Game Day command center** — midnight navy #061729/#071525 base, electric sky blue #3AC6F4, white/high-contrast copy. An original referee-like Zenith avatar communicates sports-specific chat. Homepage:
1. Compact navy editorial hero with readable headline **“The game. The numbers. The smarter call.”** and real controls **Explore Bets / Ask The Ref**.
2. Actual source-fed **Game Day / Scores & Matchups** immediately under hero with All/NFL/NHL/College/NBA/MLB filters and swipeable official score/fixture tiles.
3. Existing Best Bets, Props, PrizePicks, Survivor, player/fantasy, news and Brain Record remains accessible. Informational status widgets are collapsed near bottom rather than dominating first mobile screen.
4. Dark consistent site header/navigation and iPhone bottom tabs. Keep white/neutral detailed analysis reading surfaces, not all-neon charts. Ref accessible via header, hero and mobile nav on Home; contextual floating Ref remains available on other pages, but hidden on Home so it cannot cover first game-card scores.
5. Keep current logo/brand **Sports Zenith**, not switch to another product name or copy a competitor's layouts/artwork.

## Quantified UX change
Headless browser actual HTTPS site at viewport 390×844 after first build:
- Old Home: **scores section heading ~1,046 pixels** from document top, beyond first iPhone viewport, with connection status strips over games.
- New Home: **scores section heading ~447 pixels**, first real game card starts **~607 pixels**. On desktop 1280×844 scores heading ~584px, first cards ~704px. Mobile hero height 288px, desktop hero 341px. Zero horizontal page overflow and zero JavaScript page errors on either test viewport. No duplicate homepage floating Ref bubble.
- Actual score tile verified on Oct10: ESPN live college football fixture Washington State Cougars at Utah State Aggies; NHL, NBA preseason, MLB playoffs and NFL fixtures also source displayed. Dates display in America/New_York; no future 0–0 final scores invented.

## Important correction to model/data-health presentation
The new pure score/fixture presentation `commercial_web/game_day_deck.js` reads only **official ESPN NFL/NHL/CFB/NBA** score/schedule JSON already deployed and **MLB StatsAPI** JSON (existing sources; no new third-party API). No sportsbook odds are inferred from scores; no predicted winner, successful +EV ticket or confident model decision is fabricated.

Explicit states:
- `DATA_SOURCE_FAILURE` means malformed/missing source, invalid/future source timestamp, failed fetch, or provider-declared error.
- `SOURCE_STALE` means the observed source collection is older than 3 hours, in which case no old in-progress score is displayed as fresh.
- `NO_SCHEDULED_GAMES` means the validated schedule was checked and nothing matches current display window.
- `GAMES_AVAILABLE` means real source-matched fixtures/finals are present.
These states are **not** interchangeable with betting-model `NO EDGE` or `NO BET`. Future game scores never show 0–0 as a verified final. Missing league data are noted even when other leagues are healthy.

The old full source-connection widget remains one tap away on Home, with a reminder that "workflow ran" or connected feed does not prove valid lines/features. This visual pass implements these distinctions for the **homepage score deck**; the next separate backend effort is to propagate common named failure/hold gates through Bets, Props, PrizePicks and each sport, based on pipeline/source contracts rather than UI guesses.

## Files changed (owned scope)
- `commercial_web/src/CommandCenterHero.jsx` added, original local referee SVG reused.
- `commercial_web/src/HomeGameDayDeck.jsx` added, source-backed 5-league first-screen cards.
- `commercial_web/game_day_deck.js` added, deterministic timestamp/status/no-leak logic.
- `commercial_web/game_day_deck.test.js` added, 10 focused tests for game identity, source stale/error/empty, sport diversity, MLB multi-source grouping, no invented future scores, and original current source JSON compatibility.
- `commercial_web/command-center-home.e2e.spec.js` added, 7 mobile + desktop UI checks including actual error/empty/stale status behavior and navigation.
- `commercial_web/src/App.jsx` home hero and score rail replaced with imported audited components. Site chrome updated to navy/sky blue, account/Ref preserved, existing private Survivor and paid-sports models untouched.
- `commercial_web/site-clean-mobile.e2e.spec.js` and `commercial_web/ask.e2e.spec.js` old regression expectations adapted to the **actual new navigation contract**: contextual floating Ref remains on Bets, not on Home (where the explicit Ask button and bottom tab exist).
- No sportsbook historical source, scientific forward model, sports collector, bankroll, private Survivor state, or server.js modified by this visual project.

## Verified acceptance and preserved model evidence
- **231/231 JavaScript tests passed**, including 10 new pure game-data source, duplicate identity, correct score and distinct failure-regime tests.
- **55/55 Playwright browser tests passed** for Home, sport filters, actual/invalid source states, Ask Ref full route, Best Bets, Props, PrizePicks, Survivor, Brain Record and responsive navigation. The final full run used the current test run clock rather than an obsolete fixed timestamp: this is essential because source collectors refresh every five minutes and a legitimate later snapshot must not be falsely classified as a future-produced source.
- **38/38 original model/frozen-ledger source safety Python tests passed**, covering immutable prediction evidence, four-sport result cohorts and rejection of unproven model corrections. No new model version, paper bet or real wager was created by this visual change.
- Real live HTTPS screenshot at 390×844 measured **Home hero 288px high, game heading 447px, first league game tile 607px; no horizontal overflow, no page script errors, no redundant Ref bubble on Home.** At desktop width 1280: hero 341px, game heading 584px, game tile 704px, no overflow.
- Public `/api/health` HTTP 200. Private Survivor state endpoint remained authenticated in original source path, with existing tests validating no private anonymous user entry leak. Site served out of original `commercial_web/dist` and no new web server was deployed.

## Original-source backup and deployment proof
Before edits, copied `App.jsx`, `styles.css`, `dashboardConfig.js` and original file SHA hashes into `.deploy_backups/zenith_command_center_before_20261010T0430Z`. React Vite build published direct to `commercial_web/dist` for `https://sportszenith.com`. No off-site raw-state restore was claimed. Preexisting uncommitted server.js edits for another workflow were **not** staged/touched.

## Next visual phases (distinct from this release)
- Bets: OddsJam-style exact side, sportsbook, price-vs-no-vig, frozen independent model and simple verdict cards; avoid "PASS wall". This already exists partially; polish and unify.
- Props/PrizePicks: compact player cards by sport, current lines and original timestamps, rolling form, verified lineups; always distinguish PrizePicks projection threshold from true American sportsbook odds.
- Fantasy + Survivor: preserve private saved roster, entries, used teams, scoring and source proof; front page simplifies status without leaking entries.
- The Ref: expands into game-scoped assistant, analysis cards with "what changed" and actionable source-linked follow-up, no unsupported prediction causality.
- Brain Record: readable per-sport Brier/ROI/CLV/calibration and the operational error diagnoses shipped previously; model promotion requires new independent forward proof.

**No claim of a higher actual betting win rate because of these visual improvements.**
