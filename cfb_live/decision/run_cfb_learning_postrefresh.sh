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

    ARCHIVE_RC=$?
    echo "ARCHIVE RC: $ARCHIVE_RC"

    echo
    echo "=== BOUNDED INCREMENTAL INDEX OF ORIGINAL 8GB+ CFB LEDGER ==="

    if [ "$ARCHIVE_RC" -ne 0 ]; then
        echo "INDEX DEFERRED: ORIGINAL ARCHIVE FAILED, no source history removed"
        DEFERRED=1
    else
        (cd "$ROOT" && "$PY" -m cfb_live.decision.cfb_incremental_ledger_index --max-megabytes 128)
        INDEX_RC=$?
        echo "INDEX RC: $INDEX_RC"
        if [ "$INDEX_RC" -ne 0 ]; then
            echo "GRADE DEFERRED: SOURCE_INDEX_NOT_COMPLETE_OR_SOURCE_VALIDATION_FAILED"
            DEFERRED=1
        fi
    fi

    echo
    echo "=== GRADE / LEARN (ONLY FROM FULLY CAUGHT-UP ORIGINAL SOURCE) ==="
    if [ "$DEFERRED" -eq 0 ]; then
        (cd "$ROOT" && "$PY" -m cfb_live.decision.grade_cfb_recommendations)
        GRADE_RC=$?
        echo "GRADE RC: $GRADE_RC"
        if [ "$GRADE_RC" -ne 0 ]; then
            echo "GRADE DEFERRED: SOURCE_INDEX_OR_GRADER_REJECTED"
            DEFERRED=1
        fi
    else
        echo "GRADE RC: 85 (original source still safe, no unverified learning written)"
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
