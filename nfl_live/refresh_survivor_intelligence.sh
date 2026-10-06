#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/home/ubuntu/sports-hulk"
PY="$ROOT/.venv/bin/python"

cd "$ROOT"

echo "=== SURVIVOR ENTRY RESULTS ==="
"$PY" nfl_live/update_survivor_entry_results.py

echo
echo "=== GOVERNED SURVIVOR BOARD ==="
"$PY" nfl_live/build_survivor_board_from_decisions.py

echo
echo "=== SURVIVOR GAME CONTEXT ==="
"$PY" nfl_live/build_nfl_context.py

echo
echo "=== SURVIVOR WEATHER ==="
"$PY" nfl_live/build_nfl_weather.py

echo
echo "=== SURVIVOR CONTEXT SCORE ==="
"$PY" nfl_live/build_hulk_survivor_context.py

echo
echo "=== SURVIVOR DECISION BOARD ==="
"$PY" nfl_live/build_hulk_survivor_decision.py

echo
echo "=== SURVIVOR FUTURE VALUE ==="
"$PY" nfl_live/build_survivor_future_value.py

echo
echo "RESULT: SURVIVOR_INTELLIGENCE_READY"
