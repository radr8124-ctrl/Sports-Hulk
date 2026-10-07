import test from 'node:test'
import assert from 'node:assert/strict'
import { reportingEvidenceSources, reportingClaimSources } from './reporting_evidence.js'

test('fact evidence is preserved as an exact source', () => {
  const facts = [{
    fact_id: 'fact-1',
    fact_text: 'Fact claim.',
    source: 'Official Feed',
    source_tier: 'OFFICIAL_FACT',
    source_url: 'https://example.com/fact',
    effective_at: '2026-10-07T08:00:00Z',
  }]

  const sources = reportingEvidenceSources([], facts)
  const claims = reportingClaimSources([], facts)

  assert.equal(sources[0].evidence_id, 'fact-1')
  assert.equal(sources[0].url, 'https://example.com/fact')
  assert.equal(claims[0].claim, 'Fact claim.')
  assert.equal(claims[0].evidence_id, 'fact-1')
})

test('event headline and detail both map to the same event evidence', () => {
  const events = [{
    event_node_id: 'event-1',
    title: 'Headline claim',
    detail: 'Supporting detail.',
    source: 'Reporter Feed',
    source_tier: 'EXTERNAL_NEWS',
    source_url: 'https://example.com/event',
    published_or_effective_at: '2026-10-07T08:05:00Z',
  }]

  const claims = reportingClaimSources(events, [])

  assert.deepEqual(claims.map(row => row.claim), ['Headline claim', 'Supporting detail.'])
  assert.ok(claims.every(row => row.evidence_id === 'event-1'))
  assert.ok(claims.every(row => row.url === 'https://example.com/event'))
})
