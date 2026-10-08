import test from 'node:test'
import assert from 'node:assert/strict'
import { canManageSurvivorPool } from './survivor_pool_permissions.js'

test('anonymous visitor and ordinary signed-in member cannot replace pool', () => {
  assert.equal(canManageSurvivorPool(null), false)
  assert.equal(canManageSurvivorPool({ id: 'member-1', email: 'member@example.com' }), false)
  assert.equal(canManageSurvivorPool({ id: 'member-1', role: 'authenticated' }), false)
})

test('client-modifiable user metadata never grants manager permission', () => {
  const user = { id: 'member-1', user_metadata: {
    role: 'admin', survivor_pool_manager: true,
  }}
  assert.equal(canManageSurvivorPool(user), false)
})

test('server-assigned manager metadata grants access', () => {
  assert.equal(canManageSurvivorPool({
    id: 'manager', app_metadata: { survivor_pool_manager: true },
  }), true)
  assert.equal(canManageSurvivorPool({
    id: 'manager', app_metadata: { roles: ['survivor_pool_manager'] },
  }), true)
})

test('explicit server-only account ID and case-folded email allowlists', () => {
  const idUser = { id: 'safe-id' }
  const emailUser = { id: 'other', email: 'ADMIN@EXAMPLE.COM' }
  assert.equal(canManageSurvivorPool(idUser, {ids: 'id2, safe-id'}), true)
  assert.equal(canManageSurvivorPool(emailUser, {emails: 'admin@example.com'}), true)
  assert.equal(canManageSurvivorPool(emailUser, {emails: 'not-admin@example.com'}), false)
  assert.equal(canManageSurvivorPool(idUser, {}), false)
})

test('manager metadata cannot be inferred from an untrusted top-level role', () => {
  assert.equal(canManageSurvivorPool({id:'fake', role:'survivor_pool_manager'}), false)
})
