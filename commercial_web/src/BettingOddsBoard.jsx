import React, {useEffect,useMemo,useState} from 'react'
import {ChevronDown, ShieldCheck} from 'lucide-react'
import {showFrozenNFLResearch} from '../nfl_frozen_forecast_presentation.js'
import {quotedSideMeaning,fairAmericanFromPercent} from '../odds_selection_display.js'
import NflBookSourceHealth from './NflBookSourceHealth.jsx'

const MARKET_NAMES={MONEYLINE:'Moneyline',SPREAD:'Spread',TOTAL:'Game total'}
const MARKETS=['MONEYLINE','SPREAD','TOTAL']
const humanTime=value=>{
  const time=Date.parse(value||'')
  return Number.isFinite(time)?new Intl.DateTimeFormat('en-US',{
    weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',
    timeZone:'America/New_York',timeZoneName:'short'
  }).format(time):'Time not confirmed'
}
const american=n=>Number.isFinite(n)&&Math.abs(n)>=100?(n>0?'+'+n:String(n)):'—'
const signed=n=>Number.isFinite(n)?(n>0?'+'+n:String(n)):'—'
const bookDisplay={fanduel:'FanDuel',draftkings:'DraftKings',betmgm:'BetMGM',
 caesars:'Caesars',fanatics:'Fanatics',pinnacle:'Pinnacle',thescore:'theScore',
 betrivers:'BetRivers',bet365:'bet365',hardrock:'Hard Rock',betparx:'betPARX'}
const bookmaker=x=>bookDisplay[String(x||'').toLowerCase()]||String(x||'Unknown book')
const valid=(data,now)=>data&&data.status==='RESEARCH_ONLY'
  &&data.verified_positive_expected_value_bets===0
  &&data.no_approved_pick_or_bet_created===true
  &&data.all_prices_observed_not_executable===true
  &&Array.isArray(data.games)&&Number.isFinite(now)
const quality=n=>n>=2?'Notable book-to-book price difference':n>=0.4?'Small price advantage':'Typical market price'
const recentlyCaptured=(game,now)=>{
  const capture=Date.parse(game?.source_capture_at||'')
  const start=Date.parse(game?.start||'')
  if(!Number.isFinite(now)||!Number.isFinite(capture)||!Number.isFinite(start)
    ||capture>now||start<=now)return false
  const hoursToStart=(start-now)/3600000
  const age=(now-capture)/3600000
  return age<=(hoursToStart<=24?6:24)
}

function BetMarket({game,market,item,recent}){
  const sides=market==='TOTAL'?['OVER','UNDER']:['AWAY','HOME']
  return <div className="border-t border-slate-100 py-2.5">
    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
      <p className="text-xs font-black text-slate-800">{MARKET_NAMES[market]}{market==='TOTAL'?' · '+item.line+' '+(item.market_subtype==='TOTAL_RUNS'?'runs':item.market_subtype==='TOTAL_GOALS'?'goals':'points'):''}</p>
      <span className="text-[10px] text-slate-500">{item.paired_book_count} paired books</span>
    </div>
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {sides.map(side=>{
        const q=item.sides?.[side]
        if(!q)return null
        const meaning=quotedSideMeaning(game,market,side,item)
        if(!meaning)return null
        const fairPrice=fairAmericanFromPercent(q.market_consensus_no_vig_probability_pct)
        return <div key={side} className="min-w-0 rounded-xl border border-slate-200 bg-slate-50 p-2.5">
          <span className="text-[10px] font-black uppercase tracking-wider text-blue-700">{side==='HOME'?'HOME':side==='AWAY'?'AWAY':side}</span>
          <p className="mt-0.5 break-words text-sm font-black leading-5 text-slate-900">{meaning.label}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="rounded-md border border-[#B6DAD5] bg-[#DDF5ED] px-2 py-1 text-[9px] font-black uppercase text-[#0D6472]">Best observed price</span>
            <strong className="text-xl tabular-nums text-slate-950">{american(q.best_american_odds)}</strong>
            <span className="text-[10px] font-semibold text-slate-600">{bookmaker(q.best_sportsbook)}</span>
          </div>
          <p className="mt-1 text-[11px] font-medium leading-4 text-slate-600">{meaning.requirement}</p>
          <div className="mt-2 rounded-lg border border-[#E8DCC8] bg-white px-2.5 py-2 text-[10px] leading-4 text-[#536B73]">
            <b className="text-[#173E52]">Market fair price:</b> {fairPrice===null?'unverified':american(fairPrice)} <span className="text-slate-400">{fairPrice===null?'(fair chance unavailable)':`(${q.market_consensus_no_vig_probability_pct}% bookmaker fair chance)`}</span>
            <span className="mt-0.5 block">Typical competing price {american(q.median_book_american_odds)}</span>
            <span className="mt-0.5 block">Book quote last updated {humanTime(q.source_updated_at)}</span>
          </div>
          <p className={'mt-2 text-[10px] font-black '+(!recent?'text-amber-800':q.price_assessment==='BETTER PRICE THAN PEERS'?'text-emerald-700':q.price_improvement_pct_points>=.4?'text-blue-700':'text-slate-500')}>
            {!recent?'Old quote · recheck required':q.price_assessment==='BETTER PRICE THAN PEERS'?'Notably better than peers':q.price_improvement_pct_points>=.4?'Small price improvement':'Near typical price'}
            {recent&&q.price_improvement_pct_points>=.4?' · '+q.price_improvement_pct_points+'pp':''}
          </p>
        </div>
      })}
    </div>
  </div>
}

function GameCard({game,market,frozenModel=null,now=Date.now()}){
  const markets=(market==='ALL'?MARKETS:[market]).filter(m=>game.markets?.[m])
  const recent=recentlyCaptured(game,now)
  const notable=recent&&markets.some(m=>Object.values(game.markets[m].sides).some(q=>q.price_assessment==='BETTER PRICE THAN PEERS'))
  const maxGap=Math.max(0,...markets.flatMap(m=>Object.values(game.markets[m].sides).map(q=>q.price_improvement_pct_points||0)))
  return <article className="min-w-0 rounded-2xl border border-slate-200 bg-white p-3.5 shadow-soft md:p-4">
    <div className="flex items-start justify-between gap-2.5">
      <div className="min-w-0">
        <p className="text-[10px] font-black uppercase tracking-wider text-blue-700">{game.sport} · {humanTime(game.start)}</p>
        <h4 className="mt-1 text-base font-black leading-5 text-slate-950">{game.away} <span className="text-slate-400">@</span> {game.home}</h4>
      </div>
      <span className={'shrink-0 rounded-lg px-2 py-1 text-[10px] font-bold '+(recent?'bg-slate-100 text-slate-600':'bg-amber-50 text-amber-800')}>
        {recent?'DATED':'STALE'}
      </span>
    </div>
    <p className="mt-1.5 text-[11px] font-medium leading-4 text-slate-600">“Take” means the specific team or total shown—not both sides. These are dated research prices, not live offers. Captured: {humanTime(game.source_capture_at)}.</p>
    {frozenModel && (
      <div className="mt-2 rounded-xl border border-blue-100 bg-blue-50/60 px-3 py-2.5">
        <p className="text-[10px] font-black uppercase tracking-wider text-blue-700">Zenith NFL forecast · experimental</p>
        <p className="mt-1 text-xs font-black text-slate-900">
          {frozenModel.forecast_side_home_or_away==='HOME'?game.home:game.away} to win · {frozenModel.forecast_side_home_or_away==='HOME'?frozenModel.forecast_home_pct:frozenModel.forecast_away_pct}%
        </p>
        <p className="mt-0.5 text-[11px] leading-5 text-slate-600">
          Original Pinnacle no-vig: {frozenModel.forecast_side_home_or_away==='HOME'?frozenModel.book_market_fair_home_pct:frozenModel.book_market_fair_away_pct}% · model vs original book:
          {' '}{(frozenModel.forecast_side_home_or_away==='HOME'?frozenModel.delta_model_minus_book_home_pp:-frozenModel.delta_model_minus_book_home_pp)>=0?'+':''}{(frozenModel.forecast_side_home_or_away==='HOME'?frozenModel.delta_model_minus_book_home_pp:-frozenModel.delta_model_minus_book_home_pp).toFixed(2)} pp.
        </p>
        <p className="mt-0.5 text-[10px] font-bold text-amber-800">Market-assisted prediction; 2025 model did not beat the market. Not a proven bet.</p>
      </div>
    )}
    <p className="mt-2 text-[11px] font-semibold text-slate-600">
      <span className="mr-1 inline-flex rounded-md border border-[#E6C894] bg-[#FFF0D0] px-2 py-0.5 text-[10px] font-black text-[#795321]">RESEARCH · NOT PROVEN</span>
      Zenith price read: <span className={notable?'font-black text-emerald-700':'font-bold text-slate-700'}>{notable?'Notably better price on at least one line':maxGap>=.4?'Small price variations':'Typical market prices'}</span> · No proven betting edge
    </p>
    <div className="mt-2">{markets.map(m=><BetMarket key={m} game={game} market={m} item={game.markets[m]} recent={recent}/>)}</div>
    <details className="group border-t border-slate-100 pt-1">
      <summary className="flex min-h-9 cursor-pointer items-center justify-between text-xs font-black text-blue-700">
        Why Zenith rates these odds <ChevronDown size={15} className="transition-transform group-open:rotate-180"/>
      </summary>
      <div className="space-y-1 pb-1 text-[11px] leading-5 text-slate-600">
        <p>Zenith compares the best observed bookmaker odds to the typical price across the exact same outcome and line. A lower break-even price is useful for shopping, but is not proof of a profitable bet.</p>
        <p>The fair probability comes from bookmakers after removing their margin, not an independently proven Zenith win prediction. Source capture: {humanTime(game.source_capture_at)}.</p>
        <p>{game.event_identity_status==='EXACT_ESPN_TEAMS_KICKOFF_UNIQUE_EVENT'?'Official ESPN NFL event independently matched':'Source bookmaker event matched by ID, teams and kickoff; official event independently unverified'}{game.provider_source_clock_spread_minutes>0?' · Kickoff quotes vary by '+game.provider_source_clock_spread_minutes+' min across books':''}.</p>
        <p className="font-bold text-amber-800">Prices can change and are not verified as executable or available in your account. Review current sportsbook odds and player/injury information before acting.</p>
      </div>
    </details>
  </article>
}

export default function BettingOddsBoard({sport='ALL',market='ALL'}){
  const [state,setState]=useState({loaded:false,data:null,frozen:null,checkedAt:Date.now()})
  const [sort,setSort]=useState('UPCOMING')
  const [count,setCount]=useState(4)
  useEffect(()=>{
    let active=true
    const load=async()=>{
      const download=async(url)=>{
        try{
          const response=await fetch(url+'?ts='+Date.now(),{cache:'no-store'})
          return response.ok?await response.json():null
        }catch{return null}
      }
      const [data,frozen]=await Promise.all([
        download('/betting_odds_board.json'),download('/nfl_frozen_game_intelligence.json'),
      ])
      if(active)setState({loaded:true,data,frozen,checkedAt:Date.now()})
    }
    load()
    const interval=setInterval(load,5*60*1000)
    return()=>{active=false;clearInterval(interval)}
  },[])
  useEffect(()=>{setCount(4)},[sport,market,sort])
  const report=useMemo(()=>{
    if(!valid(state.data,state.checkedAt))return {rows:[],total:0,better:0}
    const relevant=state.data.games.filter(g=>(sport==='ALL'||g.sport===sport)
      &&(market==='ALL'||g.markets?.[market])
      &&Date.parse(g.start)>state.checkedAt)
    const best=g=>Math.max(0,...Object.entries(g.markets||{})
      .filter(([key])=>market==='ALL'||key===market)
      .flatMap(([,m])=>Object.values(m.sides||{}).map(q=>q.price_improvement_pct_points||0)))
    const notable=g=>Object.entries(g.markets||{}).some(([m,data])=>(market==='ALL'||market===m) && Object.values(data.sides||{}).some(q=>q.price_assessment==='BETTER PRICE THAN PEERS'))
    const better=relevant.filter(g=>recentlyCaptured(g,state.checkedAt)&&notable(g)).length
    const rows=relevant.filter(g=>sort==='UPCOMING'||(recentlyCaptured(g,state.checkedAt)&&notable(g)))
      .sort((a,b)=>sort==='UPCOMING'?Date.parse(a.start)-Date.parse(b.start):
        best(b)-best(a)||Date.parse(a.start)-Date.parse(b.start))
    return {rows,total:relevant.length,better}
  },[state,sport,market,sort])
  const view=report.rows.slice(0,count)
  const frozenGames=useMemo(()=>showFrozenNFLResearch(state.frozen||{},state.checkedAt),[state.frozen,state.checkedAt])
  const frozenMap=useMemo(()=>new Map(frozenGames.rows.map(row=>[String(row.event_id),row])),[frozenGames])
  const readModel=game=>{
    if(game.sport!=='NFL'||game.event_identity_status!=='EXACT_ESPN_TEAMS_KICKOFF_UNIQUE_EVENT')return null
    const row=frozenMap.get(String(game.official_espn_event_id))
    if(!row||Math.abs(Date.parse(row.kickoff_utc)-Date.parse(game.start))>180000)return null
    return row
  }
  return <section aria-label="Sportsbook odds and Zenith price comparisons" className="space-y-3">
    <div className="flex flex-wrap items-end justify-between gap-2">
      <div>
        <p className="eyebrow">Betting odds & intelligence</p>
        <h3 className="mt-1 text-xl font-black tracking-tight text-slate-950">Games, odds and better prices</h3>
        <p className="mt-1 text-xs leading-5 text-slate-600">Every quoted market includes bookmaker odds, typical prices, fair probabilities and Zenith's price read.</p>
      </div>
      <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-bold text-slate-700">{report.total} priced games</span>
    </div>
    {(sport==='ALL'||sport==='NFL')&&<NflBookSourceHealth />}
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div role="group" aria-label="Sort sportsbook odds" className="flex flex-wrap gap-2">
        <button type="button" onClick={()=>setSort('UPCOMING')} className={'min-h-10 rounded-xl px-3 py-2 text-xs font-black '+(sort==='UPCOMING'?'bg-slate-950 text-white':'border border-slate-200 bg-white text-slate-600')}>Upcoming games</button>
        <button type="button" onClick={()=>setSort('BETTER')} className={'min-h-10 rounded-xl px-3 py-2 text-xs font-black '+(sort==='BETTER'?'bg-slate-950 text-white':'border border-slate-200 bg-white text-slate-600')}>Better prices ({report.better})</button>
      </div>
      <span className="text-[10px] font-semibold text-slate-500">Dated market research · not executable quotes</span>
    </div>
    {sport==='NBA' && valid(state.data,state.checkedAt) && <p className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-[11px] font-semibold leading-5 text-slate-600">NBA lines in this feed are for the listed future dates. They do not substitute for unpriced NBA preseason games or prove the competition phase independently.</p>}
    {!valid(state.data,state.checkedAt)?(
      <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs font-bold text-amber-900">{state.loaded?'Source proof unavailable; no odds invented.':'Loading sportsbook sources…'}</p>
    ):view.length?(
      <div className="grid gap-3 lg:grid-cols-2">{view.map(game=><GameCard key={game.sport+'|'+game.provider_event_id} game={game} market={market} frozenModel={readModel(game)} now={state.checkedAt}/>)}</div>
    ):(
      <p className="rounded-xl border border-slate-200 bg-white p-4 text-sm font-semibold text-slate-600">
        {sport==='CBB' && state.data?.coverage?.CBB?.source_rows===0
          ? 'No college basketball odds rows were available from connected sources at the last refresh. Nothing has been invented.'
          : 'No '+(sort==='BETTER'?'recent better-than-peer prices':'exact paired markets')+' match this filter. Try another sport or market.'}
      </p>
    )}
    {count<report.rows.length&&<button type="button" onClick={()=>setCount(x=>x+12)} className="min-h-11 rounded-xl border border-blue-200 bg-white px-4 py-2.5 text-xs font-black text-blue-700">Show 12 more · {report.rows.length-count} remaining</button>}
    <div className="flex items-start gap-2 text-[11px] leading-5 text-slate-500">
      <ShieldCheck size={16} className="mt-0.5 shrink-0 text-blue-700"/>
      <p>Better odds means a better observed price than comparable books for the same outcome and line. This alone is not proof of positive expected value, a confirmed live offer, or an approved wager.</p>
    </div>
  </section>
}
