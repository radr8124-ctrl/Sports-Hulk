# NFL / MLB / NHL Forward Results Investigation — October 7, 2026

Status: Findings verified from production data; NFL exact-player fix tested in isolated worktree
Branch: feature/nfl-exact-player-grading
Scope: Grading and forward settlement only; no automatic betting promotions

## NFL — cause and safe correction
- Graded sportsbook PROP archive stores player as a nflverse ID with team suffix, e.g. 00-0038997|IND; grader erroneously normalized this as a player's literal name, so 122 PROP results were unresolved.
- Some source market types remain intentionally unsupported and must NOT be graded.
- NFL_PLAYER_STATS_RECENT contains official-like per-game player IDs, season week and opponent; source history currently includes NFL weeks 3 and 4.
- Previous grader allowed a fallback to a different week/opponent if the exact stat row was missing, which could silently use a stale performance value.
- Strict patch requires exact player ID or name, verified team-opponent pair, and verified NFL week. Unknown or duplicated player-game rows remain unresolved.
- Copied 3,659-row recommendation ledger replay produced 117 newly gradeable sportsbook PROP episodes (62 WIN, 55 LOSS). 5 previously unresolved remain, and 6 unsupported market episodes remain.
- All 712 latest recommendation keys preserved. No pre-existing WIN, LOSS, PUSH, or other graded decision changed.
- No historical PRIZEPICKS, GAME, or PARLAY grades changed.
- Copied 5,153-entry forward prop ledger safely settled 28 NFL predictions (22 WIN, 6 LOSS) by exact provider event matching, with zero other-sport grade changes and zero duplicate settlements on repeated run.
- Changes include atomic CSV result publishing to avoid concurrent partial reads.

## NHL — official box score opportunity (not automatically changed)
- NHL pending forward predictions: 1,452.
- By a unique finalized official NHL game matched to frozen game_key, unique player ID in current NHL roster, and official per-game player history: 1,152 pending predictions have full official stat evidence.
- All 1,152 use one of four supported frozen markets: ASSISTS (461), GOALS (346), POINTS (183), SHOTS (162).
- Among already settled NHL forward predictions, 447 agree with independently recomputed official player box-score results, with zero disagreements in the observed matching subset.
- Remaining pending are 271 without a finalized official game, 24 with missing/ambiguous current roster ID and 10 without a unique official player box. None is assumed LOSS.
- Puck-drop/start discrepancy among uniquely matched rows was no greater than 40 minutes, within the evaluated 120-minute validation bound.
- Previously suspicious Darnell Nurse provider game link was checked against NHL_CURRENT_ROSTERS; roster lists his team as SJS. There is no proven mislinked player-game based on that sample; no blacklisting is warranted.
- NEXT SAFE STEP: a dedicated reviewed NHL official-box forward settlement builder. Require exact official game/team/date, official player ID and opponent, completed game, supported metric/line/side, frozen pregame capture, no duplicate/conflicting box rows, and zero contradictions with already settled predictions.

## MLB — missing provenance, NOT safe for blanket backfill
- Pending MLB prop predictions: 1,979.
- Classification against existing graded episodes by frozen provider event, player, market, line and side:
  - 904 have a related event/player/market but NOT an identical frozen line and side.
  - 766 use markets absent from currently graded source episodes.
  - 192 lack matching players in graded source episodes.
  - 113 exactly match still-PENDING historical episodes.
  - 4 match DNP episodes; DNP is not automatically a loss.
- MLB player-game official Statcast/StatsAPI history exists in intelligence_warehouse/mlb_player_history, but frozen prop entries generally lack an official gamePk, both teams and a unique official player ID.
- A same-date player/stat match could involve different games or a doubleheader, so date-only historical grading is prohibited.
- NEXT SAFE STEP: preserve provider-event -> official gamePk and player ID mapping at capture time. Verify both teams, game start, unique official box and frozen market metric before replaying alternate lines.
- Do not infer outcomes from similar-priced lines or currently graded alternate wagers.

## Governance
- Frozen predictions are separate from placed real-money wagers; none of these counts is evidence of realized profits.
- Pending remains pending, DNP/review remains unresolved, and no model is automatically promoted.
- GitHub deploy workflow remains manual/read-only, no destructive live sync.
