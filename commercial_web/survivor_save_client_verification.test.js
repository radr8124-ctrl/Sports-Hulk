import test from 'node:test'
import assert from 'node:assert/strict'
import {verifySurvivorSavedAgainstPrivateState} from './survivor_save_client_verification.js'

const entryName='SYNTHETIC QA 01',week=5,teams=['Houston Texans']
const receipt={status:'PERSISTED_IN_ZENITH_NOT_EXTERNAL_POOL',verified_disk_readback:true,
 entry_name:entryName,week,teams,pool_submitted:false,external_organizer_submission_verified:false,
 saved_at_utc:'2026-10-10T21:30:00.000Z',pick_status:'SAVED_NOT_SUBMITTED',required_picks:1}
const privateState={status:'READY',entry_linked:true,active_entry:entryName,
 pool_current_week:5,current_picks:['Houston Texans'],entry_status:'ALIVE',
 current_pick_status:'SAVED_NOT_SUBMITTED',required_picks:1}
const check=(receiptOverride=receipt,stateOverride=privateState)=>verifySurvivorSavedAgainstPrivateState({receipt:receiptOverride,state:stateOverride,entryName,week,teams})

test('only matching server disk receipt AND a second authenticated owner GET confirm Saved',()=>{
 assert.deepEqual(check(),{status:'CONFIRMED_IN_ZENITH_ONLY',success:true,complete:true,required_picks:1})
})

test('a 1-of-2 Week 6 private readback is verified as incomplete, never a finished external pool entry',()=>{
 const partialReceipt={...receipt,pick_status:'INCOMPLETE_SAVED',required_picks:2}
 const partialState={...privateState,current_pick_status:'INCOMPLETE_SAVED',required_picks:2}
 assert.deepEqual(check(partialReceipt,partialState),{
  status:'CONFIRMED_IN_ZENITH_ONLY',success:true,complete:false,required_picks:2,
 })
})

test('HTTP success with prior bridge shape or missing disk receipt is NOT shown as saved',()=>{
 for(const r of [null,{},
  {status:'SAVED_NOT_SUBMITTED',teams,pool_submitted:false},
  {...receipt,verified_disk_readback:false},
  {...receipt,external_organizer_submission_verified:true},
  {...receipt,teams:['Jacksonville Jaguars']},
 ]){
  const v=check(r)
  assert.equal(v.success,false)
  assert.equal(v.status,'SERVER_SAVE_NOT_VERIFIED')
 }
})

test('a disk-verified HTTP 200 with stale, unauthenticated, or different account state is NOT saved',()=>{
 for(const state of [null,{},
  {...privateState,current_picks:[]},
  {...privateState,active_entry:'DIFFERENT MEMBER 01'},
  {...privateState,entry_linked:false},
  {...privateState,status:'AUTHENTICATED_NO_ENTRY'},
  {...privateState,pool_current_week:6},
  {...privateState,current_picks:['Jacksonville Jaguars']},
 ]){
  const v=check(receipt,state)
  assert.equal(v.success,false)
  assert.equal(v.status,'DASHBOARD_READBACK_NOT_VERIFIED')
 }
})

test('original source objects stay untouched and personal identifiers are never logged',()=>{
 const saved=JSON.stringify({receipt,state:privateState})
 for(let n=0;n<3;n++)check()
 assert.equal(JSON.stringify({receipt,state:privateState}),saved)
})
