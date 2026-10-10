// Administrative owner entitlement: account email must be provider-verified.
// The entry comes ONLY from a private, server-owned pre-assignment, never from
// user-supplied entry names, query parameters or a client-supplied email.
// Existing database ownership/claim is respected; no Survivor pick is touched.
import {createHash} from 'node:crypto'
const hash=text=>createHash('sha256').update(text).digest('hex')
const originalName=value=>typeof value==='string'?value.trim():''
const emailKey=value=>typeof value==='string'?value.trim().toLowerCase():''
function validatedManifest(manifest){
 if(manifest?.version!==1||manifest?.kind!=='SPORTS_ZENITH_ADMIN_PREVERIFIED_SURVIVOR_OWNER_ENTITLEMENTS'||
    !Array.isArray(manifest.entries)||manifest.entries.length>100)return null
 const seenNames=new Set(),seenPairs=new Set()
 for(const record of manifest.entries){
  if(!record||record.source!=='ADMIN_VERIFIED_OWNER'||
     !/^[0-9a-f]{64}$/.test(String(record.email_sha256||''))||
     !originalName(record.entry_name)||originalName(record.entry_name).length>160)return null
  const name=originalName(record.entry_name)
  if(seenNames.has(name)||seenPairs.has(record.email_sha256+':'+name))return null
  seenNames.add(name);seenPairs.add(record.email_sha256+':'+name)
 }
 return manifest.entries
}
export const validVerifiedOwnerManifest=manifest=>Boolean(validatedManifest(manifest))

export function eligibleReservedEntries(user,manifest){
 if(typeof user?.id!=='string'||!user.id.trim()||user.emailVerified!==true)return []
 const email=emailKey(user.email)
 if(!email||!email.includes('@')||email.length>254)return []
 const entries=validatedManifest(manifest)
 if(!entries)return []
 const claimedHash=hash(email)
 return entries.filter(record=>record.email_sha256===claimedHash).map(record=>originalName(record.entry_name))
}
export function isReservedForDifferentAccount(entryName,user,manifest){
 const entries=validatedManifest(manifest)
 if(!entries)return false
 const desired=originalName(entryName)
 if(!entries.some(entry=>originalName(entry.entry_name)===desired))return false
 return !eligibleReservedEntries(user,manifest).includes(desired)
}

// db must expose exact server-admin operations, never a public anonymous client.
export async function secureAutoLinkReservedEntry({user,manifest,pool,db,nowISO=new Date().toISOString()}={}){
 const names=eligibleReservedEntries(user,manifest)
 if(!names.length)return {status:'NO_PREVERIFIED_ENTRY',entry_names:[]}
 if(!db||!Array.isArray(names)||names.length!==1)throw Error('RESERVED_ENTITLEMENT_CONFIGURATION_CONFLICT')
 const entryName=names[0]
 const record=pool?.entries?.[entryName]
 if(!record||!Array.isArray(record.used_teams)||!Array.isArray(record.current_picks)){
  throw Error('RESERVED_POOL_ENTRY_NOT_VERIFIED')
 }
 if(!Number.isFinite(Date.parse(nowISO)))throw Error('RESERVED_ENTITLEMENT_CLOCK_UNVERIFIED')
 const current=await db.findOwners(entryName)
 if(!Array.isArray(current)||current.length>1||current.some(row=>row.owner_id&&row.owner_id!==user.id)){
  throw Error('RESERVED_ENTRY_OWNERSHIP_CONFLICT')
 }
 const existing=current.find(row=>row.owner_id===user.id&&row.is_active===true)
 if(existing)return {status:'ALREADY_LINKED',entry_names:[entryName]}
 if(current.length)throw Error('RESERVED_ENTRY_EXISTING_RECORD_REQUIRES_ADMIN_REVIEW')
 const claim=await db.getClaim(entryName)
 if(!claim||claim.entry_name!==entryName||
    !/^[0-9a-f]{64}$/i.test(String(claim.code_sha256||''))||
    (claim.claimed_by&&claim.claimed_by!==user.id)){
  throw Error('RESERVED_ENTRY_OWNERSHIP_CONFLICT')
 }
 if(claim.expires_at&&Date.parse(claim.expires_at)<=Date.parse(nowISO)){
  throw Error('RESERVED_ENTRY_CLAIM_EXPIRED')
 }
 if(!claim.claimed_by){
  const claimed=await db.claimIfUnclaimed(entryName,user.id,nowISO)
  if(!claimed)throw Error('RESERVED_ENTRY_OWNERSHIP_CONFLICT')
 }
 await db.insertOwner({owner_id:user.id,entry_name:entryName,is_active:true,
  used_teams:[...record.used_teams]})
 const after=await db.findOwners(entryName)
 if(!Array.isArray(after)||after.length!==1||after[0].owner_id!==user.id||after[0].is_active!==true){
  throw Error('RESERVED_ENTRY_OWNER_READBACK_FAILED')
 }
 return {status:'AUTO_LINKED',entry_names:[entryName]}
}
