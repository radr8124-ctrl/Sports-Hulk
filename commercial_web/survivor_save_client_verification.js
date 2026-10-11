// Pure browser-safe second readback check, called only after successful POST.
// A generic 200 status or a stale private response must NEVER say 'Saved'.
const compare=(a,b)=>Array.isArray(a)&&Array.isArray(b)&&
 a.length===b.length&&a.every((item,i)=>item===b[i])
export function verifySurvivorSavedAgainstPrivateState({receipt,state,entryName,week,teams}={}){
 const validSave=['SAVED_NOT_SUBMITTED','INCOMPLETE_SAVED'].includes(receipt?.pick_status)
 const required=receipt?.required_picks
 const validCount=Number.isInteger(required)&&required>0&&required<=4&&
   teams.length<=required&&
   (receipt?.pick_status==='INCOMPLETE_SAVED'?teams.length<required:teams.length===required)
 const serverOk=receipt?.status==='PERSISTED_IN_ZENITH_NOT_EXTERNAL_POOL'&&
  receipt.verified_disk_readback===true&&receipt.entry_name===entryName&&
  receipt.week===week&&compare(receipt.teams,teams)&&validSave&&validCount&&
  receipt.pool_submitted===false&&receipt.external_organizer_submission_verified===false
 if(!serverOk)return {status:'SERVER_SAVE_NOT_VERIFIED',success:false}
 const dashboardOk=state?.status==='READY'&&state.entry_linked===true&&
  state.active_entry===entryName&&Number(state.pool_current_week)===week&&
  state.entry_status==='ALIVE'&&compare(state.current_picks,teams)&&
  state.current_pick_status===receipt.pick_status&&state.required_picks===required
 if(!dashboardOk)return {status:'DASHBOARD_READBACK_NOT_VERIFIED',success:false}
 return {status:'CONFIRMED_IN_ZENITH_ONLY',success:true,
  complete:receipt.pick_status==='SAVED_NOT_SUBMITTED',required_picks:required}
}
