import test from 'node:test'
import assert from 'node:assert/strict'
import { buildAskTraceRecord } from './ask_trace.js'

test('trace record stores question hash but never raw question', () => {
  const question = 'What is the injury status of Private Example?'
  const record = buildAskTraceRecord({
    traceId: 'trace-1',
    question,
    context: { page: 'Ask', game_context: { event_id: 'game-1' } },
    routeLane: 'GENERIC',
    sessionResolved: true,
    answer: {
      intent: 'reporting',
      status: 'CURRENT',
      confidence: 'ATTRIBUTED REPORTING',
      sources: [{ source: 'Official' }],
      claim_sources: [{ claim: 'A', source: 'Official' }],
      cards: [{}],
    },
    outputValidation: { valid: true, errors: [] },
    latencyMs: 42,
  })

  assert.equal(record.trace_id, 'trace-1')
  assert.equal(record.route_lane, 'GENERIC')
  assert.equal(record.has_game_context, true)
  assert.equal(record.session_reference_resolved, true)
  assert.equal(record.output_validation_valid, true)
  assert.equal(record.source_count, 1)
  assert.equal(record.claim_source_count, 1)
  assert.ok(record.question_hash)
  assert.equal(Object.prototype.hasOwnProperty.call(record, 'question'), false)
  assert.equal(JSON.stringify(record).includes(question), false)
})

test('error trace records error class without raw error message', () => {
  const error = new Error('secret internal detail')
  const record = buildAskTraceRecord({
    traceId: 'trace-2',
    question: 'Trigger failure',
    error,
    latencyMs: 10,
  })

  assert.equal(record.error, true)
  assert.equal(record.error_name, 'Error')
  assert.equal(record.status, 'ERROR')
  assert.equal(Object.prototype.hasOwnProperty.call(record, 'error_message'), false)
  assert.equal(JSON.stringify(record).includes('secret internal detail'), false)
})
