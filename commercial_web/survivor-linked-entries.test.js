import test from 'node:test'
import assert from 'node:assert/strict'
import { buildLinkedSurvivorSummaries, selectLinkedSurvivorEntry } from './survivor_linked_entries.js'

test('multiple linked entries preserve separate status and used-team counts', () => {
  const result = buildLinkedSurvivorSummaries(
    ['ENTRY A', 'ENTRY B', 'ENTRY A'],
    {
      pool_current_week: 5,
      entries: {
        'ENTRY A': { status: 'ALIVE', used_teams: ['A', 'B', 'C'] },
        'ENTRY B': { status: 'ELIMINATED', used_teams: ['D', 'E'] },
      },
    },
  )

  assert.equal(result.length, 2)
  assert.deepEqual(result[0], {
    entry_name: 'ENTRY A',
    entry_status: 'ALIVE',
    used_team_count: 3,
    used_teams: ['A', 'B', 'C'],
    current_picks: [],
    current_week: 5,
  })
  assert.deepEqual(result[1], {
    entry_name: 'ENTRY B',
    entry_status: 'ELIMINATED',
    used_team_count: 2,
    used_teams: ['D', 'E'],
    current_picks: [],
    current_week: 5,
  })
})

test('missing linked entry state stays non-invented', () => {
  const result = buildLinkedSurvivorSummaries(['UNKNOWN ENTRY'], { pool_current_week: 5, entries: {} })
  assert.deepEqual(result, [{
    entry_name: 'UNKNOWN ENTRY',
    entry_status: null,
    used_team_count: 0,
    used_teams: [],
    current_picks: [],
    current_week: 5,
  }])
})


test('entry selector permits linked entry and falls back for unlinked requests', () => {
  const linked = ['ENTRY A', 'ENTRY B']

  assert.equal(selectLinkedSurvivorEntry(linked, 'ENTRY B'), 'ENTRY B')
  assert.equal(selectLinkedSurvivorEntry(linked, 'NOT MINE'), 'ENTRY A')
  assert.equal(selectLinkedSurvivorEntry([], 'ENTRY A'), null)
})
