import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { FORWARD_PROOF_SCHEMA, forwardProofView, researchRoi, brierDescription, nbaTotalsSourceQualityView } from './src/forwardProofPresentation.js'

const nbaQuality = JSON.parse(readFileSync(new URL('./public/nba_total_source_quality.json', import.meta.url), 'utf8'))
const original = JSON.parse(readFileSync(new URL('./public/forward_proof_current.json', import.meta.url), 'utf8'))
const clock = Date.parse(original.updated_at_utc) + 60_000
const altered = f => { const value=structuredClone(original); f(value); return value }

test('real public scorecard is valid, research-only, and accurately labeled', () => {
  const result = forwardProofView(original, clock)
  assert.equal(result.schema, FORWARD_PROOF_SCHEMA)
  assert.equal(result.game_lines.settled,
    result.game_lines.wins + result.game_lines.losses + result.game_lines.pushes)
  assert.ok(result.game_lines.settled >= 186)
  // The official proof collector continuously adds results. Verify its
  // internal outcome accounting rather than freezing yesterday's count.
  assert.equal(result.props_and_pickem.settled,
    result.props_and_pickem.wins + result.props_and_pickem.losses + result.props_and_pickem.pushes)
  assert.ok(result.props_and_pickem.settled >= 2843)
  assert.ok(result.mlb_full16.completed_independent_game_blocks >= 1) // official collector can complete more blocks
  assert.ok(result.mlb_price_movement.frozen_source_observations >= 29)
  assert.ok(result.mlb_price_movement.graded_official_player_results <= result.mlb_price_movement.frozen_source_observations)
  assert.equal(result.mlb_price_movement.independent_upcoming_games, 2)
  assert.equal(result.nfl_forward.pregame_frozen_games, 13)
  assert.equal(result.nfl_forward.fixed_seventy_pct_plus_value_qualifiers, 0)
  assert.equal(result.truthfulness.paper_roi_not_sportsbook_winnings, true)
  assert.equal(result.game_lines.actual_real_money_roi_proven, false)
})

test('source-book paper ROI formatting is never a claim of executed wagers', () => {
  const result = forwardProofView(original, clock)
  for (const section of [result.game_lines, result.props_and_pickem]) {
    const percent = section.source_book_quoted_paper_roi_pct
    assert.ok(Number.isFinite(percent))
    assert.equal(researchRoi(percent), (percent >= 0 ? '+' : '') + percent.toFixed(2) + '%')
    assert.equal(section.actual_real_money_roi_proven, false)
    assert.equal(section.wins + section.losses + section.pushes, section.settled)
  }
  assert.match(brierDescription(result.props_and_pickem), /Sportsbook Brier is better/)
  assert.match(brierDescription(result.game_lines), /Same as sportsbook baseline/)
  assert.equal(result.proof_status, 'NOT_PROVEN')
})

test('concealed extra win without settlement is rejected, not counted', () => {
  assert.equal(forwardProofView(altered(r => { r.game_lines.wins += 1 }), clock), null)
})

test('false 70 percent profit claim is rejected', () => {
  assert.equal(forwardProofView(altered(r => { r.truthfulness.not_real_wager_profit_or_guaranteed_win_rate = false }), clock), null)
  assert.equal(forwardProofView(altered(r => { r.proof_status = 'PROVEN' }), clock), null)
  assert.equal(forwardProofView(altered(r => { r.game_lines.actual_real_money_roi_proven = true }), clock), null)
})

test('probability-review candidate still clearly lacks real-money proof', () => {
  const projected = altered(r => { r.game_lines.proof_status = 'PROBABILITY_REVIEW_CANDIDATE' })
  const view = forwardProofView(projected, clock)
  assert.equal(view.game_lines.proof_status, 'PROBABILITY_REVIEW_CANDIDATE')
  assert.equal(view.proof_status, 'NOT_PROVEN')
  assert.equal(view.truthfulness.paper_roi_not_sportsbook_winnings, true)
})

test('incorrect source settled hit rate cannot masquerade as higher precision', () => {
  assert.equal(forwardProofView(altered(r => { r.props_and_pickem.hit_rate_pct = 99.9 }), clock), null)
})

test('unverified player outcomes and missing game block counts never become results', () => {
  assert.equal(forwardProofView(altered(r => { r.mlb_price_movement.graded_official_player_results = 90 }), clock), null)
  assert.equal(forwardProofView(altered(r => { r.nfl_forward.source_grade_pending = 0 }), clock), null)
})

test('source proof timestamp in future is rejected', () => {
  assert.equal(forwardProofView(altered(r => { r.updated_at_utc = '2099-01-01T01:00:00Z' }), clock), null)
})

test('stale unchanged source remains visible but prominently labeled', () => {
  const result = forwardProofView(original, clock + 101*60_000)
  assert.equal(result.isStale, true)
})

test('invalid source version and missing trail are blocked', () => {
  assert.equal(forwardProofView(altered(r => { r.schema='UNSAFE' }), clock), null)
  assert.equal(forwardProofView(altered(r => { r.verified_append_only_history_checkpoints = 0 }), clock), null)
})

test('original NBA preseason audit distinguishes raw +4.98 and source-sensitivity -0.69', () => {
  const quality = nbaTotalsSourceQualityView(nbaQuality)
  assert.ok(quality)
  assert.equal(quality.retrospective_original_game_lines.original_quoted_paper_roi_pct,4.98)
  assert.equal(quality.isolated_source_quality_sensitivity.hypothetical_quote_paper_roi_pct,-0.69)
  assert.equal(quality.nba_preseason_audit.duplicate_regime_positions,8)
  assert.equal(quality.nba_preseason_audit.incorrect_original_start_rows_held,7)
  assert.equal(quality.nba_preseason_audit.source_ESPN_start_matched_unique_lines,91)
  assert.equal(quality.nba_preseason_audit.independent_preseason_games,19)
  assert.equal(quality.nba_preseason_audit.model_Brier,quality.nba_preseason_audit.bookmaker_Brier)
  assert.equal(quality.real_money_wagers_or_executable_prices_verified,false)
})

test('source-quality false profit or silent removed losses is rejected', () => {
  const changed = f => { const copy=structuredClone(nbaQuality);f(copy);return copy }
  assert.equal(nbaTotalsSourceQualityView(changed(r => { r.genuine_unseen_NBA_regular_season_profitability_proven=true })),null)
  assert.equal(nbaTotalsSourceQualityView(changed(r => { r.nba_preseason_audit.duplicate_regime_positions=0 })),null)
  assert.equal(nbaTotalsSourceQualityView(changed(r => { r.isolated_source_quality_sensitivity.losses=0 })),null)
  assert.equal(nbaTotalsSourceQualityView(changed(r => { r.real_money_wagers_or_executable_prices_verified=true })),null)
})

test('Brain Record UI fetches source audit and distinguishes sensitivity from true ROI', () => {
  const component=readFileSync(new URL('./src/ForwardProofPanel.jsx',import.meta.url),'utf8')
  assert.match(component,/nba_total_source_quality\.json/)
  assert.match(component,/not a revised official ROI/)
  assert.match(component,/Other sports still need independent audits/)
})

test('current active Brain Record route includes the compact proof panel', () => {
  const app = readFileSync(new URL('./src/App.jsx', import.meta.url), 'utf8')
  const performance = readFileSync(new URL('./src/PerformancePanel.jsx', import.meta.url), 'utf8')
  const component = readFileSync(new URL('./src/ForwardProofPanel.jsx', import.meta.url), 'utf8')
  assert.match(app, /<PerformancePanel\s*\/>/)
  assert.match(performance, /<ForwardProofPanel\s*\/>/)
  assert.ok(performance.indexOf('<OfficialRecord data={data} />') < performance.indexOf('<ForwardProofPanel />'))
  assert.match(component, /forward_proof_current\.json/)
  assert.match(component, /not placed bets|not placed bets|not real wager|not proven|Not proven profitable/i)
})
