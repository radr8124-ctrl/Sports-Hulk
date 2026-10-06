#!/usr/bin/env bash
set -e

ROOT="/home/ubuntu/sports-hulk"
PY="$ROOT/.venv/bin/python"
NHL="$ROOT/nhl_live"
LOGDIR="$NHL/logs"

mkdir -p "$LOGDIR"

STAMP=$(
  date -u +%Y%m%dT%H%M%SZ
)

LOG="$LOGDIR/NHL_REFRESH_${STAMP}.log"

{
    echo "=========================================="
    echo "SPORTS HULK NHL REFRESH"
    echo "UTC: $(date -u)"
    echo "=========================================="

    echo
    echo "=== CORE / HISTORY CONTEXT ==="

    "$PY" \
      "$NHL/build_nhl_data.py"

    echo
    echo "=== NHL COMPLETED BOXSCORE RESULTS ==="

    "$PY" \
      "$NHL/update_nhl_completed_results.py" \
      || echo "WARNING: NHL completed-result update failed; refresh preserved."

    echo
    echo "=== NHL MARKET COLLECTION ==="

    "$PY" \
      "$NHL/build_nhl_markets.py" \
      || echo "WARNING: NHL market refresh failed; core NHL refresh preserved."

    echo
    echo "=== NHL CONTEXT / MARKET FUSION ==="

    "$PY" \
      "$NHL/build_nhl_fusion.py" \
      || echo "WARNING: NHL fusion failed; previous fusion preserved."

    echo
    echo "=== NHL DECISION BRAIN ==="

    "$PY" \
      "$NHL/decision/build_nhl_decision_brain.py" \
      || echo "WARNING: NHL decision brain failed; prior decisions preserved."

    echo
    echo "=== NHL LEARNING / RESULTS ==="

    "$NHL/decision/run_nhl_learning_postrefresh.sh" \
      || echo "WARNING: NHL learning failed; production refresh preserved."

    echo
    echo "NHL REFRESH COMPLETE"

} >> "$LOG" 2>&1
