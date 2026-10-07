import test from 'node:test'
import assert from 'node:assert/strict'
import { survivorFutureValueOptions, survivorSaveForLater } from './survivor_future_value.js'

const candidates = [
  { team: 'Current Week Giant', future_value_index: 10, strategy_index: 90, future_value_label: 'LOW_FUTURE_VALUE' },
  { team: 'Future Team A', future_value_index: 45, strategy_index: 50, future_value_label: 'SAVE_VALUE' },
  { team: 'Future Team B', future_value_index: 35, strategy_index: 60, future_value_label: 'SOME_FUTURE_VALUE' },
]

test('save-for-later chooses highest future value rather than highest current strategy', () => {
  const result = survivorSaveForLater(candidates, [])
  assert.equal(result.status, 'SAVE_VALUE_AVAILABLE')
  assert.equal(result.top.team, 'Future Team A')
  assert.equal(result.top.future_value_index, 45)
})

test('used teams are excluded from preservation research', () => {
  const result = survivorSaveForLater(candidates, ['Future Team A'])
  assert.equal(result.top.team, 'Future Team B')
})

test('future-value options are sorted independently of current-week strategy', () => {
  const rows = survivorFutureValueOptions(candidates, [], 3)
  assert.deepEqual(rows.map(row => row.team), ['Future Team A', 'Future Team B', 'Current Week Giant'])
})

test('zero future value does not create a fake save recommendation', () => {
  const result = survivorSaveForLater([
    { team: 'A', future_value_index: 0, strategy_index: 99 },
    { team: 'B', future_value_index: 0, strategy_index: 50 },
  ], [])
  assert.equal(result.status, 'NO_CLEAR_SAVE_VALUE')
  assert.equal(result.top, null)
})
