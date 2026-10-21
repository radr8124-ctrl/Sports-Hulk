# Sports Zenith Hybrid Sports Destination — Design Specification

Date: 2026-10-21
Status: Owner-approved direction; implementation pending plan review
Branch: design/zenith-hybrid-destination-20261021
Scope: Existing `commercial_web` React 18/Vite 6/Tailwind app. This is **not** a new platform.

## Goal and audience
Transform the existing compressed dashboard into a premium consumer sports destination: quick scores and news for everyday fans, transparent evidence-backed picks and markets for researchers, actionable fantasy and Survivor tools for repeat visitors. Commercial goal is trust, habit, conversion, and retention—not unsubstantiated earnings claims.

## Research and owner requirements preserved
- Scores visible immediately, compact ESPN-style horizontal ticker; game details only after a click.
- Sports-media layout with hierarchy and whitespace, not stacked admin blocks. Clean, bright default, premium navy/teal and electric yellow/orange accents. Light/Dark/System.
- Compact sports editorial; immediate games; accessible Top Picks, Props, Parlays, Survivor, Fantasy, DFS.
- The owner repeatedly rejected oversized cards, an oversized news block, and desktop/mobile compression. Design must be demonstrably different from current homepage.
- Integrate existing fantasy Start/Sit and a clear side-by-side comparison with reasoning, modeled as interaction inspiration from RotoBot screenshots; do not duplicate proprietary layouts or use fake player projections.
- Marketplace comparison, PrizePicks/Underdog, Kalshi/Polymarket, sportsbooks, and special research sections are conditional on actual validated data and permissions.
- Explicit APPROVED, RESEARCH, HOLD, STALE statuses, with source and timestamp. Never fabricate lines, bets, model edges, wins or availability.
- Responsive mobile-first, fast loading, accessible focus and contrast. Never expose paid/private data in public pages.
- Preserve the previous user-approved MagicPath hybrid homepage *as reference*, not as a dependent runtime. MagicPath API quota is exhausted.
- Prior competitive/customer research across sportsbooks, ESPN/CBS sports, fantasy platforms, Reddit and customer feedback remains design input; no restart.

## Architecture
- Keep `commercial_web/src/App.jsx`, existing `AuthShell`, API/data adapters, authentication and sports engines.
- New consumer shell split into focused React components: `SiteHeader`, `CompactScoreTicker`, `GameDayHero`, `EditorialGrid`, `PicksDesk`, `FeatureRail`, `SiteFooter`.
- Home is an editorial composition, while detailed tools preserve their existing component routes or tab flows. Reuse `ScoreGameCenter`, `ParlaysV2Panel`, `PersonalStartSitPanel`, Survivor/DFS and props modules. Avoid duplicate data fetchers or cron/background services.
- Frontend components receive typed/validated view-model props mapped from existing API surfaces. Loading, empty, stale and error states are visible and consistent.
- Optional Puck editing is deferred until after the main layout works; optional 21st.dev/Onlook AI tooling is **design assistance**, never required at runtime. Onlook compatibility with Vite is unverified. Avoid adding multiple overlapping editors.
- Protect live site via separate Git branch and preview build; no production mutation before screenshot review.

## Initial homepage hierarchy
1. Narrow utility/status bar and familiar top navigation for desktop; purposeful mobile menu.
2. **Compact one-line/short two-row horizontal score ticker** (approximately 44–58px total height on common breakpoints), horizontally scrollable; tap opens full game details. For no confirmed games, informative blank state—no fictional matchups.
3. Hero/editorial lead: visual sports photography, short brand proposition, featured live/scheduled game or verified editorial story.
4. Dense-but-readable game-day feed and compact news cards; no giant placeholder news container.
5. Top Picks desk: a few real approved picks or an honest no-approved-picks state, with reason, league/book, line timestamp and evidence link. Never silently promote research.
6. Compact discovery links: Props, Parlays, Survivor, Fantasy, DFS, markets. Do not duplicate huge tiles.
7. Original reporting/research and restrained membership CTA; clear premium benefits, transparent record.
8. Footer with terms and responsible gambling statements where applicable.

## Fantasy comparison
Reuse `PersonalStartSitPanel` and actual player data. Show two columns Start / Sit, projected scores and matchup notes when verified. State league scoring and data freshness. If inputs or projections are unavailable, request the necessary team/league/player inputs instead of inventing a recommendation. Add explanatory section below comparison.

## Commercial and integrity safeguards
- Separate publicly useful free scores/news from demonstrable premium analytical value.
- Do not promise profitable bets. Track signup-to-active, weekly return rate, premium CTA conversion, mobile engagement, page speed, and data accuracy before evaluating pricing.
- Real picks display provenance, market timestamps, approval criteria, settlement results, and uncertainty; no “certified” claim without evidence.
- Protect deployment and external APIs; retain access controls, data policy, rate limiting and feature flags.

## Acceptance tests
- Desktop 1440px, tablet 768px, and mobile 390px screenshots: ticker compact; header navigable; cards not overflowing; news modest footprint.
- Existing page paths/features continue to load: Scores, Picks, Odds, NFL Props, Parlays, Survivor, Fantasy Start/Sit, DFS and research. Where data is unavailable, honest states.
- Theme control works Light/Dark/System; keyboard navigation, contrast and focus states pass basic accessibility audit.
- No content labeled approved unless a real current approved record exists; stale items never shown as today’s picks.
- Build completes on the existing Vite pipeline; no new background jobs; assess bundle growth and performance.
- Owner visually accepts preview before merging or deploying. Record screenshot evidence, build logs, source revision, and rollback ref.

## Delivery phases
A. Inventory actual existing production/branch code, data interfaces, route components and deployment/rollback behavior; take safe baseline.
B. Create frontend shell and compact score ticker + desktop/mobile preview.
C. Add editorial and premium discovery, then detailed fantasy/Survivor integration without rewriting engines.
D. Test, fix regression, owner review, and controlled production release.

## Explicit non-goals
Replacing backend sports engines, building separate websites, inserting made-up data, deploying without screenshot review, hosting AI design-editor servers on shared RAM-constrained VPS, purchasing AI subscriptions without owner authorization.
