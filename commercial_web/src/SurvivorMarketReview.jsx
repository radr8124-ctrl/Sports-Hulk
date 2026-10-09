import React, { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, CalendarClock, Database, ShieldCheck } from 'lucide-react'
import { survivorSourceReview } from '../survivor_source_review.js'

const dateET = iso => {
  const dt = Date.parse(iso || '')
  return Number.isFinite(dt)
    ? new Intl.DateTimeFormat('en-US', {
      weekday:'short', month:'short', day:'numeric', hour:'numeric', minute:'2-digit',
      timeZone:'America/New_York',timeZoneName:'short'
    }).format(dt)
    : 'Time not verified'
}

const nameRisk = s => s.replaceAll('_',' ').toLowerCase().replace(/\b\w/g,v=>v.toUpperCase())

function TeamRow({ row, index, archived=false }) {
  const f = row.future_value_index
  return (
    <article className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-black uppercase tracking-wider text-blue-700">
            #{index+1} {archived ? 'archived Friday preview · NOT current' : 'market-only research'}
          </p>
          <h3 className="mt-2 truncate text-lg font-black text-slate-950">{row.team}</h3>
          <p className="mt-1 text-xs font-semibold text-slate-600">vs {row.opponent}</p>
          <p className="mt-1 text-[11px] text-slate-500">{dateET(row.start)}</p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-xl font-black tabular-nums text-slate-900">{row.no_vig_market_pct}%</p>
          <p className="max-w-[95px] text-[10px] leading-4 text-slate-500">
            {archived ? 'Historical no-vig snapshot · NOT a current price' : 'Market-only no-vig estimate'}
          </p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-semibold text-slate-600">
        {f !== null && (
          <span className="rounded-lg bg-slate-50 px-2 py-1.5">
            Later-week value: {f} · {nameRisk(row.future_value_label || 'Unknown')}
          </span>
        )}
        <span className="rounded-lg bg-slate-50 px-2 py-1.5">Unconfirmed model edge</span>
        {archived && <span className="rounded-lg border border-amber-200 bg-amber-50 px-2 py-1.5 text-amber-800">EXPIRED / NOT LIVE</span>}
      </div>
      {row.risk_signals?.length > 0 && (
        <p className="mt-2 text-[11px] leading-5 text-amber-800">
          Watch: {row.risk_signals.map(nameRisk).join(' · ')}
        </p>
      )}
      {row.future_schedule && (
        <p className="mt-2 text-[11px] leading-5 text-slate-500">
          <b>Later matchups to consider:</b> {row.future_schedule}
        </p>
      )}
      <details className="mt-3 border-t border-slate-100 pt-2 text-xs">
        <summary className="cursor-pointer py-2 font-bold text-blue-700">Why this market estimate?</summary>
        <p className="mt-1 text-[11px] leading-5 text-slate-600">
          A paired home-and-away moneyline from {row.sportsbook} was matched to the official NFL game and had its sportsbook margin removed.
          This is not a Sports Zenith independent forecast.
        </p>
        <p className="mt-2 text-[11px] leading-5 text-slate-600">
          Last sportsbook update: {dateET(row.updated_at)}. The quote is a dated research observation,
          not a confirmed executable offer or guaranteed winner. Confirm injuries, starting QBs and lines before the pool deadline.
        </p>
      </details>
    </article>
  )
}

export default function SurvivorMarketReview({ week, candidates=[], usedTeams=[], personal=false,
  recommendedStatus='', requiredPicks=null }) {
  const [feeds,setFeeds]=useState({scores:null,references:null,checkedAt:Date.now()})
  useEffect(()=>{
    let cancelled=false
    const refresh=async()=>{
      const load=async path=>{
        try{
          const response=await fetch(path+'?ts='+Date.now(),{cache:'no-store'})
          return response.ok ? await response.json() : null
        }catch{return null}
      }
      const [scores,references]=await Promise.all([
        load('/nfl_scores.json'),load('/nfl_research_book_refs.json')
      ])
      if(!cancelled)setFeeds({scores,references,checkedAt:Date.now()})
    }
    refresh()
    const timer=setInterval(refresh,5*60*1000)
    return ()=>{cancelled=true;clearInterval(timer)}
  },[])

  const research=useMemo(()=>survivorSourceReview({
    scores:feeds.scores||{}, references:feeds.references||{},
    candidates, usedTeams:personal ? usedTeams : [],
    nowMs:feeds.checkedAt, poolWeek:week,
  }),[feeds,candidates,usedTeams,personal,week])
  // Replays only the *separate* SHA-derived source-time archive, never the
  // expired value of the current feed. Keep the archived provider time visible.
  const archived=feeds.references?.archived_snapshot
  const archiveTime=Date.parse(archived?.source_captured_at || '')
  const archivePreview=useMemo(()=>{
    if (research.length || archived?.status!=='ARCHIVED_SOURCE_ONLY_NOT_CURRENT' ||
      archived?.is_current_quote!==false || archived?.is_approved_bet!==false ||
      archived?.model_advantage_proven!==false || !Number.isFinite(archiveTime) ||
      archiveTime>feeds.checkedAt ||
      archived?.original_archive_sha256!==feeds.references?.original_archive?.sha256 ||
      !Array.isArray(archived?.fixtures)) return []
    const historical={...feeds.references,fixtures:archived.fixtures}
    return survivorSourceReview({
      scores:feeds.scores||{},references:historical, candidates,
      usedTeams:personal ? usedTeams : [], nowMs:archiveTime,poolWeek:week,
    }).filter(row=>Date.parse(row.start)>feeds.checkedAt)
  },[research,feeds,candidates,usedTeams,personal,week,archiveTime,archived])
  const isArchived=!research.length && archivePreview.length>0
  const shown=isArchived ? archivePreview : research
  const primaryWait=personal && recommendedStatus==='WAIT_FOR_FRESH_VERIFIED_MARKET_QUOTES'
  const limited=shown.slice(0,6)
  return (
    <section aria-label="Survivor weekly sportsbook review" className="rounded-[30px] border border-slate-200 bg-slate-50/70 p-5 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="eyebrow">Before Saturday's pool deadline</p>
          <h2 className="mt-1 text-xl font-black text-slate-950">Week {week||'—'} · Survivor market review</h2>
          <p className="mt-2 max-w-2xl text-xs leading-5 text-slate-600">
            Compare matchup prices, preserve teams needed later, and check lineup news. Market favorites are NOT certified Zenith recommendations.
            {personal ? ' Teams your entry already used are excluded.' : ' Sign in and link your entry to exclude your used teams.'}
          </p>
        </div>
        <span className="rounded-full bg-white px-3 py-2 text-[10px] font-black text-blue-900">
          <ShieldCheck size={13} className="mr-1 inline"/>
          {isArchived ? `0 current · ${archivePreview.length} archived comparisons` : `${research.length} source-matched options`}
        </span>
      </div>
      {primaryWait && (
        <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs font-semibold text-amber-900">
          The primary sportsbook feed remains stale. No model-backed Survivor selection is approved; the comparisons below use separately verified, dated research snapshots.
        </p>
      )}
      <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-semibold text-slate-600">
        <span className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <CalendarClock size={14} className="mr-1 inline"/> Pool deadline: Saturday 6 PM ET
        </span>
        <span className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          Week {week||'—'}: {personal && Number.isInteger(requiredPicks) ? requiredPicks : 'see official rules'} pick(s)
        </span>
        {week===5 && <span className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-amber-900">
          Week 6 needs TWO unused teams
        </span>}
      </div>
      <div className="mt-3 flex gap-2 text-xs leading-5 text-slate-600">
        <Database size={17} className="mt-0.5 shrink-0 text-blue-700"/>
        <p>Only source-time-qualified quotes count as current research. If they expire, the previous snapshot remains clearly marked ARCHIVED until a new verified capture arrives.</p>
      </div>
      {isArchived && (
        <p className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-3 text-xs font-bold leading-5 text-amber-950">
          ARCHIVED FRIDAY PREVIEW ONLY · Original source capture: {dateET(archived?.source_captured_at)}.
          These observations have expired and MUST NOT be treated as current sportsbook odds, live survival probabilities or a Zenith pick.
          Wait for a new source-confirmed market capture before choosing your pool entry.
        </p>
      )}
      {limited.length>0 ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {limited.map((row,index)=><TeamRow key={row.game_id} row={row} index={index} archived={isArchived}/>)}
        </div>
      ):(
        <p className="mt-4 rounded-xl border border-amber-200 bg-white px-3 py-3 text-sm font-semibold text-slate-700">
          No source-fresh Week {week||'current'} market reference is available yet. The scheduled NFL source collection must supply a newer verified quote; old numbers will not be relabeled as live.
        </p>
      )}
      {shown.length>limited.length && (
        <details className="mt-3">
          <summary className="cursor-pointer py-2 text-sm font-black text-blue-700">
            See {shown.length-limited.length} more Week {week||'current'} {isArchived ? 'archived comparisons' : 'research options'}
          </summary>
          <div className="mt-2 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {shown.slice(limited.length).map((row,index)=><TeamRow key={row.game_id} row={row} index={index+limited.length} archived={isArchived}/>)}
          </div>
        </details>
      )}
      <div className="mt-4 flex items-start gap-2 rounded-xl bg-white p-3 text-xs leading-5 text-slate-600">
        <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-700"/>
        <p>Do not submit picks based only on this market snapshot. Recheck starting quarterbacks, injuries, updated odds, team availability and your pool's rules. Saving a team in Zenith never submits it to your external pool.</p>
      </div>
    </section>
  )
}
