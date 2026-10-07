import test from 'node:test'
import assert from 'node:assert/strict'
import { diversifySurvivorEntries } from './survivor_diversification.js'

const candidates = [
  { team: 'Dallas Cowboys', opponent: 'TB', strategy_index: 90, market_prob_pct: 80, decision_tier: 'VIABLE' },
  { team: 'Kansas City Chiefs', opponent: 'LV', strategy_index: 85, market_prob_pct: 77, decision_tier: 'VIABLE' },
  { team: 'Buffalo Bills', opponent: 'MIA', strategy_index: 82, market_prob_pct: 75, decision_tier: 'VIABLE' },
]

test('two alive entries diversify away from duplicate team exposure when alternatives exist', () => {
  const allocations = diversifySurvivorEntries([
    {
      entry_name: 'ENTRY A',
      entry: {
        status: 'ALIVE',
        used_teams: [],
        week_5: { official_pool_sheet_confirmed: true },
      },
    },
    {
      entry_name: 'ENTRY B',
      entry: {
        status: 'ALIVE',
        used_teams: [],
        week_5: { official_pool_sheet_confirmed: true },
      },
    },
  ], candidates, 5)

  assert.equal(allocations[0].team, 'Dallas Cowboys')
  assert.equal(allocations[1].team, 'Kansas City Chiefs')
  assert.notEqual(allocations[0].team, allocations[1].team)
})

test('used teams remain ineligible for each individual entry', () => {
  const allocations = diversifySurvivorEntries([
    {
      entry_name: 'ENTRY A',
      entry: {
        status: 'ALIVE',
        used_teams: ['Dallas Cowboys'],
        week_5: { official_pool_sheet_confirmed: true },
      },
    },
    {
      entry_name: 'ENTRY B',
      entry: {
        status: 'ALIVE',
        used_teams: ['Kansas City Chiefs'],
        week_5: { official_pool_sheet_confirmed: true },
      },
    },
  ], candidates, 5)

  assert.equal(allocations[0].team, 'Kansas City Chiefs')
  assert.equal(allocations[1].team, 'Dallas Cowboys')
})

test('unconfirmed and eliminated entries are withheld instead of guessed', () => {
  const allocations = diversifySurvivorEntries([
    {
      entry_name: 'WAITING',
      entry: {
        status: 'ALIVE',
        used_teams: [],
        week_5: { official_pool_sheet_confirmed: false, rule_status: 'AWAITING_OFFICIAL_POOL_SHEET' },
      },
    },
    {
      entry_name: 'OUT',
      entry: {
        status: 'ELIMINATED',
        used_teams: [],
        week_5: { official_pool_sheet_confirmed: true },
      },
    },
  ], candidates, 5)

  assert.equal(allocations[0].team, null)
  assert.equal(allocations[0].status, 'AWAITING_OFFICIAL_POOL_SHEET')
  assert.equal(allocations[1].team, null)
  assert.equal(allocations[1].status, 'ENTRY_ELIMINATED')
})
