# Sports Zenith — Retro Premium WOW: The Ref + Signal Board
**Date:** October 10, 2026 (US/Eastern). Existing production: https://sportszenith.com

## Why this exists
User confirmed the 80s-inspired Sports Zenith page was heading in the right direction, but wanted a distinctive premium sports-magazine wow factor rather than generic black/blue AI futurism. They called the middle white dashboard cards visually flat and The Ref too small/parked in a corner. User approved the clean editorial color direction, asked for bigger animated Ref doing sports calls along the page, and more colorful cards without losing the original site's genuine data and functionality.

## Actual implemented design
**Mascot:** Replaced the previous 70-pixel circular Ref-only floating icon with an original illustrated full-body referee stage: reuse original sports Ref head, striped jersey, coral ink-bordered background, gold Z badge and named THE REF ribbon. The character is roughly 113px wide on phones, 150px on ordinary desktops, and 170px on very wide desktops. Scroll-responsive section labels and vertical position follow the six original Home areas (welcome, scores, signal board, newsroom, Survivor/Fantasy and learning). Interactive menu retains Flag, Strikeout, Whistle, Ask, Brain Record, move left/right and a new Shrink/Expand. A genuine user tap alone produces the optional short, quiet WebAudio whistle. Animations obey reduced-motion settings; movements are decorative and never claim an actual sports penalty or validated selection. Files `commercial_web/src/ZenithRefCompanion.jsx` and `ZenithRefCompanion.css`. Retired obsolete original circular-only Ref animations from `styles.css`.

**No reading obstruction:** On 768–1879px widths the original Home main content reserves 180px for a desktop/tablet sideline. At 1880px+ the natural margin around the original 1500px site canvas supplies this space. At phone widths the character is a 113px dock above the iPhone bottom navigation and can be manually shrunk. In real live 1280px HTTPS the Survivor card right edge was x≈1100 and the mascot left edge x≈1110 — no overlap; at 1920px, Survivor card right x≈1690 and mascot left x≈1730. Expanded tools may temporarily float over the page by intentional user click.

**Signal Board:** New `HomeSignalCard.jsx`, wired into the original `HomeDecisionPanel` with exactly five live shortcuts: coral Best Bets, aqua Props, gold PrizePicks, lavender Parlays and mint/sage Survivor. Warm paper backgrounds, bold real-source counts, category symbols, restrained halftone circle marks, stronger dark ink borders, issue-number accents, sharper headline hierarchy and clear status/action labels. The site keeps original source-derived numbers and signed-in account separation. Notably `shadow_plays` are no longer described as approved PLAY: visual label reads SHADOW RESEARCH when the source says so. All approval proof and no-bet gates remain unchanged. More plain-English wording and less jargon without altering models.

**News:** `NewsStoryCard.jsx` now uses light paper tints by source category (injury coral, recap cream-gold, fantasy aqua, lineup sage, transaction lavender, market sky). Exact original article href, team/time/league/category icon truth are preserved. No new articles, artificial results, paid source calls or category reclassification added.

**Design continuity:** App frame remains cream with dark ink horizontal nav and aqua/coral/gold accents; the Ref adds motion only where useful. `.superdesign/design-system.md` updated to preserve the specific approved design and prevent a later dark-only reversion.

## Safety and acceptance
- Original other-page research, odds, scoring collectors, Bet Lab, fantasy/DFS, Survivor account/picks, external Knockout Pool, source timestamps, official results, forward ledger, and published model predictions were not changed by this visual-only release.
- Clean Vite production build, **270/270** JavaScript unit/regression tests.
- **39/39** selected Playwright browser tests passed, including new distinct-card colors, real previous source data, original article links, strong Ref sizing, mobile bottom-nav clearance, desktop read-through/no-occlusion, per-section scroll following, minify/expand, manual football flag/strikeout actions, old whistle behavior, Home news, original navigation, Survivor privacy and mobile Bets/price test.
- Actual production **https://sportszenith.com** rendered HTTP 200 at four browser widths: **390, 768, 1280, 1920px**. Every width showed all five distinct colored cards and visible full-body Ref, with zero document horizontal overflow, zero browser runtime errors and no private ANNIE G 01 name exposed.
- `/api/health` was HTTP 200; anonymous `/api/survivor/state` returned HTTP 401. Original model/game score/Survivor files were not edited.
- SHA-verified local rollback of original components/tests: `.deploy_backups/zenith_retro_wow_ref_cards_before_20261010/SOURCE_SHA256.txt`. Same-VPS backup is **not independently restored off-server disaster recovery**.

## Limitations
- The Ref is an SVG/CSS animated companion with section-aware docking, not a full real-time 3D model or unbounded drag-and-drop across arbitrary coordinates.
- A real physical iPhone/Android audio/playback and native WebView test has not been performed; browser interaction and low-volume opt-in whistle UI were verified only in Chromium simulation.
- Actual source count and odds data still require the original game-by-game freshness/proof policies; decorative retro cards do not establish a sportsbook advantage or betting profit.
- Signed-in private Survivor state remains behind authentication; no Knockout pick was submitted by website visual tests.
