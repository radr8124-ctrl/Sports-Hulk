# MLB official player/game settlement — isolated acceptance

Date: 2026-10-07 UTC
Branch: feature/mlb-official-box-forward
Release status: accepted in isolated worktree, not yet live at time of this report

## Root cause
- Cached baseball_vault/derived/MLB_GAME_MASTER.csv showed October 5–7 playoff games as Scheduled, even though direct live MLB StatsAPI reports four as Final.
- MLB player history had official box scores through October 1 only. It could not safely determine October 5–7 prop outcomes.
- Frozen forward provider UUIDs are not official MLB gamePk IDs; old market snapshots preserve event UUID, both clubs and pregame time.
- Original MLB decision snapshots preserve official numeric MLB player IDs for most frozen market/player pairs.

## Exact-game settlement
- Eight provider UUIDs mapped to eight unique MLB StatsAPI official gamePks by BOTH teams plus kickoff time (within 20 minutes), not by date alone.
- Live schedule and game feed must BOTH report Final. Doubleheaders, duplicate matchups, mismatched player IDs, changed sources and unplayed batters are held.
- Every graded prediction requires a numeric MLB player ID recorded in the archived original snapshot, the same actual MLB player in the official final box, correct player team, original pregame capture, frozen side/line and a supported official stat.
- Supported hitter stats: hits, runs, RBI, doubles, home runs, steals, walks, bases, singles and hits+runs+RBI. Supported pitcher stats: strikeouts, outs in baseball thirds, earned runs, hits and walks allowed.
- A pitcher with 5.2 innings pitched is correctly 17 outs. Missing stats are never treated as 0.
- Absent player IDs, DNP, incomplete games, invalid/missing stats, capture after start or incomplete official sources remain pending, never fabricated wins/losses.
- Any contradictory prior settled grade blocks an entire MLB batch before new results are appended.
- Archive contents fingerprinted before and after read and again before writes; concurrent ledger writes also block appends.
- Output is append-only analytical results. No settled grades, frozen model probability, odds, model promotion, real-money claims or user picks are modified.

## Verified independent replay
- 2,495 MLB frozen prop predictions before replay: 289 WIN, 225 LOSS, 1,981 PENDING.
- Exactly four MLB StatsAPI final games currently verified; four additional games not final.
- Strict qualified new results: 1,213 (933 WIN, 280 LOSS). Three otherwise gradeable rows failed strict original pregame timing validation and were held.
- All 514 preexisting graded results independently confirmed with MLB official final box scores; zero contradictions.
- MLB copied forward ledger after replay: 1,222 WIN, 505 LOSS, 768 PENDING.
- Remaining pending: 517 no official final box, 221 no unique archived official numeric player ID, 27 player not verified appeared, 3 pregame/start mismatch.
- Frozen ledger byte prefix preserved; a second full replay added zero settlements. NHL outcomes and other sports' frozen grades unchanged.
- These are predictions, not proven real-money placed bets; a large win count by itself does NOT demonstrate profit at actual wager prices.

## Regression checks
- MLB new official-box, API failure, doubleheader, source-race, DNP, stat mapping and idempotence: 26 PASS.
- NHL 23 PASS, NFL 11 PASS, NBA 43 PASS, regime 59 PASS, forward 22 PASS, release safety 8 PASS.
- JavaScript 66 PASS; Vite production build PASS; Python syntax and GitHub YAML parse PASS.
- CI push only tests; GitHub release gate is manual and read-only.

## Follow-up
- Make cached MLB_GAME_MASTER officially refreshed for latest games; don't destructively replace unrelated history.
- Improve future player numeric-ID capture and expose explicit missing-ID reasons. Do not use same-date/fuzzy-name backfill to claim a win.
- Source schedule span currently guarded at 31 days, so a future rolling-window strategy will be needed as seasons accumulate.
