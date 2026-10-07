# Sports HULK MLB missing-player-ID strict crosswalk — isolated acceptance

Date: 2026-10-07 UTC
Source branch: feature/mlb-verified-id-crosswalk
State: isolated replay PASS, not yet integrated into production

## Problem
- 221 previously PENDING MLB predictions tied to only 13 provider-event/player combinations across four completed official MLB games had no original archived numeric player ID in the first-gradeable market snapshots.
- Their original frozen player/game UUID, captured timestamp, market, side, line and probability were already permanently recorded; no fabricated bet entry was needed.
- Name/date-only game pairing or fuzzy player guesses would not be acceptable and were not used.

## Explicit league-derived identity recovery
- The existing official MLB player-context table and separate historical MLB StatsAPI player-game box ledger both had to record the SAME unique numeric player ID, exact normalized player name and team.
- Historical player identity evidence had to come from the original 2026 MLB StatsAPI OFFICIAL_LEAGUE_FEED final-game history, and the first official game observation must predate the frozen prediction capture.
- After the unique provider UUID had separately matched one MLB official gamePk by original opponent pair and first-pitch time, the final MLB StatsAPI box had to independently confirm that exact official numeric player ID, full name, team, game state and actual played stat.
- Any ambiguous ID, conflicting name/team, invalid early history, duplicate official player, missing metric, DNP or future/unfinal game remains PENDING.
- Confirmatory tables share the StatsAPI upstream, so they are corroborating official-derived records rather than separate independent sports-data vendors.
- Both source files are SHA-256 fingerprinted before/after research and before append, and concurrent ledger writes block new results.
- Existing archived numeric player IDs retain first-tier matching and cannot be silently overridden by a conflicting crosswalk.
- Model probability, selection state, odds and earlier settled outcomes never change; official analytical grades are not evidence of real-money bets or payouts.

## Five frozen-data batches (isolated copy)
- Original MLB: 2,495 tracked; 1,222 WIN, 505 LOSS, 768 PENDING.
- Exactly 216 recovered using exact corroborated numeric identities, with 147 WIN and 69 LOSS.
- Five batches with a hard ceiling of 50 events: 50 + 50 + 50 + 50 + 16.
- All 216 new rows carried the provenance TWO_STATSAPI_ID_SOURCES_EXACT_NAME_AND_TEAM and MLB_VERIFIED_HISTORICAL_ID_CROSSWALK.
- Remaining five of the original 221 did not have a verified participation/played box and stayed PENDING.
- After isolated replay: MLB 1,369 WIN, 574 LOSS, 552 PENDING.
- Other remaining PENDING: 517 without completed official game, 32 unplayed-player records including the five above, three with invalid pregame timing.
- No existing WIN, LOSS, PUSH or other sport grade changed. Entire original forward-ledger byte prefix preserved, frozen 5,191 entries retained.
- One additional pass settled zero records. The full original MLB and NHL/American football/basketball frozen records were unchanged except for the 216 append-only MLB outcomes.
- No automatic model promotion or real-money payout claims.

## Acceptance test coverage
- New exact official identity, corrupt-source detection, data-race blocking, date and name checks and resumable 50-at-a-time batch tests: 15 PASS.
- Existing MLB game/player 26 PASS and MLB official master status freshness 14 PASS.
- NHL 23 PASS; NFL 11 PASS; NBA 43 PASS; regime proof 59 PASS; forward evidence 22 PASS; GitHub deployment safety 8 PASS.
- JavaScript UI/API suite: 66 PASS.
- Vite production build and Python compile/YAML validity: PASS.
- Only source code, tests and this report are eligible for Git commit; untracked copied runtime source and ledger files are excluded.

## Controlled live deployment prerequisites
- Check active MLB refresh, Prop V2 and Brain Performance writers.
- Back up original ledger, official historical identity sources, archived snapshots, public Brain/Prop summary and source manifest.
- Merge only after verifying no overlapping uncommitted edits; source-only fast-forward.
- Run five batches and validate each one before continuing. If current official game statuses have changed, report verified differences and never force stale expected counts.
- Rebuild Brain Performance and verify public NHL/MLB/NFL records, Survivor, append-only ledgers, and GitHub CI-only sync.
