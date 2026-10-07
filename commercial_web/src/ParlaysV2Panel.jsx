import React, { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, ChevronRight, Link2, ShieldCheck } from 'lucide-react'
import { explainBet, formatAmericanOdds } from './BetMeaning'

const humanize = value => String(value || '')
  .replaceAll('_', ' ')
  .toLowerCase()
  .replace(/\b\w/g, letter => letter.toUpperCase())

const numberOrNull = value => {
  if (value === null || value === undefined || String(value).trim() === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

const pct = value => {
  const number = numberOrNull(value)
  return number == null ? '—' : `${number.toFixed(1)}%`
}

function parlayStatus(row) {
  const decision = String(row?.shadow_decision || '').toUpperCase()
  if (decision === 'SHADOW_PLAY') return { label: 'PLAY', tone: 'bg-emerald-50 text-emerald-700 border-emerald-100' }
  if (decision === 'SHADOW_MONITOR') return { label: 'MONITOR', tone: 'bg-amber-50 text-amber-700 border-amber-100' }
  return { label: 'PASS', tone: 'bg-slate-100 text-slate-700 border-slate-200' }
}

function legStatus(leg) {
  if (leg?.source_proof_ready) return { label: 'SOURCE PROVEN', tone: 'bg-emerald-50 text-emerald-700' }
  const decision = String(leg?.source_shadow_decision || '').toUpperCase()
  if (decision === 'SHADOW_MONITOR') return { label: 'MONITOR', tone: 'bg-amber-50 text-amber-700' }
  if (decision === 'SHADOW_PLAY') return { label: 'PLAY', tone: 'bg-emerald-50 text-emerald-700' }
  if (decision.startsWith('PASS')) return { label: 'PASS', tone: 'bg-slate-100 text-slate-600' }
  return { label: 'RESEARCH', tone: 'bg-blue-50 text-blue-700' }
}

function legRow(leg) {
  const market = String(leg?.market || '').toUpperCase()
  const line = leg?.source_exact_line ?? leg?.line ?? null
  const exactSelection = String(leg?.source_exact_selection || leg?.selection || '').toUpperCase()

  if (String(leg?.kind || '').toUpperCase() === 'PROP') {
    return {
      market: leg.market,
      player: leg.player,
      selection: exactSelection,
      side: exactSelection,
      line,
    }
  }

  if (market === 'TOTAL') {
    return { market, selection: exactSelection, side: exactSelection, line }
  }

  return {
    market,
    selection: leg.selection,
    line: market === 'MONEYLINE' ? null : line,
  }
}

function legLabel(leg) {
  const market = String(leg?.market || '').toUpperCase()
  const line = leg?.source_exact_line ?? leg?.line ?? null
  const selection = String(leg?.source_exact_selection || leg?.selection || '').toUpperCase()

  if (String(leg?.kind || '').toUpperCase() === 'PROP') {
    return `${leg.player || 'Player'} · ${humanize(selection)} ${line ?? ''} ${humanize(leg.market)}`.trim()
  }

  if (market === 'MONEYLINE') return `${leg.selection} moneyline`
  if (market === 'SPREAD') return `${leg.selection} ${Number(line) > 0 ? '+' : ''}${line}`
  if (market === 'TOTAL') return `${humanize(selection)} ${line}`
  return [leg.selection, line, humanize(market)].filter(value => value !== null && value !== '').join(' ')
}

function correlationCopy(status) {
  const value = String(status || '').toUpperCase()
  if (value === 'CROSS_GAME_RESEARCH_INDEPENDENCE') {
    return {
      title: 'Cross-game research',
      detail: 'Joint research uses an independence assumption here. That is not the same as measured correlation.',
    }
  }
  if (value.includes('SHARED') || value.includes('SAME_GAME')) {
    return {
      title: 'Shared-event exposure',
      detail: 'These legs interact inside the same event, so simple independence should not be assumed.',
    }
  }
  if (value.includes('MEASURED')) {
    return {
      title: humanize(status),
      detail: 'Correlation is backed by the connected research field for this combination.',
    }
  }
  return {
    title: humanize(status || 'Correlation research only'),
    detail: 'Correlation is research context unless the underlying combination has direct measured evidence.',
  }
}

function weakestLeg(legs) {
  const comparable = (legs || []).map((leg, index) => ({
    index,
    value: numberOrNull(leg.source_conservative_probability_pct),
    leg,
  }))
  if (!comparable.length || comparable.some(item => item.value == null)) return null
  return [...comparable].sort((a, b) => a.value - b.value)[0]
}

function riskItems(row) {
  const items = ['Any one losing leg loses the entire parlay.']
  const unproven = (row.legs || []).filter(leg => !leg.source_proof_ready).length
  if (unproven) items.push(`${unproven} of ${row.leg_count || row.legs?.length || 0} legs still lack forward source proof.`)
  if (!row.captured_parlay_american_odds) items.push('The combined payout has not been captured, so Sports Zenith will not claim parlay EV or payout value.')
  if (row.shared_event_exposure_block) items.push('Shared-event exposure is blocking promotion.')
  if (row.shared_leg_exposure_block) items.push('A repeated/shared-leg exposure is blocking promotion.')
  if (String(row.correlation_status || '').toUpperCase() === 'CROSS_GAME_RESEARCH_INDEPENDENCE') {
    items.push('The joint research probability assumes independence; it is not measured correlation.')
  }
  return items
}

function LegCard({ leg, index, weakest }) {
  const status = legStatus(leg)
  const meaning = explainBet(legRow(leg))

  return (
    <div className={`rounded-2xl border p-4 ${weakest ? 'border-amber-200 bg-amber-50/70' : 'border-slate-200 bg-slate-50'}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Leg {index + 1}</div>
          <div className="mt-1 text-sm font-black text-slate-950">{legLabel(leg)}</div>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {weakest && <span className="rounded-full bg-amber-100 px-2.5 py-1 text-[10px] font-black text-amber-800">WEAKEST LEG</span>}
          <span className={`rounded-full px-2.5 py-1 text-[10px] font-black ${status.tone}`}>{status.label}</span>
        </div>
      </div>
      <div className="mt-3 text-sm font-black leading-6 text-slate-800">{meaning.primary}</div>
      {meaning.secondary && <div className="mt-1 text-xs font-semibold leading-5 text-slate-500">{meaning.secondary}</div>}
      {numberOrNull(leg.source_conservative_probability_pct) != null && (
        <div className="mt-3 text-[11px] font-semibold text-slate-400">
          Conservative source probability {pct(leg.source_conservative_probability_pct)} · research context only
        </div>
      )}
    </div>
  )
}

function ParlayCard({ row }) {
  const status = parlayStatus(row)
  const correlation = correlationCopy(row.correlation_status)
  const weakest = weakestLeg(row.legs || [])
  const risks = riskItems(row)
  const captured = numberOrNull(row.captured_parlay_american_odds)

  return (
    <article className="rounded-[30px] border border-slate-200 bg-white p-5 shadow-soft md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-black uppercase tracking-[0.14em] text-violet-700">{row.sport} · {row.leg_count || row.legs?.length || 0}-LEG PARLAY</div>
          <div className="mt-2 flex flex-wrap items-baseline gap-3">
            <h3 className="text-2xl font-black tracking-tight text-slate-950">
              {captured == null ? 'Price not captured' : formatAmericanOdds(captured)}
            </h3>
            <span className={`rounded-full border px-3 py-1 text-[10px] font-black ${status.tone}`}>{status.label}</span>
          </div>
        </div>
        <div className="rounded-2xl border border-violet-200 bg-violet-50 px-4 py-3 text-center">
          <div className="text-[10px] font-black uppercase tracking-[0.12em] text-violet-700">Rule</div>
          <div className="mt-1 text-sm font-black text-violet-950">ALL LEGS MUST WIN</div>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {(row.legs || []).map((leg, index) => (
          <LegCard
            key={`${leg.kind}-${leg.event}-${leg.player_key || leg.selection}-${index}`}
            leg={leg}
            index={index}
            weakest={weakest?.index === index}
          />
        ))}
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-blue-100 bg-blue-50/70 p-4">
          <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.12em] text-blue-700"><Link2 size={14} /> Correlation</div>
          <div className="mt-2 text-sm font-black text-slate-950">{correlation.title}</div>
          <div className="mt-1 text-xs font-semibold leading-5 text-slate-600">{correlation.detail}</div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Weakest leg</div>
          {weakest ? (
            <>
              <div className="mt-2 text-sm font-black text-slate-950">Leg {weakest.index + 1} · {legLabel(weakest.leg)}</div>
              <div className="mt-1 text-xs font-semibold text-slate-500">Lowest comparable conservative source probability: {pct(weakest.value)}</div>
            </>
          ) : (
            <div className="mt-2 text-xs font-semibold leading-5 text-slate-500">Not ranked because every leg does not have a comparable conservative source probability.</div>
          )}
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4">
        <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.12em] text-amber-800"><AlertTriangle size={14} /> What can break this parlay</div>
        <ul className="mt-2 space-y-1.5 text-xs font-semibold leading-5 text-amber-950">
          {risks.map((risk, index) => <li key={index}>• {risk}</li>)}
        </ul>
      </div>

      <details className="group mt-5 rounded-2xl border border-slate-200 bg-white">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-xs font-black text-slate-700">
          <span>View parlay evidence</span>
          <ChevronRight size={16} className="shrink-0 text-slate-400 transition-transform group-open:rotate-90" />
        </summary>
        <div className="border-t border-slate-100 px-4 pb-4 pt-4">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl bg-slate-50 p-3 text-center">
              <div className="text-lg font-black text-slate-950">{row.joint_v2_probability_pct == null ? '—' : `${row.joint_v2_probability_pct}%`}</div>
              <div className="mt-1 text-[10px] font-black uppercase tracking-wide text-slate-400">Research joint</div>
            </div>
            <div className="rounded-xl bg-slate-50 p-3 text-center">
              <div className="text-lg font-black text-slate-950">{row.joint_conservative_probability_pct == null ? '—' : `${row.joint_conservative_probability_pct}%`}</div>
              <div className="mt-1 text-[10px] font-black uppercase tracking-wide text-slate-400">Conservative joint</div>
            </div>
            <div className="rounded-xl bg-slate-50 p-3 text-center">
              <div className="text-lg font-black text-slate-950">{captured == null ? '—' : formatAmericanOdds(captured)}</div>
              <div className="mt-1 text-[10px] font-black uppercase tracking-wide text-slate-400">Captured payout</div>
            </div>
            <div className="rounded-xl bg-slate-50 p-3 text-center">
              <div className="text-lg font-black text-slate-950">{row.resolved_legs ?? 0}/{row.leg_count ?? row.legs?.length ?? 0}</div>
              <div className="mt-1 text-[10px] font-black uppercase tracking-wide text-slate-400">Exact legs resolved</div>
            </div>
          </div>
          <div className="mt-3 text-[11px] font-semibold leading-5 text-slate-500">
            Research joint probability is not promoted to a payout or EV claim unless source-leg proof and the actual combined price both clear their gates.
          </div>
        </div>
      </details>
    </article>
  )
}

export default function ParlaysV2Panel() {
  const [data, setData] = useState({ summary: {}, picks: [] })

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const response = await fetch(`/parlay_v2_current.json?ts=${Date.now()}`, { cache: 'no-store' })
        const payload = response.ok ? await response.json() : { summary: {}, picks: [] }
        if (!cancelled) setData(payload)
      } catch {
        if (!cancelled) setData({ summary: {}, picks: [] })
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const summary = data.summary || {}
  const rows = useMemo(() => (data.picks || [])
    .filter(row => row.resolved_legs === row.leg_count)
    .sort((a, b) => {
      const rank = row => String(row.shadow_decision) === 'SHADOW_PLAY' ? 3 : String(row.shadow_decision) === 'SHADOW_MONITOR' ? 2 : 1
      return rank(b) - rank(a)
        || (numberOrNull(b.joint_v2_probability_pct) || -1) - (numberOrNull(a.joint_v2_probability_pct) || -1)
    })
    .slice(0, 10), [data.picks])

  return (
    <section className="space-y-5">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Betting</p>
          <h2>Parlays</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            Every leg must win. Sports Zenith keeps leg proof, correlation research and the actual combined payout separate so an interesting combination never becomes a fake value claim.
          </p>
        </div>
        <span className="health-pill">{summary.candidates ?? 0} CURRENT</span>
      </div>

      <div className="flex gap-3 overflow-x-auto pb-1 lg:grid lg:grid-cols-5 lg:overflow-visible">
        {[
          ['Candidates', summary.candidates ?? 0],
          ['Exact V2 legs', summary.resolved_all_legs ?? 0],
          ['Source proven', summary.all_source_legs_forward_proven ?? 0],
          ['Captured payout', summary.captured_parlay_price ?? 0],
          ['Monitors', summary.shadow_monitors ?? 0],
        ].map(([label, value]) => (
          <div key={label} className="min-w-[150px] flex-1 rounded-2xl border border-slate-200 bg-white p-4 shadow-soft lg:min-w-0">
            <div className="text-2xl font-black text-slate-950">{value}</div>
            <div className="mt-1 text-xs font-black uppercase tracking-[0.12em] text-slate-400">{label}</div>
          </div>
        ))}
      </div>

      <div className="flex gap-3 rounded-2xl border border-violet-200 bg-violet-50 p-4 text-sm leading-6 text-violet-950">
        <ShieldCheck size={18} className="mt-0.5 shrink-0" />
        <div><b>Parlay discipline:</b> if source legs are unproven or the combined price is missing, PASS is the correct result. Sports Zenith will not turn research probability into a payout claim.</div>
      </div>

      {rows.length ? (
        <div className="grid gap-5 xl:grid-cols-2">
          {rows.map((row, index) => <ParlayCard key={`${row.combo_signature}-${index}`} row={row} />)}
        </div>
      ) : (
        <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-500 shadow-soft">
          No fully resolved V2 parlay combinations are available right now.
        </div>
      )}
    </section>
  )
}
