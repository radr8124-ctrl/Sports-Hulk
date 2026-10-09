# Sports Zenith — MLB upcoming player-hits price/source identity audit

**2026-10-09 UTC — independent-source research only. No wager, model change, or predictive advantage proved.**

## Why this matters

The existing sportsbook aggregator already supplies upcoming `PLAYER_TOTAL_HITS` OVER and UNDER 0.5 prices, but within the SAME provider event UUID it also carries source rows with **different scheduled start times**. A stale opening start is NOT proof of a currently valid game price. Never match a provider's player prop quote by game name or UUID alone. Exact official MLB gamePk, independently verified current home/away identity and original first pitch must match the quote's provider event and source start to within 180 seconds.

Actual audited raw current source: `mlb_live/markets/current/MLB_PLAYER_PROP_MARKET.csv`, 1,895 original aggregator price rows. Immutable source checksum at first study: `a212b69671e436fd3e0a989421443194c4a2684cc339031a5a84df18fbf7f753`. Original corrected official MLB game-master checksum: `f0cf17ddb8609def3cc5269cb3e1d42000196a359335524c1857265156a9d60c`. Official original schedule cache SHA: `149caa269e737b071fdcc955d52521ca868651eb922824d7c0b4f030cc80d725`. No paid API request was needed: all primary source snapshots already existed locally.

## Honest strict matches — research-only, not wagers

| Upcoming official fixture | Correctly matched same-book+same-capture 0.5 hits OVER/UNDER pairs | Books with eligible research source | Full original lineups confirmed? |
|---|---:|---|---|
| White Sox at Guardians (Oct 10, 8 PM ET) | **28** | DraftKings, theScore | No |
| Dodgers at Brewers (Oct 11, 8 PM ET) | **11** | theScore | No |
| **Total** | **39** | — | **No** |

These 39 are bookmaker-provider grouped *player-hits two-sided price pairs*, NOT 39 independent games, not qualified sports bets, not MLBAM-verified player identities, and not genuinely independently observed executable book prices. **36 stale official-start mismatch rows were rejected** from the same two provider events (including an incorrect 2h-early Dodgers/Brewers scheduled start). Another 1,779 original vendor rows were different market/side types; 2 additional rows were not the exact required hits 0.5 line. No outcome, profit, edge or model calibration is inferred from these paired source prices.

Original publisher `captured_at` is the aggregator's collection timestamp only, NOT independently verified actual update time at that named sportsbook. A future model quote still requires exact independent pregame batting order, official MLBAM player ID crosswalk, original source at the right clock, a newly observed two-sided bookmaker quote after the model input freeze, and source/price verification. Do NOT retroactively price previously frozen probabilities or assume sportsbooks' originally executable lines are licensed for commercial distribution.

## Permanent protection

- Added read-only `intelligence_warehouse/mlb_pregame_capture/audit_upcoming_market_alignment.py`.
- Verifies the latest official source-readiness receipt, recent original MLB public schedule cache and checksum, and the unchanged authoritative game master. Rejects duplicate or unresolved game IDs, placeholders, TBD kickoffs, wrong teams, wrong venue, started fixtures, stale source data and quotes outside the original 180-second scheduled start tolerance.
- Requires exact `PLAYER_TOTAL_HITS` with line 0.5, one OVER and one UNDER at same sportsbook, provider event UUID, player UUID, original source game start, aggregator capture timestamp and same book. Rejects invalid prices, invalid bookmaker overround, duplicate or single-side groups, cross-book/composite quotes and changed original source clocks. Only explicitly validated future game sources are counted.
- The only output is a derived private source-quality summary `MLB_PRETIPOFF_BOOK_FIXTURE_ALIGNMENT_AUDIT.json` with accepted pair counts, skipped source row reasons and original source checksums. NO bookmaker account action, betting decision, forecast or model training is implemented.
- Integrated as a new nonblocking governed 12-second research step **AFTER the existing official fixture/source readiness gate**, inside the existing 10-minute `mlb_live/run_mlb_refresh.sh` loop. One standalone governed run succeeded (rc=0), using only local source files.
- New source audit/wiring regression suite **9 tests passed**; all existing/new MLB regressions **412 passed**, no failures, shell syntax and Python module compiled.
- This research derived source summary remains private and Git-excluded; original sportsbook raw prices and older event history are not committed. A checksum-backed rollback copy of the original live MLB driver is retained locally at `.deploy_backups/zenith_mlb_live_quote_crosswalk_guard_PRE_20261009T080700Z`. Independent off-VPS source restore remains **unverified**.

**Next:** accept the actual next ordinary MLB timer log: check stage exit rc=0 and that original Full16 frozen SHA-256 stays `0cea5e38c94451cacbc1ff552276c5df7aa1e341296b127fd0cfa6a2d19c66a8`. Then wait for genuine original batting-order/player source and fresh enough paired quotes; do not label schedule readiness or vendor lines as a 70% betting edge.
