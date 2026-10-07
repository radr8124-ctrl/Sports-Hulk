# NBA official competition-regime ingestion

Date: 2026-10-07
Branch: feature/nba-regime-official-feed
Status: isolated implementation, awaiting final acceptance and integration

## Original defect
- ESPN Core event records expose an explicit seasonType reference (e.g., seasons/2027/types/1), but nba_live/build_nba_core.py previously read only the unresolved season reference. Therefore nba_live/derived/NBA_GAMES_CURRENT.csv had blank season_type cells.
- nba_live/decision/build_nba_decision_brain.py outputs odds-derived rows with a game_key and scheduled start but no competition_regime/season_type fields, despite ESPN scoreboard events exposing season.type as an official integer.

## Implementation
- NBA Core parses the event's explicit seasonType reference (no extra HTTP request and no season/calendar inference). Conflicting year or type evidence returns UNKNOWN.
- After the decision brain runs successfully, the NBA refresh pipeline runs an ESPN scoreboard enrichment step.
- ESPN discovery dates include the odds candidate's UTC day and prior day only to find the right event. The date is **never** used to determine preseason/regular/postseason.
- A verified join requires matching both normalized NBA team codes and a unique event start within 20 minutes of the odds start.
- Only ESPN event season.type 1, 2 or 3 can assign PRESEASON / REGULAR / POSTSEASON.
- Missing ESPN source, ambiguous match, unknown season type, conflicting existing metadata or wrong game key never supplies an authoritative proof label.
- Adds season_type, competition_regime, competition_regime_source and espn_event_id to NBA_GAME_DECISIONS.csv and NBA_GAME_FINALISTS.csv.
- Captures an auditable receipt in nba_live/decision/receipts/NBA_REGIME_SOURCE_RECEIPT.json.
- If every scoreboard source fetch fails, avoids touching the source CSV and returns a warning.
- Never changes Betting V2 promotion policy, does not infer wins or edges and does not alter old frozen ledgers.
- All writes are atomic; no destructive bulk synchronization or GitHub deployment.

## Official source check
- ESPN Core event 401914123 (Oct 7 preseason) yields explicit source (2027,1).
- ESPN Core event 401909089 (Oct 20 regular season) yields explicit source (2027,2).
- Official site scoreboard by day returns matching events with season.type.

## Real feed dry run (copied snapshot; no production CSV written)
- 776 NBA_GAME_DECISIONS.csv rows
- 16 distinct NBA games
- All 776 rows / 16 games uniquely matched to ESPN event and explicit competition regime
- 5 ESPN date queries succeeded; 0 failed
- 0 unverified game labels
- No Betting V2 promotion permitted

## Remaining checks
Run full Python proof and commercial tests, inspect live protection, integrate source-only changes into main without touching unrelated local edits, snapshot live decisions before running enrichment, re-run downstream proof builders and smoke test HTTP endpoints.

## Final isolated acceptance
- Python competition regime + NBA source tests: 59 PASS
- Deployment safety unit tests: 8 PASS
- Commercial Node tests: 66 PASS
- Commercial Vite build: PASS
- Python and bash syntax: PASS
- Live ESPN enrichment run on an isolated copy of the decision CSV: 776/776 rows verified, 16/16 distinct games verified, all identified as REGULAR by ESPN season.type=2; 5/5 date queries succeeded
- Existing early-market watch decisions remained unchanged. No betting promotion was attempted.
