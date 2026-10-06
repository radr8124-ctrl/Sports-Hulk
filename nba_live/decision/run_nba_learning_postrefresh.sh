#!/usr/bin/env bash

set +e

ROOT="/home/ubuntu/sports-hulk"
PY="$ROOT/.venv/bin/python"
NBA="$ROOT/nba_live"
DEC="$NBA/decision"
LOGDIR="$DEC/history/logs"

mkdir -p "$LOGDIR"

STAMP=$(
  date -u +%Y%m%dT%H%M%SZ
)

LOG="$LOGDIR/NBA_LEARNING_${STAMP}.log"

{
    echo "=========================================="
    echo "SPORTS HULK NBA LEARNING"
    echo "UTC: $(date -u)"
    echo "=========================================="

    echo
    echo "=== ARCHIVE DECISIONS ==="

    "$PY" \
      "$DEC/archive_nba_decisions.py"

    echo "ARCHIVE RC: $?"

    echo
    echo "=== GRADE / LEARN ==="

    "$PY" \
      "$DEC/grade_nba_recommendations.py"

    echo "GRADE RC: $?"

    echo
    echo "NBA LEARNING COMPLETE"

} >> "$LOG" 2>&1


# Learning must never break the production refresh.
exit 0
