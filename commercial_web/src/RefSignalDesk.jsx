import React,{useEffect,useMemo,useState} from 'react'
import {ArrowUpRight,CalendarClock,Clock3,ShieldAlert,Sparkles} from 'lucide-react'
import {refMarketReview} from '../ref_market_review.js'

const bookNames={fanduel:'FanDuel',draftkings:'DraftKings',pinnacle:'Pinnacle',
  caesars:'Caesars',betmgm:'BetMGM',thescore:'theScore',fanatics:'Fanatics'}
const bookmaker=value=>bookNames[String(value||'').toLowerCase()]||value||'Unknown book'
const dateET=value=>{
  const stamp=Date.parse(value||'')
  return Number.isFinite(stamp)?new Intl.DateTimeFormat('en-US',{
    weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',
    timeZone:'America/New_York',timeZoneName:'short',
  }).format(stamp):'Game time unverified'
}

function ResearchCard({item,onReview,disabled}) {
  return <article className="w-[min(81vw,320px)] flex-none snap-start rounded-2xl border border-sky-400/15 bg-slate-900/85 p-3.5 text-white lg:w-auto lg:min-w-0">
    <div className="flex items-center justify-between gap-2">
      <span className="text-[10px] font-black uppercase tracking-[0.12em] text-sky-300">
        Market favorite · not a pick
      </span>
      <span className={'text-[10px] font-bold '+(item.quoteStatus==='ARCHIVED_RECHECK'?'text-amber-300':'text-slate-400')}>
        {item.quoteStatus==='ARCHIVED_RECHECK'?'EXPIRED':'DATED'} · {item.priceAgeLabel} old
      </span>
    </div>
    <p className="mt-2 line-clamp-1 text-[11px] font-semibold text-slate-400" title={item.away+' @ '+item.home}>
      {item.sport} · {item.away} @ {item.home}
    </p>
    <h3 className="mt-1 text-base font-black leading-5 text-white">{item.team}</h3>
    <p className="mt-1 text-[11px] text-slate-400">{dateET(item.kickoff)}</p>
    <div className="mt-3 rounded-xl border border-white/10 bg-white/[.055] p-2.5">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Observed ML price</p>
          <p className="mt-0.5 text-xl font-black tabular-nums text-white">{item.bestAmericanPrice}</p>
        </div>
        <div className="min-w-0 text-right">
          <p className="text-xs font-black text-sky-300">{bookmaker(item.bestBook)}</p>
          <p className="text-[10px] text-slate-400">Peer median {item.typicalAmericanPrice||'—'}</p>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 border-t border-white/10 pt-2.5">
        <div>
          <p className="text-[10px] font-bold text-slate-400">Book fair</p>
          <p className="text-lg font-black tabular-nums text-slate-100">{item.marketFairPct}%</p>
        </div>
        <div>
          <p className="text-[10px] font-bold text-slate-400">Zenith research</p>
          <p className="text-lg font-black tabular-nums text-sky-300">
            {item.modelResearchPct===null?'Unproven':item.modelResearchPct+'%'}
          </p>
        </div>
      </div>
    </div>
    <p className="mt-2 flex items-start gap-1.5 text-[11px] leading-4 text-slate-400">
      <ShieldAlert size={13} className="mt-0.5 shrink-0 text-amber-300"/>
      {item.modelResearchPct===null?'No independent model forecast for this market.':
        'Experimental forecast includes market input; no independently proven edge.'}
    </p>
    <button type="button" disabled={disabled}
      onClick={()=>onReview?.(item.question,item.context,item)}
      className="mt-3 flex min-h-10 w-full items-center justify-center gap-2 rounded-xl border border-sky-400/30 bg-sky-400/10 px-3 text-xs font-black text-sky-200 transition hover:bg-sky-400/20 disabled:opacity-50">
      <Sparkles size={14}/> Ask the Ref about this game <ArrowUpRight size={13}/>
    </button>
  </article>
}

export default function RefSignalDesk({onReview,disabled=false}) {
  const [sources,setSources]=useState({odds:null,frozen:null,checkedAt:Date.now(),loading:true})
  useEffect(()=>{
    let active=true
    const fetchJson=async path=>{
      try{
        const res=await fetch(path+'?ts='+Date.now(),{cache:'no-store'})
        return res.ok?await res.json():null
      }catch{return null}
    }
    const run=async()=>{
      const [odds,frozen]=await Promise.all([
        fetchJson('/betting_odds_board.json'),
        fetchJson('/nfl_frozen_game_intelligence.json'),
      ])
      if(active)setSources({odds,frozen,checkedAt:Date.now(),loading:false})
    }
    run()
    const interval=setInterval(run,5*60*1000)
    return()=>{active=false;clearInterval(interval)}
  },[])
  const games=useMemo(()=>refMarketReview({
    odds:sources.odds||{},frozen:sources.frozen||{},
    nowMs:sources.checkedAt,sport:'NFL'
  }),[sources])
  return <section aria-label="The Ref source-backed matchup preview" className="rounded-2xl border border-white/10 bg-[#061423] p-3.5 md:p-4">
    <div className="flex flex-wrap items-start justify-between gap-2">
      <div>
        <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.12em] text-sky-300">
          <CalendarClock size={14}/> Signal Desk · NFL
        </div>
        <h2 className="mt-1 text-base font-black text-white md:text-lg">What the market thinks. What Zenith thinks.</h2>
        <p className="mt-1 text-[11px] leading-4 text-slate-400">Swipe game cards, see the actual side and price, then ask for the reasoning.</p>
      </div>
      <span className="rounded-full border border-sky-400/20 bg-sky-400/5 px-2.5 py-1.5 text-[10px] font-black text-sky-300">
        {games.length} matchup{games.length===1?'':'s'} checked
      </span>
    </div>
    {games.length? <div className="mt-3 flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2 lg:grid lg:grid-cols-3 lg:overflow-visible">
      {games.slice(0,3).map(item=><ResearchCard key={item.id} item={item} onReview={onReview} disabled={disabled}/>)}
    </div>: <div className="mt-3 flex items-start gap-2 rounded-xl border border-amber-300/15 bg-white/5 p-3 text-xs leading-5 text-slate-300">
      <Clock3 size={16} className="mt-0.5 shrink-0"/>
      {sources.loading?'Matching official game IDs and original sportsbook quotes…':
        'No official-source-matched upcoming NFL game odds are available in the current research window. No picks or prices will be invented.'}
    </div>}
    <p className="mt-1 text-[10px] leading-4 text-slate-500">
      Dated bookmaker observations are not guaranteed executable. “Book fair” is no-vig market consensus.
      “Zenith research” is experimental, not an established independent advantage.
    </p>
  </section>
}
