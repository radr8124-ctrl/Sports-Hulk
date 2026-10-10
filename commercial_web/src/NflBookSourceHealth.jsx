import React,{useEffect,useState} from 'react'
import {ChevronRight,ShieldAlert} from 'lucide-react'

const dateET=iso=>{
 const time=Date.parse(iso||'')
 return Number.isFinite(time)?new Intl.DateTimeFormat('en-US',{
  month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZone:'America/New_York',
  timeZoneName:'short',
 }).format(new Date(time)):'Unverified'
}
const count=n=>Number.isInteger(n)?n.toLocaleString('en-US'):'—'

// Public source authority; not an account, a bookmaker integration, or a pick.
export default function NflBookSourceHealth(){
 const [data,setData]=useState(null)
 const [state,setState]=useState('LOADING')
 useEffect(()=>{
  let running=true
  const poll=async()=>{
   try{
    const response=await fetch('/api/nfl/book-source-health?ts='+Date.now(),{cache:'no-store'})
    const source=await response.json()
    if(!running)return
    if(response.ok&&source?.no_approved_bet_or_survivor_pick_created===true){
     setData(source);setState('VERIFIED')
    }else{setData(null);setState('UNAVAILABLE')}
   }catch{if(running){setData(null);setState('UNAVAILABLE')}}
  }
  poll()
  const interval=window.setInterval(poll,120*1000)
  return()=>{running=false;window.clearInterval(interval)}
 },[])
 const verified=state==='VERIFIED'&&data&&Number.isInteger(data.official_upcoming_games)
 return (
  <section aria-label="NFL bookmaker source authority status" data-nfl-book-source-health
   data-source-health-status={verified?data.status:state}
   className="min-w-0 overflow-hidden rounded-xl border border-[#D1DED8] bg-[#F1F8F4] px-3 py-2.5 text-[#173E52] sm:px-4">
   <div className="flex flex-wrap items-center justify-between gap-2">
    <p className="text-[10px] font-black uppercase tracking-[.09em] text-[#0E7280] sm:tracking-[.12em]">
      <span className="sm:hidden">NFL SOURCE CHECK</span>
      <span className="hidden sm:inline">NFL SOURCE AUTHORITY · ORIGINAL TIMESTAMPS</span>
    </p>
    <span className="shrink-0 rounded-md border border-[#E2C29B] bg-[#FFF5E6] px-2 py-1 text-[9px] font-black text-[#855B25]">
      <span className="sm:hidden">NOT LIVE</span><span className="hidden sm:inline">NOT VERIFIED LIVE OFFERS</span>
    </span>
   </div>
   {!verified?(
    <p className="mt-1.5 text-[11px] font-semibold leading-4 text-slate-600">
     <ShieldAlert size={13} className="mr-1 inline text-amber-700" />
     {state==='LOADING'?'Checking original NFL bookmaker times and independent fixture identities…':
      'Original source verification unavailable. No current sportsbook offer or qualified pick can be inferred.'}
    </p>
   ):(
    <>
     <div className="mt-2 grid grid-cols-2 gap-2 text-[11px]">
      <div className="min-w-0 rounded-lg border border-[#D5E0DB] bg-white px-2.5 py-2">
       <p className="font-black"><span className="sm:hidden">Primary feed</span><span className="hidden sm:inline">Original primary feed</span></p>
       <p className="mt-0.5 font-semibold tabular-nums text-[#7D4D27]">{count(data.primary_fresh_game_count)} / {count(data.official_upcoming_games)} <span className="sm:hidden">fresh</span><span className="hidden sm:inline">timestamps fresh</span></p>
      </div>
      <div className="min-w-0 rounded-lg border border-[#D5E0DB] bg-white px-2.5 py-2">
       <p className="font-black">Research archive</p>
       <p className="mt-0.5 font-semibold tabular-nums text-[#0E7280]">{count(data.research_recent_paired_games)} / {count(data.official_upcoming_games)} <span className="sm:hidden">paired</span><span className="hidden sm:inline">dated pairs</span></p>
      </div>
     </div>
     <details className="group mt-2 rounded-lg border border-[#C8DCD6] bg-white px-2.5 py-2">
      <summary className="flex min-h-5 cursor-pointer list-none items-center justify-between gap-2 text-[10px] font-black leading-4 text-[#173E52]">
       <span><span className="sm:hidden">Why isn't this a live offer?</span><span className="hidden sm:inline">Why research does not equal a qualified sportsbook price</span></span>
       <ChevronRight size={15} className="shrink-0 transition group-open:rotate-90" />
      </summary>
      <div className="mt-2 space-y-1 border-t border-[#E3EAE7] pt-2 text-[11px] font-medium leading-5 text-slate-600">
       <p><b>Propline original primary source:</b> Latest matched provider quote updated {dateET(data.primary_latest_provider_at)}.
        {' '}{count(data.primary_live_label_but_stale_count)} rows carry a LIVE text label but fail source-time freshness.
        LIVE text is not a verified timestamp or an executable offer.</p>
       <p><b>SportWizzard archived research:</b> SHA-256 of the original historical CSV {data.research_archive_verified?'verified':'unverified'}.
        Capture {dateET(data.research_capture_at)}. Two-sided same-book observations are not confirmed available for a real account, a verified main line or independent model advantage.</p>
       <p><b>Alternate provider:</b> {data.alternate_quota_status==='QUOTA_LIMITED_AT_LAST_CAPTURE'
        ? 'TheRundown last recorded quota limit; no verified fallback prices.':'Quota/fallback availability not verified.'}</p>
       <p className="font-bold text-amber-800">No independent model edge, executable price, approved bet, or Survivor pick is established by this source audit.</p>
      </div>
     </details>
    </>
   )}
  </section>
 )
}
