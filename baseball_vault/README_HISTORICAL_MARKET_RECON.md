# Sports HULK MLB Historical Market Reconciliation Build

Goal:
Make historical market context trustworthy before it is allowed to influence HULK.

Matching logic:
- normalize team names
- match away/home teams + exact date first
- allow +/- 1 day for UTC/local-date crossover
- final fallback uses nearest same-matchup start time within 36 hours
- ambiguous matches are rejected
- unmatched rows remain UNKNOWN
- no sportsbook event ID is assumed to equal MLB gamePk

Outputs:
- MLB_MARKET_RECONCILED_ROWS
- MLB_MARKET_RECON_VALIDATION
- MLB_MARKET_HISTORY_RECONCILED
- MLB_MARKET_GAME_COVERAGE
- MLB_HISTORICAL_CORE_WITH_MARKET
- MLB_HISTORICAL_MARKET_QA

Important:
This build does NOT tune BET/WATCH/PASS.
It first proves data linkage quality.
