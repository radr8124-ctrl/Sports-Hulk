# Sports Zenith — Complete Home Page Theme Continuity Fix
Date: October 10, 2026, UTC

## User-reported defect
User uploaded an actual photograph of their desktop monitor showing the website's navy Game Day scores row immediately above a bright **white** "What matters now" section with white Bets/Props/PrizePicks/Parlays/Survivor cards and further white News & Insights cards. They said **"Whole home page isn’t the same."** This was a genuine unfinished redesign: the new top of Home was navy, but the old HomeDecisionPanel, HomeImpactNews, HomeSnapshots and footer were still on the old white/silver treatment.

## Scope and exact repair
A **Home-specific theme continuity pass**; not a rewrite of the application or any sport model:
- Existing hero and Game Day score deck retained exactly; no change to league feeds, sportsbook odds, source validation, or game statuses.
- App root now uses uninterrupted `#061525` navy only when Home is active. The document HTML background follows active route on iPhone Safari overscroll. Other routes preserve their previous `#F1F5FA` page color and `#f8fafc` overscroll background.
- "What matters now" cards now use dark navy gradients (`#12304C` → `#0A2037`), subtle blue borders, clear white headlines and sky-blue actions. Original real figures, prices, proof labels, card click targets and route targets remain unchanged.
- "What changed that could matter" news now uses matched dark navy gradients, readable white titles, muted blue-grey descriptions and dark injury/fantasy badges. On genuinely empty news feeds, a dark empty-state appears rather than the old generic white placeholder.
- Survivor, Fantasy+DFS and Brain Record home preview tiles are dark, preserving all existing authenticated private-pool checks and published result labels. The separate Brain Record link still opens the unchanged detailed evidence page.
- Existing four-step learning flow already dark now uses the same shade, border, type hierarchy and blue accent.
- Collapsible "Source connections and system status" panel, its four health tiles/pills, surrounding borders and footer also follow the navy treatment; exact independent source health metrics unchanged. A collector connected badge is not considered evidence of a proven betting edge.
- Scoped CSS `.zenith-home .section-heading h2` and `.zenith-home .eyebrow` sets readable white/blue on Home, with no global heading changes.
- The main layout keeps the original deeper research spacing for **non-Home** routes and only uses compact Home spacing. Bets, Fantasy, Survivor, detailed Brain Record and the Ref retain their existing reading styles and functionality.

## Verified acceptance on actual VPS
- First inspected actual Home photo matched the observed failure (navy upper row, white lower rows).
- After the build, manual headless Chromium at 390 and 1280px found root CSS background **rgb(6,21,37)**, dark news/fantasy/Survivor/Brain cards, learning section and footer **rgb(7,27,47)**, real white headings, zero page JavaScript errors, and **no horizontal overflow**.
- New targeted DOM/CSS/browser regression `commercial_web/home-theme-continuity.e2e.spec.js` includes **5 passing tests** for dark Home card backgrounds, news when either fed OR genuinely empty, all decision routes, private Survivor/Fantasy preview cards, source health accordion, footer and other routes remaining light.
- Full `node --test ./*.test.js` **231/231 PASS**; independent Python source/provenance/model safety **38/38 PASS**; responsive Playwright regression across the homepage, scores, Best Bets, Props, PrizePicks, The Ref, Fantasy, Survivor, betting tools and learning **60/60 PASS**.
- The original website `App.jsx` and `styles.css` were backed up and SHA256 readback-verified before modification in `.deploy_backups/zenith_home_full_theme_before_20261010T0453Z`.
- `commercial_web/server.js` and `commercial_web/src/SurvivorPickEditor.jsx` had unrelated pre-existing changes and were expressly not edited/staged for this change.
- Original frozen NFL game-probability ledger, four-sport shadow grades, settlement source data and actual private Survivor entries were not modified by this UI-only fix.
- Live production source served out of the existing Vite `commercial_web/dist`, HTTPS `/api/health` 200 and private unauthenticated Survivor route 401.
- This is a **presentation correction only**; no claim of increased betting accuracy, approved wagers, profitable source odds or automatic model promotion.

## Next
Keep homepage styling consistent while later improving specific Bets/Props/PrizePicks research layouts; do **not** claim those deeper pages have also been fully redesigned or secretly change scientific prediction rules. Off-server raw restore has not been verified by this change.
