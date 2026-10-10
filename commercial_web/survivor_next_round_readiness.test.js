import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {buildSurvivorNextRoundReadiness} from './survivor_next_round_readiness.js'

const exactSource={max_week_in_file:4,source_sha256:'a'.repeat(64),source_filename:'WEEK #4 PICKS .pdf'}
const base={status:'ALIVE',current_week:5,current_picks:[],used_teams:[
 'Los Angeles Chargers','San Francisco 49ers','Kansas City Chiefs','Buffalo Bills','Minnesota Vikings'],
 week_5:{required_picks:null,rule_status:'AWAITING_OFFICIAL_POOL_SHEET',
   entry_result:'OPEN',picks:[],submitted:false,official_pool_sheet_confirmed:false},
}
const copy=x=>structuredClone(x)
const read=(entry=base,officialMeta=exactSource,poolWeek=5)=>buildSurvivorNextRoundReadiness({entry,officialMeta,poolWeek})
const importedWin=()=>{
 const entry=copy(base)
 entry.week_5={required_picks:1,rule_status:'CONFIRMED_FROM_IMPORTED_POOL_HEADER',
 official_pool_sheet_confirmed:true,entry_result:'WIN',
 picks:[{team:'Jacksonville Jaguars',result:'WIN',game_status:'FINAL: Philadelphia Eagles 10 - Jacksonville Jaguars 24'}],submitted:false}
 return entry
}
const official5={max_week_in_file:5,source_sha256:'b'.repeat(64),source_filename:'WEEK #5 PICKS.pdf'}

test('actual entry awaiting official Week5 sheet cannot be advanced or called eliminated',()=>{
 const v=read()
 assert.equal(v.status,'AWAITING_OFFICIAL_WEEK5_SHEET')
 assert.equal(v.pool_week,5)
 assert.equal(v.owner_entry_week,5)
 assert.equal(v.required_next_week_picks,2)
 assert.equal(v.required_current_week_picks,1)
 assert.equal(v.official_source_week,4)
 assert.equal(v.saved_week5_picks,0)
 assert.equal(v.verified_week5_picks,0)
 assert.equal(v.verified_week5_result,false)
 assert.equal(v.ready_for_week6,false)
 assert.equal(v.external_pool_submission_verified,false)
 assert.equal(v.automatic_rollover_permitted,false)
 assert.equal(v.used_team_count,5)
 assert.equal(v.latest_source_kind,'ORGANIZER_PDF_PRIOR_WEEK_ONLY')
 assert.equal(JSON.stringify(v).includes('ANNIE G'),false)
})

test('saved-in-Zenith team does not count as external organizer source or Week 6 eligibility',()=>{
 const entry=copy(base)
 entry.current_picks=['Jacksonville Jaguars']
 entry.week_5={required_picks:1,entry_result:'WIN',official_pool_sheet_confirmed:false,
  rule_status:'CONFIRMED_FROM_2026_ORIGINAL_RULES',submitted:false,
  picks:[{team:'Jacksonville Jaguars',result:'WIN'}]}
 const result=read(entry)
 assert.equal(result.status,'AWAITING_OFFICIAL_WEEK5_SHEET')
 assert.equal(result.saved_week5_picks,1)
 assert.equal(result.verified_week5_picks,0)
 assert.equal(result.ready_for_week6,false)
})

test('imported Week 5 sheet with incomplete actual final results waits for grading',()=>{
 const entry=importedWin()
 entry.week_5.entry_result='OPEN'
 entry.week_5.picks[0].result='PENDING'
 const result=read(entry,official5)
 assert.equal(result.status,'WAITING_WEEK5_GAME_FINAL')
 assert.equal(result.verified_week5_picks,1)
 assert.equal(result.ready_for_week6,false)
 assert.equal(result.verified_week5_result,false)
})

test('organizer Week 5 sheet and a fully recorded winning result permit reviewing Week6 rollover',()=>{
 const entry=importedWin()
 const result=read(entry,official5)
 assert.equal(result.status,'WEEK5_SURVIVAL_CERTIFIED_NEXT_ROUND_PENDING')
 assert.equal(result.ready_for_week6,true)
 assert.equal(result.automatic_rollover_permitted,true)
 assert.equal(result.verified_week5_result,true)
 assert.equal(result.required_next_week_picks,2)
 assert.equal(result.external_pool_submission_verified,false)
 assert.equal(result.verified_week5_picks,1)
})

test('verified Week 5 win with pool Week 6 is two-pick ready only after entry week updates',()=>{
 const entry=importedWin()
 const hold=read(entry,official5,6)
 assert.equal(hold.status,'WAITING_PRIVATE_WEEK6_ACTIVATION')
 assert.equal(hold.ready_for_week6,false)
 entry.current_week=6
 entry.week_6={entry_result:'OPEN',picks:[],required_picks:2,rule_status:'CONFIRMED_FROM_2026_ORIGINAL_RULES'}
 const open=read(entry,official5,6)
 assert.equal(open.status,'WEEK6_TWO_PICK_ROUND_READY')
 assert.equal(open.ready_for_week6,true)
 assert.equal(open.required_next_week_picks,2)
})

test('official sheet alone never turns missing pick or reported Dallas losses into certified elimination',()=>{
 const entry=copy(base)
 entry.week_5={required_picks:1,rule_status:'CONFIRMED_FROM_IMPORTED_POOL_HEADER',
  official_pool_sheet_confirmed:true,picks:[],entry_result:'OPEN',submitted:false}
 const result=read(entry,official5)
 assert.equal(result.status,'OFFICIAL_WEEK5_TICKET_ABSENT_REVIEW')
 assert.equal(result.ready_for_week6,false)
 assert.equal(result.verified_week5_result,false)
 assert.equal(result.external_pool_submission_verified,false)
})

test('exact official losing ticket blocks Week 6, but absent certificate does not assume eliminated',()=>{
 const entry=importedWin()
 entry.week_5.entry_result='LOSS'
 entry.week_5.picks[0].result='LOSS'
 entry.status='ELIMINATED'
 assert.equal(read(entry,official5).status,'OFFICIAL_WEEK5_ELIMINATED')
 assert.equal(read(entry,official5).ready_for_week6,false)
 entry.week_5.official_pool_sheet_confirmed=false
 assert.equal(read(entry,official5).status,'UNVERIFIED_POOL_STATUS_REVIEW_REQUIRED')
})

test('duplicate ticket, conflicting required pick count and forged source identity fail closed',()=>{
 const duplicate=importedWin()
 duplicate.week_5.picks.push({...duplicate.week_5.picks[0]})
 assert.equal(read(duplicate,official5).status,'SOURCE_CONFLICT_REVIEW_REQUIRED')
 const conflicting=importedWin()
 conflicting.week_5.required_picks=2
 assert.equal(read(conflicting,official5).status,'SOURCE_CONFLICT_REVIEW_REQUIRED')
 const badMeta={...official5,source_sha256:'fake'}
 assert.equal(read(importedWin(),badMeta).status,'OFFICIAL_SOURCE_UNVERIFIED')
 assert.equal(read(importedWin(),exactSource).status,'OFFICIAL_SOURCE_CONFLICT')
})

test('no signed-in owner or invalid pool week exposes no player, competitor, eligibility or private history',()=>{
 for(const request of [
  {entry:null,poolWeek:5,officialMeta:official5},
  {entry:undefined,poolWeek:5,officialMeta:official5},
  {entry:base,poolWeek:0,officialMeta:official5},
 ]){
  const result=buildSurvivorNextRoundReadiness(request)
  assert.equal(result.ready_for_week6,false)
  assert.equal(result.external_pool_submission_verified,false)
  assert.equal(result.automatic_rollover_permitted,false)
 }
})

test('the original real owner source never manufactures Week 6 readiness ahead of organizer sheet',()=>{
 const privateState=JSON.parse(readFileSync(new URL('../nfl_live/derived/SURVIVOR_ENTRIES.json',import.meta.url),'utf8'))
 const source=JSON.parse(readFileSync(new URL('../nfl_live/survivor_pool/derived/LATEST_OFFICIAL_POOL.json',import.meta.url),'utf8'))
 if(privateState.pool_current_week!==5)return
 const result=buildSurvivorNextRoundReadiness({entry:privateState.entries['ANNIE G 01'],poolWeek:5,officialMeta:source})
 assert.equal(result.status,'AWAITING_OFFICIAL_WEEK5_SHEET')
 assert.equal(result.ready_for_week6,false)
 assert.equal(result.required_next_week_picks,2)
 assert.equal(result.saved_week5_picks,0)
})
