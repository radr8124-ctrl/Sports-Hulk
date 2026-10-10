import test from 'node:test'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import {eligibleReservedEntries, isReservedForDifferentAccount, secureAutoLinkReservedEntry} from './survivor_verified_owner_autolink.js'

const hash=s=>createHash('sha256').update(s).digest('hex')
const owner={id:'verified-unique-user-id',email:'OWNER@EXAMPLE.COM',emailVerified:true}
const manifest={version:1,kind:'SPORTS_ZENITH_ADMIN_PREVERIFIED_SURVIVOR_OWNER_ENTITLEMENTS',entries:[{
 entry_name:'FAMILY TEST 01',email_sha256:hash('owner@example.com'),source:'ADMIN_VERIFIED_OWNER',
}]}
const pool={pool_current_week:5,entries:{'FAMILY TEST 01':{status:'ALIVE',used_teams:['Buffalo Bills'],current_picks:[],week_5:{submitted:false}}}}
function fakeDatabase(options={}) {
 const state={owners:options.owners??[],claimedBy:options.claimedBy??null,claimedAt:null,queries:[],writes:0}
 const db={
  async findOwners(name){state.queries.push('owners');return state.owners.filter(r=>r.entry_name===name)},
  async getClaim(name){state.queries.push('claim');return name==='FAMILY TEST 01'?{entry_name:name,claimed_by:state.claimedBy,code_sha256:hash('secret')}:null},
  async claimIfUnclaimed(name,id,now){state.queries.push('claim-if-unclaimed');if(state.claimedBy)return false;state.claimedBy=id;state.claimedAt=now;state.writes++;return true},
  async insertOwner(row){state.queries.push('insert');if(options.failInsert)throw Error('Storage unavailable');state.owners.push({...row,id:'generated',is_active:true});state.writes++;return true},
 }
 return {state,db}
}

test('verified email alone discovers the preassigned entry; never requires a claimant to type a name or code',()=>{
 assert.deepEqual(eligibleReservedEntries(owner,manifest),['FAMILY TEST 01'])
 assert.deepEqual(eligibleReservedEntries({...owner,email:' owner@example.com '},manifest),['FAMILY TEST 01'])
 assert.deepEqual(eligibleReservedEntries({...owner,emailVerified:false},manifest),[])
 assert.deepEqual(eligibleReservedEntries({...owner,email:'other@example.com'},manifest),[])
 assert.deepEqual(eligibleReservedEntries({...owner,id:''},manifest),[])
 assert.equal(isReservedForDifferentAccount('FAMILY TEST 01',{...owner,email:'other@example.com'},manifest),true)
 assert.equal(isReservedForDifferentAccount('FAMILY TEST 01',owner,manifest),false)
})

test('automatic verified owner claim is atomic, persists owner ID, and returns only the authorized entry',async()=>{
 const {state,db}=fakeDatabase()
 const result=await secureAutoLinkReservedEntry({user:owner,manifest,pool,db,nowISO:'2026-10-10T20:50:00.000Z'})
 assert.deepEqual(result,{status:'AUTO_LINKED',entry_names:['FAMILY TEST 01']})
 assert.deepEqual(state.queries,['owners','claim','claim-if-unclaimed','insert','owners'])
 assert.equal(state.claimedBy,owner.id)
 assert.equal(state.owners[0].owner_id,owner.id)
 assert.equal(state.owners[0].entry_name,'FAMILY TEST 01')
 assert.deepEqual(state.owners[0].used_teams,['Buffalo Bills'])
 assert.equal(state.writes,2)
 assert.deepEqual(pool.entries['FAMILY TEST 01'].current_picks,[])
 assert.equal(pool.entries['FAMILY TEST 01'].week_5.submitted,false)
})

test('idempotent second login reads existing owner and never writes a duplicate account',async()=>{
 const {state,db}=fakeDatabase()
 const request={user:owner,manifest,pool,db,nowISO:'2026-10-10T20:50:00.000Z'}
 assert.equal((await secureAutoLinkReservedEntry(request)).status,'AUTO_LINKED')
 const before=state.writes
 assert.equal((await secureAutoLinkReservedEntry(request)).status,'ALREADY_LINKED')
 assert.equal(state.writes,before)
})

test('auth with nonverified email or a different verified email cannot access or mutate private pool',async()=>{
 const {state,db}=fakeDatabase()
 for(const user of [{...owner,emailVerified:false},{...owner,email:'someone-else@example.com'},null]){
  const result=await secureAutoLinkReservedEntry({user,manifest,pool,db,nowISO:'2026-10-10T20:50:00.000Z'})
  assert.deepEqual(result,{status:'NO_PREVERIFIED_ENTRY',entry_names:[]})
 }
 assert.equal(state.writes,0)
 assert.deepEqual(state.queries,[])
})

test('existing different owner or claimed-by-other record fails closed with zero writes',async()=>{
 for(const options of [
  {owners:[{id:'old-entry',entry_name:'FAMILY TEST 01',owner_id:'another-user',is_active:true}]},
  {claimedBy:'another-user'},
 ]){
  const {state,db}=fakeDatabase(options)
  await assert.rejects(secureAutoLinkReservedEntry({user:owner,manifest,pool,db,nowISO:'2026-10-10T20:50:00.000Z'}),/RESERVED_ENTRY_OWNERSHIP_CONFLICT/)
  assert.equal(state.writes,0)
 }
})

test('storage failure after claim CAS stays reserved for same verified identity and retries safely',async()=>{
 const {state,db}=fakeDatabase({failInsert:true})
 const request={user:owner,manifest,pool,db,nowISO:'2026-10-10T20:50:00.000Z'}
 await assert.rejects(secureAutoLinkReservedEntry(request),/Storage unavailable/)
 assert.equal(state.claimedBy,owner.id)
 assert.equal(state.owners.length,0)
 const safeRetry=fakeDatabase({claimedBy:owner.id})
 const done=await secureAutoLinkReservedEntry({...request,db:safeRetry.db})
 assert.equal(done.status,'AUTO_LINKED')
 assert.equal(safeRetry.state.claimedBy,owner.id)
 assert.equal(safeRetry.state.owners.length,1)
})

test('claim compare-and-swap failure never inserts owner or takes an already claimed entry',async()=>{
 const {state,db}=fakeDatabase()
 db.claimIfUnclaimed=async()=>false
 await assert.rejects(secureAutoLinkReservedEntry({user:owner,manifest,pool,db,nowISO:'2026-10-10T20:50:00.000Z'}),/RESERVED_ENTRY_OWNERSHIP_CONFLICT/)
 assert.equal(state.owners.length,0)
 assert.equal(state.writes,0)
})

test('entitlement does not manufacture pool entries, old teams or an invalid manifest',async()=>{
 const {state,db}=fakeDatabase()
 const broken={...pool,entries:{}}
 await assert.rejects(secureAutoLinkReservedEntry({user:owner,manifest,pool:broken,db,nowISO:'2026-10-10T20:50:00.000Z'}),/RESERVED_POOL_ENTRY_NOT_VERIFIED/)
 assert.equal(state.writes,0)
 assert.deepEqual(eligibleReservedEntries(owner,{...manifest,version:3}),[])
 assert.deepEqual(eligibleReservedEntries(owner,{...manifest,entries:[...manifest.entries,...manifest.entries]}),[])
})
