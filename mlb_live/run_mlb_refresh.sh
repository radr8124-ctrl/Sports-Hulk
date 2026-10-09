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
    echo "=== MLB PREGAME PROVENANCE CAPTURE (RESEARCH ONLY) ==="

    SPORTS_LABEL=mlb-pregame-evidence \
    SPORTS_MAX_SECONDS=35 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" -m intelligence_warehouse.mlb_pregame_capture.capture_evidence \
        --lookahead-hours 72 --feed-max-games 4 --weather-max-games 2 \
      || echo "WARNING: pregame evidence capture skipped or failed; prior data preserved."

    echo
    echo "=== MLB OFFICIAL PREKICKOFF V2 RESEARCH (VERIFIED POSTSEASON FORM, NO BETTING) ==="

    SPORTS_LABEL=mlb-asof-research-v2 \
    SPORTS_MAX_SECONDS=35 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" -m intelligence_warehouse.historical_recovery.mlb_live_research_feature_freeze_v2 \
      || echo "WARNING: MLB V2 feature freezing failed; source research prior records preserved; previous V1 frozen history preserved."

    echo

    echo "=== OFFICIAL MLB MASTER STATUS FRESHNESS ==="

    SPORTS_LABEL=mlb-master-status \
    SPORTS_MAX_SECONDS=55 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" "$ROOT/baseball_vault/refresh_mlb_master_status.py" \
        --days-back 8 --days-forward 3 \
      || echo "WARNING: MLB master status freshness held; previous master preserved."

    echo
    echo "=== MLB SOURCE-TIME PROBABLE PITCHER AND PRIOR-2025 PARK RESEARCH (NO BETS) ==="

    SPORTS_LABEL=mlb-probable-pitcher-park-research \
    SPORTS_MAX_SECONDS=45 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" -m intelligence_warehouse.historical_recovery.mlb_pitcher_park_source_asof --stage freeze_research_context \
      || echo "WARNING: pregame pitcher/park verification skipped; older source research preserved."

    echo

    echo "=== MLB PREQUOTE FULL HISTORICAL OPPONENT TEAM/PARK/ROLE RESEARCH CONTEXT (NO BETS) ==="

    SPORTS_LABEL=mlb-v4-full-team-source-context \
    SPORTS_MAX_SECONDS=45 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" -m intelligence_warehouse.historical_recovery.mlb_full_context_source_time --stage freeze_prior_context \
      || echo "WARNING: completed prior full-context research failed; original source-time context records preserved."

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
    echo "=== MLB TRUE PREMATCH PAIRED BOOK PRICE RESEARCH (NO BETS) ==="

    SPORTS_LABEL=mlb-paired-book-source-research \
    SPORTS_MAX_SECONDS=28 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" -m intelligence_warehouse.historical_recovery.mlb_paired_pregame_market_freeze \
      || echo "WARNING: paired market source research failed; previous research book-price evidence preserved."

    echo

    echo "=== MLB FIRST TRUE MARKET-CONTROL SHADOW PROBABILITIES (NO BETS) ==="

    SPORTS_LABEL=mlb-market-only-shadow-model \
    SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" -m intelligence_warehouse.historical_recovery.mlb_shadow_market_control \
      || echo "WARNING: market-only shadow research failed; prior source-time shadow forecasts preserved."

    echo

    echo "=== MLB FROZEN LIMITED SPEED/BAT/WALKS FORWARD SHADOW (RESEARCH, NO BETS) ==="

    SPORTS_LABEL=mlb-restricted-speed-walk-shadow \
    SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" -m intelligence_warehouse.historical_recovery.mlb_restricted_speed_walk_shadow --stage freeze_forecasts \
      || echo "WARNING: restricted prequote advanced research freeze failed; original source-time advanced shadow records preserved."

    echo

    echo "=== MLB FROZEN PREQUOTE FULL SIXTEEN-COLUMN PROSPECTIVE RESEARCH CHALLENGER (NO BETS) ==="

    SPORTS_LABEL=mlb-v4-full-sixteen-shadow \
    SPORTS_MAX_SECONDS=25 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" -m intelligence_warehouse.historical_recovery.mlb_full_context_true_forward_shadow --stage freeze_latest_pregame_quote \
      || echo "WARNING: 16-column model same-book shadow failed; previous context model forecasts preserved."

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
    echo "=== MLB NEW-FUTURE FULL16 70-PERCENT SOURCE-PRICED RESEARCH (NO BETS) ==="

    SPORTS_LABEL=mlb-full16-selective70-future-research \
    SPORTS_MAX_SECONDS=15 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" -m intelligence_warehouse.selective_forward.mlb_70_forward_evidence --stage both \
      || echo "WARNING: MLB selective future-value source research incomplete; original Full16 predictions and grades preserved."

    echo
    echo "=== MLB OFFICIAL SCHEDULE AND NEXT VERIFIED SOURCE READINESS (RESEARCH ONLY) ==="

    SPORTS_LABEL=mlb-official-fixture-readiness \
    SPORTS_MAX_SECONDS=16 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" -m intelligence_warehouse.mlb_pregame_capture.build_forward_readiness \
      || echo "WARNING: independent source readiness check failed; original master, source and forecasts preserved."

    echo
    echo "=== MLB EXACT OFFICIAL GAME VERSUS SAME-BOOK PLAYER HITS QUOTES (RESEARCH ONLY) ==="

    SPORTS_LABEL=mlb-source-book-official-alignment-audit \
    SPORTS_MAX_SECONDS=12 \
    "$ROOT/scripts/sports-safe-run.sh" \
      "$PY" -m intelligence_warehouse.mlb_pregame_capture.audit_upcoming_market_alignment \
      || echo "WARNING: MLB source-book fixture alignment could not be verified; original odds, context and games preserved."

    echo
    echo "MLB REFRESH COMPLETE"

} >> "$LOG" 2>&1
