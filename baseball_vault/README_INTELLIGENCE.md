# SPORTS HULK — Baseball Intelligence v1

Adds:
- chunked Baseball Savant Statcast backfill
- pitcher arsenal profiles
- batter-vs-pitch-type profiles
- MLB Game Master (2024-2026 by default)
- home/away days-since-last-game
- weather hook via Open-Meteo using park coordinates
- CSV + Parquet derived outputs

Important:
- This does not touch app.py or .env.
- Installer makes no network calls.
- Statcast downloads are chunked to reduce Baseball Savant query size.
- Current Odds API data is linked only as a current snapshot, not mislabeled as historical odds.
- Historical line movement remains based on HULK's own timestamped nightly snapshots plus future historical-market backfill.
- Catcher/defense/park-factor enrichment remains a separate derived layer because we do not want to scrape unstable leaderboard HTML into the core vault.

Recommended tonight:
1. Build 2024-2026 MLB Game Master.
2. Pull a 30-day Statcast sample first to prove the pitch pipeline.
3. If clean, backfill 2025 and 2026 in larger date batches.
