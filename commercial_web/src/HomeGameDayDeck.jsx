import React,{useEffect,useMemo,useState} from 'react'
import {Activity,AlertTriangle,ArrowUpRight,CalendarClock,ChevronRight,Radio} from 'lucide-react'
import {GAME_DAY_SPORTS,GAME_DAY_SOURCE_FILES,normalizeGameDayFeed,gameDayDeck} from '../game_day_deck.js'

const labelDate=value=>{
 const ms=Date.parse(value||'')
 if(!Number.isFinite(ms))return 'Time unverified'
 return new Intl.DateTimeFormat('en-US',{
  timeZone:'America/New_York',weekday:'short',month:'short',day:'numeric',
  hour:'numeric',minute:'2-digit',timeZoneName:'short',
 }).format(ms)
}
const pillStyles={
 LIVE:'border-rose-400/30 bg-rose-500/10 text-rose-300',
 FINAL:'border-slate-500/20 bg-slate-500/10 text-slate-400',
 UPCOMING:'border-sky-400/25 bg-sky-400/10 text-sky-200',
 STATUS_NOT_VERIFIED:'border-amber-400/20 bg-amber-500/10 text-amber-300',
 SCORE_UNVERIFIED:'border-amber-400/20 bg-amber-500/10 text-amber-300',
}

function TeamLine({code,name,logo,score,showScore}){
 return <div className="flex min-w-0 items-center gap-2">
   {logo?<img src={logo} alt="" className="h-8 w-8 shrink-0 object-contain" loading="lazy"/>:
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-[11px] font-black text-sky-100">{code.slice(0,3)}</span>}
   <span className="min-w-0 flex-1 truncate text-[13px] font-black text-white" title={name}>{name}</span>
   {showScore?<b className="pl-2 text-lg font-black tabular-nums text-white">{score}</b>:
    <span className="text-[11px] font-bold text-slate-500">{code.slice(0,4)}</span>}
 </div>
}

function GameTile({game}){
 const label=game.state==='LIVE'?'LIVE':
  game.state==='FINAL'?'FINAL':game.state==='UPCOMING'?'UPCOMING':'VERIFY STATUS'
 const showScore=(game.state==='LIVE'||game.state==='FINAL') &&
   game.awayScore!==null&&game.homeScore!==null
 return <article data-testid={'gameday-'+game.key}
   className="w-[min(77vw,286px)] shrink-0 snap-start rounded-2xl border border-white/10 bg-[#0D2138] p-3.5 text-white lg:w-auto">
   <div className="flex flex-wrap items-center justify-between gap-2">
     <span className="text-[11px] font-black tracking-widest text-sky-300">{game.sport}</span>
     <span className={'rounded-lg border px-2 py-1 text-[9px] font-black tracking-wider '+(pillStyles[game.state]||pillStyles.STATUS_NOT_VERIFIED)}>{label}</span>
   </div>
   <div className="mt-3 space-y-2.5">
     <TeamLine code={game.awayCode} name={game.away} logo={game.awayLogo}
       score={game.awayScore} showScore={showScore}/>
     <TeamLine code={game.homeCode} name={game.home} logo={game.homeLogo}
       score={game.homeScore} showScore={showScore}/>
   </div>
   <div className="mt-3 flex min-w-0 items-center justify-between gap-2 border-t border-white/10 pt-2.5">
     <p className="min-w-0 truncate text-[10px] font-bold text-slate-400">{labelDate(game.start)}</p>
     <span className="shrink-0 text-[9px] font-bold text-slate-500">{game.sourceName}</span>
   </div>
 </article>
}

export default function HomeGameDayDeck({onNavigate}){
 const [sport,setSport]=useState('ALL')
 const [data,setData]=useState({loading:true,checkedAt:Date.now(),feeds:{}})
 useEffect(()=>{
  let active=true
  const fetchAll=async()=>{
   const now=Date.now()
   const pairs=await Promise.all(GAME_DAY_SPORTS.map(async league=>{
    try{
     const res=await fetch(GAME_DAY_SOURCE_FILES[league]+'?ts='+now,{cache:'no-store'})
     const value=res.ok?await res.json():null
     return [league,normalizeGameDayFeed(league,value,now)]
    }catch{
     return [league,normalizeGameDayFeed(league,null,now)]
    }
   }))
   if(active)setData({loading:false,checkedAt:now,feeds:Object.fromEntries(pairs)})
  }
  fetchAll()
  const interval=setInterval(fetchAll,5*60*1000)
  return()=>{active=false;clearInterval(interval)}
 },[])
 const deck=useMemo(()=>gameDayDeck(data.feeds,sport,data.checkedAt),
  [data.feeds,data.checkedAt,sport])
 return <section aria-label="Game Day scores and schedule" className="overflow-hidden rounded-[24px] border border-[#18314E] bg-[#071525] p-3.5 shadow-xl shadow-slate-900/10 md:p-5">
  <div className="flex flex-wrap items-start justify-between gap-2">
   <div>
    <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[.14em] text-sky-300">
     <Activity size={14}/> Game Day
    </div>
    <h2 className="mt-1 text-xl font-black tracking-tight text-white sm:text-2xl">Scores & matchups</h2>
    <p className="mt-1 text-[11px] font-medium leading-5 text-slate-400">
     Actual schedules and finals. Never simulated game results.
    </p>
   </div>
   <button type="button" onClick={()=>onNavigate('Scores')}
     className="inline-flex min-h-9 items-center gap-1 rounded-xl border border-sky-500/25 bg-sky-400/10 px-2.5 text-xs font-black text-sky-200">
     All scores <ArrowUpRight size={13}/>
   </button>
  </div>
  <div role="group" aria-label="Choose Game Day sport" className="mt-3 flex gap-2 overflow-x-auto pb-1">
   {[['ALL','All'],['NFL','NFL'],['NHL','NHL'],['CFB','College'],['NBA','NBA'],['MLB','MLB']].map(([id,label])=>
    <button key={id} type="button" aria-pressed={sport===id} onClick={()=>setSport(id)}
      className={'min-h-9 shrink-0 rounded-xl border px-3 py-1 text-xs font-black transition '+
       (sport===id?'border-sky-400 bg-sky-400 text-[#071525]':
       'border-white/10 bg-white/[.055] text-slate-300 hover:border-sky-400/40')}>
      {label}
    </button>)}
  </div>
  {data.loading?<div className="mt-3 flex min-h-36 items-center justify-center gap-2 text-sm font-semibold text-slate-300">
    <Radio size={15} className="animate-pulse text-sky-300"/> Checking league feeds…
   </div>:deck.games.length?
   <div className="mt-3 flex snap-x snap-mandatory gap-3 overflow-x-auto pb-1 lg:grid lg:grid-cols-3 xl:grid-cols-5 lg:overflow-visible">
    {deck.games.map(game=><GameTile key={game.key} game={game}/>)}
   </div>:
   <div className="mt-3 flex min-h-28 items-center gap-3 rounded-xl border border-white/10 bg-[#10243C] p-4">
    <AlertTriangle size={17} className="shrink-0 text-amber-300"/>
    <div>
     <p className="text-xs font-black text-white">
      {deck.state==='DATA_SOURCE_FAILURE'?'DATA SOURCE FAILURE':
       deck.state==='SOURCE_STALE'?'SOURCE STALE':'No games in the display window'}
     </p>
     <p className="mt-1 text-[11px] leading-4 text-slate-400">
      {deck.state==='DATA_SOURCE_FAILURE'?'The selected sport feed failed verification. This is NOT a betting-model NO BET.':
       deck.state==='SOURCE_STALE'?'The latest score feed is too old. Games will not be presented as live.':
        'A valid schedule was checked; no relevant game is currently in this time window.'}
     </p>
    </div>
   </div>}
  {!data.loading&&(deck.sourceFailureCount>0||deck.sourceStaleCount>0)&&
   <p className="mt-2 text-[11px] font-semibold text-amber-200" role="status">
    {deck.sourceFailureCount>0?deck.sourceFailureCount+' league feed'+(deck.sourceFailureCount===1?'':'s')+' unavailable. ':''}
    {deck.sourceStaleCount>0?deck.sourceStaleCount+' league feed'+(deck.sourceStaleCount===1?'':'s')+' stale.':''}
    {' '}Source failures are not counted as NO BET decisions.
   </p>}
  <p className="mt-3 text-[10px] font-semibold leading-4 text-slate-500">
   Score & schedule sources: ESPN / MLB StatsAPI. Game status and source freshness are separate from a validated sportsbook price or positive-EV model.
  </p>
 </section>
}
