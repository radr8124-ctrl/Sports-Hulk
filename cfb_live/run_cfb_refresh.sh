#!/usr/bin/env bash
set -e

ROOT="/home/ubuntu/sports-hulk"
PY="$ROOT/.venv/bin/python"
CFB="$ROOT/cfb_live"
LOGDIR="$CFB/logs"

mkdir -p "$LOGDIR"

STAMP=$(
  date -u +%Y%m%dT%H%M%SZ
)

LOG="$LOGDIR/CFB_REFRESH_${STAMP}.log"

{
    echo "=========================================="
    echo "SPORTS HULK CFB REFRESH"
    echo "UTC: $(date -u)"
    echo "=========================================="

    echo
    echo "=== CFB CURRENT CORE ==="

    "$PY" \
      "$CFB/build_cfb_core.py"

    echo
    echo "=== CFB COMPLETED RESULTS ==="

    SPORTS_LABEL=cfb-results \
    SPORTS_MAX_SECONDS=45 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" "$CFB/update_cfb_completed_results.py" \
      || echo "WARNING: CFB result ingestion failed; current core preserved."

    echo
    echo "=== CFB GAME MARKETS ==="

    SPORTS_LABEL=cfb-markets \
    SPORTS_MAX_SECONDS=75 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" "$CFB/build_cfb_markets.py" \
      || echo "WARNING: CFB market refresh failed; prior market preserved."

    echo
    echo "=== CFB MARKET FUSION ==="

    SPORTS_LABEL=cfb-fusion \
    SPORTS_MAX_SECONDS=45 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" "$CFB/build_cfb_fusion.py" \
      || echo "WARNING: CFB fusion failed; prior fusion preserved."

    echo
    echo "=== CFB DECISION BRAIN ==="

    SPORTS_LABEL=cfb-decision \
    SPORTS_MAX_SECONDS=60 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" "$CFB/decision/build_cfb_decision_brain.py" \
      || echo "WARNING: CFB decision brain failed; prior decisions preserved."

    echo
    echo "=== CFB LEARNING / RESULTS ==="

    "$CFB/decision/run_cfb_learning_postrefresh.sh" \
      || echo "WARNING: CFB learning failed; production refresh preserved."

    echo
    echo "CFB REFRESH COMPLETE"

} >> "$LOG" 2>&1
