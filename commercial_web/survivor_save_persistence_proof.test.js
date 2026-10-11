import test from 'node:test'
import assert from 'node:assert/strict'
import {verifySurvivorPickPersistence} from './survivor_save_persistence_proof.js'

const at='2026-10-10T21:40:00.000Z'
const withPick={
 pool_current_week:5,entries:{'SYNTHETIC MEMBER 01':{
 status:'ALIVE',current_week:5,current_picks:['Houston Texans'],
 current_pick_status:'SAVED_NOT_SUBMITTED',used_teams:['Minnesota Vikings'],
 week_5:{entry_result:'OPEN',picks:[{team:'Houston Texans',result:'PENDING',source:'SPORTS_HULK_MANUAL_UI'}],
   manual_saved:true,manual_saved_at:at,submitted:false,required_picks:1},
 }},
}
const request={entryName:'SYNTHETIC MEMBER 01',poolWeek:5,teams:['Houston Texans'],
 bridge:{status:'SAVED_NOT_SUBMITTED',entry_name:'SYNTHETIC MEMBER 01',week:5,teams:['Houston Texans'],pick_status:'SAVED_NOT_SUBMITTED',pool_submitted:false},
 nowMs:Date.parse('2026-10-10T21:40:45Z')}
const verify=(alter={})=>verifySurvivorPickPersistence({...request,state:withPick,...alter})

test('verified owner-state and week ticket, real disk save timestamp are required before success',()=>{
 const proof=verify()
 assert.deepEqual(proof,{
  status:'PERSISTED_IN_ZENITH_NOT_EXTERNAL_POOL',
  verified_disk_readback:true,entry_name:request.entryName,week:5,
  teams:['Houston Texans'],saved_at_utc:at,pool_submitted:false,
  pick_status:'SAVED_NOT_SUBMITTED',required_picks:1,
  external_organizer_submission_verified:false,
 })
})

test('Week 6 one-of-two saves are proof of an INCOMPLETE Zenith draft, never final entry submission',()=>{
 const sample=structuredClone(withPick)
 sample.pool_current_week=6
 const entry=sample.entries['SYNTHETIC MEMBER 01']
 entry.current_week=6
 entry.current_pick_status='INCOMPLETE_SAVED'
 entry.week_6={...entry.week_5,required_picks:2}
 delete entry.week_5
 const result=verify({state:sample,poolWeek:6,bridge:{...request.bridge,week:6,pick_status:'INCOMPLETE_SAVED'}})
 assert.equal(result.verified_disk_readback,true)
 assert.equal(result.pick_status,'INCOMPLETE_SAVED')
 assert.equal(result.required_picks,2)
 assert.equal(result.external_organizer_submission_verified,false)
})

test('a fake HTTP or bridge success without original disk write never qualifies',()=>{
 const state=structuredClone(withPick)
 state.entries['SYNTHETIC MEMBER 01'].current_picks=[]
 assert.equal(verify({state}).status,'PERSISTENCE_NOT_VERIFIED')
 assert.equal(verify({state:{pool_current_week:5,entries:{}}}).verified_disk_readback,false)
})

test('private state and original week ticket must both match exactly including team order',()=>{
 const entry=structuredClone(withPick)
 entry.entries['SYNTHETIC MEMBER 01'].week_5.picks=[{team:'Jacksonville Jaguars',result:'PENDING'}]
 assert.equal(verify({state:entry}).status,'PERSISTENCE_NOT_VERIFIED')
 const wrongWeek=structuredClone(withPick)
 wrongWeek.entries['SYNTHETIC MEMBER 01'].current_week=6
 assert.equal(verify({state:wrongWeek}).status,'PERSISTENCE_NOT_VERIFIED')
 const wrongPool=structuredClone(withPick)
 wrongPool.pool_current_week=6
 assert.equal(verify({state:wrongPool}).status,'PERSISTENCE_NOT_VERIFIED')
})

test('unauthorized, eliminated or differently named ticket never appears as saved',()=>{
 assert.equal(verify({entryName:'ANOTHER USER'}).status,'PERSISTENCE_NOT_VERIFIED')
 const bad=structuredClone(withPick)
 bad.entries['SYNTHETIC MEMBER 01'].status='ELIMINATED'
 assert.equal(verify({state:bad}).status,'PERSISTENCE_NOT_VERIFIED')
})

test('untrusted bridge response, stale timestamp and unconfirmed external status fail closed',()=>{
 for(const bridge of [
  {...request.bridge,teams:['Jacksonville Jaguars']},
  {...request.bridge,pool_submitted:true},
  {...request.bridge,status:'SUCCESS'},
  {...request.bridge,entry_name:'OTHER USER'},
 ])assert.equal(verify({bridge}).status,'PERSISTENCE_NOT_VERIFIED')
 const old=structuredClone(withPick)
 old.entries['SYNTHETIC MEMBER 01'].week_5.manual_saved_at='2026-10-09T21:40:00Z'
 assert.equal(verify({state:old}).status,'PERSISTENCE_NOT_VERIFIED')
 const future=structuredClone(withPick)
 future.entries['SYNTHETIC MEMBER 01'].week_5.manual_saved_at='2026-10-10T22:45:00Z'
 assert.equal(verify({state:future}).status,'PERSISTENCE_NOT_VERIFIED')
 const organizer=structuredClone(withPick)
 organizer.entries['SYNTHETIC MEMBER 01'].week_5.submitted=true
 assert.equal(verify({state:organizer}).status,'PERSISTENCE_NOT_VERIFIED')
})

test('a successful save never claims prior history, a proved external pool entry, or an invented market edge',()=>{
 const result=verify(),serialized=JSON.stringify(result)
 for(const forbidden of ['won','odds','model_edge','official_pool_sheet_confirmed','account_id','token','claim_code']){
  assert.equal(serialized.includes(forbidden),false,forbidden)
 }
 assert.equal(result.pool_submitted,false)
})

test('cleared team list cannot accidentally return a success saying Texans is saved',()=>{
 const altered=structuredClone(withPick)
 altered.entries['SYNTHETIC MEMBER 01'].current_picks=[]
 altered.entries['SYNTHETIC MEMBER 01'].week_5.picks=[]
 assert.equal(verify({state:altered,teams:['Houston Texans']}).status,'PERSISTENCE_NOT_VERIFIED')
})

test('original private record unchanged; this verifier does not perform any writes',()=>{
 const before=JSON.stringify(withPick)
 for(let i=0;i<3;i++)verify()
 assert.equal(JSON.stringify(withPick),before)
})
