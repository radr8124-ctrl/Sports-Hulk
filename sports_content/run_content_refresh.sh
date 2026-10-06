#!/usr/bin/env bash
set -e

ROOT="/home/ubuntu/sports-hulk"
PY="$ROOT/.venv/bin/python"
CONTENT="$ROOT/sports_content"
LOGDIR="$CONTENT/logs"

mkdir -p "$LOGDIR"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$LOGDIR/CONTENT_REFRESH_$STAMP.log"

{
  echo "=========================================="
  echo "SPORTS HULK CONTENT REFRESH"
  echo "UTC: $(date -u)"
  echo "=========================================="

  echo
  echo "=== NEWS + FACT INTELLIGENCE ==="

  SPORTS_LABEL=content-intel SPORTS_MAX_SECONDS=45 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$CONTENT/build_intelligence_feed.py"

  echo
  echo "=== INJURY / AVAILABILITY LIFECYCLE ==="

  SPORTS_LABEL=availability-lifecycle SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/availability/build_availability_lifecycle.py" \
    || echo "WARNING: availability lifecycle refresh failed; prior lifecycle preserved."

  echo
  echo "=== ADVANCED ROLE / TRACKING FEATURES ==="

  SPORTS_LABEL=advanced-feature-store SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/features/build_role_feature_store.py" \
    || echo "WARNING: advanced feature refresh failed; prior feature store preserved."

  echo
  echo "=== TEAM STYLE / COACHING TENDENCIES ==="

  SPORTS_LABEL=team-style-intelligence SPORTS_MAX_SECONDS=45 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/team_style/build_team_style.py" \
    || echo "WARNING: team style refresh failed; prior team style context preserved."

  echo
  echo "=== MATCHUP STYLE INTERACTIONS ==="

  SPORTS_LABEL=matchup-style-intelligence SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/matchup_style/build_matchup_style.py" \
    || echo "WARNING: matchup style refresh failed; prior matchup context preserved."

  echo
  echo "=== FANTASY MARKET / ADD-DROP INTELLIGENCE ==="

  SPORTS_LABEL=fantasy-market SPORTS_MAX_SECONDS=30 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/fantasy_market/build_fantasy_market.py" \
    || echo "WARNING: fantasy market refresh failed; prior fantasy market context preserved."

  SPORTS_LABEL=fantasy-faab SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/fantasy_decisions/build_faab_research.py" \
    || echo "WARNING: fantasy FAAB research failed; prior FAAB board preserved."

  SPORTS_LABEL=fantasy-ir-stash SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/fantasy_decisions/build_ir_stash.py" \
    || echo "WARNING: fantasy IR stash research failed; prior stash board preserved."

  echo
  echo "=== STARTER / LINEUP CONFIRMATION LIFECYCLE ==="

  SPORTS_LABEL=starter-lifecycle SPORTS_MAX_SECONDS=30 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/starters/build_starter_lifecycle.py" \
    || echo "WARNING: starter lifecycle refresh failed; prior starter context preserved."

  echo
  echo "=== PLAYER OPPORTUNITY / MATCHUP PRESSURE ==="

  SPORTS_LABEL=player-opportunity SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/player_opportunity/build_player_opportunity.py" \
    || echo "WARNING: player opportunity refresh failed; prior opportunity context preserved."

  echo
  echo "=== OPPONENT DEFENSIVE / POSITION PRESSURE ==="

  SPORTS_LABEL=defensive-pressure SPORTS_MAX_SECONDS=30 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/defensive_pressure/build_defensive_pressure.py" \
    || echo "WARNING: defensive pressure refresh failed; prior defensive pressure preserved."

  echo
  echo "=== MLB PLAYER-GAME HISTORY / PREGAME FEATURES ==="

  SPORTS_LABEL=mlb-player-history SPORTS_MAX_SECONDS=45 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/mlb_player_history/build_mlb_player_game_history.py" \
    --max-games 1 --sleep 0.02 \
    || echo "WARNING: MLB player history refresh failed; prior player-game history preserved."

  echo
  echo "=== HISTORICAL SIGNAL CALIBRATION / WALK-FORWARD ==="

  SPORTS_LABEL=signal-calibration SPORTS_MAX_SECONDS=120 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/signal_calibration/build_signal_calibration.py" \
    || echo "WARNING: signal calibration refresh failed; prior calibration preserved."

  echo
  echo "=== CALIBRATION EVIDENCE GATES ==="

  SPORTS_LABEL=evidence-gates SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/evidence_gates/build_evidence_gates.py" \
    || echo "WARNING: evidence gate refresh failed; prior evidence gates preserved."

  echo
  echo "=== EVIDENCE-AWARE SIGNAL CONSENSUS / CONFLICTS ==="

  SPORTS_LABEL=signal-consensus SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/signal_consensus/build_signal_consensus.py" \
    || echo "WARNING: signal consensus refresh failed; prior consensus context preserved."

  echo
  echo "=== DECISION READINESS / EVIDENCE ELIGIBILITY ==="

  SPORTS_LABEL=decision-readiness SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/decision_readiness/build_decision_readiness.py" \
    || echo "WARNING: decision readiness refresh failed; prior readiness context preserved."

  echo
  echo "=== PREGAME RESEARCH COHORT SNAPSHOTS ==="

  SPORTS_LABEL=pregame-cohorts SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/pregame_cohorts/build_pregame_cohorts.py" \
    || echo "WARNING: pregame cohort refresh failed; prior cohort snapshots preserved."

  echo
  echo "=== POSTGAME RESEARCH GRADING ==="

  SPORTS_LABEL=postgame-grading SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/postgame_grading/build_postgame_grading.py" \
    || echo "WARNING: postgame grading refresh failed; prior grades preserved."

  echo
  echo "=== COHORT LEARNING / READY VS CONTROL ==="

  SPORTS_LABEL=cohort-learning SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/cohort_learning/build_cohort_learning.py" \
    || echo "WARNING: cohort learning refresh failed; prior learning summary preserved."

  echo
  echo "=== LEARNING GOVERNANCE / CHANGE ELIGIBILITY ==="

  SPORTS_LABEL=learning-governance SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/learning_governance/build_learning_governance.py" \
    || echo "WARNING: learning governance refresh failed; prior governance state preserved."

  echo
  echo "=== DFS SALARY / PROJECTION / VALUE INTELLIGENCE ==="

  SPORTS_LABEL=dfs-contest-intelligence SPORTS_MAX_SECONDS=30 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/dfs/build_dfs_intelligence.py" \
    || echo "WARNING: DFS contest intelligence refresh failed; prior DFS context preserved."

  SPORTS_LABEL=dfs-stack-research SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/dfs/build_dfs_stack_research.py" \
    || echo "WARNING: DFS stack/archetype refresh failed; prior stack research preserved."

  SPORTS_LABEL=dfs-dk-leverage SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/dfs/build_dfs_dk_leverage.py" \
    || echo "WARNING: DFS DraftKings leverage research failed; prior leverage board preserved."

  SPORTS_LABEL=dfs-nfl-lineup-research SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/dfs/build_dfs_nfl_lineup_research.py" \
    || echo "WARNING: DFS NFL lineup research failed; prior lineup research preserved."

  SPORTS_LABEL=dfs-dk-nfl-lineup-research SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/dfs/build_dfs_dk_nfl_lineup_research.py" \
    || echo "WARNING: DFS DraftKings NFL lineup research failed; prior lineup research preserved."

  SPORTS_LABEL=dfs-mlb-nhl-lineup-research SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/dfs/build_dfs_mlb_nhl_lineup_research.py" \
    || echo "WARNING: DFS MLB/NHL lineup research failed; prior lineup research preserved."

  echo
  echo "=== STRUCTURED NEWS / EVENT GRAPH ==="

  SPORTS_LABEL=news-event-graph SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/news_graph/build_news_event_graph.py" \
    || echo "WARNING: news event graph refresh failed; prior graph context preserved."

  echo
  echo "=== SCHEDULE / FATIGUE / ENVIRONMENT ==="

  SPORTS_LABEL=schedule-fatigue-environment SPORTS_MAX_SECONDS=30 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/schedule/build_schedule_intelligence.py" \
    || echo "WARNING: schedule/environment refresh failed; prior schedule context preserved."

  SPORTS_LABEL=fantasy-defense-streaming SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/fantasy_decisions/build_defense_streaming.py" \
    || echo "WARNING: defense streaming research failed; prior defense board preserved."

  SPORTS_LABEL=fantasy-idp SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/fantasy_decisions/build_idp_opportunity.py" \
    || echo "WARNING: IDP usage research failed; prior IDP board preserved."

  SPORTS_LABEL=fantasy-weekly-decisions SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/fantasy_decisions/build_weekly_decisions.py" \
    || echo "WARNING: weekly fantasy decision research failed; prior weekly board preserved."

  SPORTS_LABEL=ask-sports-hulk-context SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/commercial_web/build_ask_context.py" \
    || echo "WARNING: Ask Sports HULK context refresh failed; prior Ask snapshot preserved."

  SPORTS_LABEL=ask-sports-hulk-retrieval SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/commercial_web/build_ask_retrieval.py" \
    || echo "WARNING: Ask Sports HULK retrieval refresh failed; prior retrieval snapshot preserved."

  echo
  echo "=== MARKET LIFECYCLE / CLOSING TRUTH ==="

  SPORTS_LABEL=market-lifecycle SPORTS_MAX_SECONDS=25 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/markets/build_market_lifecycle.py" \
    || echo "WARNING: market lifecycle refresh failed; prior market lifecycle preserved."

  echo
  echo "=== CFB ROSTER CONTINUITY / TRANSFER CONTEXT ==="

  SPORTS_LABEL=cfb-roster-continuity SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/cfb_roster/build_cfb_roster_continuity.py" \
    || echo "WARNING: CFB roster continuity refresh failed; prior roster context preserved."

  echo
  echo "=== CBB POSSESSION / EFFICIENCY ==="

  SPORTS_LABEL=cbb-efficiency SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/cbb_efficiency/build_cbb_efficiency.py" \
    || echo "WARNING: CBB efficiency refresh failed; prior efficiency context preserved."

  echo
  echo "=== HULK ORIGINAL ARTICLE DRAFTS ==="

  SPORTS_LABEL=article-drafts SPORTS_MAX_SECONDS=30 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$CONTENT/build_article_drafts.py"

  echo
  echo "=== ASK SPORTS HULK GROUNDED CONTEXT ==="

  SPORTS_LABEL=ask-sports-hulk-context SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/commercial_web/build_ask_context.py" \
    || echo "WARNING: Ask Sports HULK context refresh failed; prior grounded snapshot preserved."

  echo
  echo "=== SOURCE / FRESHNESS TRUTH ==="

  SPORTS_LABEL=freshness-truth SPORTS_MAX_SECONDS=20 \
    "$ROOT/scripts/sports-safe-run.sh" \
    "$PY" "$ROOT/intelligence_warehouse/freshness/build_freshness_manifest.py" \
    || echo "WARNING: freshness manifest failed; prior health truth preserved."

  echo
  echo "CONTENT REFRESH COMPLETE"

} >> "$LOG" 2>&1
