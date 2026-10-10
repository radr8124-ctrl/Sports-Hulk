import React,{useEffect,useState} from 'react'
import {AlertTriangle,ChevronRight,FileCheck2,ShieldCheck,TrendingDown} from 'lucide-react'

const whole=n=>typeof n==='number'&&Number.isFinite(n)?n.toLocaleString('en-US'):'—'
const metric=n=>typeof n==='number'&&Number.isFinite(n)?n.toFixed(4):'Pending Finals'
const shortHash=s=>typeof s==='string'&&/^[0-9a-f]{64}$/i.test(s)?s.slice(0,12):'Unverified'

export default function NflModelValidationPanel(){
 const [state,setState]=useState({status:'LOADING'})
 useEffect(()=>{
  let cancelled=false
  const load=async()=>{
   try{
    const res=await fetch('/api/nfl/model-validation?ts='+Date.now(),{cache:'no-store'})
    const answer=await res.json()
    if(!cancelled){
     setState(res.ok&&answer?.status?answer:{status:'SOURCE_UNAVAILABLE'})
    }
   }catch{if(!cancelled)setState({status:'SOURCE_UNAVAILABLE'})}
  }
  load()
  const timer=window.setInterval(load,60*1000)
  return()=>{cancelled=true;window.clearInterval(timer)}
 },[])
 const ready=state.status==='AWAITING_INDEPENDENT_FINALS'||
   state.status==='OFFICIAL_FINAL_AWAITING_VALIDATED_GRADE'||
   state.status==='TINY_FORWARD_SAMPLE_NOT_MARKET_EDGE'||
   state.status==='DIAGNOSTIC_REVIEW_ONLY_NOT_PROVEN_EDGE'
 const scored=ready&&Number(state.compared_games)>0
 const floor=ready?Math.max(0,Number(state.remaining_to_first_review||0)):null
 return (
  <section aria-label="NFL model versus market validation" data-nfl-model-validation
   className="relative overflow-hidden rounded-[24px] border-2 border-[#173E52] bg-[#173E52] p-4 text-[#FFF8ED] shadow-[4px_4px_0_#46CDD247] md:p-6">
   <div aria-hidden="true" className="absolute inset-x-0 top-0 h-[5px] bg-[linear-gradient(90deg,#FF7766_0%,#FF7766_35%,#FFD36A_35%,#FFD36A_65%,#46CDD2_65%,#46CDD2_100%)]"/>
   <div className="flex flex-wrap items-start justify-between gap-2">
    <div className="min-w-0 flex-1">
     <p className="text-[10px] font-black uppercase tracking-[.16em] text-[#7CE2DF]">THE NFL PROOF LAB · FORWARD RESULTS</p>
     <h2 className="mt-1 text-xl font-black tracking-tight text-[#FFF8ED] md:text-2xl">Can Zenith actually beat the market?</h2>
     <p className="mt-1 max-w-3xl text-[11px] font-medium leading-[1.55] text-[#DEEBE8] md:text-xs">
      Same pregame games, same frozen bookmaker reference, independent official Final scores. No retroactive picks or model changes.
     </p>
    </div>
    <span className="hidden rounded-lg border border-[#67A5A2] bg-[#244C5D] px-3 py-1.5 text-[10px] font-black tracking-wide text-[#FFD36A] md:inline-flex">
     NO UNVERIFIED WINNING CLAIMS
    </span>
   </div>
   {!ready?(
    <div className="mt-3 rounded-xl border border-[#C48C5B]/60 bg-[#304D59] px-3 py-3 text-xs font-semibold leading-5 text-[#FFF4E2]">
     <AlertTriangle size={15} className="mr-1 inline text-[#FFD36A]"/>
     {state.status==='LOADING'?'Checking the immutable pregame ledger and independently verified results…':
      'Original NFL model or Final-source integrity could not be verified. Scores are hidden until the evidence agrees.'}
    </div>
   ):(
    <>
     <div className="mt-4 grid grid-cols-3 gap-1.5 rounded-xl bg-[#FFF8ED] p-1.5 text-center text-[#173E52] sm:gap-2 sm:p-2">
      {[
       ['frozen',state.frozen_games,'Frozen games'],
       ['settled',state.compared_games,'Paired Finals'],
       ['floor',state.review_floor,'First review floor'],
      ].map(([id,count,label])=>(
       <div data-nfl-proof-metric={id} key={id} className="min-w-0 rounded-lg bg-white px-1 py-2 sm:px-2">
        <div className="text-xl font-black leading-none tabular-nums sm:text-2xl">{whole(count)}</div>
        <div className="mt-1 text-[9px] font-bold leading-3 text-[#517381] sm:text-[10px]">{label}</div>
       </div>
      ))}
     </div>
     <div className="mt-3 rounded-xl border border-[#B5B5A2]/50 bg-[#234B5E] px-3 py-2.5 text-xs leading-5 text-[#E9F3EF]">
      <div className="flex items-start gap-2">
       <ShieldCheck size={16} className="mt-0.5 shrink-0 text-[#FFD36A]"/>
       <p><b className="font-black text-[#FFE4A9]">No independent NFL model advantage has been proven.</b>{' '}
        {scored?`${state.compared_games} matched final games are still only research observations.`:
         'Brier score and log loss are withheld until verified final game results.'}
        {' '}The first 30 independent Finals allow a review, not automatic approval.
       </p>
      </div>
     </div>
     {state.retro_2025_result==='NINE_FEATURE_MODEL_WORSE_THAN_RAW_BOOK'&&(
      <div className="mt-2 flex items-start gap-2 rounded-xl bg-[#FFF2DD] px-3 py-2.5 text-xs font-semibold leading-5 text-[#804F25]">
       <TrendingDown size={16} className="mt-0.5 shrink-0" />
       <p><b>Historical warning:</b> The nine-feature model's 2025 retrospective test was worse than the raw bookmaker market. Retrospective results do not prove future performance.</p>
      </div>
     )}
     {scored&&(
      <div className="mt-2 rounded-xl border border-[#BBD0D5] bg-white p-3 text-[#173E52]">
       <div className="text-[10px] font-black uppercase tracking-wide text-[#166A79]">Original same-game Brier scores · lower is better</div>
       <div className="mt-2 grid grid-cols-3 gap-2 text-center">
        {[
         ['Raw book',state.scores?.raw_book_brier],
         ['Market-only',state.scores?.market_only_brier],
         ['Nine-feature',state.scores?.score_form_brier],
        ].map(([name,score])=>(
         <div key={name} className="min-w-0 rounded-lg bg-[#F2F5F4] p-2">
          <div className="text-sm font-black tabular-nums">{metric(score)}</div>
          <div className="mt-1 text-[9px] font-bold text-slate-600">{name}</div>
         </div>
        ))}
       </div>
       <p className="mt-2 text-[10px] font-medium leading-4 text-slate-600">
        These numbers do not establish a profitable bet. All models use the exact same matched independent game results; ROI stays unavailable without verified executable wagers.
       </p>
      </div>
     )}
     <details className="group mt-3 rounded-xl border border-[#547887] bg-[#234C5C] px-3 py-2.5 text-[#E7F2EF]">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-[11px] font-black">
       <span><FileCheck2 size={14} className="mr-1 inline text-[#7CE2DF]"/>Audit methodology and original-source checks</span>
       <ChevronRight size={16} className="shrink-0 transition-transform group-open:rotate-90"/>
      </summary>
      <div className="mt-2 border-t border-[#486F7E] pt-2 text-[11px] font-medium leading-[1.6] text-[#DDE9E6]">
       <p>Prospective 2026 forecasts are frozen before kickoff. Historical raw-book no-vig, market-only and nine-feature probabilities are evaluated using the exact same independently Final ESPN/NFLverse game identities.</p>
       <p className="mt-1">{whole(state.official_final_games)} independent Finals source-verified · {whole(state.scoring_backlog_games)} waiting for scored-ledger readback · {whole(floor)} more graded games until the first sample-size floor.</p>
       <p className="mt-1">Any duplicate ID, score mismatch, time-travel prediction or altered original SHA hides all metrics. A 2025 retrospective test is not fresh 2026 forward evidence.</p>
       <p className="mt-1 text-[#9ADBD5]">Frozen game ledger SHA {shortHash(state.forecast_source_sha256)} · Independent Final SHA {shortHash(state.official_final_source_sha256)} · automatic bets and model promotion disabled.</p>
      </div>
     </details>
    </>
   )}
  </section>
 )
}
