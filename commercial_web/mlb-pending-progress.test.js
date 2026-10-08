import test from 'node:test'
import assert from 'node:assert/strict'
import { mlbPendingProgress } from './src/mlbPendingProgress.js'

function brain({
  pending = 434,
  sourceStatus = 'SOURCE_RECONCILED',
  sourcePending = 434,
  breakdown = {},
} = {}) {
  const props = {
    entries: 2524, settled: 2090,
    wins: 1467, losses: 623, pushes: 0, pending,
    pending_overdue_12h: 35,
  }
  if (pending !== 434) props.entries = 2090 + pending
  return {
    forward_results_accountability: {
      by_sport: { MLB: { PROPS: props } },
      mlb_official_pending_breakdown: {
        status: sourceStatus,
        pending_total: sourcePending, settled_total: 2090,
        official_receipt_generated_at: '2026-10-08T00:38:03Z',
        awaiting_official_final: 394,
        unverified_player_participation: 37,
        unverified_pregame_capture: 3,
        other_source_holds: 0,
        verified_ready_next_batch: 0,
        ...breakdown,
      },
    },
  }
}

test('shows exact frozen MLB forward results and officially corroborated hold buckets', () => {
  const data = mlbPendingProgress(brain())
  assert.deepEqual(
    [data.tracked, data.settled, data.wins, data.losses, data.pending],
    [2524, 2090, 1467, 623, 434],
  )
  assert.equal(data.sourceValid, true)
  assert.equal(data.awaitingFinal, 394)
  assert.equal(data.participationHold, 37)
  assert.equal(data.pregameHold, 3)
  assert.equal(data.readyToGrade, 0)
  assert.equal(data.overdue, 35)
})

test('hides cause counts on stale source receipt but retains frozen ledger totals', () => {
  const data = mlbPendingProgress(brain({ sourceStatus: 'STALE_OFFICIAL_RECEIPT' }))
  assert.equal(data.pending, 434)
  assert.equal(data.sourceValid, false)
  assert.equal(data.awaitingFinal, null)
  assert.equal(data.participationHold, null)
  assert.equal(data.sourceStatus, 'STALE_OFFICIAL_RECEIPT')
})

test('hides causes when source receipt cannot account for every frozen pending pick', () => {
  const data = mlbPendingProgress(brain({ breakdown: { awaiting_official_final: 393 } }))
  assert.equal(data.sourceValid, false)
  assert.equal(data.awaitingFinal, null)
})

test('hides source buckets when new frozen predictions have not reached official grade receipt', () => {
  const data = mlbPendingProgress(brain({ pending: 435, sourcePending: 434 }))
  assert.equal(data.sourceValid, false)
  assert.equal(data.pending, 435)
})

test('accepts a nonzero verified-gradeable queue only when all reasons reconcile', () => {
  const data = mlbPendingProgress(brain({
    breakdown: { awaiting_official_final: 294, verified_ready_next_batch: 100 },
  }))
  assert.equal(data.sourceValid, true)
  assert.equal(data.readyToGrade, 100)
})

test('never constructs an MLB record from a missing or inconsistent ledger', () => {
  assert.equal(mlbPendingProgress({}), null)
  assert.equal(mlbPendingProgress(null), null)
  const malformed = brain()
  malformed.forward_results_accountability.by_sport.MLB.PROPS.wins = 1468
  assert.equal(mlbPendingProgress(malformed), null)
})

test('never leaks source reason counts for an invalid or negative league receipt', () => {
  const data = mlbPendingProgress(brain({
    breakdown: { unverified_player_participation: -1 },
  }))
  assert.equal(data.sourceValid, false)
  assert.equal(data.participationHold, null)
})
