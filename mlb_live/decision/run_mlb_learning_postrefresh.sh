#!/usr/bin/env bash
set +e

ROOT="/home/ubuntu/sports-hulk"
PY="$ROOT/.venv/bin/python"
DEC="$ROOT/mlb_live/decision"

SPORTS_LABEL=mlb-results \
SPORTS_MAX_SECONDS=45 \
"$ROOT/scripts/sports-safe-run.sh" \
  "$PY" "$ROOT/baseball_vault/result_refresh.py"

SPORTS_LABEL=mlb-archive \
SPORTS_MAX_SECONDS=30 \
"$ROOT/scripts/sports-safe-run.sh" \
  "$PY" "$DEC/archive_mlb_decisions.py"

SPORTS_LABEL=mlb-grade \
SPORTS_MAX_SECONDS=60 \
"$ROOT/scripts/sports-safe-run.sh" \
  "$PY" "$DEC/grade_mlb_recommendations.py"

SPORTS_LABEL=mlb-prop-grade-context \
SPORTS_MAX_SECONDS=20 \
"$ROOT/scripts/sports-safe-run.sh" \
  "$PY" "$ROOT/intelligence_warehouse/mlb_player_history/build_prop_grade_context.py"

exit 0
