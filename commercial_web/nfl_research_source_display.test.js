import test from 'node:test'
import assert from 'node:assert/strict'
import { sourceResearchForGame, describeQuote } from './nfl_research_source_display.js'

const now = Date.parse('2026-10-09T20:00:00Z')
const start = new Date(now + 48 * 60 * 60 * 1000).toISOString()
const base = () => ({
  status: 'RESEARCH_ONLY',
  original_source: 'SPORTWIZZARD_ARCHIVED_SAME_BOOK_TWO_SIDED_RESEARCH',
  book_prices_live_or_executable_verified: false,
  betting_decision_created: false,
  model_advantage_proven: false,
  fixtures: [{
    official_espn_event_id: 'espn-1', source_event_id: 'book-uuid-1',
    official_start: start, approved_play: false, away: 'PHI', home: 'JAX',
    markets: {
      MONEYLINE: {
        market: 'MONEYLINE', book: 'fanduel', line: null,
        source_event_id: 'book-uuid-1',
        source_updated_at: '2026-10-09T06:00:00Z',
        source_captured_at: '2026-10-09T06:02:00Z',
        quote_type: 'TWO_SIDED_ARCHIVED_RESEARCH_SNAPSHOT',
        is_executable_current_offer: false, is_verified_main_line: false,
        is_approved_bet: false, home_price: -390, away_price: 310,
      },
    },
  }],
})
const game = () => ({
  event_id: 'espn-1', start_time: start,
  away_abbr: 'PHI', home_abbr: 'JAC', state: 'pre', final: false,
})
test('official-game and archived paired bookmaker source render as research, not bet', () => {
  const found = sourceResearchForGame(base(), game(), now)
  assert.equal(found.official_espn_event_id, 'espn-1')
  assert.match(describeQuote(found, 'MONEYLINE'), /PHI \+310.*JAC -390/)
})
test('fabricated play or executable odds cannot show', () => {
  for (const mutate of [
    p => { p.betting_decision_created = true },
    p => { p.model_advantage_proven = true },
    p => { p.fixtures[0].markets.MONEYLINE.is_executable_current_offer = true },
    p => { p.fixtures[0].approved_play = true },
    p => { p.fixtures[0].markets.MONEYLINE.source_event_id = 'other-event' },
    p => { p.fixtures[0].markets.MONEYLINE.home_price = null },
  ]) {
    const p = base(); mutate(p)
    assert.equal(sourceResearchForGame(p, game(), now), null)
  }
})
test('official start / unique event ID must match exactly', () => {
  const g = game(); g.event_id = 'other'
  assert.equal(sourceResearchForGame(base(), g, now), null)
  const p = base(); p.fixtures[0].official_start = new Date(now + 2 * 3600 * 1000).toISOString()
  assert.equal(sourceResearchForGame(p, game(), now), null)
  const duplicate = base(); duplicate.fixtures.push({...duplicate.fixtures[0]})
  assert.equal(sourceResearchForGame(duplicate, game(), now), null)
})
test('freshness tightens to 6 hours within 24 hours of kickoff', () => {
  const p = base()
  assert.ok(sourceResearchForGame(p, game(), now))
  const tomorrow = new Date(now + 20 * 3600 * 1000).toISOString()
  p.fixtures[0].official_start = tomorrow
  const g = game(); g.start_time = tomorrow
  assert.equal(sourceResearchForGame(p, g, now), null)
  p.fixtures[0].markets.MONEYLINE.source_updated_at = new Date(now - 2 * 3600 * 1000).toISOString()
  p.fixtures[0].markets.MONEYLINE.source_captured_at = new Date(now - 1 * 3600 * 1000).toISOString()
  assert.ok(sourceResearchForGame(p, g, now))
})
test('source timestamp after observation time and games already started fail closed', () => {
  const p = base()
  p.fixtures[0].markets.MONEYLINE.source_captured_at = new Date(now + 300_000).toISOString()
  assert.equal(sourceResearchForGame(p, game(), now), null)
  assert.equal(sourceResearchForGame(base(), game(), Date.parse(start)), null)
})
test('archived real source fixture readback at historical 2026 observation clock', async () => {
  const { readFileSync } = await import('node:fs')
  const source = JSON.parse(readFileSync('./public/nfl_research_book_refs.json', 'utf8'))
  const scores = JSON.parse(readFileSync('./public/nfl_scores.json', 'utf8'))
  const checkTime = Date.parse('2026-10-09T20:55:00Z')
  const records = scores.next_games.map(g => sourceResearchForGame(source, g, checkTime)).filter(Boolean)
  assert.equal(records.length, 13)
  assert(records.every(r => Object.keys(r.markets).length === 3))
})
