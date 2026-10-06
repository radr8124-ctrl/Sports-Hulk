import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createAdminClient, createClient } from '@insforge/sdk'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const ROOT = path.resolve(__dirname, '..')
const COMMERCIAL = path.join(ROOT, 'commercial_web')

async function jsonFile(p) {
  return JSON.parse(await readFile(p, 'utf8'))
}

function parseEnv(text) {
  const out = {}
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim()
    if (!line || line.startsWith('#') || !line.includes('=')) continue
    const i = line.indexOf('=')
    out[line.slice(0, i).trim()] = line.slice(i + 1).trim()
  }
  return out
}

const meta = await jsonFile(path.join(ROOT, '.insforge', 'project.parent.json'))
const env = parseEnv(await readFile(path.join(COMMERCIAL, '.env.local'), 'utf8'))
const baseUrl = env.VITE_INSFORGE_URL
const anonKey = env.VITE_INSFORGE_ANON_KEY

if (!baseUrl || !anonKey || !meta.api_key) throw new Error('InsForge production configuration is incomplete')

const admin = createAdminClient({ baseUrl, apiKey: meta.api_key })
const publicClient = createClient({ baseUrl, anonKey })

const links = await jsonFile(path.join(COMMERCIAL, 'private_member_links.json'))
const survivorState = await jsonFile(path.join(ROOT, 'nfl_live', 'derived', 'SURVIVOR_ENTRIES.json'))

let migrated = 0
let alreadyPresent = 0
let skipped = 0
let conflicts = 0
let claimsMigrated = 0
let claimsUpdated = 0
let claimsSkipped = 0

for (const [ownerId, entryName] of Object.entries(links.survivor_entries || {})) {
  const entry = survivorState?.entries?.[entryName]
  if (!entry) {
    skipped += 1
    continue
  }

  const { data: existingRows, error: existingError } = await admin.database
    .from('survivor_entries')
    .select('id,owner_id,entry_name,is_active')
    .eq('owner_id', ownerId)
    .limit(20)

  if (existingError) throw existingError

  const conflicting = (existingRows || []).find(row => row.entry_name !== entryName && row.is_active !== false)
  if (conflicting) {
    conflicts += 1
    continue
  }

  const existing = (existingRows || []).find(row => row.entry_name === entryName)
  const payload = {
    owner_id: ownerId,
    entry_name: entryName,
    is_active: true,
    used_teams: Array.isArray(entry.used_teams) ? entry.used_teams : [],
  }

  if (existing) {
    const { error } = await admin.database.from('survivor_entries').update(payload).eq('id', existing.id)
    if (error) throw error
    alreadyPresent += 1
  } else {
    const { error } = await admin.database.from('survivor_entries').insert(payload)
    if (error) throw error
    migrated += 1
  }
}

for (const [entryName, claim] of Object.entries(links.survivor_claims || {})) {
  if (!claim || typeof claim !== 'object' || !claim.code_sha256) {
    claimsSkipped += 1
    continue
  }

  const { data: existingClaims, error: existingClaimsError } = await admin.database
    .from('survivor_claims')
    .select('entry_name')
    .eq('entry_name', entryName)
    .limit(1)
  if (existingClaimsError) throw existingClaimsError

  const payload = {
    entry_name: entryName,
    code_sha256: String(claim.code_sha256),
    claimed_by: claim.claimed_by || null,
    claimed_at: claim.claimed_at || null,
    expires_at: claim.expires_at || null,
  }

  if (Array.isArray(existingClaims) && existingClaims.length) {
    const { error } = await admin.database.from('survivor_claims').update(payload).eq('entry_name', entryName)
    if (error) throw error
    claimsUpdated += 1
  } else {
    const { error } = await admin.database.from('survivor_claims').insert(payload)
    if (error) throw error
    claimsMigrated += 1
  }
}

const { data: adminRows, error: adminReadError } = await admin.database
  .from('survivor_entries')
  .select('id')
if (adminReadError) throw adminReadError

const { data: publicRows, error: publicReadError } = await publicClient.database
  .from('survivor_entries')
  .select('id')

const fakeOwner = '00000000-0000-0000-0000-000000000001'
const { error: publicInsertError } = await publicClient.database
  .from('survivor_entries')
  .insert({ owner_id: fakeOwner, entry_name: '__RLS_PROBE__', is_active: true, used_teams: [] })

if (!publicInsertError) {
  await admin.database.from('survivor_entries').delete().eq('entry_name', '__RLS_PROBE__')
  throw new Error('RLS probe unexpectedly allowed anonymous insert')
}

const { data: adminClaimRows, error: adminClaimReadError } = await admin.database
  .from('survivor_claims')
  .select('entry_name')
if (adminClaimReadError) throw adminClaimReadError

const { data: publicClaimRows, error: publicClaimReadError } = await publicClient.database
  .from('survivor_claims')
  .select('entry_name')

const { error: publicClaimInsertError } = await publicClient.database
  .from('survivor_claims')
  .insert({ entry_name: '__CLAIM_RLS_PROBE__', code_sha256: '0'.repeat(64) })

if (!publicClaimInsertError) {
  await admin.database.from('survivor_claims').delete().eq('entry_name', '__CLAIM_RLS_PROBE__')
  throw new Error('Claim RLS probe unexpectedly allowed anonymous insert')
}

console.log(JSON.stringify({
  migrated,
  alreadyPresent,
  skipped,
  conflicts,
  claims_migrated: claimsMigrated,
  claims_updated: claimsUpdated,
  claims_skipped: claimsSkipped,
  admin_row_count: Array.isArray(adminRows) ? adminRows.length : 0,
  admin_claim_row_count: Array.isArray(adminClaimRows) ? adminClaimRows.length : 0,
  anonymous_read_row_count: Array.isArray(publicRows) ? publicRows.length : 0,
  anonymous_read_blocked_or_empty: Boolean(publicReadError) || (Array.isArray(publicRows) && publicRows.length === 0),
  anonymous_insert_blocked: Boolean(publicInsertError),
  anonymous_claim_read_row_count: Array.isArray(publicClaimRows) ? publicClaimRows.length : 0,
  anonymous_claim_read_blocked_or_empty: Boolean(publicClaimReadError) || (Array.isArray(publicClaimRows) && publicClaimRows.length === 0),
  anonymous_claim_insert_blocked: Boolean(publicClaimInsertError),
}, null, 2))
