// Pure public view contract. Only server-whitelisted aggregates may render.
// Never mistake paper ROI, correlated props or research shadow for actual bets.
export const FORWARD_PROOF_SCHEMA = 'ZENITH_RESEARCH_ONLY_PUBLIC_FORWARD_PROOF_V1'

const finite = value => typeof value === 'number' && Number.isFinite(value)
const integer = value => Number.isSafeInteger(value) && value >= 0

function validLane(lane) {
  if (!lane || typeof lane !== 'object') return false
  const numbers = ['wins', 'losses', 'pushes', 'settled', 'independent_game_blocks']
  if (!numbers.every(key => integer(lane[key]))) return false
  if (lane.wins + lane.losses + lane.pushes !== lane.settled) return false
  if (!finite(lane.hit_rate_pct) || lane.hit_rate_pct < 0 || lane.hit_rate_pct > 100) return false
  const decisions = lane.wins + lane.losses
  if (decisions > 0 && Math.abs(lane.hit_rate_pct - 100 * lane.wins / decisions) > 0.11) return false
  if (decisions === 0 && lane.hit_rate_pct !== 0) return false
  if (lane.source_book_quoted_paper_roi_pct !== null && !finite(lane.source_book_quoted_paper_roi_pct)) return false
  for (const name of ['source_market_brier', 'model_brier']) {
    if (!finite(lane[name]) || lane[name] < 0 || lane[name] > 1) return false
  }
  if (lane.actual_real_money_roi_proven !== false) return false
  // A probability-review label is not proof of actual sportsbook profit.
  return ['NOT_PROVEN', 'BUILDING_FORWARD_SAMPLE', 'PROMISING_NOT_PROVEN',
    'PROBABILITY_REVIEW_CANDIDATE', 'REVIEW_CANDIDATE'].includes(lane.proof_status)
}

export function forwardProofView(payload, nowMs = Date.now()) {
  if (!payload || typeof payload !== 'object') return null
  if (payload.schema !== FORWARD_PROOF_SCHEMA || payload.research_only !== true ||
      payload.proof_status !== 'NOT_PROVEN' ||
      payload.truthfulness?.paper_roi_not_sportsbook_winnings !== true ||
      payload.truthfulness?.automatic_model_promotion_allowed !== false ||
      payload.truthfulness?.not_real_wager_profit_or_guaranteed_win_rate !== true ||
      !integer(payload.verified_append_only_history_checkpoints) ||
      payload.verified_append_only_history_checkpoints === 0 ||
      !/^[0-9a-f]{16}$/.test(payload.source_receipt_hash_prefix || '')) return null
  if (!validLane(payload.game_lines) || !validLane(payload.props_and_pickem)) return null
  const mlb = payload.mlb_full16
  const movement = payload.mlb_price_movement
  const nfl = payload.nfl_forward
  const cfb = payload.cfb_research
  if (!mlb || !movement || !nfl || !cfb) return null
  if (!integer(mlb.completed_independent_game_blocks) ||
      !integer(mlb.same_game_player_predictions) ||
      mlb.improvement_statistically_proven !== false) return null
  if (!integer(movement.frozen_source_observations) ||
      !integer(movement.independent_upcoming_games) ||
      !integer(movement.graded_official_player_results) ||
      !integer(movement.waiting_for_official_player_bridge) ||
      movement.graded_official_player_results + movement.waiting_for_official_player_bridge > movement.frozen_source_observations ||
      movement.research_price_signal_proven !== false) return null
  if (![nfl.pregame_frozen_games, nfl.source_grade_pending, nfl.official_game_results,
         nfl.fixed_seventy_pct_plus_value_qualifiers].every(integer) ||
      nfl.source_grade_pending + nfl.official_game_results !== nfl.pregame_frozen_games ||
      nfl.profitable_betting_strategy_proven !== false) return null
  if (!integer(cfb.latest_distinct_recommendations) ||
      !integer(cfb.historically_settled_research_grades) ||
      cfb.historically_settled_research_grades > cfb.latest_distinct_recommendations ||
      cfb.not_executable_real_money_bets !== true) return null
  const at = Date.parse(payload.updated_at_utc)
  if (!Number.isFinite(at) || at > nowMs + 5 * 60_000) return null
  return {
    ...payload,
    snapshotAgeMinutes: Math.max(0, Math.round((nowMs - at) / 60_000)),
    isStale: nowMs - at > 95 * 60_000,
  }
}

export function researchRoi(value) {
  if (!finite(value)) return 'Waiting'
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
}

export function brierDescription(lane) {
  if (!lane || !finite(lane.model_brier) || !finite(lane.source_market_brier)) return 'Awaiting paired model/market probabilities'
  if (Math.abs(lane.model_brier - lane.source_market_brier) < 0.000005) return 'Same as sportsbook baseline at current precision'
  if (lane.model_brier < lane.source_market_brier) return 'Model Brier lower than sportsbook; advantage not proven'
  return 'Sportsbook Brier is better than model'
}

export const NBA_QUALITY_SCHEMA = 'ZENITH_NBA_TOTAL_SOURCE_QUALITY_SENSITIVITY_PUBLIC_V1'

export function nbaTotalsSourceQualityView(raw) {
  if (!raw || typeof raw !== 'object' ||
      raw.schema !== NBA_QUALITY_SCHEMA ||
      raw.audited_original_snapshot_only !== true ||
      raw.real_money_wagers_or_executable_prices_verified !== false ||
      raw.source_frozen_model_or_grade_ledger_mutated !== false ||
      raw.genuine_unseen_NBA_regular_season_profitability_proven !== false ||
      !/^[0-9a-f]{16}$/.test(raw.audit_sha256_prefix || '')) return null

  const original = raw.retrospective_original_game_lines
  const adjusted = raw.isolated_source_quality_sensitivity
  const nba = raw.nba_preseason_audit
  if (!original || !adjusted || !nba ||
      !integer(original.priced_line_observations) ||
      !integer(original.wins) || !integer(original.losses) ||
      original.wins + original.losses !== original.priced_line_observations ||
      !finite(original.original_quoted_paper_roi_pct) ||
      !integer(adjusted.quote_observations) ||
      !integer(adjusted.wins) || !integer(adjusted.losses) ||
      adjusted.wins + adjusted.losses !== adjusted.quote_observations ||
      adjusted.quote_observations >= original.priced_line_observations ||
      adjusted.not_official_restatement_of_all_sports !== true ||
      adjusted.all_other_sport_market_lanes_not_yet_source_graded !== true ||
      !finite(adjusted.hypothetical_quote_paper_roi_pct) ||
      !integer(nba.duplicate_regime_positions) ||
      !integer(nba.incorrect_original_start_rows_held) ||
      !integer(nba.source_ESPN_start_matched_unique_lines) ||
      !integer(nba.independent_preseason_games) ||
      nba.independent_preseason_games === 0 ||
      nba.source_ESPN_start_matched_unique_lines >= nba.original_total_line_records ||
      nba.original_total_line_records - nba.source_ESPN_start_matched_unique_lines !==
        nba.duplicate_regime_positions + nba.incorrect_original_start_rows_held ||
      nba.held_source_start_difference_minutes !== 15 ||
      !finite(nba.model_Brier) || !finite(nba.bookmaker_Brier) ||
      nba.model_probability_edge_proven !== false ||
      !Array.isArray(nba.game_cluster_95pct_quote_paper_roi_interval_pct) ||
      nba.game_cluster_95pct_quote_paper_roi_interval_pct.length !== 2 ||
      !nba.game_cluster_95pct_quote_paper_roi_interval_pct.every(finite)) return null

  return raw
}
