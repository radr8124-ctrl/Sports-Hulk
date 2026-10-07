#!/usr/bin/env bash
set -e

ROOT="/home/ubuntu/sports-hulk"
PY="$ROOT/.venv/bin/python"
NBA="$ROOT/nba_live"
LOGDIR="$NBA/logs"

mkdir -p "$LOGDIR"

STAMP=$(
  date -u +%Y%m%dT%H%M%SZ
)

LOG="$LOGDIR/NBA_REFRESH_${STAMP}.log"

{
    echo "=========================================="
    echo "SPORTS HULK NBA REFRESH"
    echo "UTC: $(date -u)"
    echo "=========================================="

    echo
    echo "=== CORE GAMES ==="

    "$PY" \
      "$NBA/build_nba_core.py"

    echo
    echo "=== PLAYER / TEAM / INJURY CONTEXT ==="

    "$PY" \
      "$NBA/update_nba_context.py"

    echo
    echo "=== NBA MARKET COLLECTION ==="

    "$PY" \
      "$NBA/build_nba_markets.py" \
      || echo "WARNING: NBA market refresh failed; core NBA refresh preserved."

    echo
    echo "=== NBA CONTEXT / MARKET FUSION ==="

    "$PY" \
      "$NBA/build_nba_fusion.py" \
      || echo "WARNING: NBA fusion failed; previous fusion preserved."

    echo
    echo "=== NBA DECISION BRAIN ==="

    if "$PY" "$NBA/decision/build_nba_decision_brain.py"; then
        echo
        echo "=== EXPLICIT ESPN GAME REGIME VERIFICATION ==="
        "$PY" "$NBA/decision/enrich_nba_competition_regime.py" \
          || echo "WARNING: ESPN regime source unavailable; unlabeled picks remain UNKNOWN."
    else
        echo "WARNING: NBA decision brain failed; previous decisions preserved."
    fi

    echo
    echo "=== NBA LEARNING / RESULTS ==="

    "$NBA/decision/run_nba_learning_postrefresh.sh" \
      || echo "WARNING: NBA learning layer failed; production refresh preserved."

    echo
    echo "NBA REFRESH COMPLETE"

} >> "$LOG" 2>&1
