# Sports Zenith — first actual Full16 MLB outcome and automatic next-source audit

**Date / basis:** October 9, 2026, about 05:20–05:33 UTC. Research only. **Betting percentage improvement/profitability is NOT proven.**

## Durable result from yesterday's genuinely frozen model

First verified MLB postseason original prospectively frozen Full16 model: official gamePk **849832**, scheduled official first pitch **2026-10-09T00:00:00Z**. Original 18 full-lineup player source identities were captured before first pitch; all 14 player/park/opponent context inputs frozen **2026-10-08T23:23Z**, new exact same-book source quote frozen ~23:27Z, full 16-context predictions immutable at ~23:28Z. Model originally trained on 90 pre-July historical games, never on this October actual Final.

After independently verified MLB StatsAPI game Final and 18 actual hitter boxscore outcomes, the fixed (not reselected) three-way probability score is:

| Frozen prospective model, same later bookmaker quote | Brier (lower better) | Log loss (lower better) |
|---|---:|---:|
| Bookmaker's raw, no-vig 18 player-hits lines | **0.216895142** | 0.625441351 |
| Training-only market-calibration control | **0.216613137** | 0.623943058 |
| Frozen 16-feature speed/bat/walks/opponent/team/park player model | **0.215108184** | 0.620061725 |

Full16 beat raw bookmaker by 0.001786958 Brier points and market calibration by 0.001504953 on **this one game**. These 18 player/line observations share one game; they are **one independent completed-game block**, not 18 independently validated bets. Moneyline/prop market execution, expected value and ROI are unverified; zero real wagers or LIVE PLAY promotions. As of 05:20 UTC, all 18 original research forecasts are officially analytically graded (not sportsbook wagers) with no pending records. Reference receipt is the preexisting **intelligence_warehouse/mlb_pregame_capture/MLB_V4_FULL16_SAME_NEW_QUOTE_SCORE_SUMMARY.json**, left unchanged.

The market/probability and official result source hashes were checked via original automated scorer on the ordinary 05:20 MLB refresh. The full16 first-frozen source SHA for exactly 18 records was `0cea5e38c94451cacbc1ff552276c5df7aa1e341296b127fd0cfa6a2d19c66a8`.

## New next-game accuracy defect, verified with official MLB schedule

**Direct authoritative MLB StatsAPI schedule queried 2026-10-09T05:26Z**, HTTP 200, source body SHA-256 `5b3cc12f4750bfc3ca5843f78f500a8004175d775621cd043dff04aa13c2acb3`. Compared against independently preserved `baseball_vault/derived/MLB_GAME_MASTER.csv` and pregame source evidence.

Within the next 72h of audit:
- **849821** (ATL at LAD), **849824** (SD at MIL), and **849836** (NYY at TB) are still marked scheduled in the local master but **not present in the currently published official MLB schedule**. This does not prove a cancellation, only that they cannot be treated as verified upcoming fixtures.
- **849831** (CWS at CLE) is marked Oct 10 21:00Z in the local master but the directly read official schedule, and its previously captured independent 03:09Z source evidence, agree on **2026-10-11T00:00Z**. Difference **3 hours**. This event is held for proper source-time reconciliation; do not automatically rewrite the original master or prior source captures.
- **849809** has placeholder team names and an approximate 07:33Z stored master first pitch. The current official source identifies Dodgers @ Brewers for **2026-10-12T00:00Z**. Such placeholder identity/time must not qualify for verified sports betting.

Only two directly published official scheduled fixtures are present within this 72h source view; **zero upcoming fixtures** yet have both exact master/source time identity *and* a fully confirmed 18-player pregame batting order. This is expected with current games not yet inside the near-start published lineup window.

Original MLB decision board already had zero final GAME / PROP eligible picks at the observed checkpoint. **Do not equate a working source audit with a retroactive fix to the stored master or site output.** Remediation for source-master disagreements must separately attest fixture and start before modifying any source master.

## New permanent read-only pregame readiness guard

Created **intelligence_warehouse/mlb_pregame_capture/build_forward_readiness.py**. It:
- Uses official MLB StatsAPI schedule from a cryptographically checked 50-minute time-bounded private cache, minimizing additional requests and not spending paid sportsbook API credits.
- Cross-reconciles all original master future games against exact MLB gamePk, resolved home/away IDs, original scheduled first pitch within three minutes, and definite pregame status.
- Checks original independently captured official game lineups (9 true verified batting-order IDs per team), original V2/V3/V4 model source counts, frozen Full16 predictions and official grade counts.
- Records mismatches and source eligibility **research-only**, fail-closed. Quarantines placeholder/absent/off-time games in the audit; does not guess a kickoff or quietly delete/postedit source data, reprice frozen predictions or change the LIVE betting rules.
- Writes only derived private `MLB_NEXT_GAME_SOURCE_READINESS.json` and a non-public cached official source response. Actual official schedule, game master, original source ledger, paid markets, models, bets and app remain unchanged.
- Added an optional nonblocking **16-second** stage *after* original MLB learning in the existing `mlb_live/run_mlb_refresh.sh`. This ordinary source-audit stage uses the protected `scripts/sports-safe-run.sh`, so failure preserves all original research and game refresh.

Tests: **12 source-readiness unit/wiring tests** (plus existing real game and source tests; 28-targeted-test suite passed). Shell syntax passed. Standalone safe-run returned rc=0 with official cache replay. New stage is wired for the existing ten-minute timer, but a subsequent full ordinary timer run after wiring has **not** yet been explicitly accepted from a fresh log. An earlier normal MLB run at 05:20 UTC was healthy and scored the first forward game.

## Critical persistence repair

Audit found many original MLB production research modules/tests from yesterday present but **uncommitted**, making recovery dependent only on VPS files and local tarballs. All **73 original source/test/driver files** were copied, SHA-256 checked, tarred, restored and individually reread successfully in a protected local archive. **64 previously unversioned code/test and run-driver files** were preserved with local Git commit **9c803b6**, with no remote push and no original result/model/odds data included. The latest new readiness code and tests also require source control commit. All private training model artifacts, source books and original official box scores remain on VPS or on its local protected backups; independent off-VPS restoration remains unverified.

## Next limited batch

1. Confirm the next ordinary ten-minute MLB timer ran the nonblocking readiness stage once and that it preserves original model/results hashes.
2. Wait for **real current game's** authoritative lineup publication, then run independently attested identity/first-pitch reconciliation and freeze newly supported *future* 16-feature research candidates. Never backdate to stale local master time.
3. Keep original frozen same-book probability, model/market Brier, ROI uncertainty and independent game counts separate. Require many future independent games, priced return evidence and robust improvement before commercial betting status. Do not chase 70% by selecting expensive favorites alone.
4. Restore source code + raw private books and source results **from an independent destination** before claiming disaster recovery.
