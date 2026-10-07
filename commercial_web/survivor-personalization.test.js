import test from 'node:test'
import assert from 'node:assert/strict'
import { buildPersonalizedSurvivorSource } from './survivor_personalization.js'

test('confirmed active entry carries personal used teams and clears the rule gate', () => {
  const result = buildPersonalizedSurvivorSource(
    'ENTRY 01',
    {
      status: 'ALIVE',
      used_teams: ['Team A', 'Team B'],
      week_5: {
        official_pool_sheet_confirmed: true,
        rule_status: 'CONFIRMED_FROM_IMPORTED_POOL_HEADER',
      },
    },
    { pool_current_week: 5 },
    { candidates: [{ team: 'Team C' }], recommendation_status: 'PERSONAL_CONTEXT_REQUIRED' },
  )

  assert.equal(result.active_entry, 'ENTRY 01')
  assert.deepEqual(result.used_teams, ['Team A', 'Team B'])
  assert.equal(result.rule_confirmed, true)
  assert.equal(result.recommendation_status, 'PERSONALIZED_READY')
  assert.equal(result.ownership.status, 'LINKED_ENTRY_RULE_CONFIRMED')
})

test('eliminated linked entry stays blocked', () => {
  const result = buildPersonalizedSurvivorSource(
    'ENTRY 02',
    {
      status: 'ELIMINATED',
      used_teams: ['Team A'],
      week_5: { official_pool_sheet_confirmed: true },
    },
    { pool_current_week: 5 },
    {},
  )

  assert.equal(result.active_entry_status, 'ELIMINATED')
  assert.equal(result.recommendation_status, 'ENTRY_ELIMINATED')
})

test('active entry without current official rule stays waiting', () => {
  const result = buildPersonalizedSurvivorSource(
    'ENTRY 03',
    {
      status: 'ALIVE',
      used_teams: ['Team A'],
      week_5: {
        official_pool_sheet_confirmed: false,
        rule_status: 'AWAITING_OFFICIAL_POOL_SHEET',
      },
    },
    { pool_current_week: 5 },
    {},
  )

  assert.equal(result.rule_confirmed, false)
  assert.equal(result.rule_status, 'AWAITING_OFFICIAL_POOL_SHEET')
  assert.equal(result.recommendation_status, 'PERSONAL_CONTEXT_WAITING')
  assert.equal(result.ownership.official_pool_week, null)
})
