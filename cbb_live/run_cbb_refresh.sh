#!/usr/bin/env bash
set -e

ROOT="/home/ubuntu/sports-hulk"
PY="$ROOT/.venv/bin/python"
CBB="$ROOT/cbb_live"
LOGDIR="$CBB/logs"

mkdir -p "$LOGDIR"

STAMP=$(
  date -u +%Y%m%dT%H%M%SZ
)

LOG="$LOGDIR/CBB_REFRESH_${STAMP}.log"

{
    echo "=========================================="
    echo "SPORTS HULK CBB REFRESH"
    echo "UTC: $(date -u)"
    echo "=========================================="

    echo
    echo "=== CBB CORE ==="

    "$PY" \
      "$CBB/build_cbb_core.py"

    echo
    echo "=== CBB COMPLETED RESULTS ==="

    "$PY" \
      "$CBB/update_cbb_completed_results.py" \
      || echo "WARNING: CBB result ingestion failed; core preserved."

    echo
    echo "=== CBB GAME MARKETS ==="

    "$PY" \
      "$CBB/build_cbb_markets.py" \
      || echo "WARNING: CBB market refresh failed; core preserved."

    echo
    echo "=== CBB MARKET / RATING FUSION ==="

    "$PY" \
      "$CBB/build_cbb_fusion.py" \
      || echo "WARNING: CBB fusion failed; prior fusion preserved."

    echo
    echo "=== CBB DECISION BRAIN ==="

    "$PY" \
      "$CBB/decision/build_cbb_decision_brain.py" \
      || echo "WARNING: CBB decision brain failed; prior decisions preserved."

    echo
    echo "=== CBB LEARNING / RESULTS ==="

    "$CBB/decision/run_cbb_learning_postrefresh.sh" \
      || echo "WARNING: CBB learning failed; production refresh preserved."

    echo
    echo "CBB REFRESH COMPLETE"

} >> "$LOG" 2>&1
