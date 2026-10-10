import React from 'react'
import {ChevronRight,ShieldAlert} from 'lucide-react'
import {projectPropForwardTruth} from '../prop_forward_truth.js'

const order=['NFL','NBA','NHL','MLB']
const count=n=>Number.isInteger(n)?n.toLocaleString('en-US'):'—'
const brier=n=>typeof n==='number'&&Number.isFinite(n)?n.toFixed(5):'—'
const label=code=>{
 if(code==='MODEL_WORSE_THAN_MARKET')return 'Model worse than market'
 if(code==='NO_DEMONSTRATED_MARKET_DIFFERENCE')return 'No improvement over market'
 if(code==='MODEL_BETTER_THAN_MARKET_IN_RESEARCH_ONLY')return 'Lower model Brier in research only'
 if(code==='AWAITING_SETTLEMENT')return 'Awaiting verified results'
 return 'Not pooled across sports'
}
const marketLabel=v=>v==='MODEL_WORSE_THAN_MARKET'?'text-rose-700':
 v==='MODEL_BETTER_THAN_MARKET_IN_RESEARCH_ONLY'?'text-amber-800':'text-[#526D7A]'
const recorded=iso=>{
 const ms=Date.parse(iso||'')
 return Number.isFinite(ms)?new Intl.DateTimeFormat('en-US',{
  month:'short',day:'numeric',hour:'numeric',minute:'2-digit',
  timeZone:'America/New_York',timeZoneName:'short',
 }).format(ms):'Time unverified'
}

export default function PropForwardProofLens({current,forward,lane='PROP',sport='ALL',clock}){
 const state=projectPropForwardTruth({current,forward,lane,sport,atMs:clock})
 const loading=forward===undefined && !current?.generated_at
 const sourceStatus=loading?'LOADING':state.status
 const prize=lane==='PRIZEPICKS'
 const verified=state.status==='SOURCE_TRACKED_RESEARCH_ONLY'
 const segment=sport!=='ALL'
 const sample=loading?'Checking forward results…':verified?`${count(state.settled)} settled ${prize?'leg':'prop'} records`:'No verifiable forward sample'
 return (
  <section aria-label={prize?'PrizePicks forward result proof':'Props forward result proof'}
   data-prop-forward-proof data-proof-source-status={sourceStatus}
   className="rounded-2xl border border-[#C8D9D4] bg-[#EAF7F2] px-3 py-3 text-[#173E52] sm:px-4">
   <div className="flex flex-wrap items-start justify-between gap-x-2 gap-y-1">
    <div className="min-w-0">
     <div className="text-[10px] font-black uppercase tracking-[.12em] text-[#0E7280]">
      FORWARD EVIDENCE · {segment?sport:'SPORT-BY-SPORT'}
     </div>
     <h3 className="mt-0.5 text-sm font-black leading-5">{sample}</h3>
    </div>
    <span className="hidden rounded-lg border border-[#DEB9A8] bg-[#FFF8ED] px-2 py-1 text-[9px] font-black uppercase text-[#98523F] sm:inline-flex">
      Not a qualified bet
    </span>
   </div>
   {loading?(
    <p data-prop-proof-verdict className="mt-1 text-[11px] font-semibold leading-5 text-[#536D7A]">Loading timestamped sport-by-sport model results. No prediction or profit will be assumed.</p>
   ):verified?(
    <>
     <div data-prop-proof-verdict className="mt-1 text-[10px] font-semibold leading-[1.4] text-[#4B6570] sm:mt-1.5 sm:text-[11px] sm:leading-[1.55]">
      <p className="sm:hidden">
       {segment
        ? `${label(state.relative_model_reading)}. ${state.settled?`${count(state.independent_blocks)} game blocks · Brier difference ${state.v2_minus_market_brier>=0?'+':''}${brier(state.v2_minus_market_brier)}.`:'No verified settled results.'}`
        : 'Separate sport samples. No proven model advantage.'}
       {' '}{prize?'Full-entry payout not verified.':'Not a proven winning strategy.'}
      </p>
      <p className="hidden sm:block">
       {segment?(
        <>
         <b className={marketLabel(state.relative_model_reading)}>{label(state.relative_model_reading)}.</b>{' '}
         {state.settled?`${count(state.independent_blocks)} reported game blocks; Brier difference ${state.v2_minus_market_brier>=0?'+':''}${brier(state.v2_minus_market_brier)} (lower is better).`:
          'No independently settled observations in this sport yet.'}
        </>
       ):'These are separate sport samples, not one pooled model advantage. None qualifies a current selection.'}
       {' '}{prize?'Individual legs do not prove full-entry payout.':'Historical hit rate alone does not establish profitable bets.'}
      </p>
     </div>
     <details className="group mt-2 rounded-xl border border-[#C1D7D7] bg-white px-3 py-2 text-[#173E52]">
      <summary className="flex min-h-6 cursor-pointer list-none items-center justify-between gap-2 text-[11px] font-black">
       <span>Open sport-by-sport proof</span>
       <ChevronRight size={15} className="shrink-0 text-[#0E7280] transition group-open:rotate-90"/>
      </summary>
      <div className="mt-2 space-y-2 border-t border-[#E5ECE9] pt-2">
       {state.sport_breakdown.sort((a,b)=>order.indexOf(a.sport)-order.indexOf(b.sport)).map(row=>(
        <div key={row.sport} data-forward-sport={row.sport}
         className="min-w-0 rounded-lg border border-[#E3EAE9] bg-[#F8FAF8] px-2.5 py-2 text-[10px] font-semibold leading-[1.5] text-[#496471]">
         <div className="flex flex-wrap justify-between gap-x-2">
          <span className="font-black text-[#173E52]">{row.sport} · {count(row.settled)} settled · {count(row.independent_blocks)} game blocks</span>
          <span className={marketLabel(row.relative_model_reading)}>{label(row.relative_model_reading)}</span>
         </div>
         {row.settled>0&&(
          <p className="mt-0.5">Original bookmaker Brier {brier(row.market_brier)} · Zenith research Brier {brier(row.v2_brier)}
           {' '}· hit rate {row.hit_rate_pct==null?'—':row.hit_rate_pct+'%'} (not proof of edge)</p>
         )}
         {row.paper_roi_pct!==null&&!prize&&(
          <p className="mt-0.5 font-bold text-[#6D4B39]">Reference-price paper ROI {row.paper_roi_pct>0?'+':''}{row.paper_roi_pct}% · simulated research only, not your actual profit</p>
         )}
        </div>
       ))}
       <p className="text-[10px] font-semibold leading-4 text-slate-600">
        {prize
         ? 'No full-entry pick-em payout or correlation proof. Leg-level pricing-proxy ROI is deliberately not displayed.'
         : 'Research prices may be old or non-executable. No current approved sportsbook bet or independently established profit.'}
       </p>
       <p className="text-[10px] font-medium text-slate-500">Source: original V2 forward shadow ledger, captured {recorded(state.source_generated_at)}. Different sports stay separate; model coefficients are unchanged.</p>
      </div>
     </details>
    </>
   ):(
    <p data-prop-proof-verdict className="mt-2 flex items-start gap-1.5 text-[11px] font-semibold leading-5 text-amber-900">
     <ShieldAlert size={14} className="mt-0.5 shrink-0" />
     Model versions, results or source timestamps could not be verified. Performance figures are withheld; no profitable selection is implied.
    </p>
   )}
  </section>
 )
}
