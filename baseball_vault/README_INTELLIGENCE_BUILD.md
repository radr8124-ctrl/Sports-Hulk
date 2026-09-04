# SPORTS HULK MLB INTELLIGENCE BUILD

This is a larger research/calibration build.

Adds:
1. Leakage-safe walk-forward historical comp calibration
2. Winner accuracy by comp-distance bucket
3. Total-runs MAE by distance bucket
4. Home-margin MAE by distance bucket
5. Current-game comp quality grades
6. Comp directional signal: HOME / AWAY / NEUTRAL
7. Comp vs existing HULK-model alignment: SUPPORT / CONFLICT / NEUTRAL
8. Intelligence board CSV + Parquet
9. One-command runner

Important:
- Existing BET/WATCH/PASS thresholds are NOT changed.
- Historical comps remain research-only until calibration proves useful.
- app.py untouched.
- .env untouched.
- no network calls in installer.
- existing historical feature/comps scripts are reused from MASTER.
