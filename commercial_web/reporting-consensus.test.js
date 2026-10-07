import test from 'node:test'
import assert from 'node:assert/strict'
import { reportingConsensus } from './reporting_consensus.js'

test('two independent trusted sources supporting the same claim unlock consensus', () => {
  const result = reportingConsensus([
    {
      event_node_id: 'event-1',
      detail: 'Consensus Runner returned to full practice.',
      source: 'Team Official',
      source_tier: 'OFFICIAL_NEWS',
      source_url: 'https://team.example/runner',
    },
    {
      event_node_id: 'event-2',
      detail: 'Consensus Runner returned to full practice.',
      source: 'Trusted Beat',
      source_tier: 'EXTERNAL_NEWS',
      source_url: 'https://beat.example/runner',
    },
  ], [])

  assert.equal(result.status, 'MULTI_SOURCE_AGREEMENT')
  assert.equal(result.source_count, 2)
  assert.equal(result.claim, 'Consensus Runner returned to full practice.')
  assert.deepEqual(result.evidence_ids, ['event-1', 'event-2'])
})

test('different labels from the same source domain count as one source', () => {
  const result = reportingConsensus([
    {
      event_node_id: 'event-1',
      detail: 'Consensus Runner returned to full practice.',
      source: 'Desk A',
      source_tier: 'EXTERNAL_NEWS',
      source_url: 'https://same.example/a',
    },
    {
      event_node_id: 'event-2',
      detail: 'Consensus Runner returned to full practice.',
      source: 'Desk B',
      source_tier: 'EXTERNAL_NEWS',
      source_url: 'https://same.example/b',
    },
  ], [])

  assert.equal(result.status, 'NO_MULTI_SOURCE_AGREEMENT')
})

test('community evidence cannot unlock trusted multi-source agreement', () => {
  const result = reportingConsensus([
    {
      event_node_id: 'event-1',
      detail: 'Consensus Runner returned to full practice.',
      source: 'Team Official',
      source_tier: 'OFFICIAL_NEWS',
      source_url: 'https://team.example/runner',
    },
    {
      event_node_id: 'event-2',
      detail: 'Consensus Runner returned to full practice.',
      source: 'Community Forum',
      source_tier: 'COMMUNITY',
      source_url: 'https://forum.example/runner',
    },
  ], [])

  assert.equal(result.status, 'NO_MULTI_SOURCE_AGREEMENT')
})

test('different claims about the same subject do not count as agreement', () => {
  const result = reportingConsensus([
    {
      event_node_id: 'event-1',
      detail: 'Consensus Runner was limited at practice.',
      source: 'Team Official',
      source_tier: 'OFFICIAL_NEWS',
      source_url: 'https://team.example/runner',
    },
    {
      event_node_id: 'event-2',
      detail: 'Consensus Runner is expected to play Sunday.',
      source: 'Trusted Beat',
      source_tier: 'EXTERNAL_NEWS',
      source_url: 'https://beat.example/runner',
    },
  ], [])

  assert.equal(result.status, 'NO_MULTI_SOURCE_AGREEMENT')
})
