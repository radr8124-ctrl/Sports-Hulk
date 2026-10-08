# Week 5 member Survivor picks — isolated acceptance

- The main Survivor tab now has an authenticated private Week 5 pick editor that filters already-used teams and supports multiple required picks. It says prominently that saving to Sports HULK never submits picks to the external pool.
- The new /api/survivor/save-picks route requires a valid Insforge bearer, an entry linked to the current user, rate limiting and a validated current pool week. It invokes a constrained Python bridge using the existing atomic Survivor editor and serializes concurrent API saves with a file lock. No anonymous write access.
- Kickoff is verified from the current ESPN NFL score feed for both previous current-week selections and newly proposed teams. A started game or unverified kickoff blocks saving, to prevent rewriting a prediction after first pitch/kickoff. Used/resolved teams and eliminated entries cannot be reused or edited.
- Personal ANNIE G 01 Week 4 Vikings WIN and historical Week 3 results are never regraded or cleared. No real user pick was submitted during development.
- Ten sandbox tests passed: safe Week 5 save, multiple picks, used team, eliminated entry, stale week, kickoff lock, missing fixture proof, settled week, bad input and other-entry preservation. Full Node API/UI 81 tests passed, and the isolated Vite hybrid build passed with the user's existing uncommitted PropsV2Panel refactor.
- Activation for a specific member requires account sign-in and linking the correct Survivor entry; the local fallback member registry contained no linked accounts at the time of verification.
