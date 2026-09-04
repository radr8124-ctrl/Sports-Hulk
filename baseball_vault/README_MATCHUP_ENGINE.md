# SPORTS HULK — Baseball Matchup Engine v1.1

This update adds:
- Statcast automatic retry/backoff
- resume from cached chunks
- failed-chunk tracking instead of losing a whole backfill
- full-season backfill runner
- probable-starter arsenal vs opponent lineup scoring
- bullpen workload integration
- current market join
- confidence grading
- BET CANDIDATE / WATCH / PASS classification
- CSV + Parquet matchup board output

Important:
- "BET CANDIDATE" is an internal threshold label, not a guaranteed wager recommendation.
- The matchup score is deliberately transparent and conservative.
- Current market snapshots are not mislabeled as historical market history.
- app.py and .env are untouched.
- Installer makes no network calls.

First command after install:
python3 baseball_vault/matchup_engine.py

Then, if the board builds cleanly, backfill 2025:
python3 baseball_vault/statcast_season_runner.py --years 2025
