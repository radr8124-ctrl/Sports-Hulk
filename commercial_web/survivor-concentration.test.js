import test from 'node:test'
import assert from 'node:assert/strict'
import { survivorConcentrationAudit } from './survivor_concentration.js'
import { diversifySurvivorEntries } from './survivor_diversification.js'

const activeEntry = (name) => ({
  entry_name: name,
  entry: {
    status: 'ALIVE',
    used_teams: [],
    week_5: { official_pool_sheet_confirmed: true },
  },
})

test('allocator avoids opposite sides of same game when another independent option exists', () => {
  const candidates = [
    { team: 'Team A', opponent: 'Team B', strategy_index: 100, market_prob_pct: 80 },
    { team: 'Team B', opponent: 'Team A', strategy_index: 99, market_prob_pct: 79 },
    { team: 'Team C', opponent: 'Team D', strategy_index: 90, market_prob_pct: 75 },
  ]

  const rows = diversifySurvivorEntries([activeEntry('ENTRY 1'), activeEntry('ENTRY 2')], candidates, 5)

  assert.equal(rows[0].team, 'Team A')
  assert.equal(rows[1].team, 'Team C')
  assert.equal(rows[1].same_game_across_entries, false)
})

test('clear concentration audit reports fully independent allocations', () => {
  const audit = survivorConcentrationAudit([
    { team: 'Team A', opponent: 'Team B' },
    { team: 'Team C', opponent: 'Team D' },
    { team: 'Team E', opponent: 'Team F' },
  ])

  assert.equal(audit.status, 'CLEAR')
  assert.equal(audit.unique_teams, 3)
  assert.equal(audit.same_game_collision_count, 0)
  assert.equal(audit.duplicate_team_count, 0)
  assert.equal(audit.max_team_exposure_pct, 33.3)
})

test('same-game collision is high concentration', () => {
  const audit = survivorConcentrationAudit([
    { team: 'Team A', opponent: 'Team B' },
    { team: 'Team B', opponent: 'Team A' },
  ])

  assert.equal(audit.status, 'HIGH')
  assert.equal(audit.same_game_collision_count, 1)
})

test('forced duplicate team is high concentration', () => {
  const audit = survivorConcentrationAudit([
    { team: 'Team A', opponent: 'Team B' },
    { team: 'Team A', opponent: 'Team B' },
  ])

  assert.equal(audit.status, 'HIGH')
  assert.equal(audit.duplicate_team_count, 1)
  assert.equal(audit.max_team_exposure_pct, 100)
})
