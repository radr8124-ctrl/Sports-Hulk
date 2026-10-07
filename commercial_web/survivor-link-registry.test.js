import test from 'node:test'
import assert from 'node:assert/strict'
import { addSurvivorLink, survivorEntryOwnedByOther, survivorLinkNames } from './survivor_link_registry.js'

test('legacy single-entry string remains readable', () => {
  assert.deepEqual(survivorLinkNames('ANNIE G 01'), ['ANNIE G 01'])
})

test('adding another entry migrates legacy string to a deduplicated array', () => {
  const registry = { user1: 'ANNIE G 01' }
  const next = addSurvivorLink(registry, 'user1', 'ANNIE G 02')
  assert.deepEqual(next.user1, ['ANNIE G 01', 'ANNIE G 02'])

  const duplicate = addSurvivorLink(next, 'user1', 'ANNIE G 02')
  assert.deepEqual(duplicate.user1, ['ANNIE G 01', 'ANNIE G 02'])
})

test('one entry cannot be linked to a different account', () => {
  const registry = {
    user1: ['ANNIE G 01', 'ANNIE G 02'],
    user2: 'OTHER ENTRY',
  }

  assert.equal(survivorEntryOwnedByOther(registry, 'user2', 'ANNIE G 01'), true)
  assert.equal(survivorEntryOwnedByOther(registry, 'user1', 'ANNIE G 01'), false)
})
