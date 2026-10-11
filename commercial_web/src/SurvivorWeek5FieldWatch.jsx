import React,{useEffect,useState} from 'react'
import {Activity,RefreshCw,ShieldCheck} from 'lucide-react'
const clock=v=>{
 const date=new Date(v||'')
 return Number.isFinite(date.valueOf())?new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(date):'not verified'
}
const mood=status=>status==='LIVE_AHEAD'?'text-emerald-700':status==='LIVE_BEHIND'?'text-red-700':status==='UPCOMING'?'text-[#536C76]':'text-amber-800'
const gameLabel=game=>({UPCOMING:'Upcoming',LIVE_AHEAD:'Live · ahead',LIVE_BEHIND:'Live · behind',LIVE_TIED:'Live · tied',FINAL_AWAITING_ORGANIZER:'Final · pool grading pending',SCORE_NOT_VERIFIED:'Score waiting'})[game?.status]||'Score waiting'
export default function SurvivorWeek5FieldWatch({entryName,getAccessToken}){
 const [value,setValue]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(false)
 useEffect(()=>{
  let active=true,controller=null
  const load=async()=>{
   if(!active)return
   setBusy(true)
   controller?.abort();controller=new AbortController()
   try{
    const bearer=await getAccessToken()
    if(!bearer)throw Error('Account not authenticated')
    const url='/api/survivor/field-watch?entry='+encodeURIComponent(entryName)+'&at='+Date.now()
    const res=await fetch(url,{headers:{Authorization:'Bearer '+bearer},cache:'no-store',signal:controller.signal})
    if(!res.ok)throw Error('Field feed unavailable')
    const next=await res.json()
    if(active){setValue(next);setError(false)}
   }catch(e){if(active&&e.name!=='AbortError')setError(true)}
   finally{if(active)setBusy(false)}
  }
  void load()
  const timer=window.setInterval(()=>{if(document.visibilityState==='visible')void load()},120_000)
  const visible=()=>{if(document.visibilityState==='visible')void load()}
  document.addEventListener('visibilitychange',visible)
  return()=>{active=false;controller?.abort();clearInterval(timer);document.removeEventListener('visibilitychange',visible)}
 },[entryName,getAccessToken])
 if(!value&&error)return <section aria-label="Week 5 full field tracker" className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-xs font-semibold text-amber-900">Week 5 field tracking is temporarily unavailable; your official pool file and picks are unchanged.</section>
 return <section aria-label="Week 5 full field tracker" data-week5-full-field className="min-w-0 rounded-[22px] border border-[#A9CAC8] bg-[#EFF8F5] p-3 text-[#173E52] sm:p-4">
  <div className="flex flex-wrap items-start justify-between gap-2">
   <div><p className="text-[10px] font-black uppercase tracking-[.13em] text-[#167982]">Knockout Pool · Sunday Field Watch</p>
   <h2 className="mt-1 text-base font-black">All 333 tickets · Week 5</h2></div>
   <span className="inline-flex items-center gap-1 rounded-lg bg-white px-2 py-1 text-[10px] font-black text-[#116B76]"><RefreshCw size={12} className={busy?'animate-spin':''}/> Auto-refreshes every 2 min</span>
  </div>
  {value?.status==='VERIFIED_OFFICIAL_FIELD'?<>
    <div className="mt-3 grid grid-cols-3 gap-1.5 text-center">
      {[['Original field',value.total_entries],['Marked Dallas losses',value.marked_eliminated_before_sunday],['In play before Sunday',value.in_contention_before_sunday]].map(([label,count])=><div key={label} className="min-w-0 rounded-lg border border-[#D7E8E1] bg-white p-2"><div className="text-xl font-black tabular-nums">{count}</div><div className="text-[9px] font-bold leading-3 text-[#536F78]">{label}</div></div>)}
    </div>
    {value.owner&&<div className="mt-2 rounded-xl border border-[#8CC3BC] bg-white px-3 py-2.5">
      <p className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-wide text-[#146B74]"><ShieldCheck size={13}/> My organizer ticket · {value.owner.entry_name}</p>
      <p className="mt-1 text-sm font-black">{value.owner.official_teams.length?value.owner.official_teams.join(' + '):'Exact numbered ticket not matched'}</p>
      {value.owner.synchronization==='ORGANIZER_PDF_ONLY_NOT_ZENITH_SAVED'&&<p className="mt-1 text-[11px] font-semibold text-amber-800">Confirmed on organizer’s Week 5 sheet; not saved in Zenith’s separate pick editor.</p>}
    </div>}
    {value.live_exposure && <div className="mt-3 grid grid-cols-3 gap-1.5 text-center" aria-label="Provisional live tickets">
      {[['Live ahead',value.live_exposure.currently_ahead],['Live behind',value.live_exposure.currently_behind],['Live tied',value.live_exposure.currently_tied]].map(([label,count])=><div key={label} className="rounded-lg border border-[#D3E5E0] bg-white px-1.5 py-2"><div className="text-lg font-black tabular-nums">{count}</div><div className="text-[9px] font-bold text-[#536F78]">{label}</div></div>)}
      <p className="col-span-3 text-left text-[10px] font-medium leading-4 text-[#5C727B]">ESPN game positions only, never official survival. {value.live_exposure.final_games_pending_pool_grade} tickets have final scores still awaiting organizer grading; {value.live_exposure.waiting_or_unverified} tickets await games or verified scores.</p>
    </div>}
    <div className="mt-3 flex items-center justify-between gap-2"><p className="text-xs font-black">Sunday teams · tickets at stake</p><p className="text-[10px] text-[#647B83]">ESPN {value.scoreboard_status==='ESPN_CURRENT'?`updated ${clock(value.scoreboard_updated_at)}`:'score update pending'}</p></div>
    <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
    {value.teams.map(item=><div key={item.team} className="flex min-w-0 items-center justify-between gap-2 rounded-lg border border-[#D4E3DF] bg-white p-2">
      <div className="min-w-0"><p className="truncate text-xs font-black">{item.team}</p><p className={'text-[10px] font-semibold '+mood(item.game?.status)}>{gameLabel(item.game)}{item.game?.opponent?' vs '+item.game.opponent:''}</p>{item.game?.score_line&&<p className="text-[10px] font-semibold text-[#526A72]">{item.game.score_line}</p>}</div>
      <div className="shrink-0 text-right"><p className="text-lg font-black tabular-nums">{item.entries}</p><p className="text-[9px] font-semibold text-[#64818A]">tickets</p></div>
    </div>)}
    </div>
    <p className="mt-2 text-[10px] font-medium leading-4 text-[#5C727B]">148 Dallas losses are marked on the organizer PDF. The 185 figure is before Sunday's results, not a continuously certified remaining count. ESPN live scores do not certify pool survival. Only organizer evidence can settle entries.</p>
   </>:<p className="mt-3 text-xs font-bold text-amber-800">{busy?'Loading the official pool field…':'Verified Week 5 field data is not yet available.'}</p>}
 </section>
}
