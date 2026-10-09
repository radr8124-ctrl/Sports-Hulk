#!/usr/bin/env bash

set +e

ROOT="/home/ubuntu/sports-hulk"
PY="$ROOT/.venv/bin/python"
DEC="$ROOT/nfl_live/decision"
HIST="$DEC/history"
LOGDIR="$HIST/logs"

mkdir -p "$LOGDIR"

STAMP=$(
  date -u +%Y%m%dT%H%M%SZ
)

LOG="$LOGDIR/NFL_LEARNING_${STAMP}.log"

{
    echo "=========================================="
    echo "SPORTS HULK NFL POST-REFRESH LEARNING"
    echo "UTC: $(date -u)"
    echo "=========================================="

    echo
    echo "=== ARCHIVE CURRENT DECISIONS ==="

    "$PY" \
      "$DEC/archive_nfl_decision_history.py"

    ARCHIVE_RC=$?

    echo
    echo "ARCHIVE RC: $ARCHIVE_RC"


    echo
    echo "=== REFRESH RESULTS / GRADES ==="

    "$PY" \
      "$DEC/grade_nfl_recommendations.py"

    GRADE_RC=$?

    echo
    echo "GRADE RC: $GRADE_RC"


    echo
    echo "=== OUTCOME REVIEW / SIGNAL LEARNING ==="

    "$PY" \
      "$DEC/analyze_nfl_learning.py"

    REVIEW_RC=$?

    echo
    echo "REVIEW RC: $REVIEW_RC"


    echo
    echo "=== SURVIVOR CURRENT-WEEK REFRESH ==="

    SURVIVOR_RC=0

    for script in \
      "$ROOT/nfl_live/build_nfl_current_week.py" \
      "$ROOT/nfl_live/build_nfl_context.py" \
      "$ROOT/nfl_live/build_nfl_weather.py" \
      "$ROOT/nfl_live/build_hulk_survivor_context.py" \
      "$ROOT/nfl_live/build_hulk_survivor_decision.py" \
      "$ROOT/nfl_live/build_survivor_future_value.py" \
      "$ROOT/nfl_live/update_survivor_current_week.py"
    do
        "$PY" "$script"
        STEP_RC=$?

        if [ "$STEP_RC" -ne 0 ]; then
            SURVIVOR_RC=$STEP_RC
            echo "WARNING: Survivor step failed: $script rc=$STEP_RC"
        fi
    done

    echo
    echo "SURVIVOR RC: $SURVIVOR_RC"


    echo
    echo
    echo "=== NFL INDIVIDUAL ESPn VERIFIED FINAL GAME SOURCE FOR FROZEN RESEARCH (NO BETS) ==="

    SPORTS_LABEL=nfl-first-original-final-game-research \
    SPORTS_MAX_SECONDS=25 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" -m intelligence_warehouse.historical_recovery.nfl_forward_individual_final_source --stage collect_original_game_finals \
      || echo "WARNING: NFL independent Final source not available; original verified game results preserved."

    echo
    echo "=== NFL ORIGINAL SAME-QUOTE RAW BOOK VS MARKET VS NINE-FEATURE FINAL SCORE (RESEARCH ONLY) ==="

    SPORTS_LABEL=nfl-first-9feature-market-final-scorer \
    SPORTS_MAX_SECONDS=15 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" -m intelligence_warehouse.historical_recovery.nfl_nine_col_official_scoring \
      || echo "WARNING: NFL independent Final research model comparison failed; original NFL research score preserved."

    echo
    echo "=== NFL FROZEN 70-PERCENT + PRICE-VALUE FORWARD RESEARCH (NO BETS) ==="

    SPORTS_LABEL=nfl-selective70-forward-research \
    SPORTS_MAX_SECONDS=15 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" -m intelligence_warehouse.selective_forward.nfl_70_forward_evidence --stage both \
      || echo "WARNING: NFL research-only selective forward capture/grade did not complete; original frozen forecasts and results preserved."

    echo

    echo "=========================================="
    echo "LEARNING POST-REFRESH COMPLETE"
    echo "Production refresh is never blocked"
    echo "by a learning-layer failure."
    echo "=========================================="

} >> "$LOG" 2>&1


# Deliberately always succeed.
# Learning must never break the live NFL refresh.
exit 0
