#!/usr/bin/env bash

set +e

ROOT="/home/ubuntu/sports-hulk"
PY="$ROOT/.venv/bin/python"
CBB="$ROOT/cbb_live"
DEC="$CBB/decision"
LOGDIR="$DEC/history/logs"

mkdir -p "$LOGDIR"

STAMP=$(
  date -u +%Y%m%dT%H%M%SZ
)

LOG="$LOGDIR/CBB_LEARNING_${STAMP}.log"

{
    echo "=========================================="
    echo "SPORTS HULK CBB LEARNING"
    echo "UTC: $(date -u)"
    echo "=========================================="

    echo
    echo "=== ARCHIVE CURRENT CBB RESEARCH ==="

    "$PY" \
      "$DEC/archive_cbb_decisions.py"

    echo "ARCHIVE RC: $?"

    echo
    echo "=== GRADE / LEARN ==="

    "$PY" \
      "$DEC/grade_cbb_recommendations.py"

    echo "GRADE RC: $?"

    echo
    echo "CBB LEARNING COMPLETE"

} >> "$LOG" 2>&1

# Learning may never break production refresh.
exit 0
