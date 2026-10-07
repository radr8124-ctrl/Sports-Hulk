# MLB rolling official results — live release acceptance

Date: 2026-10-07 UTC
Source commit: 7b1130c
Production root: /home/ubuntu/sports-hulk
Recovery branch: backup/pre-mlb-rolling-20261007T232744Z
Backup location: .deploy_backups/mlb_rolling_forward_20261007T232744Z

## What is live
- Official MLB result verification now queries limited 31-day-or-shorter league schedule windows around the original dates of immutable forward research events, rather than failing once frozen events span more than 31 days across a season.
- Windows may span weeks, months or different years, and the complete batch is verified before any analytical outcome gets appended.
- Conflicting MLB gamePk facts across overlapping official schedule requests are an integrity hold; identical facts are deduplicated.
- When original provider research archives lag or do not exist, only newly frozen immutable pregame event ID + MLB numeric player ID + exact original club pair + first pitch may establish a provider-event->unique official-gamePk connection. The source must then be confirmed by MLB StatsAPI final game and participating player box score before any outcome is graded.
- Any conflicting original archive and frozen entry invalidates the provider event; no name/date guessing and no post-first-pitch outcome.
- All prior model versions, frozen probabilities, betting prices and forward grade rules remain unchanged. No automatic model promotion or claim of a wager/payout.

## Verified production rollout
- The source-only feature branch was fast-forward merged with zero overlapping uncommitted source files. Existing frontend and sport market edits were preserved.
- Prior to merging, the original immutable PROP_V2_FORWARD_LEDGER and associated receipts, historical official player data, archived snapshots and Brain Record were copied to a date-stamped backup with a SHA256 manifest.
- Immediate postmerge checks: 10 rolling window tests PASS and 10 original-event fallback tests PASS.
- Before/after merge live prop forward ledger bytes exactly identical: 9,308,818, with 5,199 frozen entries. No historical result or frozen bet overwritten.
- Current MLB record: 2,497 predictions, 1,369 WIN, 574 LOSS, 554 PENDING. Official proof reads 8 provider event UUIDs and four finalized MLB games, confirming 1,943 prior grades and zero new eligible outcomes or conflicts.
- Scheduled MLB official collector is active; the hourly performance refresh will continue the 50-outcome-per-run limits and recheck official sources.
- Latest status poll: White Sox/Guardians was Game Over (not yet official Final in official MLB feed), Dodgers/Braves In Progress, and the upcoming Yankees/Rays plus Brewers/Padres games Pre-Game. Such games remain ungraded until official Final and complete participated box scores.

## Regression
- New rolling window and partial/ambiguous official source tests: 10 PASS.
- New frozen event original-source proof tests: 10 PASS.
- Existing MLB final box 26, MLB identity crosswalk 15, original capture 17, MLB master 14, NHL 23, NFL 11, NBA 43, competition regime 59, forward provenance 22, workflow safety 8: PASS.
- Commercial Node tests 66 PASS; Vite frontend production build and GitHub workflow YAML/Python syntax PASS.
- Site smoke status: commercial HTTP 200, Survivor HTTP 200; public Brain Record remains READY.
- GitHub CI main push runs tests only and cannot deploy destructively.

## Next
- Monitor next official MLB Final receipts; when official game+participant stat is complete, add only up to 50 new source-backed grade events per hourly pass with append-only proof.
- Review public Brain Record and source receipts after the scheduled forward refresh. Never force unsettled Game Over/DNP or ambiguous player cases into WIN/LOSS.
