import test from 'node:test'
import assert from 'node:assert/strict'

import { allMarketsProofRows } from './src/allMarketsProofRows.js'

test('regime-aware payload uses proof lanes and never duplicates aggregate NBA lane', () => {
  const rows = allMarketsProofRows({
    current: {
      by_lane: {
        NBA_TOTAL: { candidates: 1, history_n: 1 },
      },
      by_proof_lane: {
        'NBA_TOTAL|PRESEASON': {
          lane_key: 'NBA_TOTAL',
          competition_regime: 'PRESEASON',
          candidates: 0,
          history_n: 1,
        },
        'NBA_TOTAL|REGULAR': {
          lane_key: 'NBA_TOTAL',
          competition_regime: 'REGULAR',
          candidates: 1,
          history_n: 0,
          probability_source: 'MARKET_REFERENCE_INSUFFICIENT_HISTORY',
        },
      },
    },
    validation: {
      lanes: {
        'NBA_TOTAL|PRESEASON': {
          lane_key: 'NBA_TOTAL',
          competition_regime: 'PRESEASON',
          history_n: 1,
        },
      },
    },
    forward: {
      by_lane: {
        NBA_TOTAL: {
          all_predictions: { tracked: 50 },
          promotion: { recommendation: 'AGGREGATE_DO_NOT_USE' },
        },
      },
      by_proof_lane: {
        'NBA_TOTAL|PRESEASON': {
          all_predictions: { tracked: 1 },
          promotion: { recommendation: 'HOLD_PRESEASON' },
        },
        'NBA_TOTAL|REGULAR': {
          all_predictions: { tracked: 0 },
          promotion: { recommendation: 'BUILDING_REGULAR' },
        },
      },
    },
  })

  assert.deepEqual(rows.map(row => row.key), [
    'NBA_TOTAL|PRESEASON',
    'NBA_TOTAL|REGULAR',
  ])
  assert.equal(rows.some(row => row.key === 'NBA_TOTAL'), false)

  const regular = rows.find(row => row.key === 'NBA_TOTAL|REGULAR')
  assert.equal(regular.laneKey, 'NBA_TOTAL')
  assert.equal(regular.competitionRegime, 'REGULAR')
  assert.equal(regular.live.candidates, 1)
  assert.equal(regular.live.history_n, 0)
  assert.equal(regular.forward.promotion.recommendation, 'BUILDING_REGULAR')
})

test('legacy payload falls back to by_lane when proof-lane views are absent', () => {
  const rows = allMarketsProofRows({
    current: {
      by_lane: {
        CFB_TOTAL: { candidates: 2, history_n: 20 },
      },
    },
    validation: {
      lanes: {
        CFB_TOTAL: { history_n: 20 },
      },
    },
    forward: {
      by_lane: {
        CFB_TOTAL: {
          all_predictions: { tracked: 3 },
          promotion: { recommendation: 'BUILDING_FORWARD_PROOF' },
        },
      },
    },
  })

  assert.deepEqual(rows.map(row => row.key), ['CFB_TOTAL'])
  assert.equal(rows[0].laneKey, 'CFB_TOTAL')
  assert.equal(rows[0].competitionRegime, null)
  assert.equal(rows[0].live.candidates, 2)
  assert.equal(rows[0].forward.all_predictions.tracked, 3)
})
