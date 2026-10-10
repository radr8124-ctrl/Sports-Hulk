# Sports Zenith — PropsBot ChatGPT Betting-Bot reference + finished Ref integration
**Inspected:** 2026-10-09 evening Eastern (website data checked remotely Oct 10 UTC).
**Third-party reference:** https://propsbot.ai/chatgpt-sports-betting-bot/
**Supplemental:** https://propsbot.ai/sports-betting-bot/

## What the public PropsBot page actually says
Its public July 9, 2026 article stresses four decision gates: (1) freshness of lines/injuries, (2) projection vs implied probability and actual sportsbook price, (3) sport-specific market settlement quirks, and (4) results proven against pregame records. A bot should explain an exact wager, the number/price it needs to be usable, why the current line passes or fails, and enable later audit. It warns against generic chat answers and recommends PASS when quotes moved, a lineup changes, or the market is thin. It advertises player-prop tools, odds-shopping, DFS context and track-record links, but public copy is **not** evidence of actual model accuracy or a demonstration of an authenticated, integrated live chatbot.

## Sources as complementary inspiration
- PolyPredictr: concise immediate decision presentation, separate market probability/AI research/risk, expandable detail. Its single confidence meter was not independently validated.
- Stat Sniper: branded sports AI conversational identity with short answers, contextual follow-ups; user wants an original **referee-like** Zenith bot, not a clone.
- OddsJam: exact outcome/sportsbook/line and source clock, price-shopping, proper +EV math, real CLV/settlement. Its paid API and premium data were not purchased.
- PropsBot: four **data freshness, market math, sport context, proof** gates, price-to-play vs a nice-sounding prediction. These form the Ref's explanation and abstention principles, not a false success claim.

## Concrete Zenith work completed here
- Original custom navy/cyan referee-inspired SVG character in `commercial_web/src/ZenithRefAvatar.jsx`. No external image licensing, logos or fonts.
- New responsive `AskSportsHulkPage` hero, small page-specific prompts, dedicated transcript and scroll behavior. Fixed the old route-load `scrollIntoView` that scrolled an iPhone directly to the bottom before the user asked anything. Preserved original auth and Ask backend API, feedback and citation links.
- New `RefSignalDesk.jsx` (read-only research) and `ref_market_review.js` show official-ID-bound NFL matchups with real quoted moneyline selections, bookmaker, typical peer quote, time/age, no-vig market fair percentage and **separate** frozen market-assisted experimental Zenith projection where source IDs/team abbreviations/kickoff match. Action `Ask the Ref about this game` supplies exact validated official ESPN context, not a fabricated bet.
- New `ref_odds_answer.js` adds server-backed research replies using the *same* `betting_odds_board.json` and `nfl_frozen_game_intelligence.json` as the visible Bets page. It reports ML, exact opposing same-line spreads, totals, original bookmaker prices, break-even probability, signed **hypothetical** illustrative EV and source update age, with **PASS / 0 units** when an independent validated advantage is unavailable. No sources/quotes were invented. Generic query `What is the best NFL bet right now and why?` now lists qualified upcoming game research instead of erroneously asserting no NFL records, and supports real follow-up questions.
- New contextual mobile/desktop Ref drawer with source-aware quick prompts and followups; mobile launcher is placed above fixed bottom nav. Existing personal Survivor data still comes from the original authenticated API; it is not exposed to anonymous client market cards.
- Server-side read-only data bridge registers two already-public JSON files in existing `loadAll()`. The pre-existing, **uncommitted** Survivor-related edits in `commercial_web/server.js` were expressly preserved and excluded from the isolated staged Ref backend change. No original betting models, market source CSVs, frozen outputs or private Survivor entries edited.

## Honest market/proof labels
Every market quote is dated and may already be stale or unavailable. Model projections use bookmaker markets as an input and their independent predictive gain is unproven. The market favorite and best shopping price are **not** treated as a positive-EV PLAY. Sports with no qualified quotes are not synthesized. The conversational brand makes the software easier to use but is not a profitable bot claim.

## Acceptance and recovery
- Original before-state `AskSportsHulk.jsx`, `App.jsx` and `styles.css` backed up with SHA256 checks in `.deploy_backups/zenith_ref_chat_before_20261010T0145Z`.
- Baseline server HEAD, previous uncommitted working tree and **Ref-only patch** separately archived. Git staging for server intentionally includes only seven new odds bridge lines.
- Live `sports-hulk-commercial.service` restarted via authorized user service with existing Survivor logic preserved; local and public health return HTTP 200. Real server `POST /api/ask` returned the same recorded NFL prices on generic and Raiders–Patriots questions. Fantasy question still works.
- React build and independent sources/validation unit tests passed. Mobile and desktop Chromium checks: Ask opens at scrollY=0, width 390px without overflow; mascot, 13 source-linked game previews, market/model separation. Five new Ref-specific mobile tests passed: generic API, exact Raiders–Patriots ML/spread/total, follow-up retains exact fixture, floating contextual drawer, Survivor and fantasy prompts.
- Additional full-regression test counts and scoped version checkpoint recorded when final validation completes.
- Backups are on the VPS only. **Independent off-site raw-state restore is not verified.**
