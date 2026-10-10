# Sports Zenith — The Ref Spontaneous Sideline Calls
Date: October 10, 2026 (America/New_York)
Status: **LIVE HTTPS VERIFIED / UI BEHAVIOR RELEASE**
Repository: /home/ubuntu/sports-hulk
Production: https://sportszenith.com
Change scope: original Home/News full-body referee component and its CSS; no new project, service, paid API, wager, or prediction change.

## User-approved interaction
The user specifically wanted The Ref to act like a fun referee **spontaneously while visiting the page** instead of only throwing flags or signalling strike three after a button tap. User approved occasional autonomous performances, page-section awareness, no automatic sounds, reduced-motion support, and retaining the visible original full-body character.

## Actual behavior
- The original mascot on **Home** and **News & Insights** now performs visual flag throws, strike-three/umpire arm motions and whistle speech cues automatically after about 12 seconds of browsing, then at unhurried ~27-second idle intervals.
- His choice reflects the active Home section; the first Home welcome call is flag, the scoreboard call is strike, News uses a visual whistle; immediate repeats rotate to another gesture. Signals remain theatrical and **never represent an actual referee call, score, injury, model prediction or approved bet**.
- Automatic whistle gestures are **silent**. Existing short WebAudio whistle is still available only when the visitor manually presses Whistle. Automatic speech announcements use aria-live=off; manual call text keeps the original accessibility behavior.
- If the visitor opens The Ref's control panel or performs a manual call, automatic actions pause for 40 seconds. They remain paused while controls are expanded, the mascot is shrunk, a mouse pointer is hovering over him, the page is hidden, or reduced-motion is requested.
- A new **Surprise Ref calls** switch in the existing controls defaults ON, may be turned OFF, and saves this per-device choice in localStorage (`zenith-ref-surprise-calls-v1`), without sending visitor data anywhere.
- Original move-left/right, manual flag, strikeout, whistle, shrink/expand, Ask and Brain Record buttons remain. Original warm cream/coral/aqua/gold branding and the full-body SVG are preserved.
- Mobile 390px keeps the original **113px** character size (no reduction). To reduce occlusion, silent automatic cues hide their speech bubble on phones; the character remains above the fixed 5-tab mobile navigation.
- The large original Ref is intentionally limited to existing Home and News placements in this UI batch; other interior routes still use their existing compact Ask launcher to avoid covering betting, fantasy, and Survivor forms. Extending a full-body mascot to interior screens would require separate safe-layout work.

## Red / Green and evidence
- A scope-specific SHA-verified pre-edit backup of `ZenithRefCompanion.jsx` and `.css` was saved to `.deploy_backups/zenith_ref_spontaneous_calls_before_20261010/`. This remains **same-VPS** backup, not off-server disaster recovery.
- Pure timing/eligibility tests were written first, failed because the module did not exist, then passed (5/5) after adding `commercial_web/ref_motion_presentation.js`.
- New Playwright browser tests were written first and failed against the original site because no automatic calls occurred. Preview Vite at port 8549 identified a lazy-mount timing issue in one test; it was corrected by waiting for the mascot to mount. New preview browser suite then passed **6/6**.
- Initial combined live tests caught two further conditions: an unwanted score-section size reduction (removed to preserve the agreed full-size Ref), and a second-call timing assertion vulnerable to parallel Chromium page visibility changes. Live auto tests were run **serially** so background-tab visibility safety is meaningful rather than nondeterministic.
- Final production static Vite build succeeded, with existing nonfatal chunk-size warning.
- Full Node JavaScript regression: **314/314 passed**.
- Final live localhost:8510 Playwright: **6/6** new spontaneous-call tests (one worker) and **21/21** selected existing Home, Ref, mobile, editorial and command-center tests (two workers).
- Actual `https://sportszenith.com/` Chromium HTTPS smoke: four scenarios returned **HTTP 200** with no horizontal overflow: 390px mobile Home automatically signalled strike with speech hidden and 113px figure above bottom nav; 1280px Home automatically threw flag; 1280px News automatically displayed visual whistle; 390px reduced-motion stayed idle even after 56s of virtual time.
- Anonymous private Survivor endpoint returned **HTTP 401**; no private entry or pick was modified.
- This was **UI-only**: no server backend, data collection, API key, billing, odds, source facts, official bets, model parameters or user personal records changed.

## Files and repeatability
- `commercial_web/src/ZenithRefCompanion.jsx` — auto scheduling, state and visible switch.
- `commercial_web/src/ZenithRefCompanion.css` — hide automatic speech bubble on phones, preserving character size.
- `commercial_web/ref_motion_presentation.js` — deterministic, pure pacing and gesture mapping.
- `commercial_web/ref_motion_presentation.test.js` — five timing/eligibility tests.
- `commercial_web/ref-spontaneous-calls.e2e.spec.js` — six interactive browser checks.

Run:
```bash
cd /home/ubuntu/sports-hulk/commercial_web
node --test *.test.js
npm run build
npx --no-install playwright test ref-spontaneous-calls.e2e.spec.js --workers=1 --reporter=dot
npx --no-install playwright test retro-wow-ref-cards.e2e.spec.js home-theme-continuity.e2e.spec.js site-clean-mobile.e2e.spec.js command-center-home.e2e.spec.js --workers=2 --reporter=dot
```

## Boundaries and follow-ups
- A physical iPhone Safari/device playback session has **not** been personally tested; phone evidence uses Chromium emulated screen size.
- Preserve the user's existing explicit preference to keep the full-body Ref visible, not replace him with a generic tiny sports bot. No automatic audio, motion when reduced-motion is enabled, or text representing a fictional event as real sports facts.
- Separate future batch: safe on-page full-body Ref appearances beyond Home and News where page layouts can reserve unobstructed space; retain private Survivor and Fantasy actions.
- Avoid staging existing unrelated dirty `commercial_web/src/SurvivorPickEditor.jsx` or any model/data files.
