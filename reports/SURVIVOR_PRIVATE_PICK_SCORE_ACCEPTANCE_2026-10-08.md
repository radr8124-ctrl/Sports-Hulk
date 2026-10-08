# Survivor Personal Pick Score — safe production candidate

Date: 2026-10-08 UTC

## Scope
- Main Sports HULK Survivor page now has a compact My Pick Score section for the authenticated, linked private Survivor entry, including multiple picks, team, opponent, score/clock where the live feed supports it, and a distinct saved Survivor result.
- Its server endpoint already enforces authenticated user and linked-entry ownership. The new response adds only the selected entry's recent personal pick score cards, derived from immutable historical week blocks and live public NFL scores.
- It never changes saved picks, adjudicates an actual pool submission, revives eliminated entries, or treats a live lead/scoreboard final as a settled pool entry unless the saved official Survivor state itself is settled.
- The current pool week is Week 5, while the live private source still contains the Week 4 Minnesota Vikings WIN and two Week 3 wins for ANNIE G 01. Read-only acceptance reproduced all three scorelines and preserved the original JSON bytes.

## Verification
- Eight focused Node regression tests PASS: historical Week 4 Vikings, multiple Week 5 live picks, ungraded final game, stale wrong-week score filtering, rollover isolation, duplicate team across different weeks, invalid/no-entry, and upcoming games.
- All 81 existing and new commercial Node/API/UI tests PASS.
- Vite React production build PASS with the new private score component, Node server syntax PASS.
- Live user App.jsx contains unrelated uncommitted PropsV2Panel refactor. A check confirmed the exact pre-existing user patch replays onto this feature branch cleanly. Preserve that patch and all user data on release.

## Remaining Survivor roadmap
- The older Streamlit app accepts PDF, XLSX and CSV whole-pool sheets with preview/confirm; the last 9-page PDF parsed 364 entries and 1,811 picks read-only. The main commercial Survivor tab lacks this uploader and needs a private, authorized import workflow before feature parity.
- The main commercial tab currently links existing private entries but does not let the member save a new week's teams. This will require an authenticated linked-entry write endpoint with the existing Survivor rollover and no-reuse guards. Do not alter saved records during test work.
- User's main site has zero local linked Survivor accounts in the local fallback file; remote InsForge account links may be separate. Do not publish historical personal entries to anonymous visitors. Linking the entry remains required before the personal scorecard appears.
