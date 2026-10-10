# Sports HULK Design System

## Product context
Sports HULK is a premium sports-intelligence product combining live scores, best bets research, props, parlays, Survivor, fantasy, DFS, paper betting, permanent model accountability, and an embedded sports assistant. The product must feel trustworthy, fast, expert, and consumer-friendly rather than like a raw analyst notebook.

Primary jobs:
- Get the simple answer fast.
- Drill into evidence only when wanted.
- Move between scores, betting intelligence, fantasy/DFS, Survivor, and assistant without losing context.
- See whether the brain is actually improving over time.
- Distinguish live recommendations from research/shadow/accountability data.

## Existing information architecture
Current primary views: Home, Scores, Betting, Fantasy, Survivor, News & Insights, Brain Record and Ask. Betting destinations are Best Bets, Props, PrizePicks and Parlays; DFS lives under Fantasy. Keep the existing sticky brand row, desktop task navigation and compact iPhone bottom navigation. Home shows a compact editorial hero, live source-fed score cards, decision shortcuts, top news (maximum four), Survivor/Fantasy/Brain quick links and a collapsed technical status section. Ask Sports HULK keeps its own dark assistant language.

## Visual foundation — October 10, 2026 user-updated 1980s sports-broadcast edition
- **New approved direction:** premium, brighter 1980s-inspired sports magazine/editorial identity, not an all-dark navy app; this supersedes the former navy-only homepage and the old slate/blue-only constraint.
- Font: Inter for navigation, scorecards and readable body text. Bold, tight-tracked sports-magazine headlines are welcome; avoid novelty cartoon fonts.
- Main Home background: warm cream `#FFF8ED`; hero and masthead: `#FFF5E4`; main text and contrast: deep ink `#173E52`.
- Accent palette: bright aqua `#46CDD2`, coral `#FF7766`, sunshine gold `#FFD36A` plus dark ink and soft warm ivory. Use these as category/navigation and sports-masthead accents, not for fabricated betting confidence.
- Score-rail panel: pale mint `#DAF4EE`, real game tiles white with strong readable ink labels and thin coral sports-strip top. Other interior evidence pages stay white/slate and readable until intentionally adapted.
- Editorial Top News is light with small source-attributed story cards, original category icon signs, visible injury/recap/fantasy distinctions. No more than four Home headlines; the News page houses the full organized six-sport news collection.
- Deep ink navy is **one contrasting supporting surface** (for The Ref, selected learning cards, and verified proof), not a full-screen background blanket.
- Radius: controlled 12–24px; occasional squared magazine-like edges, restrained 2px editorial borders, subtle offset stripe shadows. No casino lights, faux VHS glitch, or kitsch.
- Layout: centered max-width around 1500px, compact first-screen score rail on phones, five mobile primary tabs and large touch targets.
- Motion: restrained hover lift and color transitions, honoring `prefers-reduced-motion`.
- Icons: Lucide line icons and existing original Zenith Ref avatar. Do not imply an injury is officially confirmed because a news article is tagged Injury.

## Assistant visual language
Ask Sports HULK uses a deep green-black surface with subtle grid/radial lighting, cyan/emerald accents, white type, and dark cards. It should remain distinctive but still clearly belong to the same Sports HULK brand.

## Product personality
Premium retro sports broadcast and magazine editorial, confident, intelligent and human-readable. Aqua/coral/gold evoke a 1980s sports cover without casinos, obnoxious neon, dense sports-broadcast clutter, fake certainty, sports-ad clutter or overuse of gradients. Public copy should say what a bet means (for example “Take Arizona +3.5”), not rely on opaque betting jargon or confuse model research with approval.

## UX principles for the review
1. Simple answer first; proof second.
2. Reduce top-level navigation overload.
3. Separate consumer decision surfaces from internal diagnostics.
4. Make live/current/forward/research state unmistakable.
5. Preserve accountability without forcing users through giant tables.
6. Give sports pages consistent anatomy.
7. Fantasy and DFS should feel like one family, but remain clearly distinct modes.
8. PrizePicks and Props deserve dedicated top-level destinations.
9. Survivor should prioritize the user's actual entry, used teams, current rule, current pick, score and next-best options.
10. Brain Record should summarize first and progressively disclose deep validation.
11. Mobile should not rely on a long horizontal top-nav as the main discovery pattern.
12. Assistant access should remain persistent and prominent.

## Current component style constraints
Use the **new cream/aqua/coral/gold/ink palette** above for the public frame, Home, scores, category signs and navigation, with white/slate readable research interiors and normal semantic emerald/amber/rose statuses. Keep the existing Sports Zenith identity, pages, user accounts, Book/Survivor proof gates, frozen model ledgers, assistant avatar and real sports-data sources. No generic dark-app regression, slot-machine/gambling imagery, excessive gradients, purple/pink brand rework or misleading decorative green PLAY badges. Retain original `styles.css` route safety and accessibility. New user-visible terminology must be written in plain English.

## Verified implementation and regression
- October 10 initial live 80s release: `commercial_web/src/CommandCenterHero.jsx`, `HomeGameDayDeck.jsx`, `HomeTopNews.jsx`, `App.jsx`, `styles.css` and updated original Home browser tests.
- Existing live account/private Survivor/scorecards/model pipelines unchanged. Scored game outcomes and timestamps may not be visually reinvented. The full next visual step is bringing this editorial brand system into each interior task page while preserving the compact answer-first hierarchy.
- Never claim site-wide visual rollout is complete from a Home-only pass. Verify on iPhone-width and desktop real HTTPS, zero horizontal overflow and no private identity leaks.

## Review target
The review should preserve the Sports HULK identity while identifying what should be kept, simplified, regrouped, moved, collapsed, promoted, or removed. Any recommended redesign should feel like an evolution of the current product rather than an unrelated app.

## October 10 — Retro Premium Sideline and Signal Board release
The user approved a distinctive premium sports-magazine identity: clean, memorable, warm cream + aqua + coral + gold + ink, not another black/blue futuristic-AI dashboard. Preserve that direction and the original Sports Zenith branding. Implemented directly in the current website, not as an isolated mockup:

- Full-body original referee mascot in `commercial_web/src/ZenithRefCompanion.jsx` and `ZenithRefCompanion.css`, reusing the existing Zenith referee helmet avatar. Coral field, ink-striped referee jersey, branded chest/ribbon, flag throw, strikeout arm swing, user-initiated low-volume WebAudio whistle, reduced-motion handling, Ask/Brain shortcuts, side-swapping and optional shrink.
- The referee companion follows the Home page sections in a restrained scroll-responsive fixed sideline: welcome / real scores / signal board / news / Survivor & fantasy / learning lab. No autonomous simulated game penalty or claim of a winning bet. On 768–1879px homepage viewports, reserve a 180px editorial sideline so the mascot **does not cover** the cards. On smaller screens, retain full content width and dock safely above the bottom navigation. Above 1880px, the site's natural external margin supplies sideline space.
- `commercial_web/src/HomeSignalCard.jsx` gives the five original Home decision shortcuts distinct source-grounded premium editorial treatments: coral Best Bets, aqua Props, gold PrizePicks, restrained lavender Parlays and sage Survivor. Preserve exact underlying live source counts and privacy boundaries; never turn shadow research into an approved or executable play.
- Light News article cards use matching category-specific editorial paper, not generic bright white, while retaining exact original attributed link, injury/recap/fantasy category icon truth and published time.
- Continue to show proof and data freshness in plain English. Do not create synthetic statistics or claim predictive advantages from decorative badges.
- A user-specific visual request to make a mascot more visible does not authorize automatic audio, microphone permissions, gambling actions or manipulation of actual results.


## October 10 — The Ref spontaneous sideline performances
The user specifically wants The Ref to be a playful full-body animated companion who can throw flags, make umpire strike-three motions, and show whistle gestures **automatically while visitors browse**, not just when tapped. On Home and News the original SVG Ref now stages occasional decorative silent calls, choosing motions by current section; he stays quiet when a tab is hidden, reduced motion is requested, controls are open, he is minimized or hovered, and after manual interaction. A saved **Surprise Ref calls** switch lets each visitor turn the feature off without accounts or telemetry. Whistle AUDIO always requires a real human tap. On mobile hide only the automatic speech bubble, not the full-body character; preserve nav clearance and accepted character size. Do not mistake theatrical gestures for verified game events or approved betting selections.

## October 10 — Zenith News Desk Home editorial upgrade
The user said the old Top Sports News strip blended too much into the rest of Home and approved a more dramatic **Zenith News Desk**. The existing Home now uses a distinct deep-ink (#173E52) broadcast masthead, a restrained coral/gold/aqua editorial edition stripe, a source-attributed lead feature and three compact original-source headlines. Story cards retain their soft sport/category paper, category icon signs, source/time metadata and direct original article links. On phones, supporting stories use a horizontally swipeable rail; on desktop, a featured left column pairs with three compact right-hand briefs. Preserve the exact deterministic curated selection (maximum four), stale/failure honesty and the separate six-sport News & Insights hub. Do not replace this with four identical white cards, all-dark page styling, fake BREAKING labels, unverified injury claims or fabricated betting signals. Keep mobile Ref occlusion as an explicit separate layout issue, not a reason to shrink the approved full-body character.
