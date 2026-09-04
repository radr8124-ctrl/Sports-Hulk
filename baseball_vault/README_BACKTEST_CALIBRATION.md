# Sports HULK — MLB Backtest + Calibration v1

This update adds the honest learning loop:

1. Save every matchup-board prediction BEFORE the game.
2. Join actual final results later.
3. Grade the lean.
4. Bucket results by absolute edge.
5. Measure hit rate by edge bucket, confidence, and decision.
6. Recommend threshold regions only after enough real samples exist.
7. Never auto-lower thresholds to manufacture picks.

Why not fake a historical backtest?
The current MLB matchup score uses blended Statcast profiles. Recomputing old games with data that became available later would introduce leakage. This package therefore starts a clean, timestamped prediction history now.

Files:
- history/MLB_PREDICTION_HISTORY.csv
- history/MLB_GRADED_PREDICTIONS.csv
- derived/MLB_CALIBRATION_EDGE_BUCKETS.csv
- derived/MLB_CALIBRATION_BY_CONFIDENCE_DECISION.csv
- derived/MLB_CALIBRATION_SUMMARY.txt

No app.py changes.
No .env changes.
Installer makes no network calls.
