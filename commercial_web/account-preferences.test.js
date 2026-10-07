import test from 'node:test'
import assert from 'node:assert/strict'
import { sanitizeAccountPreferences } from './account_preferences.js'

test('preferences normalize and deduplicate opt-in sports data', () => {
  const result = sanitizeAccountPreferences({
    favorite_teams: ['New York Yankees', ' new   york   yankees ', 'Buffalo Bills'],
    sports_followed: ['nfl', 'NBA', 'golf', 'NFL'],
    watched_players: ['Josh Allen', ' Josh Allen ', 'Amon-Ra St. Brown'],
    risk_preference: 'conservative',
  })

  assert.deepEqual(result.favorite_teams, ['New York Yankees', 'Buffalo Bills'])
  assert.deepEqual(result.sports_followed, ['NFL', 'NBA'])
  assert.deepEqual(result.watched_players, ['Josh Allen', 'Amon-Ra St. Brown'])
  assert.equal(result.risk_preference, 'CONSERVATIVE')
})

test('unsupported risk values fall back to balanced', () => {
  const result = sanitizeAccountPreferences({ risk_preference: 'YOLO_MAX' })
  assert.equal(result.risk_preference, 'BALANCED')
})

test('unknown fields are not persisted by the sanitizer', () => {
  const result = sanitizeAccountPreferences({
    favorite_teams: ['Mets'],
    secret_note: 'do not store this',
    conversation_history: ['private chat'],
  })

  assert.equal(Object.hasOwn(result, 'secret_note'), false)
  assert.equal(Object.hasOwn(result, 'conversation_history'), false)
  assert.deepEqual(Object.keys(result).sort(), [
    'favorite_teams',
    'risk_preference',
    'sports_followed',
    'watched_players',
  ].sort())
})
