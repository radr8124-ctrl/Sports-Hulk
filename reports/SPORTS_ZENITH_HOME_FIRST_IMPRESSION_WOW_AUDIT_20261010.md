# Sports Zenith — Home First-Impression Premium/WOW Audit (read-only)
Date: 2026-10-10 (America/New_York)
Status: **LIVE FIRST-VISITOR AUDIT COMPLETE — bounded visual polish concept awaiting user confirmation**
Website: https://sportszenith.com
Repository baseline: commit `c63f350` (The Ref spontaneous calls)

## Existing approved identity (retain)
The source of truth is `.superdesign/design-system.md`: premium 1980s sports-magazine/broadcast editorial look, warm paper `#FFF8ED`, cream `#FFF5E4`, dark ink `#173E52`, coral `#FF7766`, aqua `#46CDD2`, gold `#FFD36A`. The original full-body animated Ref is part of the product identity; it makes spontaneous *silent* flag, strikeout and whistle gestures on Home/News. Do NOT replace this with casino neon, bland SaaS dashboards, fake betting advantages or a tiny generic AI icon.

## Verified live first-visit audit
Captured actual production `https://sportszenith.com/` in headless Chromium at 390x844, 430x932, 1280x900, and 1920x1080, waiting for the real UI and public data to load. Every response was HTTP 200, no JS exceptions, no document overflow. The screenshots and full technical extraction are under VPS-local `/tmp/zenith_wow_home_audit_20261010/` (ephemeral, not user attachments). No user authentication or private records accessed.

| Screen | Hero top | Hero height | Score deck top | First score card | Total page length |
|---|---:|---:|---:|---:|---:|
| 390px iPhone | 90px | 309px | 419px | ~634px | 3395px |
| 430px phone | 90px | 290px | 400px | ~615px | 3324px |
| 1280px desktop | 174px | 407px | 601px | ~762px | 2688px |
| 1920px wide | 174px | 351px | 545px | ~707px | 2565px |

The first phone viewport does show Home actions and a real schedule feed, which is good. Desktop's score panel and first-row games are clearly readable, with a reserved Ref sideline. Four trust-bearing components are already correctly wired: real feed tiles, honest research candidates, official Brain Record, and source-labelled news.

## What prevents a truly exceptional first impression
1. **Hero resembles a competent dashboard, not yet an unforgettable sports publication cover.** Heading `The game. The numbers. The smarter call.` is understandable but generic, and the desktop second column repeats a small Ref portrait inside a conventional dark feature card despite the full-body Ref living alongside it. The approved palette is consistent, but the cover lacks a distinctive editorial signature or edition hierarchy.
2. **Mobile Ref blocks scores.** On 390px the full-size fixed 113x142px figure occupies approximately (x269..382,y601..743). The first scoreboard card extends about (x32..318,y634..815), yielding ~**5,333px²** of overlap with the first verified score card. At 430px overlap is ~1,155px²; 320px ~190px²; none on 768px or 1280px. This is a genuine trust and usability defect despite zero horizontal overflow.
3. **Some above-the-fold information is important but too matter-of-fact.** The plain dark inset and multiple microcopy badges feel like development instrumentation rather than a premium editorial experience. Source/proof must remain, but benefits and first-click path should be sharper.
4. **Long secondary Home journey.** 390px Home scroll height ~3395px, because below the credible first-fold deck are a five-card rail, news, three product area cards, learning explainer and technical accordion. The Home should tease, not compete with its detailed destinations. The official account/public proof must remain visible and honest; low-priority technical material stays collapsed.

## Bounded design proposal (awaiting user affirmation)
**Recommended creative direction: 'Saturday Edition — Sports Zenith Game Day'.** Preserve the original site and components; elevate the existing Home hero into a true sports-magazine cover using bold editorial typography, a strong edition/masthead rhythm, and a premium visual treatment of the existing original mascot. Emphasize real games, public verified evidence and the link to The Ref rather than an unsubstantiated winning prediction. No paid media/images, random sports-player photos, opaque betting odds or fake success claims.

**Mobile Ref solution requires an explicit layout choice:** preserve the full-body figure, but give him an intentional mobile sideline/stage that does not overlap scores. Prefer a dedicated safe-space dock integrated with Game Day rather than arbitrary floating over score numbers, or a context-sensitive dock during score-reading; do not simply shrink him or obscure controls. Retain his existing automatic actions, manual controls, sound opt-in, motion preference, and local toggle.

**Keep the fast job:** the first genuine score tile should still appear on the first phone screen if practical; both primary CTAs remain tappable. Desktop should retain visible games above fold at the audited size. Preserve all page navigation, evidence, score IDs, game source time, news, Survivor privacy, and model ledgers.

## Acceptance for subsequent implementation
- Obtain user agreement to the cover-focused direction and Ref mobile stage/tradeoff before editing the UI.
- Limit first code batch to Home hero, Ref mobile placement and associated CSS/tests. Treat source-data and account code as out-of-scope.
- TDD baseline red/green for a home card/ref overlap test; assert intersection area = 0 for the first score tile when shown, 0 nav and action collisions and full-size referee figure maintained.
- Check 320, 390, 430, 768, 1280 and 1920px, screenshot actual production before/after, zero overflow, responsive typography, keyboard focus, reduced-motion and zero automatic audio.
- All existing Node and Playwright Home/Ref tests, production build and HTTPS test must pass, plus signed-out Survivor route must still be 401.
- Preserve a scoped SHA-verified backup and Git commit; report honestly if off-VPS restore remains unverified.
- Stage B free Groq LLM remains paused pending secure user-side key entry; **no model/API spending or production LLM connection** is part of homepage work.

## Read-only status
No website source changed in this report, no external pool picks sent, no model weights or official grades updated. The concept is ready for user review.
