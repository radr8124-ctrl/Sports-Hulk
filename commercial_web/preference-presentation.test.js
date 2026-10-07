import test from 'node:test'
import assert from 'node:assert/strict'
import { preferencePresentation, watchlistNewsHits } from './preference_presentation.js'

test('presentation detects watched players and favorite teams without model adjustment', () => {
  const result = preferencePresentation(
    {
      take: 'Josh Allen is the current top research candidate.',
      cards: [
        { type: 'fantasy', title: 'Josh Allen', team: 'Buffalo Bills' },
        { type: 'fantasy', title: 'Amon-Ra St. Brown', team: 'Detroit Lions' },
      ],
    },
    {
      favorite_teams: ['Buffalo Bills', 'New York Yankees'],
      watched_players: ['Josh Allen', 'Shohei Ohtani'],
      sports_followed: ['NFL', 'MLB'],
      risk_preference: 'CONSERVATIVE',
    },
  )

  assert.deepEqual(result.matched_favorite_teams, ['Buffalo Bills'])
  assert.deepEqual(result.matched_watched_players, ['Josh Allen'])
  assert.equal(result.risk_preference, 'CONSERVATIVE')
  assert.equal(result.presentation_only, true)
  assert.equal(result.model_adjustment, false)
})

test('presentation leaves unmatched preferences as metadata only', () => {
  const result = preferencePresentation(
    {
      take: 'No current bet has cleared the V2 PLAY gate.',
      cards: [{ type: 'bet_research', title: 'NBA · Spread', selection: 'Boston Celtics' }],
    },
    {
      favorite_teams: ['Buffalo Bills'],
      watched_players: ['Josh Allen'],
      sports_followed: ['NFL'],
      risk_preference: 'AGGRESSIVE',
    },
  )

  assert.deepEqual(result.matched_favorite_teams, [])
  assert.deepEqual(result.matched_watched_players, [])
  assert.equal(result.model_adjustment, false)
})


test('watchlist surfaces recent preference matches and withholds stale ones', () => {
  const now = Date.parse('2026-10-07T12:00:00Z')
  const hits = watchlistNewsHits(
    [
      {
        title: 'Eagles RT Lane Johnson To Retire',
        source: 'Pro Football Rumors',
        url: 'https://example.com/eagles',
        published_at: '2026-10-07T04:00:00Z',
      },
      {
        title: 'Josh Allen injury update',
        source: 'Test Wire',
        url: 'https://example.com/allen',
        published_at: '2026-10-06T18:00:00Z',
      },
      {
        title: 'Old Buffalo Bills feature',
        source: 'Old Wire',
        url: 'https://example.com/old-bills',
        published_at: '2026-10-04T00:00:00Z',
      },
    ],
    {
      favorite_teams: ['Philadelphia Eagles', 'Buffalo Bills'],
      watched_players: ['Josh Allen'],
    },
    now,
  )

  assert.equal(hits.length, 2)
  assert.equal(hits[0].matched_preference, 'Philadelphia Eagles')
  assert.equal(hits[1].matched_preference, 'Josh Allen')
  assert.equal(hits.some(hit => hit.title.includes('Old Buffalo Bills')), false)
})
