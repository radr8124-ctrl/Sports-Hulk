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
Top-level views: Home, Ask Sports HULK, NFL, MLB, NBA, CFB, Props, Parlays, Survivor, Fantasy, Practice, Brain Record, Research.
The current UI uses a sticky brand row plus a second horizontal tab row. Home includes a large command-center hero, health status cards, live scores, decision cards, Survivor strategy and a learning-loop section. Brain Record contains many stacked accountability sections and large data tables. Ask Sports HULK uses its own dark visual language.

## Visual foundation
- Font: Inter only.
- Main app background: #f8fafc.
- Primary surfaces: white cards with #e2e8f0-like slate borders.
- Main text: slate-950/slate-900.
- Secondary text: slate-500/slate-400.
- Brand emphasis: strong blue-700.
- Success: emerald.
- Warning: amber.
- Error: rose.
- Radius: rounded-2xl/rounded-3xl; hero around 30px.
- Shadows: subtle, soft; no heavy glossy effects.
- Layout: centered max-width about 1500px, generous horizontal space on desktop.
- Motion: restrained hover lift and color transitions.
- Iconography: Lucide line icons.

## Assistant visual language
Ask Sports HULK uses a deep green-black surface with subtle grid/radial lighting, cyan/emerald accents, white type, and dark cards. It should remain distinctive but still clearly belong to the same Sports HULK brand.

## Product personality
Confident, intelligent, calm, transparent. Avoid casino aesthetics, neon betting clichés, sports-broadcast clutter, fake certainty, or overuse of gradients.

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
Use only Inter, slate/white/blue/emerald/amber/rose colors, soft borders, subtle shadows and Lucide-style icons. Do not introduce purple/pink branding, decorative serif fonts, glassmorphism-heavy effects, or casino/neon visual language.

## Review target
The review should preserve the Sports HULK identity while identifying what should be kept, simplified, regrouped, moved, collapsed, promoted, or removed. Any recommended redesign should feel like an evolution of the current product rather than an unrelated app.
