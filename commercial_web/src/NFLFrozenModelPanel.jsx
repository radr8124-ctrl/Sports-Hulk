import React, {useEffect,useMemo,useState} from 'react'
import {Activity,CalendarClock,ChevronRight,Database,Info,ShieldAlert} from 'lucide-react'
import {showFrozenNFLResearch} from '../nfl_frozen_forecast_presentation.js'

const timeLabel=value=>{
 const n=Date.parse(value||'')
 if(!Number.isFinite(n))return 'Unknown source time'
 return new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZone:'America/New_York',timeZoneName:'short'}).format(n)
}
const pp=value=>{
 const n=Number(value)
 if(!Number.isFinite(n))return 'Unavailable'
 return `${n>=0?'+':''}${n.toFixed(2)} pp`
}

// This does NOT add unverified sportsbook picks. It reveals original
// market-assisted frozen forecasts in their own strictly labeled research area.
export default function NFLFrozenModelPanel({data}) {
 const [expanded,setExpanded]=useState(false)
 const [feed,setFeed]=useState(null)
 useEffect(()=>{
   if (data) return undefined
   let active=true
   const load=async()=>{
     try {
       const response=await fetch(`/nfl_frozen_game_intelligence.json?ts=${Date.now()}`,{cache:'no-store'})
       if (!response.ok) throw new Error('Unavailable frozen model evidence')
       const next=await response.json()
       if(active) setFeed(next)
     } catch {
       if(active) setFeed(null)
     }
   }
   load()
   const id=window.setInterval(load,300000)
   return()=>{active=false;window.clearInterval(id)}
 },[data])
 const selected=useMemo(()=>showFrozenNFLResearch(data||feed),[data,feed])
 const all=selected.rows
 const shown=expanded?all:all.slice(0,3)
 return (
   <section aria-label="NFL frozen model forecasts" className="rounded-2xl border border-slate-200 bg-white p-3 shadow-soft md:p-4">
     <div className="flex flex-wrap items-center justify-between gap-3">
       <div className="flex min-w-0 items-center gap-2 text-sm font-black text-slate-900">
         <Activity size={18} className="shrink-0 text-blue-700" />
         What the NFL model actually predicts
       </div>
       <span className="rounded-full bg-amber-50 px-3 py-1 text-[10px] font-black text-amber-800">
         Frozen research · 0 proven betting edges
       </span>
     </div>
     <p className="mt-2 text-xs leading-5 text-slate-600">
       These are original pregame nine-feature forecasts, compared with the <b>same captured Pinnacle moneyline</b> after removing bookmaker margin.
       The 2025 holdout did not beat the market. These are <b>not approved plays, spread forecasts, or live sportsbook quotes.</b>
     </p>
     {selected.status!=='FROZEN_RESEARCH' && (
       <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-semibold text-amber-900">
         Verified frozen model history is unavailable. No forecast has been fabricated.
       </div>
     )}
     {selected.status==='FROZEN_RESEARCH'&&!all.length && (
       <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs font-semibold text-slate-600">
         No future official matchups remain in this frozen research set; wait for the next verified pregame source.
       </div>
     )}
     {shown.length>0 && (
       <div className="mt-3 grid gap-2 xl:grid-cols-2">
         {shown.map(g=>{
           const mostLikelyHome=g.forecast_home_pct>=50
           const mainPct=mostLikelyHome?g.forecast_home_pct:g.forecast_away_pct
           return (
             <article key={g.event_id} className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
               <div className="flex flex-wrap items-center justify-between gap-2">
                 <div className="text-sm font-black text-slate-900">{g.away} @ {g.home}</div>
                 <div className="inline-flex items-center gap-1 text-[11px] text-slate-500">
                   <CalendarClock size={12}/>{timeLabel(g.kickoff_utc)}
                 </div>
               </div>
               <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
                 <div>
                   <div className="text-[10px] font-black uppercase tracking-wide text-blue-700">Frozen Zenith research forecast</div>
                   <div className="mt-0.5 text-sm font-black text-slate-900">{g.forecast_side_team} to win · {mainPct.toFixed(1)}%</div>
                 </div>
                 <div className="text-right">
                   <div className="text-[10px] font-semibold text-slate-500">Model vs original book</div>
                   <div className="text-sm font-black text-slate-700">{pp(g.delta_model_minus_book_home_pp)} <span className="text-[10px] font-semibold text-slate-500">home</span></div>
                 </div>
               </div>
               <div className="mt-2 text-[11px] font-semibold leading-5 text-slate-500">
                 {g.originalPriceTooOldForLiveContext
                    ? 'Original quote is over 24 hours old; do not treat it as current.'
                    : 'Original quote is under 24 hours old; not independently verified executable.'}
               </div>
               <details className="mt-2 rounded-lg border border-slate-200 bg-white">
                 <summary className="flex min-h-10 cursor-pointer list-none items-center justify-between px-3 py-2 text-xs font-black text-slate-700">
                   <span>Show model vs bookmaker evidence</span><ChevronRight size={14} className="text-slate-400"/>
                 </summary>
                 <div className="border-t border-slate-100 px-3 py-2 text-[11px] leading-5 text-slate-600">
                   <div>Zenith model home win: <b>{g.forecast_home_pct.toFixed(2)}%</b>; away: <b>{g.forecast_away_pct.toFixed(2)}%</b>.</div>
                   <div>Original Pinnacle no-vig fair home: <b>{g.book_market_fair_home_pct.toFixed(2)}%</b>; away: <b>{g.book_market_fair_away_pct.toFixed(2)}%</b>.</div>
                   <div>Original observed Pinnacle ML: home <b>{g.original_home_american_price>0?'+':''}{g.original_home_american_price}</b>; away <b>{g.original_away_american_price>0?'+':''}{g.original_away_american_price}</b>.</div>
                   <div>Source quote last updated: <b>{timeLabel(g.book_quote_last_updated_at_utc)}</b>; frozen forecast: {timeLabel(g.forecast_frozen_at_utc)}.</div>
                   <div>Inputs include original book probability, prior scoring margin, offense-versus-defense form, rest and neutral venue. Feature contributions were not individually validated.</div>
                   <div className="mt-1 font-bold text-amber-800">No demonstrated independent edge. Neither a fresh offered quote nor a wager. The forecast is primarily market-assisted.</div>
                 </div>
               </details>
             </article>
           )
         })}
       </div>
     )}
     {!expanded&&all.length>shown.length && (
       <button type="button" onClick={()=>setExpanded(true)} className="mt-3 min-h-10 rounded-xl border border-blue-200 bg-white px-4 text-xs font-black text-blue-700">
         Show all {all.length} frozen game forecasts
       </button>
     )}
     <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 text-[11px] font-semibold text-slate-500">
       <span className="inline-flex items-center gap-1"><ShieldAlert size={13} /> {all.length} independent games frozen · paper research only</span>
       <a href="#brain-record" className="inline-flex items-center gap-1 font-black text-blue-700">
         Verify model record <ChevronRight size={13}/>
       </a>
     </div>
   </section>
 )
}
