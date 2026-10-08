import React, { useMemo, useState } from 'react'
import { AlertTriangle, ArrowLeftRight, BarChart3, Plus, ShieldCheck, X } from 'lucide-react'
import { compareFantasyTrade } from './fantasyTradeResearch'

const fmt = value => value == null ? '—' : Number(value).toFixed(1)
const eligible = ['DIRECTIONAL_RESEARCH_ONLY']

function TradeInputs({ title, values, onChange, sourcePlayers, idPrefix }) {
  const update = (index, value) => onChange(values.map((item,i)=>i===index ? value : item))
  const add = () => values.length<4 && onChange([...values,''])
  const remove = index => onChange(values.filter((_,i)=>i!==index))
  return (
    <div className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4">
      <h3 className="text-xs font-black uppercase tracking-wide text-slate-700">{title}</h3>
      <div className="mt-3 space-y-2">
        {values.map((value,i)=>(
          <div className="flex min-w-0 items-center gap-2" key={i}>
            <input
              type="text" list={idPrefix+'-trade-players'}
              aria-label={title+' player '+(i+1)} value={value} maxLength={120}
              autoComplete="off"
              onChange={event=>update(i,event.target.value)}
              placeholder={i===0?'Enter NFL player name':'Add another player'}
              className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-slate-50 px-3 py-3 text-sm font-semibold text-slate-950 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
            />
            {values.length>1&&(
              <button type="button" onClick={()=>remove(i)} aria-label={'Remove '+title+' player '+(i+1)}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-slate-200 text-slate-500"><X size={17}/></button>
            )}
          </div>
        ))}
      </div>
      <datalist id={idPrefix+'-trade-players'}>{sourcePlayers.map(name=><option key={name} value={name}/>)}</datalist>
      <button type="button" onClick={add} disabled={values.length>=4}
        className="mt-3 inline-flex min-h-10 items-center gap-1 text-xs font-black text-blue-700 disabled:opacity-40"><Plus size={14}/> Add player</button>
    </div>
  )
}

function PlayerEvidence({ title, rows }) {
  return (
    <div className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4">
      <h3 className="text-xs font-black uppercase tracking-wide text-slate-500">{title}</h3>
      <div className="mt-3 divide-y divide-slate-100">
        {rows.map((row,i)=>(
          <div key={row.input+'-'+i} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <div className="min-w-0 flex-1">
              <div className="text-sm font-black text-slate-950">{row.name}</div>
              <div className="mt-0.5 text-xs text-slate-500">{row.found? [row.team,row.position].filter(Boolean).join(' · '): 'Not covered'}</div>
            </div>
            <div className="text-right">
              <div className="text-lg font-black tabular-nums text-slate-900">{fmt(row.ros)}</div>
              <div className="text-[10px] font-bold uppercase tracking-wide text-slate-500">ROS research</div>
              {row.ambiguous&&<div className="text-[10px] font-bold text-amber-700">Ambiguous name</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function FantasyTradeResearch({
  weeklyRows=[], generatedAt=null, teams=[], selectedLeagueId=null,
}) {
  const [give,setGive]=useState([''])
  const [receive,setReceive]=useState([''])
  const [analyzed,setAnalyzed]=useState(false)
  const chosen=teams.find(team=>team.league_id===selectedLeagueId) || teams[0] || null
  const roster=Array.isArray(chosen?.roster)?chosen.roster:[]
  const playerNames=useMemo(()=>(Array.isArray(weeklyRows)?weeklyRows:[])
    .map(row=>String(row?.player||'').trim()).filter(Boolean)
    .sort((a,b)=>a.localeCompare(b)),[weeklyRows])
  const comparison=useMemo(() => compareFantasyTrade({
    give,receive,weeklyRows,sourceGeneratedAt:generatedAt,savedRoster:roster,
  }),[give,receive,weeklyRows,generatedAt,roster])
  const updateGive=values=>{setGive(values);setAnalyzed(false)}
  const updateReceive=values=>{setReceive(values);setAnalyzed(false)}
  const canAnalyze=give.some(item=>item.trim())&&receive.some(item=>item.trim())

  return (
    <section aria-label="Fantasy trade research" className="space-y-5">
      <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-soft sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-[11px] font-black uppercase tracking-[0.16em] text-blue-700">Fantasy · Trades</div>
            <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-950">Trade research desk</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Explore NFL rest-of-season research for players you might give and receive. The index is research, not a fantasy-point projection or a verdict that a trade is fair.</p>
          </div>
          <span className="rounded-full bg-blue-50 px-3 py-1.5 text-[10px] font-black uppercase text-blue-800">Read-only</span>
        </div>
        <div className="mt-4 flex flex-wrap gap-2 text-xs font-semibold text-slate-500">
          <span className="rounded-full bg-slate-50 px-3 py-1.5">NFL covered: {playerNames.length} named research rows</span>
          <span className="rounded-full bg-slate-50 px-3 py-1.5">Saved league: {chosen ? chosen.league_name || chosen.team_name || 'Selected team' : 'None'}</span>
          <span className="rounded-full bg-slate-50 px-3 py-1.5">Updated: {generatedAt && !Number.isNaN(Date.parse(generatedAt)) ? new Date(generatedAt).toLocaleDateString():'Unknown'}</span>
        </div>

        <div className="mt-5 grid min-w-0 gap-3 md:grid-cols-[1fr_auto_1fr] md:items-start">
          <TradeInputs title="You give" values={give} onChange={updateGive} sourcePlayers={playerNames} idPrefix="give"/>
          <div className="hidden pt-9 text-blue-700 md:block"><ArrowLeftRight size={24}/></div>
          <TradeInputs title="You receive" values={receive} onChange={updateReceive} sourcePlayers={playerNames} idPrefix="receive"/>
        </div>
        <button type="button" onClick={()=>setAnalyzed(true)} disabled={!canAnalyze}
          className="mt-4 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-5 py-3 text-sm font-black text-white disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto">
          <BarChart3 size={17}/> Compare research
        </button>
      </div>

      {analyzed && (
        <div aria-live="polite" className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-soft sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-xl font-black text-slate-950">What the evidence supports</h3>
            <span className="rounded-full bg-amber-50 px-3 py-1.5 text-[10px] font-black uppercase text-amber-800">
              {comparison.status.replaceAll('_',' ')}
            </span>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <PlayerEvidence title="Giving" rows={comparison.giving}/>
            <PlayerEvidence title="Receiving" rows={comparison.getting}/>
          </div>
          {comparison.comparable && eligible.includes(comparison.status) && (
            <div className="mt-4 rounded-2xl border border-blue-200 bg-blue-50 p-4">
              <div className="text-[10px] font-black uppercase tracking-wide text-blue-700">Directional ROS research index change</div>
              <div className="mt-2 text-3xl font-black tabular-nums text-slate-950">{comparison.deltaRos>=0?'+':''}{fmt(comparison.deltaRos)}</div>
              <div className="mt-2 text-xs font-semibold text-blue-900">Matched positions and equal player counts only. Positive does not mean accept the trade.</div>
            </div>
          )}
          <div className="mt-4 flex gap-3 rounded-2xl bg-slate-50 p-4">
            <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-600"/>
            <p className="text-xs leading-6 text-slate-700">{comparison.explanation}</p>
          </div>
          {comparison.givingNotOnSavedRoster.length>0 && (
            <p className="mt-3 text-xs font-semibold text-amber-800">Not listed on the selected saved roster: {comparison.givingNotOnSavedRoster.join(', ')}. Confirm your latest roster before considering a trade.</p>
          )}
          <p className="mt-4 flex items-start gap-2 text-[11px] leading-5 text-slate-500"><ShieldCheck size={14} className="mt-0.5 shrink-0"/> No trades are submitted. Other managers’ team rosters, offer availability, league scoring rules and transaction permissions are not verified by this public research comparison.</p>
        </div>
      )}
    </section>
  )
}
