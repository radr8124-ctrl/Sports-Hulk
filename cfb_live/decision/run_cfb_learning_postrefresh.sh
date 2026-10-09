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
DEFERRED=0

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

    # Grader currently reads the entire immutable ledger into pandas.
    # An oversize source must not OOM-kill other sports refreshes.
    LEDGER_BYTES=$(stat -c%s "$DEC/history/CFB_RECOMMENDATION_LEDGER.csv" 2>/dev/null || echo 0)
    if [ "$LEDGER_BYTES" -gt 536870912 ]; then
        echo "GRADE DEFERRED: OVERSIZE_SOURCE_LEDGER bytes=$LEDGER_BYTES"
        echo "GRADE RC: 85 (incremental grader required; no prior data removed)"
        DEFERRED=1
    else
        "$PY" \
          "$DEC/grade_cfb_recommendations.py"
        echo "GRADE RC: $?"
    fi

    echo
    if [ "$DEFERRED" -eq 1 ]; then
        echo "CFB LEARNING INCOMPLETE: grading deferred; original evidence retained"
    else
        echo "CFB LEARNING COMPLETE"
    fi

} >> "$LOG" 2>&1

if [ "$DEFERRED" -eq 1 ]; then
    echo "WARNING: CFB grading deferred because its original history exceeds the safe full-load limit."
    exit 85
fi

# Learning may never break production refresh.
exit 0
