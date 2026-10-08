# Sports Zenith Fantasy platform connections — acceptance

Date: 2026-10-08 UTC.

## Why users could not sign into Fantasy platforms

The Fantasy page only provided a manual Rate My Team roster entry with an account sign-in requirement. There were no Yahoo, ESPN or Sleeper fantasy-provider authentication or import controls. Signing into Sports Zenith does not sign users into third-party fantasy accounts.

## New supported workflow

- A clear responsive provider section is now at the top of Fantasy > Season-Long. Users can open the real Sleeper, Yahoo Fantasy and ESPN Fantasy websites via explicit external links (all checked) instead of nonfunctional fake sign-in buttons.
- Sleeper **NFL** provides read-only import using public username, one-time listing of that person's public leagues, selected roster lookup and server-side resolution of player IDs, D/ST, starters, bench, roster settings and scoring. No Sleeper passwords, tokens or account credentials are collected, and the provider identity is explicitly marked **unverified** since Sleeper's public API does not authenticate the user. There is no write back to the Sleeper league.
- A user must first authenticate to Sports Zenith; the Sleeper lookup/import APIs reject unauthenticated requests and rate-limit authenticated users. Import writes to private Fantasy league/roster tables scoped by the current authenticated user, keeping their existing manual teams and other users' private records separate. A repeated import refreshes the same Sleeper league, not a duplicate. Player data is cached and unknown roster players block import instead of being guessed.
- Yahoo's Fantasy API currently requires approved developer access and OAuth 2.0 setup; no Yahoo OAuth app key is configured. ESPN private-league authorized integration is also absent. The UI states both connections are **not active** and does not collect their passwords or claim them as connected. Manual roster setup continues to work for those leagues.
- After a successful Sleeper import, the existing My Teams/Rate My Team and Fantasy Team Control refresh their saved league list automatically.

## Verification and limits

- 16 new Node tests PASS: input validation, privacy minimization, Sleeper profile and league lookup, roster ownership matching, sample player/DST and settings mapping, failure-closed unknown player IDs, separate-user storage, idempotent updates, and partial-storage rollback.
- All 103 commercial Node/API/UI tests PASS with uncommitted user PropsV2Panel changes in an isolated hybrid production build; Vite build PASS.
- Read-only live Sleeper API sample username lookup returned READY with a minimized user object, without exposing the public provider's unrelated profile fields. Three responsive Chromium browser checks at 1280x800, 390x844 and 320x568 PASS showing all three platforms and three official-site links. Anonymous lookup button is correctly disabled.
- No test user sign-in or authenticated InsForge roster insert was performed on the live account: a real user's Sleeper username/league is needed for end-to-end verification. Yahoo OAuth and ESPN private sync are **not** ready and must never be shown as active.
- No changes to previous manual Fantasy leagues, Survivor picks, frozen predictions or user data.
