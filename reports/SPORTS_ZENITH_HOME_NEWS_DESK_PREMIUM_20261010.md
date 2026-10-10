# Sports Zenith — Premium Zenith News Desk Release
Date: 2026-10-10 (America/New_York)
Status: **Production live, verified**. Existing website `https://sportszenith.com/`, same codebase and homepage.

## User request and creative rationale
The user wants the homepage to look exceptionally memorable on first visit and observed that the old "Top Sports News" section blended into the other sections. The user approved a distinct broadcast-inspired **Zenith News Desk**, with one visually featured story and three supporting stories. Preserve the premium retro sports-magazine brand (cream, ink, coral, aqua and gold), animated full-size Ref, real scores and source-backed research.

## Changes
- `commercial_web/src/HomeTopNews.jsx` now presents the existing curated source-linked headlines in an editorial **ink/navy masthead** with three-color edition stripe, warm ivory heading, gold "All sports news" button and a much stronger visual section boundary.
- One existing, still source-linked `NewsStoryCard` is presented as the lead story on warm gold paper. Three other curated stories are displayed as compact source-labelled briefs in a supporting rail; no duplicate or invented headline. On phone the briefs are horizontally swipeable; on desktop the lead spans a larger left feature with three readable stacked briefs.
- `commercial_web/src/NewsStoryCard.jsx` gains a backward-compatible optional `compact` flag and data tags for layout validation; the full News & Insights hub and all original article URLs, publication timestamps, category signs and source attribution are retained.
- Feed loading, source failure, stale source, no-qualified-article and no-recent-headline statuses still display distinctly. When there are no sourced stories, the masthead says Newsroom source status instead of pretending there are four fresh articles.
- `home-theme-continuity.e2e.spec.js` validates warm ivory News Desk text on deep ink, and accepts a preview URL via environment for pre-release QA. `sports-news-hub.e2e.spec.js` also supports that preview URL without altering the default production test route.
- `home-news-desk.e2e.spec.js` adds 4 end-to-end browser tests covering actual hierarchy, exact featured headline ordering, source URLs, sport signs, desktop placement, phone swipe, zero sideways overflow and honest empty/failure states.

## Source integrity and privacy
- Curation remains `selectHomeTopStories(..., limit=4)` from `commercial_web/news_curation.js`, no selection or sportsbook/availability logic was changed. **A news category is attributed reporting, not verification of a real player injury or a current bet.**
- Real source links remain hyperlinks opening the original articles; lead/brief status is purely layout, not an AI recommendation.
- The output never includes private Survivor entries/used-team history, fantasy rosters, account data or user identifiers to anonymous visitors. Private Survivor state still returns HTTP **401** anonymously.
- No backend routes, sports collector, analytics observer, LLM, paid service, prediction weights, official performance ledger or Survivor pick were changed.

## TDD / regression evidence (same day)
- New browser spec written first and confirmed RED: original page had no `data-news-desk-masthead`.
- After implementing the layout, new test suite GREEN: **4/4**.
- Added test for empty/failure masthead source truth, confirmed RED for hardcoded "Lead headline + 3 quick reads"; fixed with the exact current curation count and neutral source-status copy.
- Existing palette test verified a planned RED caused by moving the headline from navy-on-cream to **ivory-on-ink**, then updated to assert the new intended contrast.
- Preview (isolated local Vite at 8554): **19/19** combined `home-news-desk`, `home-theme-continuity`, `sports-news-hub` browser checks PASS.
- Entire original Node website test suite: **314/314 PASS**.
- Production frontend `npm run build`: **PASS**, with an existing nonfatal Rollup chunk-size warning.
- Post-build production (localhost 8510): **24/24 PASS** across `home-news-desk`, `home-theme-continuity`, `sports-news-hub` and `retro-wow-ref-cards` browser suites.
- Real HTTPS at **320, 390, 430, 768, 1280, and 1920px**: all six visits returned HTTP 200; each had source-linked lead + three briefs (4/4 with category signs), a dark masthead `rgb(23,62,82)`, **0 horizontal overflow, 0 JavaScript errors, and 0 anonymous private-entry leakage**.
- Observed News Desk section height: 953px at 320px, 859px at 390px, 828px at 430px, 796px at 768px, 688px at 1280px, 680px at 1920px. The larger, editorial feature increases page scroll; do **not** misrepresent it as an overall mobile-page length reduction.
- HTTPS screenshot artifacts were recorded only on the OVH VPS under `/tmp/zenith_news_desk_https_20261010/`. No screenshot is published or uploaded to a third party.

## Known remaining UI issues / next work
- On narrow mobile screens the existing fixed full-body Ref can still overlap parts of the score rail or news briefs at certain scroll positions. The user explicitly wants him animated and visible; a dedicated mobile sideline/stage should be designed in a separate approval-tested batch, rather than quietly shrinking/removing him.
- The News Desk is below the live scores and signal board; this pass intentionally updates that one section and does **not** overhaul the hero, navigation or underlying predictions.
- Physical Safari/iPhone touch playback is not yet independently tested; Chromium emulated widths and live HTTPS checks passed.
- Same-host Git plus scoped SHA-verified pre-change files prove versioned source recoverability **on the same VPS**, not a separately restored off-server backup.

## Rollback and scoped provenance
- Original `HomeTopNews.jsx` and `NewsStoryCard.jsx` were SHA-verified in `.deploy_backups/zenith_news_desk_before_20261010/`. No unrelated dirty `commercial_web/src/SurvivorPickEditor.jsx` or model data was staged or modified for this UI release.
- When reverting, restore only the named News Desk source and accompanying tests, then build and verify. Do not revert original mascot behavior or private pool source state.
