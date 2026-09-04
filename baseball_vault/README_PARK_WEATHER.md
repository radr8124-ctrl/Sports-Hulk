# Sports HULK — MLB Park + Weather Enrichment

Adds:
- historical run-environment park factors from MLB Game Master
- weather feature extraction from the existing Open-Meteo raw weather file
- enriched matchup board with park/weather context
- hitter-friendly / pitcher-friendly environment flag

Important:
- Park factor is descriptive historical run environment, not a proprietary sportsbook factor.
- Weather and park context do NOT automatically change BET/WATCH/PASS thresholds in this update.
- Historical comps are next, but we will keep them leakage-safe. We will not pretend future information was known before old games.
- app.py and .env untouched.
