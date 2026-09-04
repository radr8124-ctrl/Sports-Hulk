# Sports HULK MLB Decision Brain Research Build

What this larger build does:
- profiles the current MASTER schema automatically
- auto-detects the best available numeric edge/model field instead of hard-coding one name
- converts comp calibration into capped reliability
- compares historical-comp direction to the existing model direction
- creates SUPPORT / CONFLICT / NEUTRAL alignment
- creates a guarded research consensus score
- cannot manufacture a BET
- discovers market/odds source files and writes a source inventory for the next market-history layer
- writes CSV + Parquet decision-brain research output

Important calibration finding from the previous build:
- B_GOOD comps outperformed A_CLOSE in the 750-game sample.
- Therefore this build does not assume lower distance is automatically better.
- Reliability comes from observed bucket accuracy and sample count.

No app.py changes.
No .env changes.
No network calls in installer.
