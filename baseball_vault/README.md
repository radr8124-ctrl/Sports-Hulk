# SPORTS HULK — Baseball Live Vault v1

This is the first MLB live/nightly collector. It does **not** touch the Streamlit app.

## It collects
- MLB schedule for today + tomorrow
- probable starting pitchers
- game status/scores
- recent posted lineups / batting order when boxscores are available
- pitcher usage from recent games
- first-pass HULK bullpen workload table
- SportsGameOdds MLB full market snapshots, including player props where books post them
- The Odds API MLB moneyline/run-line/total snapshot
- timestamped market history CSVs so HULK starts building its own line-movement database tonight

## Existing keys
It reads the existing `.env` in `SPORTS_HULK_STARTER`.
No key is copied into this package.

## Files
`baseball_vault/latest/`
- MLB_SCHEDULE.csv
- MLB_LINEUPS_RECENT.csv
- MLB_PITCHER_USAGE_RECENT.csv
- MLB_BULLPEN_WORKLOAD.csv
- MLB_SGO_MARKETS.csv
- MLB_ODDS_API_MARKETS.csv
- LAST_RUN.json

`baseball_vault/history/`
- MLB_SGO_MARKET_HISTORY.csv
- MLB_ODDS_API_MARKET_HISTORY.csv

`baseball_vault/raw/`
- timestamped raw API snapshots

## Run
`python3 baseball_vault/collect_nightly.py`

By default it collects today + tomorrow and looks back 3 days for bullpen workload.

## Important
The bullpen workload score is deliberately a first-pass transparent score. HULK saves the raw pitch/appearance components so we can test and recalibrate the weight instead of pretending the first formula is perfect.

SportsGameOdds is capped at 25 MLB events per run to conserve the current plan's entity allowance.

Next Baseball HULK layers:
- Statcast pitch-by-pitch backfill
- pitch arsenal vs batter profile
- park + weather
- catcher framing/blocking
- fielding/baserunning
- historical game master + comps
