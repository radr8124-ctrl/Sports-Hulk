import test from 'node:test'
import assert from 'node:assert/strict'
import { survivorHomeSummary } from './survivor_home_summary.js'

test('signed-out home summary stays generic', () => {
  const result = survivorHomeSummary({
    signedIn: false,
    genericState: { pool_current_week: 5 },
  })

  assert.equal(result.status, 'SIGN IN')
  assert.equal(result.title, 'Week 5 generic research')
})

test('signed-in account with no linked entry stays no-pool', () => {
  const result = survivorHomeSummary({
    signedIn: true,
    privateState: { entry_linked: false },
  })

  assert.equal(result.status, 'NO POOL')
  assert.equal(result.title, 'No Survivor pool linked')
})

test('single linked entry preserves ready summary behavior', () => {
  const result = survivorHomeSummary({
    signedIn: true,
    privateState: {
      entry_linked: true,
      linked_entry_count: 1,
      rule_confirmed: true,
      active_entry: 'ENTRY A',
      shadow_recommendation: [{ team: 'Dallas Cowboys', market_prob_pct: 80.6 }],
      pool_current_week: 5,
    },
  })

  assert.equal(result.status, 'READY')
  assert.equal(result.title, 'Dallas Cowboys')
  assert.equal(result.detail, 'ENTRY A · 80.6% market survival')
})

test('multi-entry home summary shows diversified allocation', () => {
  const result = survivorHomeSummary({
    signedIn: true,
    privateState: {
      entry_linked: true,
      linked_entry_count: 2,
      pool_current_week: 5,
      diversified_allocations: [
        { entry_name: 'ENTRY A', team: 'Dallas Cowboys' },
        { entry_name: 'ENTRY B', team: 'Kansas City Chiefs' },
      ],
    },
  })

  assert.equal(result.status, 'DIVERSIFIED')
  assert.equal(result.title, '2 entries · diversified plan ready')
  assert.equal(result.detail, 'ENTRY A → Dallas Cowboys · ENTRY B → Kansas City Chiefs')
})

test('multi-entry home summary shows waiting when no allocation is actionable', () => {
  const result = survivorHomeSummary({
    signedIn: true,
    privateState: {
      entry_linked: true,
      linked_entry_count: 2,
      pool_current_week: 5,
      diversified_allocations: [
        { entry_name: 'ENTRY A', status: 'AWAITING_OFFICIAL_POOL_SHEET', team: null },
        { entry_name: 'ENTRY B', status: 'ENTRY_ELIMINATED', team: null },
      ],
    },
  })

  assert.equal(result.status, 'WAITING')
  assert.equal(result.title, 'Week 5 multi-entry plan locked')
  assert.match(result.detail, /ENTRY A: Awaiting Official Pool Sheet/)
})
