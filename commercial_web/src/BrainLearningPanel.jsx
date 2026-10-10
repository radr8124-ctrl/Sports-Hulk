import React,{useEffect,useState} from 'react'
import {Brain,ChevronDown,Clock3,ShieldCheck,Target} from 'lucide-react'

const fmt=n=>Number.isInteger(n)?n.toLocaleString():'—'
const valid=j=>j?.schema==='ZENITH_POSTGAME_ERROR_REVIEW_V1'
  &&j?.status==='LEARNING_IN_SHADOW_ONLY'
  &&j?.snapshot?.live_new_model_adjustments_applied===0
  &&j?.frozen_forward_challenger_score?.automated_live_model_adjustment_allowed===false
  &&j?.pre_registered_calibration_shadow?.automatic_recommendation_or_model_change===false
  &&Array.isArray(j?.by_lane) && Array.isArray(j?.previous_game_case?.original_cases)
  &&j?.previous_game_case?.status==='ARCHIVED_PREGAME_RESEARCH_ONLY'
  &&j?.first_frozen_nfl_model_postgame_review?.no_manual_backfilling_of_predictions===true
  &&/^[a-f0-9]{64}$/.test(j?.source_hashes?.original_betting_v2_all_markets_forward_sha256||'')
  &&/^[a-f0-9]{64}$/.test(j?.source_hashes?.original_nfl_nine_feature_future_sha256||'')
  &&/^[a-f0-9]{64}$/.test(j?.source_hashes?.original_nfl_oct4_archive_grade_sha256||'')
  &&Object.values(j?.source_hashes||{}).every(x=>x==null||/^[a-f0-9]{64}$/.test(x))

const marketLabel=m=>m==='MONEYLINE'?'Moneyline':m==='SPREAD'?'Spread':'Total'

function Oct4Example({data}) {
  const ordered=['MONEYLINE','SPREAD','TOTAL']
  const cases=ordered.map(m=>data.original_cases?.find(x=>x.market===m)).filter(Boolean)
  return <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
    <p className="text-[10px] font-black uppercase tracking-wider text-blue-700">Actual postgame learning example · Oct 4</p>
    <h4 className="mt-1 text-sm font-black text-slate-900">Chiefs {data.result_score_away ?? '—'} — Raiders {data.result_score_home ?? '—'}</h4>
    <div className="mt-2 grid gap-2 sm:grid-cols-3">
      {cases.map(c=><div key={c.market} className="rounded-lg border border-slate-200 bg-white p-2.5">
        <div className="flex flex-wrap items-center justify-between gap-1">
          <span className="text-[11px] font-bold text-slate-700">
            {marketLabel(c.market)} · {c.market==='TOTAL'?'Over '+c.line:c.market==='SPREAD'?'Chiefs '+c.line:'Chiefs to win'}
          </span>
          <span className={'text-[10px] font-black '+(c.grade==='WIN'?'text-emerald-700':'text-rose-700')}>{c.grade}</span>
        </div>
        <p className="mt-1 text-[11px] leading-4 text-slate-600">
          {c.market==='SPREAD'
            ? 'KC won by 3 but needed 6+ to cover Chiefs -5.'
            : c.market==='MONEYLINE'
              ? 'Correct winner, but not proof of an independently calibrated model.'
              : '57 combined points cleared the 47.5 total.'}
        </p>
      </div>)}
    </div>
    <p className="mt-2 text-[11px] leading-5 text-slate-500">The original saved scores were heuristic research rankings, not calibrated win probabilities. We can identify the margin mismatch, but cannot claim a particular injury, weather event or model feature caused it.</p>
  </div>
}

function CorrectionTrialRecord({register}) {
  const truthful=register?.schema==='ZENITH_MODEL_CORRECTION_REGISTRY_V1'
    &&register?.status==='POSTGAME_CORRECTIONS_REVIEWED_NOT_PROMOTED'
    &&register?.model_weights_changed===false
    &&register?.promotion_allowed_without_independent_future_evidence===false
    &&register?.fresh_unseen_2026_outcomes_required===true
    &&Array.isArray(register?.candidate_models)
    &&register?.tested_hypotheses_count===register?.candidate_models?.length
    &&register?.proposed_correction_count===3
    &&register?.rejected_proposed_corrections_count<=register?.proposed_correction_count
    &&register?.candidate_models?.every(x=>x.live_model_update_approved===false)
  if(!truthful)return <p className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs font-semibold leading-5 text-slate-600">
    Historical correction evidence is not verified yet; no past results will be described as a successful upgrade.
  </p>
  const rejected=register.rejected_proposed_corrections_count
  const total=register.proposed_correction_count
  return <details className="group rounded-xl border border-slate-200 bg-white p-3">
    <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3">
      <span className="min-w-0 text-left">
        <span className="block text-sm font-black text-slate-900">Corrections tested: {total} · rejected: {rejected}</span>
        <span className="mt-0.5 block text-[11px] font-medium leading-4 text-slate-600">Historical fixes must beat the sportsbook, not just explain a past loss</span>
      </span>
      <ChevronDown size={17} className="shrink-0 text-blue-700 transition-transform group-open:rotate-180"/>
    </summary>
    <div className="mt-2 space-y-2 border-t border-slate-100 pt-3">
      <p className="text-[11px] leading-5 text-slate-600">
        {register.original_game_cohort_count} previously inspected NFL games, 2022–2025. Lower Brier score is better.
        The benchmark uses retrospectively compiled book prices, not a verified executable sportsbook offer.
      </p>
      {register.candidate_models.map(model=><div key={model.hypothesis_id} className="rounded-xl border border-slate-200 bg-slate-50 p-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-[11px] font-black text-slate-900">{model.hypothesis_id==='original_model'?'Original NFL model':model.description}</span>
          <span className="text-[10px] font-bold text-rose-700">{model.status==='REJECTED_NOT_BETTER_THAN_BOOKMAKER'?'REJECTED':'NOT PROVEN'}</span>
        </div>
        <p className="mt-1 text-[11px] tabular-nums text-slate-600">
          Book Brier {model.retrospective_market_brier.toFixed(5)} · Trial {model.retrospective_candidate_brier.toFixed(5)} · Better in {model.better_than_book_in_historical_test_years}/4 seasons
        </p>
      </div>)}
      <p className="text-[11px] font-semibold leading-5 text-slate-600">
        No live weights changed. Rejecting a failed correction is progress; any future improvement must survive a newly frozen, independent forward cohort.
      </p>
    </div>
  </details>
}

function CurrentProgress({review}) {
  const snap=review.snapshot
  const lanes=review.by_lane
  const largest=[...lanes].sort((a,b)=>b.graded_rows-a.graded_rows)[0]
  const shadow=review.pre_registered_calibration_shadow
  const shadowResult=review.frozen_forward_challenger_score
  const frozenOriginals=review.first_frozen_nfl_model_postgame_review || {}
  const firstOfficialGames=frozenOriginals.individual_games || []
  return <div className="space-y-3">
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {[
        ['Settled research',fmt(snap.valid_settled_market_research)],
        ['Different games',fmt(snap.distinct_settled_game_blocks)],
        ['Losing selections',fmt(snap.losses_observed)],
        ['Models promoted',fmt(snap.live_new_model_adjustments_applied)],
      ].map(([key,value])=><div key={key} className="rounded-xl bg-slate-50 px-3 py-3">
        <div className="text-[10px] font-black uppercase tracking-wide text-slate-500">{key}</div>
        <div className="mt-1 text-xl font-black tabular-nums text-slate-950">{value}</div>
      </div>)}
    </div>
    <p className="text-xs leading-5 text-slate-600">
      So far, <b>{fmt(snap.market_based_predictions_same_as_market)} of {fmt(snap.valid_settled_market_research)}</b> settled game-market research probabilities were identical to the sportsbook baseline. A positive win count for these research records is not proof of independent model skill; a single game can appear on multiple lines.
    </p>
    <p className="text-xs leading-5 text-slate-600">
      {largest&&<>Largest lane: <b>{largest.lane.replaceAll('_',' ')}</b> — {largest.graded_rows} graded lines from only {largest.independent_game_blocks} distinct games. </>}
      First original nine-feature NFL forecasts: <b>{fmt(snap.frozen_nfl_nine_feature_games)}</b> frozen, <b>{fmt(snap.frozen_nfl_nine_feature_games_officially_settled)}</b> independently settled in their own scorer.
    </p>
    {firstOfficialGames.length>0 && <div className="rounded-xl border border-slate-200 bg-white p-3">
      <p className="text-xs font-black text-slate-900">First frozen NFL game forecasts after official final</p>
      <p className="mt-1 text-[11px] text-slate-600">{frozenOriginals.model_correct_winner_count} winner predictions correct · {frozenOriginals.wrong_winner_count} missed. Original same-book probability is the baseline—not proof of wagering profit.</p>
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        {firstOfficialGames.slice(0,6).map(game=><div key={game.event_id} className="rounded-lg bg-slate-50 p-2.5 text-[11px] leading-5">
          <b className="text-slate-900">{game.away} @ {game.home} · {game.official_away_points}-{game.official_home_points}</b>
          <p className="text-slate-600">Frozen model: {game.predicted_winner} · Actual: {game.actual_winner}</p>
          <p className={game.model_winner_correct?'font-bold text-emerald-700':'font-bold text-rose-700'}>{game.model_winner_correct?'Winner correct':'Wrong winner'} · Model minus book Brier {game.model_minus_book_brier>=0?'+':''}{game.model_minus_book_brier}</p>
          {!game.feature_root_cause_verified&&<p className="text-slate-500">Root feature or injury cause not independently confirmed.</p>}
        </div>)}
      </div>
    </div>}
    <div className="rounded-xl border border-blue-100 bg-blue-50/40 p-3">
      <div className="flex items-center gap-2 text-xs font-black text-blue-900"><Target size={15}/> Next correction under test</div>
      <p className="mt-1 text-xs leading-5 text-slate-700">Separate outright-winner predictions, exact point-spread cover probabilities and totals. Freeze proposed changes as shadow models and compare their outcomes against the original market on new games.</p>
      <p className="mt-1 text-[11px] font-semibold leading-5 text-slate-600">
        {fmt(shadow.ready_asof_future_predictions)} prospective calibration challengers meet the strict as-of training gate today. {fmt(shadowResult.independent_shadow_game_blocks)} independent shadow games settled; {shadowResult.review_eligible?'manual review eligible':'no validated improvement yet'}.
      </p>
    </div>
  </div>
}

export default function BrainLearningPanel() {
  const [data,setData]=useState(null)
  const [loaded,setLoaded]=useState(false)
  useEffect(()=>{
    let active=true
    const load=async()=>{
      try{
        const r=await fetch('/zenith_learning_review.json?ts='+Date.now(),{cache:'no-store'})
        const j=r.ok?await r.json():null
        if(active){setData(j);setLoaded(true)}
      }catch{if(active){setData(null);setLoaded(true)}}
    }
    load()
    const timer=setInterval(load,5*60*1000)
    return()=>{active=false;clearInterval(timer)}
  },[])
  const okay=valid(data)
  return <section aria-label="How Zenith learns from mistakes" className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft md:p-6">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-wider text-blue-700">
          <Brain size={17}/> Continuous model learning
        </div>
        <h3 className="mt-1 text-xl font-black tracking-tight text-slate-950">How Zenith learns from mistakes</h3>
        <p className="mt-1 text-xs leading-5 text-slate-600">Freeze → grade → explain → test a correction → prove it on new games.</p>
      </div>
      <span className="rounded-full border border-blue-100 bg-blue-50 px-3 py-1.5 text-[10px] font-black text-blue-800">
        Shadow learning · no automatic bets
      </span>
    </div>
    {!okay ? <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-semibold text-amber-900">
      {loaded?'Learning evidence could not be validated. No unverified learning metrics will be displayed.':'Loading frozen outcome evidence…'}
    </div> : <div className="mt-4 space-y-4">
      <Oct4Example data={data.previous_game_case}/>
      <CurrentProgress review={data}/>
      <CorrectionTrialRecord register={data.error_correction_trial_registry}/>
      <details className="group rounded-xl border border-slate-200 bg-white p-3">
        <summary className="flex min-h-10 cursor-pointer items-center justify-between gap-2 text-xs font-black text-blue-700">
          Show error categories, original source quality and learning gates
          <ChevronDown size={17} className="shrink-0 transition-transform group-open:rotate-180"/>
        </summary>
        <div className="mt-2 space-y-3 border-t border-slate-100 pt-3">
          <div className="grid gap-2 sm:grid-cols-2">
            {(data.hypotheses_for_shadow_tests||[]).slice(0,7).map(item=><div key={item.lane}
              className="rounded-lg border border-slate-100 bg-slate-50 p-2.5">
              <div className="text-[11px] font-black text-slate-900">{item.lane.replaceAll('_',' ')}</div>
              <div className="mt-0.5 text-[11px] leading-5 text-slate-600">{item.why_test_this}</div>
              <div className="mt-1 text-[10px] font-bold text-slate-500">{item.independent_completed_games}/{item.minimum_independent_games_for_fitting} different games before fitting review</div>
            </div>)}
          </div>
          <p className="flex items-start gap-2 text-[11px] leading-5 text-slate-600">
            <ShieldCheck size={15} className="mt-0.5 shrink-0 text-blue-700"/>
            Every retained grade agrees arithmetically with its recorded final score. {data.snapshot.original_prediction_snapshot_field_is_pregame_for_settled} result records retain an original *pregame recommendation* timestamp—this is not a verified postgame result timestamp. Full official boxscore double-check remains outstanding.
          </p>
          <p className="flex items-start gap-2 text-[11px] leading-5 text-amber-800">
            <Clock3 size={15} className="mt-0.5 shrink-0"/>No original prediction, past result or live-model coefficient is overwritten. New candidate probabilities are frozen only after enough completed, time-valid games exist before the next forecast.
          </p>
        </div>
      </details>
    </div>}
  </section>
}
