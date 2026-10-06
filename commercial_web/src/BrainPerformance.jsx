import React, { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle, BarChart3, Brain, CheckCircle2, Gauge, ShieldCheck,
  Target, Trophy, XCircle, Zap,
} from 'lucide-react'

const pretty = value => String(value || '').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase())

const pct = value => value == null ? '—' : Number(value).toFixed(1) + '%'

const record = item => {
  if (!item) return '—'
  return `${item.wins || 0}-${item.losses || 0}${item.pushes ? `-${item.pushes}` : ''}`
}

function StatusPill({ value }) {
  const text = String(value || 'WAITING')
  const upper = text.toUpperCase()
  const tone =
    upper.includes('MATUR') || upper.includes('READY')
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : upper.includes('WAIT') || upper.includes('TINY')
        ? 'border-amber-200 bg-amber-50 text-amber-700'
        : 'border-blue-200 bg-blue-50 text-blue-700'
  return <span className={`rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-wide ${tone}`}>{text}</span>
}

function RecordCard({ item, icon: Icon }) {
  const rate = item?.hit_rate_pct
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
          <Icon size={21} />
        </div>
        <StatusPill value={item?.maturity} />
      </div>
      <div className="mt-5 text-xs font-black uppercase tracking-[0.14em] text-slate-400">{item?.label || 'Record'}</div>
      <div className="mt-2 flex flex-wrap items-end gap-x-3 gap-y-1">
        <div className="text-3xl font-black tracking-tight text-slate-950">{rate == null ? 'WAITING' : pct(rate)}</div>
        <div className="pb-1 text-sm font-extrabold text-slate-500">{record(item)}</div>
      </div>
      <div className="mt-3 text-xs leading-5 text-slate-500">
        {item?.decisions ? `${item.decisions} settled decisions` : 'No settled sample yet'}
        {item?.wilson_low_pct != null && item?.wilson_high_pct != null
          ? ` · 95% range ${pct(item.wilson_low_pct)}–${pct(item.wilson_high_pct)}`
          : ''}
      </div>
      <div className="mt-4 border-t border-slate-100 pt-3 text-[11px] font-semibold text-slate-400">
        Units / ROI: {item?.units_status || 'WAITING'}
      </div>
    </div>
  )
}

function DfsRow({ row }) {
  return (
    <tr className="border-b border-slate-100 align-top">
      <td className="px-4 py-3 font-black text-slate-900">{row.platform === 'DRAFTKINGS' ? 'DraftKings' : 'FanDuel'}</td>
      <td className="px-4 py-3 font-extrabold text-slate-700">{pretty(row.mode)}</td>
      <td className="px-4 py-3 text-slate-600">{row.replay_slates}</td>
      <td className="px-4 py-3 font-black text-slate-900">{row.avg_actual_points ?? '—'}</td>
      <td className="px-4 py-3 font-black text-blue-700">{pct(row.avg_random_baseline_percentile)}</td>
      <td className="px-4 py-3 text-slate-600">{pct(row.beat_random_median_rate_pct)}</td>
      <td className="px-4 py-3">
        <StatusPill value={row.maturity} />
      </td>
    </tr>
  )
}

export default function BrainPerformance() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const response = await fetch(`/brain_performance.json?ts=${Date.now()}`, { cache: 'no-store' })
        if (!response.ok) throw new Error('Brain Record is unavailable')
        const payload = await response.json()
        if (!cancelled) setData(payload)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Brain Record is unavailable')
      }
    }
    load()
    const timer = window.setInterval(load, 60000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  const categories = data?.categories || []
  const categoryMap = useMemo(() => Object.fromEntries(categories.map(x => [x.label, x])), [categories])
  const sports = data?.sports || []
  const dfsRows = data?.dfs?.replay_modes || []
  const watch = data?.selectivity_watch || []

  if (error) {
    return (
      <div className="rounded-3xl border border-rose-200 bg-rose-50 p-5 text-sm font-semibold text-rose-800">
        {error}
      </div>
    )
  }

  if (!data) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-500 shadow-soft">
        Loading the permanent performance record…
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-[30px] border border-slate-800 bg-slate-950 p-6 text-white shadow-soft md:p-8">
        <div className="grid gap-6 lg:grid-cols-[1fr_360px] lg:items-end">
          <div>
            <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.18em] text-emerald-300">
              <Brain size={16} /> Permanent Accountability Record
            </div>
            <h2 className="mt-3 text-4xl font-black tracking-tight md:text-5xl">How good is the brain?</h2>
            <p className="mt-3 max-w-3xl text-lg font-bold text-emerald-300">Fewer bets. Better bets. Proven results.</p>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-300">
              Every settled qualified pick stays in the record. Losing picks do not disappear.
              Pending results stay pending, and DFS replay tests are kept separate from live-forward results.
            </p>
          </div>
          <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
            <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">Verified settled decisions</div>
            <div className="mt-2 text-4xl font-black text-white">{data.transparency?.verified_settled_decisions ?? 0}</div>
            <div className="mt-2 text-xs leading-5 text-slate-400">
              No automatic model changes are being applied from this page.
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-emerald-200 bg-emerald-50 p-5">
        <div className="flex items-start gap-3">
          <ShieldCheck size={22} className="mt-0.5 shrink-0 text-emerald-700" />
          <div>
            <div className="font-black text-emerald-950">The record cannot be cleaned up after the fact.</div>
            <div className="mt-2 grid gap-2 text-sm font-semibold text-emerald-900 md:grid-cols-2">
              {(data.transparency?.rules || []).map(rule => (
                <div key={rule} className="flex gap-2">
                  <CheckCircle2 size={15} className="mt-0.5 shrink-0" />
                  <span>{rule}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Betting performance</p>
            <h2>What is actually winning?</h2>
          </div>
          <span className="health-pill emerald">SETTLED ONLY</span>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <RecordCard item={categoryMap['Best Bets']} icon={Target} />
          <RecordCard item={categoryMap['Props']} icon={Gauge} />
          <RecordCard item={categoryMap['PrizePicks']} icon={Trophy} />
          <RecordCard item={categoryMap['Parlays']} icon={Zap} />
        </div>
        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
          <b>Important:</b> parlay hit rate is not directly comparable to straight-bet hit rate because payouts differ.
          Units and ROI stay hidden until consistent wager-price capture is verified.
        </div>
      </section>

      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">By sport</p>
            <h2>Where the brain is strongest</h2>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {sports.map(item => (
            <div key={item.label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-black text-slate-950">{item.label}</div>
                <StatusPill value={item.maturity} />
              </div>
              <div className="mt-3 text-2xl font-black text-slate-950">{pct(item.hit_rate_pct)}</div>
              <div className="mt-1 text-xs font-semibold text-slate-500">{record(item)} · {item.decisions || 0} decisions</div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">DFS accountability</p>
            <h2>Optimizer replay vs. legal random baseline</h2>
          </div>
          <span className="health-pill">PRE-LOCK REPLAY</span>
        </div>
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-start gap-3 rounded-2xl border border-blue-100 bg-blue-50 p-4">
            <BarChart3 size={20} className="mt-0.5 shrink-0 text-blue-700" />
            <div className="text-sm leading-6 text-blue-950">
              These tests reconstruct the last available player pool <b>before slate lock</b>, build the lineup without seeing results,
              and then grade it. The percentile below is only against deterministic random legal lineups from that same pool.
              <b> It is not a DraftKings/FanDuel contest percentile.</b>
            </div>
          </div>

          {dfsRows.length ? (
            <div className="mt-5 overflow-x-auto">
              <table className="min-w-[900px] w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
                    <th className="px-4 py-3">Site</th>
                    <th className="px-4 py-3">Mode</th>
                    <th className="px-4 py-3">Replay slates</th>
                    <th className="px-4 py-3">Avg actual pts</th>
                    <th className="px-4 py-3">Random baseline percentile</th>
                    <th className="px-4 py-3">Beat random median</th>
                    <th className="px-4 py-3">Sample</th>
                  </tr>
                </thead>
                <tbody>{dfsRows.map(row => <DfsRow key={`${row.platform}-${row.mode}`} row={row} />)}</tbody>
              </table>
            </div>
          ) : (
            <div className="mt-5 text-sm font-semibold text-slate-500">No verified pre-lock replay sample yet.</div>
          )}

          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs font-black uppercase tracking-wide text-slate-400">Real DFS cash rate</div>
              <div className="mt-2 text-xl font-black text-slate-950">WAITING</div>
              <div className="mt-2 text-xs leading-5 text-slate-500">{data.dfs?.contest_metrics_status}</div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs font-black uppercase tracking-wide text-slate-400">Live-forward benchmark</div>
              <div className="mt-2 text-xl font-black text-slate-950">{data.dfs?.forward_official_snapshots || 0} frozen lineups</div>
              <div className="mt-2 text-xs leading-5 text-slate-500">Only snapshots captured before slate lock can enter this record.</div>
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Selectivity watch</p>
            <h2>What should earn more or fewer picks?</h2>
          </div>
          <span className="health-pill">NO AUTO CHANGES</span>
        </div>
        <div className="grid gap-3 lg:grid-cols-2">
          {watch.slice(0, 10).map((item, index) => (
            <div key={`${item.label}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="font-black text-slate-950">{item.label}</div>
                <StatusPill value={item.status} />
              </div>
              <div className="mt-2 text-xs font-semibold text-slate-500">
                {item.decisions || 0} decisions · {pct(item.hit_rate_pct)}
              </div>
              <div className="mt-3 text-sm leading-6 text-slate-600">{item.reason}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wide text-slate-400">
            <Trophy size={16} /> Survivor brain record
          </div>
          <div className="mt-3 text-xl font-black text-slate-950">{data.survivor?.status || 'WAITING'}</div>
          <div className="mt-2 text-sm leading-6 text-slate-500">{data.survivor?.reason}</div>
        </div>
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wide text-slate-400">
            <BarChart3 size={16} /> Practice bankroll
          </div>
          <div className="mt-3 text-xl font-black text-slate-950">{data.practice_bankroll?.status || 'NOT STARTED'}</div>
          <div className="mt-2 text-sm leading-6 text-slate-500">{data.practice_bankroll?.reason}</div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
        <div className="flex gap-3">
          <AlertTriangle size={20} className="mt-0.5 shrink-0 text-amber-600" />
          <div>
            <div className="font-black text-slate-950">What this page will never claim</div>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              A hit rate is not a guarantee of future wins. Tiny samples are labeled tiny. DFS random-baseline results are not real contest finishes.
              And ROI stays unavailable until the underlying prices are complete enough to calculate it honestly.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
