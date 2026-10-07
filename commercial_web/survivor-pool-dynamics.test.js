import test from 'node:test'
import assert from 'node:assert/strict'
import { survivorPoolDynamics } from './survivor_pool_dynamics.js'

const week = (n, values = {}) => ({
  [`week_${n}`]: {
    official_pool_sheet_confirmed: true,
    ...values,
  },
})

test('current verified pool counts are marked current', () => {
  const result = survivorPoolDynamics({
    pool_current_week: 5,
    entries: {
      A: {
        ...week(5, {
          pool_entries_start_week5: 500,
          pool_alive_before_sunday: 350,
          pool_lost_before_sunday: 150,
        }),
      },
    },
  })

  assert.equal(result.status, 'CURRENT_VERIFIED')
  assert.equal(result.current, true)
  assert.equal(result.source_week, 5)
  assert.equal(result.survival_pct, 70)
  assert.equal(result.eliminated_pct, 30)
})

test('older official counts remain historical and never become current by inference', () => {
  const result = survivorPoolDynamics({
    pool_current_week: 5,
    entries: {
      A: {
        ...week(3, {
          pool_entries_start_week3: 922,
          pool_alive_before_sunday: 820,
          pool_lost_before_sunday: 102,
        }),
      },
    },
  })

  assert.equal(result.status, 'HISTORICAL_VERIFIED')
  assert.equal(result.current, false)
  assert.equal(result.source_week, 3)
  assert.equal(result.start_entries, 922)
  assert.equal(result.alive_entries, 820)
  assert.equal(result.lost_entries, 102)
  assert.equal(result.survival_pct, 88.9)
  assert.equal(result.eliminated_pct, 11.1)
})

test('conflicting official counts are withheld', () => {
  const result = survivorPoolDynamics({
    pool_current_week: 5,
    entries: {
      A: {
        ...week(4, {
          pool_entries_start_week4: 800,
          pool_alive_before_sunday: 700,
          pool_lost_before_sunday: 100,
        }),
      },
      B: {
        ...week(4, {
          pool_entries_start_week4: 800,
          pool_alive_before_sunday: 690,
          pool_lost_before_sunday: 110,
        }),
      },
    },
  })

  assert.equal(result.status, 'POOL_COUNT_CONFLICT')
  assert.equal(result.alive_entries, null)
})

test('unconfirmed sheets do not create pool dynamics', () => {
  const result = survivorPoolDynamics({
    pool_current_week: 5,
    entries: {
      A: {
        week_5: {
          official_pool_sheet_confirmed: false,
          pool_entries_start_week5: 500,
          pool_alive_before_sunday: 400,
          pool_lost_before_sunday: 100,
        },
      },
    },
  })

  assert.equal(result.status, 'NO_VERIFIED_POOL_COUNTS')
  assert.equal(result.source_week, null)
})
