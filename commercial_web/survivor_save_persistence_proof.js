// Authenticated server-only durable readback of a recent manual Survivor save.
// HTTP 200 or a Python success string is not a persistence receipt. This
// function checks the ORIGINAL private JSON from disk *after* the Python
// writer returns, without mutating history, pool selections or accounts.
const absent=()=>({status:'PERSISTENCE_NOT_VERIFIED',verified_disk_readback:false})
const matches=(a,b)=>Array.isArray(a)&&Array.isArray(b)&&a.length===b.length&&a.every((x,i)=>x===b[i])
export function verifySurvivorPickPersistence({state,entryName,poolWeek,teams,bridge,nowMs=Date.now()}={}){
 if(!state||typeof state!=='object'||!entryName||typeof entryName!=='string'||
    !Number.isInteger(poolWeek)||poolWeek<1||poolWeek>18||!Number.isFinite(nowMs)||
    !Array.isArray(teams)||!teams.length||teams.length>4||
    teams.some(team=>typeof team!=='string'||!team.trim())||new Set(teams).size!==teams.length){
   return absent()
 }
 if(bridge?.status!=='SAVED_NOT_SUBMITTED'||bridge?.entry_name!==entryName||
    bridge?.week!==poolWeek||bridge?.pool_submitted!==false||!matches(bridge?.teams,teams)){
   return absent()
 }
 const entry=state.entries?.[entryName],week=entry?.[`week_${poolWeek}`]
 if(Number(state.pool_current_week)!==poolWeek||entry?.status!=='ALIVE'||
    Number(entry.current_week)!==poolWeek||!matches(entry.current_picks,teams)||
    !['SAVED_NOT_SUBMITTED','INCOMPLETE_SAVED'].includes(entry.current_pick_status)||
    bridge.pick_status!==entry.current_pick_status||
    !Array.isArray(week?.picks)||week.picks.length!==teams.length||
    !matches(week.picks.map(row=>row?.team),teams)||
    week.manual_saved!==true||week.submitted!==false||
    ['WIN','LOSS'].includes(String(week.entry_result||'').toUpperCase())||
    week.picks.some(row=>row?.source!=='SPORTS_HULK_MANUAL_UI'||
      ['WIN','LOSS'].includes(String(row?.result||'').toUpperCase()))){
   return absent()
 }
 const time=Date.parse(week.manual_saved_at||'')
 if(!Number.isFinite(time)||nowMs-time>120_000||time>nowMs+5000)return absent()
 return {
  status:'PERSISTED_IN_ZENITH_NOT_EXTERNAL_POOL',verified_disk_readback:true,
  entry_name:entryName,week:poolWeek,teams:[...teams],
  pick_status:entry.current_pick_status,
  required_picks:Number.isInteger(week.required_picks)?week.required_picks:null,
  saved_at_utc:new Date(time).toISOString(),pool_submitted:false,
  external_organizer_submission_verified:false,
 }
}
