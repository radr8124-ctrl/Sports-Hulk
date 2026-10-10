import React,{useEffect,useMemo,useState} from 'react'
import {CheckCircle2,ChevronDown,ShieldAlert,TrendingUp} from 'lucide-react'

const SPORTS=[['NHL','Hockey'],['CFB','College football'],['NBA','NBA preseason'],['MLB','MLB playoffs']]
const isVerified=j=>{
 const t=Date.parse(j?.generated_at_utc||'')
 return j?.schema==='ZENITH_SPORT_PHASE_LEARNING_COHORTS_V1'
  &&j?.status==='REVIEW_ONLY_NO_AUTOMATIC_MODEL_CHANGE'
  &&Number.isFinite(t)&&t<=Date.now()&&Date.now()-t<30*3600000
  &&j?.original_phase_fields_unchanged===true
  &&j?.pending_shadow_results_added_to_original_ledger===0
  &&j?.production_model_weights_changed===false
  &&j?.model_bets_approved===0&&j?.actual_sportsbook_wagers_placed===0
  &&j?.independent_model_advantage_proven===false
  &&Array.isArray(j?.cohorts)
  &&Array.isArray(j?.pending_official_final_recovery_by_sport)
  &&['NHL','CFB','NBA','MLB'].every(s=>/^[a-f0-9]{64}$/.test(j?.source_hashes?.[s+'_original_league_source_sha256']||''))
  &&/^[a-f0-9]{64}$/.test(j?.full_official_shadow_receipt_sha256||'')
  &&j.cohorts.every(c=>c.independent_model_advantage_established===false)
}

export default function SportLearningReview(){
 const [response,setResponse]=useState({loading:true,data:null})
 useEffect(()=>{
  let alive=true
  const load=async()=>{
   try{
    const res=await fetch('/zenith_sport_cohorts.json?ts='+Date.now(),{cache:'no-store'})
    const data=res.ok?await res.json():null
    if(alive)setResponse({loading:false,data})
   }catch{if(alive)setResponse({loading:false,data:null})}
  }
  load()
  const ticker=setInterval(load,5*60*1000)
  return()=>{alive=false;clearInterval(ticker)}
 },[])
 const data=isVerified(response.data)?response.data:null
 const grouped=useMemo(()=>!data?[]:SPORTS.map(([sport,label])=>{
   const c=data.cohorts.filter(x=>x.sport===sport)
   const verified=c.reduce((n,x)=>n+x.independently_verified_official_final_selections,0)
   const games=c.reduce((n,x)=>n+x.unique_official_final_games,0)
   const shadow=data.pending_official_final_recovery_by_sport.find(x=>x.sport===sport)
   return {sport,label,cohorts:c,verified,games,shadow}
 }),[data])
 return <section aria-label="Four-sport official learning cohorts" className="rounded-xl border border-slate-200 bg-white p-3.5 md:p-4">
  <div className="flex flex-wrap items-start justify-between gap-2">
   <div>
    <div className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-blue-700">
     <TrendingUp size={15}/> All-sport learning
    </div>
    <h4 className="mt-1 text-base font-black text-slate-950">Learning from hockey, CFB, NBA & MLB</h4>
   </div>
   <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-bold text-slate-600">
    League-verified research
   </span>
  </div>
  {!data?<p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs font-semibold text-amber-900">
    {response.loading?'Checking official finals and competition phases…':
     'Official source proof is missing or stale. Results are hidden rather than invented.'}
   </p>:<>
   <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] font-semibold text-slate-700">
    <span><b>{data.source_verified_final_research_selections}</b> original research lines checked against official finals</span>
    <span><b>{data.source_verified_distinct_final_games}</b> distinct games</span>
   </div>
   <div className="mt-2.5 grid grid-cols-2 gap-2 md:grid-cols-4">
    {grouped.map(x=><div key={x.sport} className="min-w-0 rounded-xl border border-slate-200 bg-slate-50 p-2.5">
     <p className="text-[11px] font-black text-slate-900">{x.label}</p>
     <p className="mt-1 text-[10px] font-medium text-slate-600">
      {x.cohorts.map(c=>c.phase_stage.replaceAll('_',' ')).join(' / ')||'Unverified phase'}
     </p>
     <div className="mt-1.5 flex items-end gap-1.5">
      <strong className="text-xl font-black tabular-nums text-slate-950">{x.games}</strong>
      <span className="pb-1 text-[10px] font-semibold text-slate-500">finished games</span>
     </div>
     <p className="text-[10px] leading-4 text-slate-600">{x.verified} saved lines checked
      {x.shadow?.derived_postgame_research_rows>0?
       ' · '+x.shadow.derived_postgame_research_rows+' shadow-graded':''}
     </p>
    </div>)}
   </div>
   <p className="mt-3 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs leading-5 text-amber-900">
    <ShieldAlert size={16} className="mt-0.5 shrink-0"/>
    <span><b>{data.derived_pending_from_official_final_research_rows} pending research lines</b> have recoverable official results.
     Their original ledger still says PENDING, so results live in a separate source-hashed shadow receipt.
     <b> They are not extra independent games or approved bets.</b></span>
   </p>
   <details className="group mt-3 border-t border-slate-100 pt-2">
    <summary className="flex min-h-10 cursor-pointer items-center justify-between gap-2 text-xs font-black text-blue-700">
     Why these results cannot yet improve the model
     <ChevronDown size={16} className="shrink-0 transition-transform group-open:rotate-180"/>
    </summary>
    <div className="mt-2 space-y-2 text-[11px] leading-5 text-slate-600">
     {grouped.filter(x=>x.shadow).map(x=><div key={x.sport} className="rounded-lg bg-slate-50 p-2.5">
      <b className="text-slate-900">{x.label}: {x.shadow.derived_postgame_research_rows} calculated outcomes</b>
      <p>{x.shadow.unique_official_games} official games.
       {' '}Market lines: {Object.entries(x.shadow.market_counts||{}).map(([m,n])=>m+' '+n).join(', ')}.
       {' '}Results: {Object.entries(x.shadow.grade_counts||{}).map(([g,n])=>g+' '+n).join(', ')}.</p>
      <p>{x.shadow.original_duplicate_line_variant_count} duplicate/alternate variants and
       {' '}{x.shadow.original_opposite_side_conflict_count} conflicting game sides were flagged at original capture.
       These cannot count as independent winning predictions.</p>
      {x.sport==='NBA'&&<p className="mt-1 font-semibold text-amber-800">
       {x.shadow.original_qualified_game_grade_line_missing_count} lines have no exact qualified game/market/selection/line match in the original grading index.
       That is why the older settlement feed could not resolve those variants; the source-preserved recovery remains separate.
      </p>}
     </div>)}
     <p className="text-xs font-black text-slate-900">A real mistake by sport — what actually failed</p>
     <div className="grid gap-2 sm:grid-cols-2">
      {SPORTS.map(([sport,label])=>{
        const incident=(data.recent_observable_errors||[]).find(x=>x.sport===sport)
        return incident?<div key={sport} className="rounded-lg border border-slate-100 bg-slate-50 p-2.5">
          <p className="font-bold text-slate-900">{label} · {incident.market}</p>
          <p className="mt-0.5 text-[10px] text-slate-500">{incident.game}</p>
          <p className="mt-1 text-[11px] leading-4 text-slate-600">{incident.observed_miss}</p>
        </div>:null
      })}
     </div>
     <p className="flex items-start gap-2">
      <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-blue-700"/>
      NBA preseason, NHL regular season, CFB regular season, and MLB postseason remain in separate cohorts.
      League phase and score were corroborated after capture; this is not proof those inputs were known at the original freeze.
     </p>
     <p><b>Next genuine improvement:</b> frozen future predictions must independently beat the same-book market across sufficient distinct games. No live model coefficients were changed.</p>
    </div>
   </details>
  </>}
 </section>
}
