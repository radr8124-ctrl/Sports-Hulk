import React, {useEffect,useMemo,useState} from 'react'
import {BarChart3,ChevronRight,Clock3,ShieldAlert} from 'lucide-react'

const SOURCE='ZENITH_NFL_PROP_PP_RESEARCH_PUBLIC_V1'
const MARKET={PLAYER_TOTAL_PASS_ATTEMPTS:'Pass attempts',PLAYER_TOTAL_PASS_COMPLETIONS:'Pass completions',PLAYER_TOTAL_INTERCEPTIONS:'Interceptions',PLAYER_TOTAL_REC_YARDS:'Receiving yards',PLAYER_TOTAL_RECEPTIONS:'Receptions',PLAYER_TOTAL_RUSH_YARDS:'Rushing yards',PLAYER_TOTAL_RUSH_ATTEMPTS:'Rush attempts'}

function parseResearch(data,lane,now=Date.now()) {
 if(data?.schema!==SOURCE || data?.real_wagers_placed!==false ||
    data?.unproven_model_not_recommendations!==true ||
    data?.must_verify_sportsbook_quote_and_game_day_injuries_before_any_bet!==true ||
    data?.prizepicks_payout_not_sportsbook_american_odds!==true ||
    !Array.isArray(data.rows))return []
 const target=lane==='PRIZEPICKS'?'NFL_PRIZEPICKS':'NFL_PROP'
 const found=[]
 const keys=new Set()
 for(const item of data.rows) {
   const targetLane=item.same_player_prop_opportunity_source_lanes?.find(x=>x.lane===target)
   const originalStart=Date.parse(item.start_utc)
   const sourceTime=Date.parse(item.source_latest_book_quote_updated_at_utc)
   const key=[item.source_game_id,item.player,item.market,item.side,item.line].join('|')
   if(!targetLane || keys.has(key) || !(originalStart>now) ||
      !Number.isFinite(sourceTime)||sourceTime>=originalStart||
      !Number.isFinite(Number(item.line)) ||
      item.approved_play!==false ||
      item.independent_model_beats_sportsbook_proven!==false||
      item.official_pre_kickoff_player_injury_and_active_confirmation_verified!==false ||
      item.history_games!==4 || item.historical_previous_four_regular_2026_week_stats?.length!==4 ||
      !Number.isFinite(Number(item.empirical_smoothed_success_frequency_pct_NOT_CALIBRATED)) ||
      !Number.isFinite(Number(targetLane.market_reference_pct)) ||
      !Number.isFinite(Number(targetLane.market_plus_empirical_20pct_challenger_pct)))continue
   keys.add(key)
   found.push({...item,laneProof:targetLane,quoteAgeHours:Math.round((now-sourceTime)/360000)/10,
       sourceAgeIsStale:now-sourceTime>86400000})
 }
 return found.sort((a,b)=>a.start_utc.localeCompare(b.start_utc) || a.player.localeCompare(b.player))
}

const kickoffTime=value=>{
 const d=new Date(value)
 return Number.isNaN(d.getTime())?'Kickoff unverified':
   new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',weekday:'short',hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(d)
}

export default function NFLPlayerPropResearchPanel({lane}) {
 const [data,setData]=useState(null)
 const [expanded,setExpanded]=useState(false)
 // Props and PrizePicks reuse this component when the tab changes; collapse
 // the previous lane's expanded list so the next page starts compact.
 useEffect(()=>setExpanded(false),[lane])
 useEffect(()=>{
  let active=true
  const load=async()=>{
   try{
    const r=await fetch(`/nfl_prop_independent_research.json?ts=${Date.now()}`,{cache:'no-store'})
    if(!r.ok)throw new Error('research source missing')
    const next=await r.json()
    if(active)setData(next)
   }catch{if(active)setData(null)}
  }
  load()
  const timer=window.setInterval(load,300000)
  return()=>{active=false;window.clearInterval(timer)}
 },[])
 const rows=useMemo(()=>parseResearch(data,lane),[data,lane])
 const display=expanded?rows:rows.slice(0,3)
 const isPP=lane==='PRIZEPICKS'
 return(
  <section aria-label="NFL independent player-form research" className="rounded-2xl border border-blue-200 bg-white p-3 shadow-soft md:p-4">
   <div className="flex flex-wrap items-center justify-between gap-2">
    <div className="inline-flex items-center gap-2 text-sm font-black text-slate-900">
     <BarChart3 size={17} className="text-blue-700"/> NFL {isPP?'PrizePicks':'Player Props'} · independent research
    </div>
    <span className="rounded-full bg-amber-50 px-2 py-1 text-[10px] font-black text-amber-900">Unproven · no approved picks</span>
   </div>
   <p className="mt-2 text-xs leading-5 text-slate-600">
    The first Week 5 challenger is frozen using <b>Weeks 1–4 actual player statistics</b>, separate from sportsbook prices.
    The four-game hit frequency is only a research baseline—not a calibrated forecast or proven betting edge.
    {isPP?' PrizePicks payout and leg combinations must be verified separately.':''}
   </p>
   {data?.schema===SOURCE && <p className="mt-2 text-[11px] font-semibold text-slate-500">
    At freeze: {data.independent_player_line_opportunities_at_freeze} distinct player lines across {data.independent_games_at_freeze} games.
    {data.source_PP_and_PROP_overlap_rows} repeated PROP/PrizePicks entries do not count as additional independent outcomes.
   </p>}
   {!data && <p className="mt-3 text-xs font-semibold text-slate-600">Waiting for verifiable frozen player research. No projections are being invented.</p>}
   {data&&rows.length===0 && <p className="mt-3 text-xs font-semibold text-slate-600">No upcoming independently sourced research opportunities remain in the frozen set.</p>}
   <div className="mt-3 grid gap-2 lg:grid-cols-2">
    {display.map(row=><article className="rounded-xl border border-slate-200 bg-slate-50/50 p-3" key={row.source_game_id+'|'+row.player+'|'+row.market+'|'+row.line}>
      <div className="flex items-start justify-between gap-2">
       <div>
        <p className="text-xs font-black text-slate-950">{row.player}</p>
        <p className="mt-0.5 text-[11px] text-slate-700">{MARKET[row.market] || row.market} · <b>{row.side} {row.line}</b></p>
        <p className="mt-1 text-[10px] text-slate-500">{row.away_team} @ {row.home_team} · {kickoffTime(row.start_utc)}</p>
       </div>
       <span className="shrink-0 rounded-lg border border-slate-200 bg-white px-2 py-1 text-[10px] font-bold text-slate-500">RESEARCH</span>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
       <span className="text-slate-700"><b>{row.prior_week_hit_count}/4</b> prior games cleared this exact line</span>
       <span className="text-slate-500">4-week mean <b>{row.prior_week_average}</b></span>
      </div>
      <div className="mt-2 rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-[11px]">
       <span className="font-bold text-slate-600">Book reference: {row.laneProof.market_reference_pct.toFixed(1)}%</span>
       <span className="mx-2 text-slate-300">|</span>
       <span className="font-bold text-slate-800">Experimental blend: {row.laneProof.market_plus_empirical_20pct_challenger_pct.toFixed(1)}%</span>
       <span className="block mt-1 text-[10px] font-semibold text-amber-800">Not validated; no positive edge claim. {row.sourceAgeIsStale?'Underlying book quote is over 24 hours old.':'Original quote may move before kickoff.'}</span>
      </div>
      <details className="mt-2 rounded-lg border border-slate-200 bg-white">
       <summary className="flex min-h-10 cursor-pointer items-center justify-between px-3 py-2 text-xs font-black text-blue-700">
        <span>Why the models disagree</span><ChevronRight size={13}/>
       </summary>
       <div className="border-t border-slate-100 px-3 py-2 text-[11px] leading-5 text-slate-700">
        <div>Previous four weekly outcomes: {row.historical_previous_four_regular_2026_week_stats.map(x=>Number(x).toLocaleString('en-US')).join(' / ')}.</div>
        <div>Uncalibrated smoothed hit frequency: {row.empirical_smoothed_success_frequency_pct_NOT_CALIBRATED.toFixed(1)}% (Beta 2,2).</div>
        <div>Challenger = 80% original sportsbook reference + 20% historical empirical rate.</div>
        <div>Book reference: {row.laneProof.reference_type==='DEVIG_FAIR'?'same-line paired-book fair':'raw source implied (not no-vig)'}, from {row.laneProof.original_book_count} books. Original source update: {new Date(row.source_latest_book_quote_updated_at_utc).toLocaleString('en-US',{timeZone:'America/New_York'})} ET.</div>
        <div className="font-black text-amber-800">Player game-day availability, starter and official outcome verification are still required. No wager and no PrizePicks payout proof.</div>
       </div>
      </details>
    </article>)}
   </div>
   {!expanded&&rows.length>display.length && <button type="button" onClick={()=>setExpanded(true)} className="mt-3 min-h-10 rounded-xl border border-blue-200 bg-white px-4 text-xs font-black text-blue-700">
    Show all {rows.length} NFL {isPP?'PrizePicks':'prop'} research lines
   </button>}
   <div className="mt-3 flex flex-wrap justify-between gap-2 border-t border-slate-100 pt-3 text-[11px] font-semibold text-slate-500">
    <span className="inline-flex items-center gap-1"><ShieldAlert size={13}/> Four historical games cannot establish predictive skill.</span>
    <a href="#brain-record" className="font-black text-blue-700">Brain Record evidence →</a>
   </div>
  </section>
 )
}
