// Historical Survivor timeline from a previously authenticated PRIVATE entry.
// Source of truth: entry.history. The separate week_N saved-pick record is used
// only for independent grade/score consistency; used_teams is a cross-check,
// not permission to invent a historical week or a pool submission.
const WIN=new Set(['WIN','SURVIVED'])
const LOSS=new Set(['LOSS','LOST'])
const clean=s=>typeof s==='string'?s.trim():''
const verdict=value=>{
 const key=clean(value).toUpperCase()
 return WIN.has(key)?'SURVIVED':LOSS.has(key)?'LOST':'REVIEW_REQUIRED'
}
const statusOnly=(status,week,entry)=>({
 status,current_week:week||null,
 current_picks_saved:Array.isArray(entry?.current_picks)?entry.current_picks.length:0,
 used_team_count:Array.isArray(entry?.used_teams)?entry.used_teams.length:0,
 total_picks:0,total_weeks:0,week_groups:[],external_pool_submission_verified:false,
 source_status:'RECORDED_PRIVATE_POOL_HISTORY_NOT_EXTERNAL_ORGANIZER_CONFIRMATION',
})
export function buildSurvivorPastPickHistory(entry,poolWeek){
 if(!entry||typeof entry!=='object'||!Number.isInteger(poolWeek)||poolWeek<1||poolWeek>25){
  return statusOnly('NO_LINKED_ENTRY',poolWeek,entry)
 }
 if(!Array.isArray(entry.history)||entry.history.length===0){
  return statusOnly('HISTORY_UNAVAILABLE',poolWeek,entry)
 }
 if(entry.history.length>120)return statusOnly('HISTORY_CONFLICT_NEEDS_REVIEW',poolWeek,entry)
 const used=Array.isArray(entry.used_teams)?new Set(entry.used_teams.map(clean)):new Set()
 const seen=new Set(),groups=new Map()
 let conflict=false
 for(const record of entry.history){
  const week=Number(record?.week),team=clean(record?.team)
  // Ignore current/future rows; never call Week 5 an archived past pick.
  if(!Number.isInteger(week)||week<1||week>=poolWeek||!team||team.length>120){
   if(record?.week!=null&&Number(record.week)<poolWeek)conflict=true
   continue
  }
  const id=week+'|'+team.toUpperCase()
  if(seen.has(id)){
   conflict=true
   const old=groups.get(week)?.picks.find(item=>item.team===team)
   if(old){old.result='REVIEW_REQUIRED';old.review_reason='DUPLICATE_ORIGINAL_RECORD'}
   continue
  }
  seen.add(id)
  const weekRecord=entry[`week_${week}`]||{}
  const saved=Array.isArray(weekRecord.picks)
    ?weekRecord.picks.filter(row=>clean(row?.team)===team):[]
  const historic=verdict(record.result)
  let result=historic
  let reviewReason=null
  if(!used.has(team))reviewReason='NOT_IN_USED_TEAM_HISTORY'
  else if(saved.length>1)reviewReason='DUPLICATE_WEEK_PICK_RECORD'
  else if(saved.length===1 && verdict(saved[0].result)!==historic)reviewReason='WEEK_GRADE_MISMATCH'
  else if(saved.length===0 && Array.isArray(weekRecord.picks)&&weekRecord.picks.length>0){
   reviewReason='HISTORY_NOT_IN_WEEK_PICK_RECORD'
  }
  if(historic==='REVIEW_REQUIRED')reviewReason ||= 'NO_RECORDED_TERMINAL_RESULT'
  if(reviewReason){result='REVIEW_REQUIRED';conflict=true}
  const scoreRaw=clean(saved[0]?.game_status)
  const gameScore=saved.length===1&&!reviewReason&&scoreRaw.startsWith('FINAL:')
    ?scoreRaw.slice(6).trim():null
  const pick={
   week,team,result,
   game_score:gameScore,
   original_source:clean(record.source)||null,
   source_kind:'RECORDED_PERSONAL_POOL_HISTORY',
   external_submitted_verified:false,
   ...(reviewReason?{review_reason:reviewReason}:{}),
  }
  if(!groups.has(week)){
   groups.set(week,{
    week,required_picks:Number.isInteger(weekRecord.required_picks)?weekRecord.required_picks:null,
    picks:[],
    official_sheet_recorded:weekRecord.official_pool_sheet_confirmed===true,
    submission_status:weekRecord.submitted===true?'SUBMISSION_RECORDED_IN_ZENITH':
      weekRecord.submitted===false?'SUBMISSION_NOT_RECORDED':'SUBMISSION_UNKNOWN',
   })
  }
  groups.get(week).picks.push(pick)
 }
 const weekGroups=[...groups.values()].sort((a,b)=>a.week-b.week)
 const total=weekGroups.reduce((n,g)=>n+g.picks.length,0)
 if(!total)return statusOnly('HISTORY_UNAVAILABLE',poolWeek,entry)
 if(total!==used.size)conflict=true
 return {
  status:conflict?'HISTORY_CONFLICT_NEEDS_REVIEW':'RECORDED_HISTORY_COMPLETE',
  current_week:poolWeek,current_picks_saved:Array.isArray(entry.current_picks)?entry.current_picks.length:0,
  used_team_count:used.size,total_picks:total,total_weeks:weekGroups.length,
  week_groups:weekGroups,external_pool_submission_verified:false,
  source_status:'RECORDED_PRIVATE_POOL_HISTORY_NOT_EXTERNAL_ORGANIZER_CONFIRMATION',
 }
}
