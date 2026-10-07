import test from 'node:test'
import assert from 'node:assert/strict'
import { faabBudgetLines } from './faab_presentation.js'

test('connected FAAB budget shows remaining balance and translated range', () => {
  const lines = faabBudgetLines({
    connected: true,
    total_budget: 100,
    remaining_budget: 37,
    remaining_pct_of_total: 37,
    research_low_units: 7,
    research_high_units: 13,
    budget_pressure: 'MODERATE_PRESSURE',
  })

  assert.deepEqual(lines, [
    'Saved FAAB remaining 37 of 100 (37% left).',
    'Saved-budget translation 7–13 units · MODERATE PRESSURE.',
  ])
})

test('unconnected FAAB budget produces no personal budget claim', () => {
  assert.deepEqual(faabBudgetLines({ connected: false }), [])
})
