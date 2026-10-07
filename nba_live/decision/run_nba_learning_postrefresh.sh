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

    GRADE_RC=$?
    echo "GRADE RC: $GRADE_RC"

    # Audits label missing/source-conflicting results and warns if the hourly
    # Betting V2 validation was generated before today's newly graded games.
    # No model is promoted by this audit and grade failures are never masked.
    if [ "$GRADE_RC" -eq 0 ]; then
        echo
        echo "=== NBA HISTORICAL PROOF INTEGRITY ==="
        "$PY" "$DEC/audit_nba_historical_proof.py"
        echo "PROOF AUDIT RC: $?"
    else
        echo "PROOF AUDIT SKIPPED: grader failed; preserve previous receipt."
    fi

    echo
    echo "NBA LEARNING COMPLETE"

} >> "$LOG" 2>&1


# Learning must never break the production refresh.
exit 0
