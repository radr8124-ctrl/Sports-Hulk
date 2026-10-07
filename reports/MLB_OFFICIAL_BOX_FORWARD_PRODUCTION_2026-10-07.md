# MLB official box-score forward settlement — production release

Date: 2026-10-07 UTC
Live source revision: 36097f4
Environment: /home/ubuntu/sports-hulk
Recovery branch: backup/pre-mlb-official-20261007T221944Z
Release snapshot: .deploy_backups/mlb_official_forward_20261007T221944Z

## Verified production results
- Mapped all eight frozen sportsbook provider event UUIDs to eight unique MLB StatsAPI gamePk IDs using archived original decision snapshots, exact teams, and game starts within 20 minutes. Four official games were Final and four were not yet final at settlement time.
- Replayed frozen MLB bets against individual authoritative MLB StatsAPI final game feeds and unique player IDs documented in original archived decision snapshots.
- New analytical PROP/PrizePicks outcomes: 1,213 = 933 WIN + 280 LOSS.
- All 514 previously settled MLB prop predictions independently agreed with direct official box-score grading; no existing result contradictions.
- MLB forward ledger total: 2,495 predictions, 1,222 WIN, 505 LOSS, 768 PENDING.
- Reasons held pending: 517 without official Final box, 221 without a unique archived MLB numeric player ID, 27 players not verified as having played, 3 with invalid pregame/start timing.
- A further three initially plausible grades were excluded by a stricter original pregame timing guard. No unverified or post-start results were counted.
- The original complete ledger was preserved byte-for-byte as a prefix of the new file: 8,119,763 -> 9,099,824 bytes.
- A second official MLB settlement scan appended 0 duplicates and reconfirmed 1,727 existing official MLB results.
- NHL outcomes unchanged: 1,935 tracked; 977 WIN, 646 LOSS, 312 PENDING.

## Evidence and guardrails
- Archived provider event UUIDs are NOT MLB official game IDs. The official gamePk was confirmed through independent exact team/start matching to the live MLB StatsAPI schedule.
- The live MLB StatsAPI game feed had to report Final, agree on gamePk/team/first pitch and game type, and explicitly list the official numeric player ID as an actual batter/pitcher with the requested stat.
- All frozen markets require exact original side/line, pregame capture and a supported official stat; DNP and absent/ambiguous player IDs remain pending. MLB pitcher outs are calculated in baseball thirds, not decimal innings.
- Original archived source files were hash-verified and concurrent source/forward-ledger changes prevent new appends. Any conflicting previous grade is a hard integrity hold.
- The official game master cached locally still incorrectly marked October 5-7 games Scheduled, but this release used direct live StatsAPI final data and did not trust or destructively replace that old game master.
- No pricing, historical grades, frozen recommendations, sports outside MLB or live model promotion were changed.
- These are graded forward predictions, not real-money wagers or profit records. High hit rates on heavily juiced lines do not establish net profitability.

## Brain Record and site health
- Brain Performance rebuilt READY and the public/embedded forward-results accountability matched.
- MLB forward: 1,727 settled, 768 pending, 251 overdue 12+ hours.
- Across four forward data families (overlapping records, not unique wagers): 7,458 tracked and 4,421 settled, 538 overdue 12+ hours, 4 overdue 48+ hours.
- NHL remained unchanged; no automatic model promotion. HTTP 200 for commercial API, Brain Record and Survivor page.

## Tests and release scope
- New MLB proof/safety/source race tests: 26 PASS.
- NHL: 23, NFL: 11, NBA: 43, regime: 59, forward provenance: 22, deployment safety: 8; all PASS.
- Commercial Node test suite: 66 PASS. Production Vite build and YAML workflows checked PASS on isolated source branch.
- Source-only fast-forward, with all unrelated live App.jsx and supplier/market edits preserved. GitHub workflows remain read-only validation on push, no auto-deploy.

## Next improvements
- Repair stale MLB_GAME_MASTER cached schedule freshness, and link the official game-final status to MLB UI/box-score data without discarding historical files.
- Expand frozen player ID capture for the 221 missing cases, and only grade if official game and player are verified. Do not use name/date guesswork for doubleheaders.
- Use rolling schedule windows across future seasons so the current 31-day safety bound doesn't cause a future fail-closed gap.
