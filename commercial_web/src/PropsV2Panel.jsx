import React, { useEffect, useMemo, useState } from 'react'
import { ChevronRight, ShieldCheck } from 'lucide-react'
import BetMeaning, { formatAmericanOdds } from './BetMeaning'
import { explainPropProof } from '../prop_proof_presentation.js'

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

function PropCard({ row, isPrize }) {
  const status = statusMeta(row.shadow_decision)
  const proof = explainPropProof(row)
  const display = propRow(row)

  return (
    <article className="min-w-0 rounded-[28px] border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-black uppercase tracking-[0.14em] text-blue-700">
            {row.sport}{row.sport === 'NBA' ? ` · ${row.competition_regime === 'UNKNOWN' ? 'Unverified season' : humanize(row.competition_regime || 'UNKNOWN')}` : ''} · {humanize(row.market_subtype)}
          </div>
          <div className="mt-2 truncate text-xl font-black tracking-tight text-slate-950">{row.player}</div>
          <div className="mt-1 text-2xl font-black text-slate-950">{humanize(row.side)} {row.line}</div>
          {!isPrize && row.american_odds != null && (
            <div className="mt-1 text-sm font-black text-slate-700">
              Reference odds {formatAmericanOdds(row.american_odds)}
            </div>
          )}
        </div>
        <span className={`shrink-0 rounded-full border px-3 py-1 text-[10px] font-black ${status.tone}`}>{status.label}</span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 rounded-xl bg-slate-50 p-3 text-xs">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Market fair probability</p>
          <p className="mt-0.5 text-base font-black tabular-nums text-slate-900">{row.market_reference_probability_pct == null ? '—' : row.market_reference_probability_pct+'%'}</p>
        </div>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            {row.probability_source?.startsWith('LANE_CORE') ? 'Zenith experimental estimate' : 'Zenith model proof'}
          </p>
          <p className="mt-0.5 text-sm font-black text-slate-900">
            {row.probability_source?.startsWith('LANE_CORE') && row.v2_probability_pct != null
              ? row.v2_probability_pct+'%' : 'No proven edge'}
          </p>
        </div>
      </div>
      <p className="mt-2 text-[11px] font-medium leading-5 text-slate-500">
        {isPrize
          ? 'PrizePicks is a pick-em line, not a sportsbook odds quote. Entry payout and correlation must be checked separately.'
          : 'Bookmaker reference price only, not a verified live or executable offer.'}
        {' '}Event: {Number.isFinite(Date.parse(row.event_start||''))
          ? new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZone:'America/New_York',timeZoneName:'short'}).format(Date.parse(row.event_start))
          : 'time unverified'}.
      </p>
      <div className="mt-3">
        <BetMeaning row={display} compact />
      </div>

      {isPrize && (
        <div className="mt-4 rounded-2xl border border-violet-200 bg-violet-50 p-3 text-xs font-semibold leading-5 text-violet-950">
          <b>Leg research only.</b> A good leg does not automatically make a profitable PrizePicks entry; payout economics and the other legs still matter.
        </div>
      )}

      <div className={`mt-4 rounded-2xl border px-4 py-3 ${status.label === 'PLAY' ? 'border-emerald-200 bg-emerald-50' : status.label === 'MONITOR' ? 'border-amber-200 bg-amber-50' : 'border-slate-200 bg-slate-50'}`}>
        <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Sports Zenith status</div>
        <div className="mt-1 text-sm font-black text-slate-800">{status.label} · {proof.label}</div>
        <p className="mt-1 text-xs font-semibold leading-5 text-slate-600">{proof.description}</p>
      </div>

      <details className="group mt-4 rounded-2xl border border-slate-200 bg-white">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-xs font-black text-slate-700">
          <span>View evidence</span>
          <ChevronRight size={16} className="shrink-0 text-slate-400 transition-transform group-open:rotate-90" />
        </summary>
        <div className="border-t border-slate-100 px-4 pb-4 pt-4">
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded-xl bg-slate-50 p-3">
              <div className="font-black text-slate-950">{row.v2_probability_pct ?? '—'}%</div>
              <div className="mt-1 text-slate-400">Model</div>
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
  const [sport, setSport] = useState('ALL')
  const [nbaPhase, setNbaPhase] = useState('ALL')
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(12)
  const [includePast, setIncludePast] = useState(false)
  const [clock, setClock] = useState(() => Date.now())

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const response = await fetch(`/prop_v2_current.json?ts=${Date.now()}`, { cache: 'no-store' })
        const payload = response.ok ? await response.json() : { summary: {}, picks: [] }
        if (!cancelled) setData(payload)
      } catch {
        if (!cancelled) setData({ summary: {}, picks: [] })
      }
    }
    load()
    const timer=setInterval(()=>{load();setClock(Date.now())},5*60*1000)
    return () => { cancelled = true; clearInterval(timer) }
  }, [])

  useEffect(()=>{setLimit(12)},[sport,nbaPhase,lane,query,includePast])

  const allRows = useMemo(
    () => (data.picks || []).filter(row => row.lane === lane),
    [data.picks, lane],
  )

  const sports = useMemo(
    () => Array.from(new Set(allRows.map(row => row.sport).filter(Boolean))).sort(),
    [allRows],
  )

  const rows = useMemo(() => {
    const decisionRank = row => row.shadow_decision === 'SHADOW_PLAY' ? 3 : row.shadow_decision === 'SHADOW_MONITOR' ? 2 : 1
    return allRows
      .filter(row => (sport === 'ALL' || row.sport === sport)
        && (sport !== 'NBA' || nbaPhase === 'ALL' || (row.competition_regime || 'UNKNOWN') === nbaPhase)
        && (includePast || (Number.isFinite(Date.parse(row.event_start||'')) && Date.parse(row.event_start)>clock))
        && (!query.trim() || [row.player,row.market_subtype,row.side,row.line]
          .some(value=>String(value||'').toLowerCase().includes(query.trim().toLowerCase()))))
      .sort((a, b) =>
        decisionRank(b) - decisionRank(a)
        || (Date.parse(a.event_start||'') || Infinity) - (Date.parse(b.event_start||'') || Infinity)
        || (Number(b.data_quality_book_count||0) - Number(a.data_quality_book_count||0))
      )
  }, [allRows, sport, nbaPhase,includePast,query,clock])

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
    <section className="space-y-5">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{isPrize ? 'Pick-em research' : 'Player markets'}</p>
          <h2>{isPrize ? 'PrizePicks' : 'Props'}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            {isPrize
              ? 'Understand each leg first. Sports Zenith keeps leg quality separate from the payout economics of the full entry.'
              : 'Understand the player line first. Model, market and conservative probabilities stay underneath as evidence rather than crowding the first view.'}
          </p>
        </div>
        <span className="health-pill">{allRows.length} CURRENT</span>
      </div>

      <div className={`rounded-2xl border p-4 text-sm font-semibold ${plays ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : monitors ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-blue-200 bg-blue-50 text-blue-900'}`}>
        {plays
          ? `${plays} PLAY${plays === 1 ? '' : 'S'} currently cleared.`
          : monitors
            ? `${monitors} MONITOR${monitors === 1 ? '' : 'S'} are promising but not proven PLAYs.`
            : 'No independently proven PLAY is being forced right now. PASS is a valid answer.'}
      </div>

      {isPrize && (
        <div className="flex gap-3 overflow-x-auto pb-1 md:grid md:grid-cols-3 md:overflow-visible">
          {[
            ['Leg proof', `${monitors} monitors · ${plays} plays`, 'A leg can be interesting without making the whole entry profitable.'],
            ['Entry economics', 'Payout proof required', 'The full entry needs actual payout economics before EV can be claimed.'],
            ['Card discipline', 'No forced entries', 'If proof does not clear, the correct recommendation is to pass.'],
          ].map(([label, value, detail]) => (
            <div key={label} className="min-w-[240px] rounded-2xl border border-violet-100 bg-white p-4 shadow-soft md:min-w-0">
              <div className="text-[10px] font-black uppercase tracking-[0.12em] text-violet-700">{label}</div>
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
            className={`min-h-11 whitespace-nowrap rounded-full px-3 text-xs font-black ${sport === item ? 'bg-blue-700 text-white' : 'border border-slate-200 bg-white text-slate-500'}`}
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
                className={`min-h-11 whitespace-nowrap rounded-full px-3 text-xs font-black ${nbaPhase === value ? 'bg-blue-700 text-white' : 'border border-slate-200 bg-white text-slate-500'}`}>
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-3">
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
      <div className="flex gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-600">
        <ShieldCheck size={18} className="mt-0.5 shrink-0 text-blue-700" />
        <div>
          <b>Interpretation first:</b> player requirements stay visible. Probability, quality and edge metrics remain available under View evidence for users who want the deeper research.
        </div>
      </div>
    </section>
  )
}
