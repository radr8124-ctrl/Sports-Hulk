#!/usr/bin/env bash

set +e

ROOT="/home/ubuntu/sports-hulk"
PY="$ROOT/.venv/bin/python"
CFB="$ROOT/cfb_live"
DEC="$CFB/decision"
LOGDIR="$DEC/history/logs"

mkdir -p "$LOGDIR"

STAMP=$(
  date -u +%Y%m%dT%H%M%SZ
)

LOG="$LOGDIR/CFB_LEARNING_${STAMP}.log"

{
    echo "=========================================="
    echo "SPORTS HULK CFB LEARNING"
    echo "UTC: $(date -u)"
    echo "=========================================="

    echo
    echo "=== ARCHIVE CURRENT CFB RESEARCH ==="

    "$PY" \
      "$DEC/archive_cfb_decisions.py"

    echo "ARCHIVE RC: $?"

    echo
    echo "=== GRADE / LEARN ==="

    "$PY" \
      "$DEC/grade_cfb_recommendations.py"

    echo "GRADE RC: $?"

    echo
    echo "CFB LEARNING COMPLETE"

} >> "$LOG" 2>&1

# Learning may never break production refresh.
exit 0
