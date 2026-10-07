import test from 'node:test'
import assert from 'node:assert/strict'
import { preferencePresentation } from './preference_presentation.js'

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
