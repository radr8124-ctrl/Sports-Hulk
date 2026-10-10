import React, { useEffect, useMemo, useState } from 'react'
import { ChevronRight, ShieldCheck } from 'lucide-react'
import BetMeaning, { formatAmericanOdds, explainBet } from './BetMeaning'
import { explainPropProof } from '../prop_proof_presentation.js'
import { validateIndependentForm, matchIndependentForm, recentFormDescription } from '../prop_independent_form_display.js'

const humanize = value => String(value || '')
  .replaceAll('_', ' ')
  .toLowerCase()
  .replace(/\b\w/g, letter => letter.toUpperCase())

function statusMeta(decision) {
  const value = String(decision || '').toUpperCase()
  if (value === 'SHADOW_PLAY') return { label: 'PLAY', tone: 'bg-emerald-50 text-emerald-700 border-emerald-100' }
  if (value === 'SHADOW_MONITOR') return { label: 'MONITOR', tone: 'bg-amber-50 text-amber-700 border-amber-100' }
  return { label: 'PASS', tone: 'bg-slate-100 text-slate-700 border-slate-200' }
}

function propRow(row) {
  return {
    market: row.market_subtype,
    player: row.player,
    selection: row.side,
    side: row.side,
    line: row.line,
    american_odds: row.american_odds,
  }
}

function PropCard({ row, isPrize, form }) {
  const status = statusMeta(row.shadow_decision)
  const proof = explainPropProof(row)
  const display = propRow(row)
  const formReading = recentFormDescription(form)
  const presentation = status.label === 'PLAY' ? 'PAPER PLAY'
    : status.label === 'MONITOR' ? 'MONITOR'
      : form && form.hit_count >= 3 ? 'FORM WATCH' : 'RESEARCH'
  const displayedSide = isPrize
    ? row.side === 'OVER' ? 'MORE' : row.side === 'UNDER' ? 'LESS' : humanize(row.side)
    : humanize(row.side)

  return (
    <article data-premium-player-card={isPrize?'prizepicks':'props'} className={`min-w-0 rounded-[24px] border border-[#E2D4C0] border-t-[5px] bg-[#FFF8ED] p-4 text-[#173E52] shadow-[0_5px_0_#173E5215] sm:p-5 ${isPrize?'border-t-[#FF7766]':'border-t-[#46CDD2]'}`}>
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-black uppercase tracking-[0.14em] text-[#0E7280]">
            {row.sport}{row.sport === 'NBA' ? ` · ${row.competition_regime === 'UNKNOWN' ? 'Unverified season' : humanize(row.competition_regime || 'UNKNOWN')}` : ''} · {humanize(row.market_subtype)}
          </div>
          <div className="mt-2 truncate text-xl font-black tracking-tight text-[#173E52]">{row.player}</div>
          <div className="mt-1 text-2xl font-black text-[#173E52]">{displayedSide} {row.line}</div>
          {!isPrize && row.american_odds != null && (
            <div className="mt-1 text-sm font-black text-slate-700">
              Bookmaker reference {formatAmericanOdds(row.american_odds)}
            </div>
          )}
        </div>
        <span className={`shrink-0 rounded-full border px-3 py-1 text-[10px] font-black ${presentation==='FORM WATCH' ? 'border-[#A5DAD7] bg-[#DFF6F1] text-[#176372]' : status.tone}`}>{presentation}</span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 rounded-xl border border-[#C9DFD8] bg-[#EAF7F2] p-3 text-xs">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Market fair probability</p>
          <p className="mt-0.5 text-base font-black tabular-nums text-slate-900">{row.market_reference_probability_pct == null ? '—' : row.market_reference_probability_pct+'%'}</p>
        </div>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            {row.probability_source?.startsWith('LANE_CORE') ? 'Zenith experimental estimate' : 'Independent model status'}
          </p>
          <p className="mt-0.5 text-sm font-black text-slate-900">
            {row.probability_source?.startsWith('LANE_CORE') && row.v2_probability_pct != null
              ? row.v2_probability_pct+'%' : 'Not validated'}
          </p>
        </div>
      </div>
      {form && (
        <div className="mt-2 rounded-xl border border-[#AED6D1] bg-[#E7F6F1] px-3 py-2.5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-black text-blue-900">{formReading.label}</span>
            <span className="text-xs font-black tabular-nums text-blue-800">{form.hit_count}/4 prior games</span>
          </div>
          <p className="mt-1 text-[11px] leading-5 text-slate-700">
            {formReading.summary} Four-game mean: <b>{form.average}</b>.
          </p>
          <p className="mt-1 text-[10px] font-semibold leading-4 text-slate-600">Historical form only; not a validated future forecast or verified player availability.</p>
        </div>
      )}
      <p className="mt-2 text-[11px] font-medium leading-5 text-slate-500">
        {isPrize
          ? 'PrizePicks is a pick-em line, not a sportsbook odds quote. Entry payout and correlation must be checked separately.'
          : 'Bookmaker reference price only, not a verified live or executable offer.'}
        {' '}Event: {Number.isFinite(Date.parse(row.event_start||''))
          ? new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZone:'America/New_York',timeZoneName:'short'}).format(Date.parse(row.event_start))
          : 'time unverified'}.
      </p>
      <div className="mt-2 rounded-xl border border-[#E2CCA9] bg-[#FFF0D9] px-3 py-2 text-xs">
        <span className="font-black text-slate-800">What {displayedSide} {row.line} means:</span>
        <span className="ml-1 font-medium leading-5 text-slate-600">{explainBet(display).primary}</span>
      </div>

      <p className="mt-2 text-[11px] font-semibold leading-5 text-slate-600">
        Zenith decision: <b className="text-slate-800">{status.label==='PLAY'?'Paper-qualified':'Not approved as a bet'}</b>
        {' '}· {proof.label}. {isPrize?'Full pick-em payout and correlation are not yet validated.':''}
      </p>

      <details className="group mt-4 rounded-2xl border border-[#D8C9B5] bg-white">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-xs font-black text-slate-700">
          <span>View evidence</span>
          <ChevronRight size={16} className="shrink-0 text-slate-400 transition-transform group-open:rotate-90" />
        </summary>
        <div className="border-t border-slate-100 px-4 pb-4 pt-4">
          <div className="mb-3"><BetMeaning row={display} /></div>
          <p className="mb-3 text-xs font-semibold leading-5 text-slate-700">{proof.description}</p>
          {form && <p className="mb-2 text-[11px] leading-5 text-slate-600">Original four weekly outcomes: {form.historical_stats.join(' / ')}. Original bookmaker source updated: {new Date(form.quote_updated_at).toLocaleString('en-US',{timeZone:'America/New_York'})} ET. Verified by player, market, side, line and scheduled time; official provider UUID was not independently cross-checked.</p>}
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded-xl bg-slate-50 p-3">
              <div className="font-black text-slate-950">{row.v2_probability_pct ?? '—'}%</div>
              <div className="mt-1 text-slate-400">{row.probability_source?.startsWith('LANE_CORE')?'Experimental':'Book-based V2'}</div>
            </div>
            <div className="rounded-xl bg-slate-50 p-3">
              <div className="font-black text-slate-950">{row.market_reference_probability_pct ?? '—'}%</div>
              <div className="mt-1 text-slate-400">Market</div>
            </div>
            <div className="rounded-xl bg-slate-50 p-3">
              <div className="font-black text-slate-950">{row.conservative_probability_pct ?? '—'}%</div>
              <div className="mt-1 text-slate-400">Conservative</div>
            </div>
          </div>

          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-xs">
              <div className="font-black text-slate-800">Quality {row.data_quality_grade || '—'}</div>
              <div className="mt-1 font-semibold text-slate-500">{row.data_quality_book_count ?? '—'} books · {humanize(row.historical_edge_confidence)}</div>
            </div>
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-xs">
              <div className="font-black text-slate-800">Conservative edge</div>
              <div className="mt-1 font-semibold text-slate-500">{row.conservative_edge_pct_points == null ? '—' : `${row.conservative_edge_pct_points}% pts`}</div>
            </div>
          </div>

          <div className="mt-3 text-[11px] font-semibold leading-5 text-slate-400">Model gate: {humanize(row.selection_rule_status)}</div>
          {isPrize && (
            <div className="mt-3 text-[11px] font-semibold leading-5 text-violet-700">
              PrizePicks leg probability is not being presented as entry EV. Entry-level payout proof is separate.
            </div>
          )}
        </div>
      </details>
    </article>
  )
}

export default function PropsV2Panel({ lane = 'PROP' }) {
  const [data, setData] = useState({ summary: {}, picks: [] })
  const [playerResearch,setPlayerResearch] = useState(null)
  const [viewMode,setViewMode] = useState('ALL')
  const [sport, setSport] = useState('ALL')
  const [nbaPhase, setNbaPhase] = useState('ALL')
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(6)
  const [includePast, setIncludePast] = useState(false)
  const [clock, setClock] = useState(() => Date.now())

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      const pull=async path=>{
        try{
          const response=await fetch(path+'?ts='+Date.now(),{cache:'no-store'})
          return response.ok?await response.json():null
        }catch{return null}
      }
      const [payload,form]=await Promise.all([
        pull('/prop_v2_current.json'),pull('/nfl_prop_independent_research.json')
      ])
      if(!cancelled){
        setData(payload || {summary:{},picks:[]})
        setPlayerResearch(form)
        setClock(Date.now())
      }
    }
    load()
    const timer=setInterval(load,5*60*1000)
    return () => { cancelled = true; clearInterval(timer) }
  }, [])

  useEffect(()=>{setLimit(6)},[sport,nbaPhase,lane,query,includePast,viewMode])

  const allRows = useMemo(
    () => (data.picks || []).filter(row => row.lane === lane),
    [data.picks, lane],
  )

  const sports = useMemo(
    () => Array.from(new Set(allRows.map(row => row.sport).filter(Boolean))).sort(),
    [allRows],
  )

  const independentForm = useMemo(()=>validateIndependentForm(playerResearch,clock),[playerResearch,clock])
  const matchedRows=useMemo(()=>allRows
    .filter(row=>(sport==='ALL'||row.sport===sport)
      &&(sport!=='NBA'||nbaPhase==='ALL'||(row.competition_regime||'UNKNOWN')===nbaPhase)
      &&(includePast||(Number.isFinite(Date.parse(row.event_start||''))&&Date.parse(row.event_start)>clock)))
    .map(row=>({...row,independentForm:matchIndependentForm(row,lane,independentForm,clock)}))
  ,[allRows,sport,nbaPhase,includePast,clock,lane,independentForm])
  const recentFormCount=matchedRows.filter(row=>row.independentForm?.hit_count>=3).length

  const rows=useMemo(()=>{
    const decisionRank=row=>row.shadow_decision==='SHADOW_PLAY'?3:row.shadow_decision==='SHADOW_MONITOR'?2:1
    return matchedRows.filter(row=>(viewMode==='ALL'||row.independentForm?.hit_count>=3)
      &&(!query.trim()||[row.player,row.market_subtype,row.side,row.line]
        .some(value=>String(value||'').toLowerCase().includes(query.trim().toLowerCase()))))
      .sort((a,b)=>viewMode==='FORM'
        ?(b.independentForm?.hit_count||0)-(a.independentForm?.hit_count||0)
          ||Date.parse(a.event_start||'')-Date.parse(b.event_start||'')
        :decisionRank(b)-decisionRank(a)
          ||(Date.parse(a.event_start||'')||Infinity)-(Date.parse(b.event_start||'')||Infinity)
          ||Number(b.data_quality_book_count||0)-Number(a.data_quality_book_count||0))
  },[matchedRows,viewMode,query])

  const nbaPhaseCounts = useMemo(() => {
    const tally = { PRESEASON: 0, REGULAR: 0, POSTSEASON: 0, UNKNOWN: 0 }
    for (const row of allRows) {
      if (row.sport === 'NBA') tally[row.competition_regime in tally ? row.competition_regime : 'UNKNOWN'] += 1
    }
    return tally
  }, [allRows])

  const plays = allRows.filter(row => row.shadow_decision === 'SHADOW_PLAY').length
  const monitors = allRows.filter(row => row.shadow_decision === 'SHADOW_MONITOR').length
  const isPrize = lane === 'PRIZEPICKS'

  return (
    <section aria-label={isPrize ? 'PrizePicks current line research' : 'Player props current line research'} className="space-y-5">
      <div data-premium-player-cover
        className="relative overflow-hidden rounded-[23px] border-2 border-[#173E52] bg-[#173E52] p-3 text-[#FFF5E4] shadow-[4px_4px_0_#46CDD24D] sm:p-5">
        <div aria-hidden="true" className="absolute inset-x-0 top-0 h-[5px] bg-[linear-gradient(90deg,#FF7766_0%,#FF7766_35%,#FFD36A_35%,#FFD36A_65%,#46CDD2_65%,#46CDD2_100%)]"/>
        <div className="relative flex flex-col gap-1.5 sm:flex-row sm:items-start sm:justify-between sm:gap-2">
          <div className="min-w-0 flex-1">
            <p className="text-[10px] font-black uppercase tracking-[.16em] text-[#7DE4E1]">
              {isPrize ? 'THE PICK-EM DESK' : 'THE PLAYER LINEUP'}
            </p>
            <h2 className="mt-1 text-[clamp(1.7rem,4vw,2.45rem)] font-black leading-[1.04] tracking-[-.04em] text-[#FFF5E4]">
              {isPrize ? 'PrizePicks' : 'Props'}<span aria-hidden="true" className="text-[#FF7766]">.</span>
            </h2>
            <p className="mt-1 max-w-[650px] text-[11px] font-semibold leading-[1.45] text-[#DCE9E8] sm:text-xs">
              {isPrize
                ? 'Research only. Entry payout is not proven; correlation still needs evidence.'
                : 'Research only. Dated player lines; independent model proof is still required.'}
            </p>
          </div>
          <span className="hidden shrink-0 rounded-lg border border-[#76CAC4]/60 bg-[#234F60] px-2 py-1 text-[9px] font-black uppercase tracking-wider text-[#FFD36A] sm:inline-flex">
            {isPrize ? 'PICK-EM RESEARCH' : 'PLAYER-LINE RESEARCH'}
          </span>
        </div>
        <div data-premium-player-metrics className="relative mt-3 grid grid-cols-3 gap-1.5 rounded-xl bg-[#FFF8ED] p-1.5 text-[#173E52] sm:gap-2 sm:p-2">
          {[
            ['lines',allRows.length,'Saved lines'],
            ['monitors',monitors,'Monitors'],
            ['plays',plays,'Paper plays'],
          ].map(([id,count,label])=>
            <div data-prop-cover-metric={id} key={id} className="min-w-0 rounded-lg bg-white px-1 py-1.5 text-center sm:py-2">
              <div className="text-xl font-black leading-none tabular-nums text-[#173E52]">{count}</div>
              <div className="mt-1 text-[9px] font-black uppercase leading-[1.2] tracking-wide text-[#557079]">{label}</div>
            </div>)}
        </div>
        <div data-prop-cover-context className="relative mt-2 border-t border-[#70A1A7]/40 pt-2 text-[10px] font-bold text-[#D9EBEA]">
          {sport==='ALL'?'All sports':sport}{sport==='NBA'&&nbaPhase!=='ALL'?' · '+humanize(nbaPhase):''} · {isPrize?'No verified entry EV':'Dated quotes, not live offers'}
        </div>
      </div>

      <div className={`rounded-2xl border p-3 text-xs font-semibold leading-5 ${plays ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : monitors ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-blue-200 bg-blue-50 text-blue-900'}`}>
        {plays
          ? `${plays} PLAY${plays === 1 ? '' : 'S'} currently cleared.`
          : monitors
            ? `${monitors} MONITOR${monitors === 1 ? '' : 'S'} are research only. None has cleared the independent prediction or payout proof required for a qualified bet.`
            : `${recentFormCount} NFL lines have recent 3-of-4 or 4-of-4 form support. None has cleared the independent prediction or payout proof required for a qualified bet.`}
      </div>

      {isPrize && (
        <div className="flex gap-3 overflow-x-auto pb-1 md:grid md:grid-cols-3 md:overflow-visible">
          {[
            ['Leg proof', `${monitors} monitors · ${plays} plays`, 'A leg can be interesting without making the whole entry profitable.'],
            ['Entry economics', 'Payout proof required', 'The full entry needs actual payout economics before EV can be claimed.'],
            ['Historical trends', `${recentFormCount} form watches`, 'Four prior results can help research a leg, not prove future accuracy.'],
          ].map(([label, value, detail]) => (
            <div key={label} className="min-w-[240px] rounded-2xl border border-[#DCCCB6] border-t-[4px] border-t-[#FF7766] bg-[#FFF8ED] p-4 shadow-[0_4px_0_#173E5210] md:min-w-0">
              <div className="text-[10px] font-black uppercase tracking-[0.12em] text-[#A45140]">{label}</div>
              <div className="mt-2 text-lg font-black text-slate-950">{value}</div>
              <div className="mt-1 text-xs leading-5 text-slate-500">{detail}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2 overflow-x-auto pb-1">
        {['ALL', ...sports].map(item => (
          <button
            key={item}
            type="button"
            onClick={() => setSport(item)}
            className={`min-h-11 whitespace-nowrap rounded-full border px-3 text-xs font-black ${sport === item ? 'border-[#173E52] bg-[#46CDD2] text-[#173E52]' : 'border-[#D6DCD4] bg-white text-[#526C75] hover:border-[#46CDD2]'}`}
          >
            {item === 'ALL' ? 'All sports' : item}
          </button>
        ))}
      </div>

      {sport === 'NBA' && (
        <div className="space-y-3 rounded-2xl border border-slate-200 bg-white px-4 py-3">
          <p className="text-xs font-semibold text-slate-600">
            NBA competition source: {nbaPhaseCounts.PRESEASON} preseason · {nbaPhaseCounts.REGULAR} regular season · {nbaPhaseCounts.POSTSEASON} postseason · {nbaPhaseCounts.UNKNOWN} unverified.
            These are separate research groups; regular-season prices never stand in for preseason lines.
          </p>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {[
              ['ALL', 'All NBA research'], ['PRESEASON', 'Preseason'],
              ['REGULAR', 'Regular season'], ['POSTSEASON', 'Postseason'], ['UNKNOWN', 'Unverified'],
            ].map(([value, label]) => (
              <button key={value} type="button" onClick={() => setNbaPhase(value)}
                className={`min-h-11 whitespace-nowrap rounded-full border px-3 text-xs font-black ${nbaPhase === value ? 'border-[#173E52] bg-[#46CDD2] text-[#173E52]' : 'border-[#D6DCD4] bg-white text-[#526C75] hover:border-[#46CDD2]'}`}>
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      <div role="group" aria-label="Player research views" className="flex flex-wrap gap-2">
        <button type="button" onClick={()=>setViewMode('ALL')} className={`min-h-10 rounded-xl px-3 py-2 text-xs font-black ${viewMode==='ALL'?'bg-slate-950 text-white':'border border-slate-200 bg-white text-slate-600'}`}>
          All upcoming lines
        </button>
        <button type="button" onClick={()=>setViewMode('FORM')} className={`min-h-10 rounded-xl px-3 py-2 text-xs font-black ${viewMode==='FORM'?'bg-slate-950 text-white':'border border-slate-200 bg-white text-slate-600'}`}>
          Recent-form watch ({recentFormCount})
        </button>
      </div>
      {viewMode==='FORM'&&<p className="text-xs leading-5 text-slate-600">Four-game historical support is a research filter, not model validation or a recommendation. Currently supported for matched NFL player lines only.</p>}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-[#C9D8D2] bg-[#FFF8ED] p-3">
        <label className="min-w-[190px] flex-1">
          <span className="sr-only">Search props by player or market</span>
          <input value={query} onChange={event=>setQuery(event.target.value)}
            placeholder="Search player, market or line" aria-label="Search props by player or market"
            className="min-h-10 w-full min-w-0 rounded-lg border border-slate-200 px-3 text-xs font-semibold text-slate-800" />
        </label>
        <label className="flex items-center gap-2 text-xs font-bold text-slate-600">
          <input type="checkbox" checked={includePast} onChange={event=>setIncludePast(event.target.checked)} />
          Include past research
        </label>
        <span className="text-[11px] font-bold text-slate-500">{rows.length} lines</span>
      </div>

      {rows.length ? (
        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {rows.slice(0,limit).map((row, index) => (
            <PropCard
              key={`${row.event_id}-${row.player_key}-${row.market_subtype}-${row.side}-${index}`}
              row={row}
              isPrize={isPrize}
              form={row.independentForm}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-500 shadow-soft">
          No upcoming {isPrize ? 'PrizePicks' : 'prop'} lines match this filter. Try another sport, clear the search, or include past research.
        </div>
      )}

      {rows.length>limit && <button type="button" onClick={()=>setLimit(n=>n+12)}
        className="min-h-11 rounded-xl border border-blue-200 bg-white px-5 py-3 text-xs font-black text-blue-700">
        Show 12 more {isPrize?'PrizePicks lines':'player props'} · {rows.length-limit} remaining
      </button>}
      <div className="flex gap-3 rounded-2xl border border-[#C6D9D0] bg-[#EBF7F1] p-4 text-sm leading-6 text-[#4C6570]">
        <ShieldCheck size={18} className="mt-0.5 shrink-0 text-blue-700" />
        <div>
          <b>Interpretation first:</b> player requirements stay visible. Probability, quality and edge metrics remain available under View evidence for users who want the deeper research.
        </div>
      </div>
    </section>
  )
}
