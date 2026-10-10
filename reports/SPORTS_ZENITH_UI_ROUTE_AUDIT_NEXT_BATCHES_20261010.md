# Sports Zenith — Live UI Route Audit and Next Small-Batch Plan
Date: 2026-10-10 (America/New_York)
Status: AUDIT VERIFIED / DESIGN PROPOSAL — user review before architectural UI changes
Live domain: https://sportszenith.com
Latest code at audit: `5fac611`
Scope: existing commercial_web frontend only. No prediction, source, bet, fantasy, Survivor or authenticated account data changed.

## User goal
User is pausing free GroqCloud key setup because they do not have their computer. Priority returns to finishing the **existing Sports Zenith UI** without starting a new site or losing the accepted retro premium visual design. They specifically dislike excessive scrolling, clutter, disappearing research, generic dark pages and promises of completion unsupported by live tests.

## Accepted design contract — source of truth
`.superdesign/design-system.md` (updated October 10):
- Premium 1980s sports broadcast / magazine, **not** all-dark futurism or casino neon.
- Cream `#FFF8ED` / `#FFF5E4`, dark ink `#173E52`, aqua `#46CDD2`, coral `#FF7766`, gold `#FFD36A`. Dark ink cards may serve as **limited contrast**, especially The Ref/Ask and proof, not generic full-screen styling.
- Simple answer first, proof on request; no fake winning confidence, promote no PASS/shadow records to verified bets.
- Five bottom navigation destinations on iPhone; DFS under Fantasy; Props and PrizePicks retain distinct destinations; Survivor must prioritize **signed-in actual entry/pick used teams/score**, not a generic public research board.
- Preserve site domain/routes, data sources, authentication and original referee assistant. No generic replacement dashboard.

## Read-only live audit
Using Chromium Playwright against actual HTTPS, not mocks, audited nine public routes at 390x844 iPhone and 1280x800 laptop on October 10. All returned a document width matching the viewport (0 sideways overflow). A later read-only smoke at widths 320, 360, 430 and 768 px also recorded 0 horizontal overflow and 0 browser JS errors (shorter initial waits on lazy-loaded pages mean those secondary heights are NOT canonical).

### Canonical snapshot heights (390 px iPhone / 1280 px laptop)
| Route | iPhone scroll height | Laptop scroll height | Finding |
| --- | ---: | ---: | --- |
| Home | 3,395 | 2,688 | Approved warm retro hero, real mint game deck, signal cards, character mascot |
| Scores | 933 | 800 | Good compact benchmark for other task pages |
| Best Bets | 8,198 | 3,813 | Serious scroll burden; long odds/research material should be progressively disclosed |
| Props | 4,238 | 2,011 | Unclear current candidate volume vs actionable qualifier; scrolling through long research |
| PrizePicks | 4,610 | 2,226 | Separate proof but long research lane |
| Fantasy | 3,702 | 2,050 | Account connection screen before weekly actions; DFS and season-long are modes |
| Survivor | 3,237 | 1,710 | Anonymous research only, no private picks exposed; deadline banner; needs signed-in verification |
| Brain Record | 12,658 | 5,405 | Highest-priority overlong page, key official results in many tall panels |
| Ask | 1,458 | 1,160 | Dark contrasting assistant intentionally distinct per design contract |

The heights are **snapshot data dependent**, not a promise about every day's page length. Screenshot copies produced during audit remain local to `/tmp/zenith_ui_audit_20261010` and are not included in Git. The JSON route/heading audit was produced live (saved separately below).

### Concrete screenshot / code observations
- Home on iPhone is visually in the approved cream/coral/aqua/gold family, but the full-size animated referee overlaps the right edge of the score tile area in the captured viewport. At 390px interior Fantasy and Props, the small floating Ask launcher visibly occupies the lower-right content area. Resolve this without eliminating accessible assistant entry or breaking the user-approved full-size Home character.
- Most non-Home research surfaces remain white/slate with blue accents; Brain Record uses an extensive full-width dark panel and dark Ask is intentionally distinct. Site needs intentionally consistent editorial accents on interior pages, preserving high-contrast text, research clarity and special dark Ask.
- Mobile bottom navigation has exactly **Home / Bets / Fantasy / Survivor / Ask**, with **Scores / News & Insights / Brain Record / Research** in More. Props / PrizePicks / Tools / Parlays / Bet Lab are in a horizontal Betting sub-navigation; part of the row clips on iPhone until horizontally scrolled. This is usable but should have explicit discoverability cues and one-tap routes.
- Props page displayed **953 CURRENT** rows and a caveat that none cleared independent proof. PrizePicks displayed **95 CURRENT** and 0 qualified monitors/plays in captured output. Those are research records, NOT 953 or 95 approved plays; improve labels (e.g. 'research lines') without changing counts or inventing outcomes.
- Survivor anonymous route shows **Week 5, deadline Saturday 6 PM Eastern**, sign-in message and explicit warning that Zenith does **not** submit an external pool pick. 0 current and 13 archived comparisons appeared in the audit, which is not evidence of a verified current playable selection. Signed-in account view is not inspected by this anonymous audit.
- Brain Record's top official stats came from the actual public source, and showed 3 published / 2 pending / 1 settled, 0-1-0 record in audited live capture. These are not redesigned or recomputed; official and shadow research must remain separate.
- Current `commercial_web/src/SurvivorPickEditor.jsx` is **dirty with unrelated existing work**. Do not overwrite, stash, discard or commit it as part of a visual pass.
- Home's documented 1980s editorial launch and sideline mascot were already released in commits and reports (especially `SPORTS_ZENITH_RETRO_PREMIUM_WOW_REF_SIGNAL_BOARD_20261010.md`), so this is **continuation**, not a new design.

## Recommended phased UI work — smallest actionable batches
### Batch 1. Mobile navigation and Ref occlusion
- Preserve five-tab bottom nav, desktop nav, original routes and deep links.
- Introduce a clear, one-tap compact way to reach Props and PrizePicks from the Bets area without guessing that horizontal sub-tabs continue offscreen; keep Parlays, Tools and Bet Lab accessible.
- Prevent the Ref launcher/mascot from hiding action labels, scores, form fields or filters at 320–430px. Preserve Home's animated full-size original referee with shrink/move tools and reduced-motion support.
- Add focus/keyboard/VoiceOver style checks, no document overflow or bottom-nav obstruction.
- Test at widths 320, 360, 390, 430, 768 and 1280px.

### Batch 2. Condense Brain Record with answer-first summaries
- Keep **permanent official accountability** visible in the first screen: official W-L-P, settled, pending, hit rate, units/ROI and proof status with exact existing figures.
- Turn secondary deep analysis, previous season learning and dense audits into **clearly named collapsed evidence panels**; retain every existing drill-down and source, never hide a pending loss.
- Shift from a full giant dark block to restrained contrasting hero + warm editorials + light evidence cards; do not replace the honest official model ledger with marketing.

### Batch 3. Best Bets / Props / PrizePicks / Parlays
- First screen: sport filter, current-source status, actionable vs research-only distinction, exactly what the user would take only if source validated. Detail is expandable.
- Current candidate counts should explicitly say RESEARCH NOT APPROVED, not generic 'CURRENT' which can be misread.
- Group rows by sport, matchup, and market; keep source/time, price, line, fair/no-vig, independently estimated probabilities and exact proof in drill-downs. Preserve failing/expired/stale states.
- Apply premium cream/coral/aqua/gold editorial treatments. No gambling casino aesthetic or fabricated PLAYs.

### Batch 4. Survivor signed-in personal decision UX
- **First card** when authenticated: My Pick Score (team, opponent, exact score/clock/status when actually source-supported), entries/duplicates, saved week, used teams, pool rule, and external submission distinction.
- Highlight the upcoming deadline and whether **official external submission + Scott's OK** is confirmed versus merely saved on Zenith. Never infer external submission from a local save.
- Second card: top eligible choices, verified freshness and future value, not just archived bookmaker comparisons.
- Test private authentication, personalized/linked entries and precise account ownership, including duplicate entry names. No edits to the currently dirty SurvivorPickEditor without reconciling concurrent changes.

### Batch 5. Fantasy/DFS + score/news consistency
- Frontload next actionable Start/Sit, Waivers, FAAB, IR, Defense, Trades and a clearly separate DFS Lineup Lab mode; hide long empty sign-in/onboarding help behind disclosure.
- Keep ESPN/Yahoo/Sleeper/CBS connection availability accurately labeled.
- Bring category/source labeling for scores and news in line with Home, without inventing live data.

## Acceptance and safety
- User reviews UI Batch 1 design before altering source; for broader architectural reorganizations, follow existing `superpowers` spec/plan.
- Build and test in small scoped changes; SHA-verified prechange backup, TDD where behavior changes, no cross-project edits, stage only named files.
- Use existing `commercial_web` Vitest/Node + Playwright for signed-out coverage, 320/360/390/430/768/1280 browser QA, reduced-motion and tab navigation; signed-in Survivor needs separate explicit authenticated test.
- Real HTTPS confirms no overflow, no collisions, no accidental claims of a bet PLAY, no account data exposed. Show actual before/after measurements, not aesthetic claims.
- Record every completed batch in versioned repository docs; Git local is NOT proof of off-VPS restore.
- Groq Free account onboarding remains parked; **no paid LLM, no automatic keys, no inference requests.**

## Current status
Read-only UI audit complete; no website UI files were changed in this checkpoint, and no Survivor pool pick was created/sent. Visual design batches are recommendations awaiting review.
