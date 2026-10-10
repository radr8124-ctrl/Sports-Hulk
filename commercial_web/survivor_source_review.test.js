import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { survivorSourceReview } from './survivor_source_review.js'

// Preserve original Friday replay; never rewind the changing production feed.
const FROZEN='./test_fixtures/zenith_frozen_20261009/'
const scores = JSON.parse(readFileSync(FROZEN+'nfl_scores.json','utf8'))
const storedRefs = JSON.parse(readFileSync(FROZEN+'nfl_research_book_refs.json','utf8'))
const archived = storedRefs.archived_snapshot
assert.equal(archived?.status,'ARCHIVED_SOURCE_ONLY_NOT_CURRENT')
assert.equal(archived?.original_archive_sha256,storedRefs.original_archive?.sha256)
// Frozen Friday replay only: current Saturday quotes remain expired.
const refs = {...storedRefs,fixtures:archived.fixtures}
const survivor = JSON.parse(readFileSync(FROZEN+'survivor_v2_current.json','utf8'))
const friday = Date.parse('2026-10-09T21:00:00Z')
const burned = ['Los Angeles Chargers', 'San Francisco 49ers', 'Kansas City Chiefs', 'Buffalo Bills', 'Minnesota Vikings']
const review = (args={}) => survivorSourceReview({
  scores, references: refs, candidates: survivor.candidates,
  usedTeams: burned, nowMs: friday, poolWeek: 5, ...args,
})

test('Week 5 original game board matches actual official ESPN fixtures and source-only book offers', () => {
  const options = review()
  assert.equal(options.length, 12)
  assert(options.every(x => x.pool_week === 5 && x.game_id && x.updated_at && x.captured_at))
  assert(options.every(x => x.no_vig_market_pct > 0 && x.no_vig_market_pct < 100))
  assert(options.every(x => x.is_executable_current_offer === false &&
    x.is_verified_main_line === false && x.is_approved_survivor_pick === false &&
    x.model_edge_proven === false))
  assert(options.every(x => !burned.includes(x.team)))
  assert(!JSON.stringify(options).includes('ANNIE G'))
})
test('source-only market probability differs from stale primary, and is never promoted', () => {
  const picks=review()
  const hou=picks.find(x => x.team==='Houston Texans')
  const jax=picks.find(x => x.team==='Jacksonville Jaguars')
  assert.ok(hou && jax)
  assert(hou.no_vig_market_pct > 70 && jax.no_vig_market_pct > 70)
  assert.equal(hou.future_value_index, 0)
  assert.equal(jax.future_value_index, 25)
  assert.match(jax.future_schedule, /W6 H vs Houston Texans/)
  assert(hou.risk_signals.includes('WEAK_FORM'))
  assert.equal(hou.is_approved_survivor_pick, false)
})
test('used favorite cannot be offered again, and underdog is not falsely promoted', () => {
  const picks=review({usedTeams:[...burned, 'Jacksonville Jaguars']})
  assert.equal(picks.some(x=>x.team==='Jacksonville Jaguars'),false)
  assert.equal(picks.some(x=>x.team==='Philadelphia Eagles'),false)
  assert.equal(picks.length,11)
})
test('source expiration, missing scoreboard and no match produce no recommendations', () => {
  assert.equal(review({nowMs:Date.parse('2026-10-10T20:00:00Z')}).length,0)
  assert.deepEqual(review({references:{}}),[])
  assert.deepEqual(review({scores:{next_games:[]}}),[])
  assert.equal(review({candidates:[]}).length,0)
  assert.equal(review({references:{...refs,model_advantage_proven:true}}).length,0)
})
test('no official duplicate game or wrong matchup can be silently matched', () => {
  const duplicate = {...survivor, candidates:[...survivor.candidates,survivor.candidates[0]]}
  const picks=review({candidates:duplicate.candidates})
  assert.equal(picks.some(x=>x.game_key==='CIN@MIA'),false)
})
