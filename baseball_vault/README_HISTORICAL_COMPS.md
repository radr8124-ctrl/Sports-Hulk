# Sports HULK — MLB Historical Comps v1

This is a leakage-safe first historical-comps layer.

Historical pregame features:
- trailing 10-game runs scored
- trailing 10-game runs allowed
- trailing 10-game win percentage
- trailing 10-game run differential
- home/away rest
- park run factor

Every historical rolling feature is shifted by one game, so the game's own result is not used to predict itself.

For each current game HULK finds the 25 nearest completed historical situations and reports:
- historical home win rate
- average total runs
- average home margin
- comp distance
- detailed comparable games

This update does NOT change BET/WATCH/PASS thresholds automatically.
It does not claim sportsbook line reconstruction yet.
Market/open-close history remains a separate layer.

app.py and .env untouched.
Installer makes no network calls.
