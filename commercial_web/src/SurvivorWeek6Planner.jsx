import React, {useEffect,useMemo,useState} from 'react'
import {CalendarDays,ChevronDown,Clock3,ShieldCheck,ShieldAlert} from 'lucide-react'
import {projectWeek6WhatIf} from '../survivor_week6_projection.js'

const etDate=iso=>{
  if(!Number.isFinite(Date.parse(iso||'')))return 'Time unverified'
  return new Intl.DateTimeFormat('en-US',{
    timeZone:'America/New_York',weekday:'short',month:'short',day:'numeric',
    hour:'numeric',minute:'2-digit',timeZoneName:'short',
  }).format(new Date(iso))
}

export default function SurvivorWeek6Planner({entryName,getAccessToken}) {
  const [plan,setPlan]=useState(null)
  const [status,setStatus]=useState('LOADING')
  const [whatIf,setWhatIf]=useState('')
  useEffect(()=>{setWhatIf('')},[entryName])
  useEffect(()=>{
    let cancelled=false
    const load=async()=>{
      try{
        const token=await getAccessToken()
        if(!token)throw Error('Sign in to view private Week 6 planning.')
        const url='/api/survivor/week6-plan?entry='+encodeURIComponent(entryName)+'&ts='+Date.now()
        const response=await fetch(url,{
          cache:'no-store',headers:{Authorization:'Bearer '+token},
        })
        const result=await response.json()
        if(cancelled)return
        if(!response.ok||result.status!=='SCHEDULE_ONLY_UNRANKED'){
          setPlan(null);setStatus(result.status||'SCHEDULE_UNAVAILABLE');return
        }
        setPlan(result);setStatus('READY')
      }catch{if(!cancelled){setPlan(null);setStatus('SCHEDULE_UNAVAILABLE')}}
    }
    load()
    const interval=window.setInterval(load,90*1000)
    return()=>{cancelled=true;window.clearInterval(interval)}
  },[entryName,getAccessToken])

  const whatIfResult=useMemo(()=>plan?projectWeek6WhatIf(plan,whatIf):null,[plan,whatIf])
  const ready=Boolean(status==='READY'&&plan&&whatIfResult&&
    ['WHAT_IF_ONLY','SAVED_IN_ZENITH_ONLY'].includes(whatIfResult.status))
  const saved=Boolean(plan?.saved_week5_team)
  const firstThursday=plan?.games?.find(row=>Date.parse(row.kickoff_et)===Date.parse(plan?.earliest_kickoff_et))

  return (
    <section aria-label="Week 6 two-pick what-if planner" data-survivor-week6-planner
      className="overflow-hidden rounded-[24px] border border-[#C9D9DC] bg-[#FFF8ED] p-4 shadow-soft md:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-black uppercase tracking-[.15em] text-[#AF574B]">SURVIVOR STRATEGY · FUTURE VALUE</p>
          <h2 className="mt-1 text-lg font-black tracking-tight text-[#173E52] md:text-xl">Week 6 · Two-pick planner</h2>
          <p className="mt-1 max-w-xl text-[11px] font-medium leading-[1.4] text-[#576C78] sm:text-xs">
            Preview how Week 5 affects next week's two required picks. Research only; nothing is saved.
          </p>
        </div>
        <span className="hidden shrink-0 rounded-lg border border-[#BCD5D4] bg-white px-2.5 py-1.5 text-[10px] font-black text-[#166674] sm:inline-flex">
          TWO UNUSED TEAMS NEEDED
        </span>
      </div>

      {!ready ? (
        <p className="mt-3 rounded-xl border border-amber-200 bg-white p-3 text-xs font-semibold leading-5 text-amber-900">
          <ShieldAlert size={14} className="mr-1 inline" />
          {status==='LOADING'?'Checking the verified NFL schedule and your private eligibility…':
            'Week 6 eligibility cannot be verified right now. No pair or team will be suggested until the schedule and rules agree.'}
        </p>
      ) : (
        <>
          <div className="mt-3 rounded-xl border border-[#CFDED7] bg-white p-3">
            {plan.week5_deadline_passed&&!saved&&(
              <p className="mb-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-black text-amber-900">
                The Week 5 Saturday 6 PM Eastern pool deadline has passed. Unsubmitted Week 5 alternatives cannot be selected here.
              </p>
            )}
            <div className="flex flex-wrap items-center justify-between gap-2">
              <label htmlFor="zenith-week6-what-if" className="text-[11px] font-black text-[#173E52]">
                {saved?'Week 5 team saved in Zenith':'What if I use this team in Week 5?'}
              </label>
              <span className="text-[10px] font-black text-[#0E7280]">WHAT-IF ONLY</span>
            </div>
            <div className="relative mt-1.5">
              <select id="zenith-week6-what-if" aria-label="Simulate Week 5 team for Week 6"
                value={saved?plan.saved_week5_team:whatIf}
                disabled={saved}
                onChange={e=>setWhatIf(e.target.value)}
                className="w-full min-w-0 appearance-none rounded-xl border border-[#BFD7D7] bg-[#F7FAF8] px-3 py-2.5 pr-10 text-xs font-bold text-[#173E52] disabled:opacity-70">
                {!saved&&<option value="">No team selected — show baseline</option>}
                {(saved?[plan.saved_week5_team]:(plan.week5_what_if_teams||[])).map(team=>(
                  <option key={team} value={team}>{team}</option>
                ))}
              </select>
              <ChevronDown size={16} className="pointer-events-none absolute right-3 top-3 text-[#527280]" />
            </div>
            <p data-week6-scenario-status className="mt-2 text-[10px] font-semibold leading-4 text-slate-600">
              {saved
                ? 'Your existing Zenith saved pick is included automatically. This does not verify external pool submission.'
                : whatIf ? `Testing ${whatIf} only. Your current Week 5 pick remains unchanged.`
                  : 'Baseline only. You have not committed to a Week 5 team.'}
            </p>
          </div>

          <div className="mt-3 grid grid-cols-3 gap-1.5 rounded-xl bg-[#173E52] p-1.5 text-center text-white">
            {[
              ['eligible',whatIfResult.eligible_week6_teams,'Eligible teams'],
              ['games',whatIfResult.games_with_eligible_sides,'Different games'],
              ['pairs',whatIfResult.distinct_game_pair_options,'Possible pairs'],
            ].map(([id,value,label])=>(
              <div key={id} data-week6-metric={id} className="min-w-0 rounded-lg bg-[#254B5D] px-1 py-2">
                <div className="text-xl font-black leading-none tabular-nums text-[#FFF5E4] sm:text-2xl">{value}</div>
                <div className="mt-1 text-[9px] font-semibold leading-tight text-[#CFE7E7] sm:text-[10px]">{label}</div>
              </div>
            ))}
          </div>
          <p className="mt-1.5 text-[10px] font-semibold leading-4 text-slate-600">
            Pair count is not a prediction. Teams already used and opposite sides of one game are excluded.
          </p>
          <div className="mt-2 rounded-xl border border-[#E0D6C2] bg-white px-3 py-2 text-[11px] font-semibold leading-5 text-[#415A67]">
            <p><CalendarDays size={13} className="mr-1 inline text-[#C26B52]" /><b>Week 6 byes:</b> {plan.byes.map(team=>team.split(' ').at(-1)).join(' · ')}</p>
            <p className="mt-0.5"><Clock3 size={13} className="mr-1 inline text-[#C26B52]" /><b>Thursday early cutoff:</b> {etDate(plan.early_game_cutoff_et)}</p>
            <details className="mt-1.5 border-t border-slate-100 pt-1 text-[10px] font-medium leading-4 text-slate-600">
              <summary className="cursor-pointer font-black text-[#166674]">Full bye and deadline rules</summary>
              <p className="mt-1">Teams on bye: {plan.byes.join(' · ')}.</p>
              <p className="mt-1">{firstThursday?.away||'Away'} at {firstThursday?.home||'Home'} begins {etDate(plan.earliest_kickoff_et)}. If using that Thursday game, the earlier-game two-hour rule applies. Otherwise the regular Saturday 6 PM Eastern pool cutoff applies. Check the organizer's acknowledgement.</p>
            </details>
          </div>
          <details className="mt-3 rounded-xl border border-[#D9D7C9] bg-white p-3">
            <summary className="cursor-pointer text-xs font-black text-[#173E52]">
              View all {plan.games.length} Week 6 fixtures and your available sides
            </summary>
            <div className="mt-2 max-h-80 space-y-1.5 overflow-y-auto text-[11px]">
              {whatIfResult.games.map(game=>(
                <div key={game.game_id} className="rounded-lg bg-[#F6F8F7] p-2.5">
                  <div className="font-black text-[#173E52]">{game.away} at {game.home}</div>
                  <div className="mt-0.5 font-medium text-slate-500">{etDate(game.kickoff_et)}</div>
                  <div className="mt-0.5 font-semibold text-[#166674]">
                    Available: {game.eligible_teams.length?game.eligible_teams.join(' / '):'Neither team'}
                  </div>
                </div>
              ))}
            </div>
          </details>
          <p className="mt-2 text-[10px] font-medium leading-4 text-slate-500">
            <ShieldCheck size={13} className="mr-1 inline text-[#0E7280]" />
            NFLverse 2026 · SHA {plan.source_sha256.slice(0,10)}. No fresh odds or proven forecasts; no pick saved here.
            <span className="hidden sm:inline"> Injury availability and official external pool acknowledgement must be checked independently.</span>
          </p>
        </>
      )}
    </section>
  )
}
