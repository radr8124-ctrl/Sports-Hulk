import test from 'node:test'
import assert from 'node:assert/strict'
import { askClaimCoverage } from './ask_claim_coverage.js'

test('fully mapped reporting answer has 100 percent claim evidence coverage', () => {
  const result = askClaimCoverage({
    intent: 'reporting',
    take: 'Headline claim.',
    why: ['Supporting fact.'],
    claim_sources: [
      { claim: 'Headline claim.', evidence_id: 'event-1' },
      { claim: 'Supporting fact.', evidence_id: 'fact-1' },
    ],
  })

  assert.equal(result.eligible, true)
  assert.equal(result.claim_count, 2)
  assert.equal(result.supported_claim_count, 2)
  assert.equal(result.unsupported_claim_count, 0)
  assert.equal(result.claim_evidence_coverage_pct, 100)
})

test('unmapped reporting claim is counted as unsupported', () => {
  const result = askClaimCoverage({
    intent: 'reporting',
    take: 'Headline claim.',
    why: ['Supported detail.', 'Unsupported interpretation.'],
    claim_sources: [
      { claim: 'Headline claim.', evidence_id: 'event-1' },
      { claim: 'Supported detail.', evidence_id: 'event-1' },
    ],
  })

  assert.equal(result.claim_count, 3)
  assert.equal(result.supported_claim_count, 2)
  assert.equal(result.unsupported_claim_count, 1)
  assert.equal(result.claim_evidence_coverage_pct, 66.7)
})

test('non-reporting answers are excluded from reporting claim coverage', () => {
  const result = askClaimCoverage({
    intent: 'survivor',
    take: 'Research take.',
    why: ['Model rationale.'],
  })

  assert.equal(result.eligible, false)
  assert.equal(result.claim_count, 0)
  assert.equal(result.claim_evidence_coverage_pct, null)
})
