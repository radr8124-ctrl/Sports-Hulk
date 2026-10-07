import test from 'node:test'
import assert from 'node:assert/strict'
import { survivorBuybackState } from './survivor_buyback.js'

test('active entry makes buyback not applicable', () => {
  const result = survivorBuybackState({ status: 'ALIVE' }, {})
  assert.equal(result.status, 'NOT_APPLICABLE_ACTIVE_ENTRY')
  assert.equal(result.eligible, false)
})

test('eliminated entry without explicit buyback state remains blocked', () => {
  const result = survivorBuybackState({ status: 'ELIMINATED' }, {})
  assert.equal(result.status, 'NO_VERIFIED_BUYBACK_STATE')
  assert.equal(result.eligible, null)
  assert.equal(result.recorded, false)
})

test('explicit recorded ineligible state remains blocked', () => {
  const result = survivorBuybackState({
    status: 'ELIMINATED',
    buyback: { eligible: false, reason: 'Buyback window closed.' },
  }, {})
  assert.equal(result.status, 'BUYBACK_NOT_ELIGIBLE')
  assert.equal(result.eligible, false)
  assert.equal(result.reason, 'Buyback window closed.')
})

test('explicit eligible state surfaces recorded terms without reactivating entry', () => {
  const result = survivorBuybackState({
    status: 'ELIMINATED',
    buyback: {
      eligible: true,
      deadline: '2026-10-10T20:00:00Z',
      cost: 50,
      reentry_week: 6,
      reset_used_teams: false,
    },
  }, {})
  assert.equal(result.status, 'BUYBACK_ELIGIBLE_RECORDED')
  assert.equal(result.eligible, true)
  assert.equal(result.cost, 50)
  assert.equal(result.reentry_week, 6)
  assert.equal(result.reset_used_teams, false)
})
