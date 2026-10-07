import test from 'node:test'
import assert from 'node:assert/strict'
import { claimEvidenceRows } from './src/claimEvidence.js'

test('claim evidence rows dedupe exact repeats and preserve source metadata', () => {
  const rows = claimEvidenceRows([
    {
      claim: 'Player is questionable.',
      source: 'Official Team',
      url: 'https://example.com/a',
      evidence_type: 'FACT',
      evidence_id: 'fact-1',
      updated_at: '2026-10-07T08:00:00Z',
    },
    {
      claim: 'Player is questionable.',
      source: 'Official Team',
      url: 'https://example.com/a',
      evidence_type: 'FACT',
      evidence_id: 'fact-1',
      updated_at: '2026-10-07T08:00:00Z',
    },
  ])

  assert.equal(rows.length, 1)
  assert.equal(rows[0].source, 'Official Team')
  assert.equal(rows[0].evidence_id, 'fact-1')
  assert.equal(rows[0].url, 'https://example.com/a')
})

test('claim evidence rows enforce display limit without dropping order', () => {
  const input = Array.from({ length: 6 }, (_, index) => ({
    claim: `Claim ${index + 1}`,
    source: `Source ${index + 1}`,
    evidence_id: `id-${index + 1}`,
  }))

  const rows = claimEvidenceRows(input, 4)

  assert.equal(rows.length, 4)
  assert.deepEqual(rows.map(row => row.claim), ['Claim 1', 'Claim 2', 'Claim 3', 'Claim 4'])
})

test('invalid rows without claim or source are withheld', () => {
  const rows = claimEvidenceRows([
    { claim: '', source: 'A' },
    { claim: 'Claim', source: '' },
    { claim: 'Valid claim', source: 'Valid source' },
  ])

  assert.deepEqual(rows.map(row => row.claim), ['Valid claim'])
})
