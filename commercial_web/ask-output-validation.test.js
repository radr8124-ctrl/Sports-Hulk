import test from 'node:test'
import assert from 'node:assert/strict'
import { validateAskOutput, outputValidationFallback } from './ask_output_validation.js'

function base(overrides = {}) {
  return {
    intent: 'reporting',
    take: 'Current verified report.',
    confidence: 'ATTRIBUTED REPORTING',
    status: 'CURRENT',
    why: ['Verified detail.'],
    risk: ['Can change with new reporting.'],
    sources: [{ source: 'Official', url: 'https://example.com/report' }],
    cards: [],
    followups: [],
    ...overrides,
  }
}

test('valid Ask output passes final contract', () => {
  const result = validateAskOutput(base())
  assert.equal(result.valid, true)
  assert.deepEqual(result.errors, [])
})

test('unsafe source URL is rejected', () => {
  const result = validateAskOutput(base({
    sources: [{ source: 'Bad Source', url: 'javascript:alert(1)' }],
  }))
  assert.equal(result.valid, false)
  assert.ok(result.errors.includes('unsafe_source_url'))
})

test('stale status must use stale reporting intent and confidence', () => {
  const result = validateAskOutput(base({
    intent: 'reporting',
    status: 'STALE_SOURCE',
    confidence: 'HIGH',
  }))
  assert.equal(result.valid, false)
  assert.ok(result.errors.includes('stale_intent_mismatch'))
  assert.ok(result.errors.includes('stale_confidence_mismatch'))
})

test('current reporting requires at least one source', () => {
  const result = validateAskOutput(base({ sources: [] }))
  assert.equal(result.valid, false)
  assert.ok(result.errors.includes('current_reporting_without_source'))
})

test('validation fallback is a safe complete Ask response', () => {
  const fallback = outputValidationFallback(['unsafe_source_url'])
  const result = validateAskOutput(fallback)
  assert.equal(result.valid, true)
  assert.equal(fallback.status, 'OUTPUT_VALIDATION_FAILED')
  assert.equal(fallback.intent, 'output_guardrail')
  assert.deepEqual(fallback.sources, [])
})
