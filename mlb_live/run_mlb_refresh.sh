#!/usr/bin/env bash
set -e

ROOT="/home/ubuntu/sports-hulk"
PY="$ROOT/.venv/bin/python"
MLB="$ROOT/mlb_live"
LOGDIR="$MLB/logs"

mkdir -p "$LOGDIR"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$LOGDIR/MLB_REFRESH_$STAMP.log"

{
    echo "=========================================="
    echo "SPORTS HULK MLB REFRESH"
    echo "UTC: $(date -u)"
    echo "=========================================="

    echo
    echo "=== MLB OFFICIAL CORE ==="

    THE_ODDS_API_KEY='' \
    SPORTSGAMEODDS_API_KEY='' \
    SPORTS_LABEL=mlb-core \
    SPORTS_MAX_SECONDS=90 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" "$ROOT/baseball_vault/collect_nightly.py" --days 8 \
      || echo "WARNING: MLB official core refresh failed; prior data preserved."

    echo
    echo "=== MLB MARKETS ==="

    SPORTS_LABEL=mlb-markets \
    SPORTS_MAX_SECONDS=75 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" "$MLB/build_mlb_markets_v2.py" \
      || echo "WARNING: MLB market refresh failed; prior market preserved."

    echo
    echo "=== MLB FUSION ==="

    SPORTS_LABEL=mlb-fusion \
    SPORTS_MAX_SECONDS=90 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" "$MLB/build_mlb_fusion_v2.py" \
      || echo "WARNING: MLB fusion failed; prior fusion preserved."

    echo
    echo "=== MLB DECISION BRAIN ==="

    SPORTS_LABEL=mlb-decision \
    SPORTS_MAX_SECONDS=60 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" "$MLB/decision/build_mlb_decision_brain_v2.py" \
      || echo "WARNING: MLB decision brain failed; prior decisions preserved."

    echo
    echo "=== MLB LEARNING / RESULTS ==="

    "$MLB/decision/run_mlb_learning_postrefresh.sh" \
      || echo "WARNING: MLB learning failed; production refresh preserved."

    echo
    echo "MLB REFRESH COMPLETE"

} >> "$LOG" 2>&1
