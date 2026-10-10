# Sports Zenith — 1980s Broadcast Editorial UI, Phase 1
**Date:** October 10, 2026. Existing production `https://sportszenith.com`; same codebase, original domain, no new service.

## User-requested correction
Previous Home was almost entirely dark/navy although the user explicitly wanted a **premium 1980s sports-magazine/broadcast look**: cream/ivory paper, aqua/teal, coral, warm sunshine gold and occasional contrasting ink dark. Avoid cheesy casino/neon imagery, endless scroll, small unreadable print, or sports status badges pretending to be confirmed model confidence. Plain-English beginner betting explanations matter; the established category signs (injury, recap, fantasy, etc.) must remain visible.

## What visibly changed and is already served via live HTTPS
- `CommandCenterHero.jsx`: original Zenith brand preserved; cream editorial masthead, four-color sport-strip accent, coral Explore Bets, warm gold highlight, aqua Game Day label, dark supporting Ref/Brain panel. **The same buttons still navigate to the same original destinations.** Mobile hero remains compact.
- `HomeGameDayDeck.jsx`: previous navy rail/cards replaced by mint scoreboard surround and white ink-text team score tiles; coral source/edition top stripe; compact 6 league filters, status distinctions, game identities, real source timestamps and ESPN/MLB attribution unchanged. Explicit `data-sport` attribute used for stable tests rather than assuming Tailwind class names.
- `HomeTopNews.jsx`: light white magazine story cards replace dark-only appearance while preserving real attributable original article links, top-four story selector, full six-sport News route, category signs, fail-closed source failure/empty/stale messaging.
- `App.jsx`: global brand/header cream, desktop ink navigation with gold selected-tab treatment, mobile cream nav with aqua active item, warm Home canvas, lighter category-colored Best Bets/Props/PrizePicks/Parlays/Survivor entry cards, coral Survivor and mint Fantasy snapshots. Dark Brain/Ref/learning remain as limited supportive contrast. Status accordion retains functional original diagnostics; all individual betting/Fantasy/Survivor pages still readable and structurally unchanged.
- `styles.css`: new Home editorial heading rules. `.superdesign/design-system.md` updated to reflect new user preference and stop future dark-app reversion.
- No change to sportsbook data, source time, calculations, confidential user tickets, model weights, forward ledger, wager state, private account database, signed-in permissions or pool submission.

## Evidence checked
- Vite React production build: PASS; original `commercial_web/dist` served on the same Sports Zenith node service without a service swap.
- 263/263 Node website tests PASS.
- 37/37 selected Playwright browser tests PASS across Home theme, Score Game Day, news, betting/mobile, Survivor privacy, Game Center and official player box scores.
- Real Cloudflare HTTPS page on 390px phone and 1280px desktop: HTTP 200, expected warm cream main canvas `rgb(255,248,237)`, hero `rgb(255,245,228)`, pale aqua source-backed scoreboard `rgb(218,244,238)`, **zero horizontal viewport overflow, zero JS errors, zero private account identity leakage**. First real score card visible around y=634px on 390px screen. Other routes remain intact.
- Live `/api/health` HTTP 200; anonymous `/api/survivor/state` HTTP 401; no new user survivor pick saved or submitted by this UI build.
- Pre-change source/test versions hash-validated in `.deploy_backups/zenith_80s_broadcast_before_20261010T0835Z/`. This is a VPS-local snapshot; **off-server raw-state disaster recovery remains unverified**.

## Next phases still outstanding
1. Bring the same retro magazine visual vocabulary into Best Bets / Props / PrizePicks / Parlays, including very clear bet meaning/actual price/source/proof. Do not turn unverified PASS into an approved play.
2. Match Fantasy/DFS and Survivor research interiors to the new design using small expandable evidence panels and clear, readable descriptions; preserve exact private entry/rules history.
3. Apply sport-category headings/identifiable iconography to Scores, News, The Ref, and Brain Record consistently; preserve 6-sport stage separation and permanent result accountability.
4. Signed-in mobile QA, native iPhone and Android apps, and authentic cross-device testing remain separately unverified.

**Important:** Phase 1 is a deployed visual rollout, NOT a claim that the full 80s redesign is finished on every page.
