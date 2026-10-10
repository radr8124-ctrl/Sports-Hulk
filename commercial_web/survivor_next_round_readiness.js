// Authenticated original-source Survivor Week 5 -> Week 6 handoff, display ONLY.
// Rules and imported organizer sheet are independent. A dated game score,
// Vegas price, shadow recommendation or Zenith saved pick is NOT proof that
// the external pool recognizes the pick or the user's survival.
import {resolveWeekPickRule} from './survivor_rules.js'

const view=(status,fields={})=>({
 status,pool_week:null,owner_entry_week:null,official_source_week:null,
 latest_source_kind:'UNVERIFIED',required_current_week_picks:null,
 required_next_week_picks:null,saved_week5_picks:0,verified_week5_picks:0,
 used_team_count:0,verified_week5_result:false,
 ready_for_week6:false,automatic_rollover_permitted:false,
 external_pool_submission_verified:false,personal_only:true,
 ...fields,
})
const legitArray=v=>Array.isArray(v)&&v.length<5&&v.every(row=>row && typeof row==='object'&&!Array.isArray(row))
const isWin=x=>x?.entry_result==='WIN'
const validNames=picks=>{
 const names=picks.map(x=>String(x.team||'').trim())
 return names.every(name=>name.length>2&&name.length<=100)&&new Set(names).size===names.length
}

export function buildSurvivorNextRoundReadiness({entry,poolWeek,officialMeta}={}){
 if(!entry||typeof entry!=='object'||Array.isArray(entry))return view('NO_LINKED_ENTRY')
 const week=Number(poolWeek),ownerWeek=Number(entry.current_week)
 if(![5,6].includes(week)||![5,6].includes(ownerWeek))return view('POOL_WEEK_NOT_VERIFIED',{
  pool_week:Number.isInteger(week)?week:null,owner_entry_week:Number.isInteger(ownerWeek)?ownerWeek:null,
 })
 const weekFive=entry.week_5&&typeof entry.week_5==='object'?entry.week_5:{}
 const weekFivePicks=weekFive.picks||[]
 const savedWeek5=ownerWeek===5 && Array.isArray(entry.current_picks)?entry.current_picks.length:0
 const burned=Array.isArray(entry.used_teams)?entry.used_teams.length:0
 const primary=view('OFFICIAL_SOURCE_UNVERIFIED',{
  pool_week:week,owner_entry_week:ownerWeek,saved_week5_picks:savedWeek5,
  used_team_count:burned,required_current_week_picks:1,required_next_week_picks:2,
 })
 const weekRule=resolveWeekPickRule(5,weekFive)
 const nextRule=resolveWeekPickRule(6,entry.week_6||{})
 if(weekRule.rule_confirmed!==true||weekRule.required_picks!==1||
    nextRule.rule_confirmed!==true||nextRule.required_picks!==2 ||
    !legitArray(weekFivePicks)||savedWeek5>2){
  return {...primary,status:'SOURCE_CONFLICT_REVIEW_REQUIRED'}
 }
 const sourceWeek=Number(officialMeta?.max_week_in_file)
 if(!Number.isInteger(sourceWeek)||sourceWeek<1||sourceWeek>18||
  !/^[0-9a-f]{64}$/i.test(String(officialMeta?.source_sha256||''))||
  typeof officialMeta?.source_filename!=='string'||!officialMeta.source_filename.trim())return primary
 const officialFlag=weekFive.official_pool_sheet_confirmed===true
 const knownSheet=sourceWeek>=5
 const result=view('AWAITING_OFFICIAL_WEEK5_SHEET',{
  ...primary,official_source_week:sourceWeek,
  latest_source_kind:knownSheet?'ORGANIZER_WEEK5_SOURCE_AVAILABLE':'ORGANIZER_PDF_PRIOR_WEEK_ONLY',
  verified_week5_picks:knownSheet&&officialFlag?weekFivePicks.length:0,
 })
 if(officialFlag&&!knownSheet)return {...result,status:'OFFICIAL_SOURCE_CONFLICT'}
 if(!officialFlag){
  return {...result,status:entry.status==='ALIVE'?'AWAITING_OFFICIAL_WEEK5_SHEET':'UNVERIFIED_POOL_STATUS_REVIEW_REQUIRED'}
 }
 if(!legitArray(weekFivePicks)||!validNames(weekFivePicks)){
  return {...result,status:'SOURCE_CONFLICT_REVIEW_REQUIRED'}
 }
 if(!weekFivePicks.length)return {...result,status:'OFFICIAL_WEEK5_TICKET_ABSENT_REVIEW'}
 if(weekFivePicks.length!==1 || !["WIN","LOSS","OPEN","PENDING"].includes(String(weekFive.entry_result||''))){
  return {...result,status:'SOURCE_CONFLICT_REVIEW_REQUIRED'}
 }
 const poolResult=weekFive.picks[0].result
 if(weekFive.entry_result==='LOSS'&&poolResult==='LOSS'){
  return {...result,status:'OFFICIAL_WEEK5_ELIMINATED'}
 }
 if(entry.status!=='ALIVE')return {...result,status:'UNVERIFIED_POOL_STATUS_REVIEW_REQUIRED'}
 if(!isWin(weekFive)||poolResult!=='WIN'){
  return {...result,status:'WAITING_WEEK5_GAME_FINAL'}
 }
 const certified={...result,status:'WEEK5_SURVIVAL_CERTIFIED_NEXT_ROUND_PENDING',
   ready_for_week6:true,verified_week5_result:true,automatic_rollover_permitted:true,
   // Official imported entry proof is not proof this application itself
   // transmitted the team to the organizer. The two concepts stay separate.
   external_pool_submission_verified:false,
 }
 if(week===6){
  if(ownerWeek!==6)return {...certified,status:'WAITING_PRIVATE_WEEK6_ACTIVATION',ready_for_week6:false,
    automatic_rollover_permitted:false}
  return {...certified,status:'WEEK6_TWO_PICK_ROUND_READY'}
 }
 return certified
}
