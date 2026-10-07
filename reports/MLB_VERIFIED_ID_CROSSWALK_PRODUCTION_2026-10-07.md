# MLB official player-ID reconciliation — production five-batch release

Date: 2026-10-07 UTC
Source revision: d981e93
Production: /home/ubuntu/sports-hulk
Backup: .deploy_backups/mlb_player_ids_20261007T224545Z
Recovery branch: backup/pre-mlb-ids-20261007T224545Z

## Exact official identity evidence
- 221 missing-archived-numeric-ID predictions clustered into 13 player-and-game identities across four MLB StatsAPI-confirmed final playoff games.
- Every allowed recovered ID required matching exact official numeric player ID, full normalized player name and team in both the MLB player-context source and pregame league-official player-game history; the player ID then had to match the same MLB StatsAPI official Final box, gamePk, official team and actual participated statistic.
- The two local historical sources are both MLB StatsAPI-derived and are corroborating, not independent competing data vendors. No fuzzy identity matching or date-only game matching was used.
- Exactly 216 of the original 221 missing-ID cases qualified. Five others were not verified as having played in the game and were left PENDING.
- Frozen probability, original pick/line/odds, timestamps, previous settled grade, game proof lanes and betting model promotion gates were not changed.

## Production batches and ledger integrity
- Five separate <=50-result batches: 50, 50, 50, 50, 16.
- Added 216 official box-scored analytical settlements, 147 WIN and 69 LOSS.
- By MLB official gamePk: 849819 = 81, 849826 = 96, 849834 = 3, 849839 = 36.
- Before: 2,495 MLB frozen predictions; 1,222 WIN, 505 LOSS, 768 PENDING.
- After: 2,495 MLB frozen predictions; 1,369 WIN, 574 LOSS, 552 PENDING.
- Original ledger byte prefix preserved, 9,106,523 -> 9,297,257 bytes at release checkpoint. Append-only and no duplicate forward keys or settled events.
- Full additional replay appended zero duplicate outcomes and reconfirmed 1,943 existing official MLB settled results.
- Every new settlement carries TWO_STATSAPI_ID_SOURCES_EXACT_NAME_AND_TEAM with MLB_VERIFIED_HISTORICAL_ID_CROSSWALK identity proof and explicit no-platform-payout flag.
- Remaining MLB PENDING: 517 no official Final game yet, 32 player-not-verified-participated records (includes five original missing-ID cases), and three invalid original pregame/start timing cases.
- Other frozen sports were unchanged: NHL 977 WIN, 646 LOSS, 317 PENDING; NFL 42 WIN, 11 LOSS, 42 PENDING; NBA 661 PENDING at pre-release checkpoint.
- Result labels are paper/proof records, NOT proof of actual user-placed bets, realized profit or a reliable winning strategy.

## Batch limits and source integrity
- The normal hourly Prop V2 forward updater now caps new MLB outcomes at 50 per refresh, and can resume at the next run.
- Prior to every append, the original archive snapshot contents, both official-derived numeric identity sources and the forward-ledger metadata are rechecked. A concurrent writer or source disagreement stops the batch.
- Corrupt, conflicting or ambiguous source IDs cannot fall back to name guesses.
- Current/future unreconciled evidence stays PENDING; no automatic promotion of models.

## Acceptance
- Isolated real-data five-batch replay finished PASS with exact ledger-byte prefix and zero duplicate rerun.
- New strict ID/cross-source, source-race and resumability tests: 15 PASS.
- Existing MLB official player/game tests 26 PASS, MLB master freshness 14 PASS, NHL 23 PASS, NFL 11 PASS, NBA 43 PASS, regime 59 PASS, forward 22 PASS, CI/deploy safety 8 PASS.
- JavaScript 66 PASS and Vite production build PASS; GitHub workflows remain CI-only on main push.
- Production source-only Git fast-forward preserved all unrelated uncommitted commercial UI, MLB market and NBA collector work.
- Brain Record rebuild and public health endpoints are verified separately before final completion.

## Next improvements
- Allow verified pregame numeric IDs from original provider quotes to be frozen for every new MLB candidate so future crosswalk work becomes unnecessary.
- Await official final game feeds for 517 current MLB predictions. Never settle unplayed batters or mismatched capture timestamps.
- Continue monitoring current scheduled refresh for source conflicts and forward append-only accounting.

## Final live Brain Record acceptance
- Normal production Prop V2 forward summary revalidated all 1,943 existing officially verified MLB settlements with zero new duplicate batches and source status READY.
- Brain Performance rebuild completed READY, and public/embedded forward accountability match.
- MLB Brain Record: 2,495 tracked, 1,369 WIN, 574 LOSS, 552 PENDING, 35 pending overdue more than 12 hours.
- NHL currently 1,940 tracked, 977 WIN, 646 LOSS, 317 PENDING (5 newly captured NHL research predictions were preserved and not altered by the MLB release).
- Cross-family Brain Record: 7,469 tracked, 4,637 settled and 322 pending overdue more than 12 hours; family counts can overlap and are not unique placed wagers.
- HTTP 200 at Sports HULK commercial API, public Brain Record endpoint and Survivor Streamlit health route.
- Model auto-promotion remains false and original user interface changes were not overwritten.
