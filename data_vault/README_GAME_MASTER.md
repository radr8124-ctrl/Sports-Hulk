# NFL Game Master
Builds 2016-2025 one-row-per-game historical master from the PBP vault plus nflverse games/schedule data.

Outputs:
- NFL_GAME_MASTER parquet + CSV
- NFL_TEAM_GAME_FEATURES parquet
- NFL_HISTORICAL_COMPS_BASE parquet + CSV

Important: historical matching uses shifted PRE-GAME rolling metrics, not same-game results. nflverse spread_line/total_line are closing market fields; opening/intraday movement remains a separate live-snapshot layer.
