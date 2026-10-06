#!/usr/bin/env bash

set +e

ROOT="/home/ubuntu/sports-hulk"
PY="$ROOT/.venv/bin/python"
NHL="$ROOT/nhl_live"
DEC="$NHL/decision"
LOGDIR="$DEC/history/logs"

mkdir -p "$LOGDIR"

STAMP=$(
  date -u +%Y%m%dT%H%M%SZ
)

LOG="$LOGDIR/NHL_LEARNING_${STAMP}.log"

{
    echo "=========================================="
    echo "SPORTS HULK NHL LEARNING"
    echo "UTC: $(date -u)"
    echo "=========================================="

    echo
    echo "=== ARCHIVE RECOMMENDATIONS ==="

    "$PY" \
      "$DEC/archive_nhl_decisions.py"

    echo "ARCHIVE RC: $?"

    echo
    echo "=== GRADE / LEARN ==="

    "$PY" \
      "$DEC/grade_nhl_recommendations.py"

    echo "GRADE RC: $?"

    echo
    echo "NHL LEARNING COMPLETE"

} >> "$LOG" 2>&1

# Learning can never break production refresh.
exit 0
