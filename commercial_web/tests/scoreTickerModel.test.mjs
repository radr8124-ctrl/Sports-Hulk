import test from 'node:test'
import assert from 'node:assert/strict'
import { buildScoreTickerItems } from '../src/site/scoreTickerModel.mjs'

test('prioritizes live, then upcoming, then final games across six feeds', () => {
  const rows = buildScoreTickerItems({
    nfl: { games: [{ away: 'NYG', home: 'DAL', final: true, away_score: 10, home_score: 20 }] },
    nba: { games: [{ away_abbr: 'NYK', home_abbr: 'BOS', live: true, away_score: 90, home_score: 88 }] },
    mlb: { today_games: [{ away: 'NYY', home: 'NYM', status: 'Scheduled' }] },
    nhl: { games: [] }, cfb: { games: [] }, cbb: { games: [] },
  })
  assert.deepEqual(rows.map(row => row.status), ['LIVE', 'UPCOMING', 'FINAL'])
  assert.equal(rows[0].score, '90–88')
  assert.equal(rows[1].score, null)
  assert.equal(rows[2].score, '10–20')
})

test('handles absent or malformed feeds without phantom matchups', () => {
  const rows = buildScoreTickerItems({ nfl: { games: null }, nba: { games: [{ live: true }] }, mlb: {} })
  assert.deepEqual(rows, [])
})

test('recognizes feed status strings and avoids scores on future games', () => {
  const rows = buildScoreTickerItems({ nhl: { games: [
    { away_team: 'Rangers', home_team: 'Islanders', status: 'In Progress', awayScore: 2, homeScore: 1 },
    { away_team: 'Devils', home_team: 'Flyers', status: 'Scheduled', awayScore: 0, homeScore: 0 },
  ] } })
  assert.equal(rows[0].status, 'LIVE')
  assert.equal(rows[1].score, null)
})
