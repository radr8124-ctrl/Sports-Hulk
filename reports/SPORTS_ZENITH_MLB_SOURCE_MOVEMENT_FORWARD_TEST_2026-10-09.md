# Sports Zenith — fixed 2-hour MLB player-hits source price movement (Oct 9, 2026)

**Research source and original price evidence; NOT an approved bettor, money-making edge, or real wager.**

## Preregistered and original proof

The fixed experiment was written and Git-committed **before any upcoming game Final**: `reports/ZENITH_MLB_2H_SOURCE_PRICE_MOVEMENT_FUTURE_PREREG_2026-10-09.json` (2026-10-09T08:23:33.182408+00:00, source SHA-256 `d6b03019bf718bfe62613f7c92e79a047c57487e58a207e215961c2583a25db9`). The prior expired gamePk 849832 is deliberately **NOT** a prospective movement test. Original old model Full16 18-player source bytes remained SHA-256 `0cea5e38c94451cacbc1ff552276c5df7aa1e341296b127fd0cfa6a2d19c66a8`.

The signal is a strictly source-time *two-hour* shift in a no-vig fair probability for **OVER 0.5 player hits** at the SAME sportsbook, vendor event UUID, player UUID and MLB official game/time. Only original paired OVER and UNDER lines at the exact same historical vendor capture time can qualify. Original prior quote time must be 90–150 minutes before the current source quote, closest to the preregistered 120-minute target. The market and independent official source time must match within 180 seconds. Quote currently observed must be after experiment preregistration, before pitch, within 20 minutes of observation time. For fixed primary horizon H4 and secondary H24/H1 windows, freeze the first available 15-minute-range record only, never search after results. An early >24h horizon is **exploratory/source discovery only**.

Prespecified alternatives to the raw same-book fair probability p:
- **Trend:** clip(p + 0.50 × (p − p_two_hours_earlier), 0.025, 0.975)
- **Reversion control:** clip(p − 0.50 × (p − p_two_hours_earlier), 0.025, 0.975)

No parameters will be retrofitted using next weekend's game result. Evaluation is future paired Brier, log loss and game-cluster uncertainty. Minimum 30 independent future games before a preliminary analysis; 100 independent player-game observations and actual bookmaker executable price/payout authentication still required. Correlated player and book snapshots do not become independent outcomes by multiplying rows.

## Initial genuine future-only locked source

On first post-registration source collection, the new research-only module `intelligence_warehouse/mlb_pregame_capture/freeze_source_price_movement.py` froze **18 source-matched player/market movement observations**, all from independent upcoming official gamePk **849831** (White Sox at Guardians), starting Oct 10 at 8 PM US ET. These are **18 player quotes in ONE game**, not 18 independent games, not model wins and not wagers.

All 18 captured sources were returned in the first no-lookahead `EARLY_DISCOVERY` window. No original source probability movement exceeded the separately fixed 3 percentage-point feature threshold. Source original captured quote time around **2026-10-09T08:23:50Z**, compared with prior same-book original archived quotes around 06:22Z. The raw book/current-vs-prior price snapshots are preserved and independently SHA checked.

Frozen append-only private research ledger SHA-256: `cc25ce065e417b507a498776a0be899814702cb3a4b9027f022abd9a3e942ca1`. Original source-matched snapshots are stored in MLB market history and pinned by file path + SHA256 within every frozen observation. Rerun verified all **18 row ledgers and 3 distinct source snapshots** without changing any old frozen bytes. The player IDs from vendor snapshots are **NOT independently identified as official MLBAM player IDs** until the separate protected true pregame full-lineup model provides a verified provider UUID crosswalk.

Second official future fixture **Dodgers at Brewers** remains present in the official game master and raw sportsbook market; the earliest correct start-time/athlete book pair had not yet persisted for the required two-hour span at the first source freeze. A missing historical price pair must stay pending, not be invented from a different sportsbook, different start, milestone YES price or guessed player name.

## Separate future grading — fail-closed

Added `intelligence_warehouse/mlb_pregame_capture/grade_future_price_movement.py`. It grades only when the original, source-verified Full16 player model subsequently preserves the SAME MLB gamePk, provider/event UUID, provider player UUID and official MLBAM ID, real pregame lineup SHA, original prospectively frozen model/quote, and separately verified official player Final hits. The official Final score must be captured after the real start. Actual official 0/1 hits-over-half outcome must agree with the verified numeric MLB hits. Unknown/ambiguous players or non-Final games stay PENDING and cannot become a profitable result or a loss by assumption.

The grader evaluates the raw no-vig market, fixed momentum challenger and fixed reversion control on **exactly the same truly frozen source** and official hits, with one independent game block for correlated player observations. It writes separate immutable analytical grades; no live betting model, bankroll, Product HULK, NHL/NBA/DFS/Survivor or sportsbook offering is touched.

First manual guarded capture and official-grader both returned **rc=0** and retained **18 frozen source signals, 0 official graded signals** (18 awaiting a truly verified pregame MLBAM player bridge), **0 wagers**. The public original MLBAM identity and final outcome are not inferred from the vendor's athlete name.

**Important limitation**: `captured_at` is the sports-data AGGREGATOR's collection time, **not** independently verified time the bookmaker changed odds. Without real executed book price and independently observed bet payout, this cannot establish closing-line-value or financial ROI.

## Source integrity, automation, recovery

- Both future-only modules are protected by original 30-file bounded source history scans and private append-only file locks. Consecutive playoff games with the same home/away teams are distinguished by exact official kickoff (±180 sec), and any provider event UUID reused across independently different gamePks is rejected. Tampered/missing original raw source digests stop new claims.
- The research-only source capture was appended to the existing nonblocking 10-minute MLB runner AFTER the official schedule/book source audit, with a 16-second governed CPU safety cap; the official after-final score review follows with a 13-second cap. Failure of either new research stage cannot block normal live MLB operations or rewrite original frozen predictions.
- **444 MLB regression tests passed**, including 41 focused source/price/player Final/wiring tests, Python compile and shell syntax. Both new guarded manual research stages returned **rc=0**. An actual subsequent full systemd timer with both new stages remains to be verified before declaring scheduled integration complete.
- Before wiring, the original MLB run script was checkpointed locally under `.deploy_backups/zenith_mlb_price_move_forward_wiring_PRE_20261009T083350Z/`. The private original frozen quote/provenance + test/code backup `.deploy_backups/zenith_mlb_price_movement_verified_first_frozen_20261009T084000Z/ORIGINAL_PRICES_FROZEN_FORWARD_PRIVATE.tar.gz` was fully extracted and **14/14 files passed individual SHA256 readback**, bundle SHA-256 `1cb77ea4fbf1e91604f457c2c4d024943b39f1ca388619c9aacc7c84edd2de2d`. This is **VPS-local only**, NOT independent off-VPS restoration.
- Private source quote records, original immutable public score/lineup source and dynamic research ledgers remain excluded from Git, preserving provider permissions; only new code, independent acceptance data and tests are eligible for Git.

**Present performance evidence:** one originally completed Full16 gamePk 849832 (18 correlated player lines) marginally outperformed the original raw sportsbook by Brier. There is still **no statistically established 70% profitable strategy or newly verified market edge**. Source-quality and historical learning do not guarantee higher winning picks.

## Actual automatic run passed — source 08:43–08:44 UTC

The ordinary source-budgeted 10-minute MLB timer successfully ran **both newly wired research stages**, the movement collector and the official-result grader, each with `rc=0`, then ended `MLB REFRESH COMPLETE`. It automatically appended **eleven** new `EARLY_DISCOVERY` source movement records for Dodgers @ Brewers to the previous **18** White Sox @ Guardians. All original 18 were verified as an exact raw-byte file prefix.

**29** frozen future player-sportsbook quote movements in **two** independent still-upcoming game blocks are preserved; all **five** distinct raw original vendor-market snapshot CSV SHA-256 checks passed. No individual movement exceeded the fixed 3 percentage-point research threshold. **ZERO** future source-confirmed player-game grades or outcomes, as the player-level MLBAM identity bridge and final full-lineup research source are still unavailable. No units, ROI, bets or improvement are therefore attributed to this movement feature.

Original frozen Full16 source SHA-256 `0cea5e38c94451cacbc1ff552276c5df7aa1e341296b127fd0cfa6a2d19c66a8` unchanged. Post-timer movement ledger SHA-256 `0d8a83a0a361ca2d8a59c3588fc0f84d5988c3bb584157c1dc48fbb9bbe56307` and byte-prefix proof recorded in `reports/MLB_TWO_HOUR_PRICE_MOVEMENT_AUTOMATED_SOURCE_ACCEPTANCE_2026-10-09.json`. **444 broad MLB regressions passed** before normal 08:43 timer. Source histories are private and explicitly not re-published or added to Git. Separate VPS-local checked recovery is available; independent off-VPS restoration remains unverified.
