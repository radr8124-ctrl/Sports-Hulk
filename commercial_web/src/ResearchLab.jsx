import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity, ArrowRight, BarChart3, Brain, CheckCircle2, Clock3,
  FlaskConical, RefreshCw, ShieldCheck, Target, TrendingUp,
} from 'lucide-react'
import { researchSummary } from './researchSummary'

const ENDPOINTS = {
  performance: '/performance_snapshot.json',
  selectivity: '/selectivity_analysis.json',
  forward: '/forward_results_accountability.json',
  fantasy: '/fantasy_v2_forward.json',
  ask: '/api/ask/evaluation-summary',
  health: '/api/health',
}

function fmt(value) {
  return value === null || value === undefined ? '—' : Number(value).toLocaleString()
}

function timeLabel(value) {
  if (!value) return 'Timestamp unavailable'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Timestamp unavailable' : date.toLocaleString()
}

function Stamp({ value }) {
  return <div className="mt-2 inline-flex items-center gap-1.5 text-[11px] font-semibold text-slate-500"><Clock3 size={12} /> Updated {timeLabel(value)}</div>
}

function Metric({ label, value, note }) {
  return (
    <div className="min-w-0 rounded-2xl border border-slate-200 bg-slate-50 p-3 sm:p-4">
      <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-black tabular-nums tracking-tight text-slate-950 sm:text-3xl">{value}</div>
      {note && <div className="mt-1 text-[11px] font-semibold leading-4 text-slate-500">{note}</div>}
    </div>
  )
}

function Section({ eyebrow, title, icon: Icon, children }) {
  return (
    <section className="min-w-0 rounded-[26px] border border-slate-200 bg-white p-4 shadow-soft sm:p-6">
      <div className="mb-4 flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700"><Icon size={19} /></div>
        <div className="min-w-0">
          <div className="text-[10px] font-black uppercase tracking-[0.12em] text-blue-700">{eyebrow}</div>
          <h2 className="mt-1 text-lg font-black tracking-tight text-slate-950 sm:text-xl">{title}</h2>
        </div>
      </div>
      {children}
    </section>
  )
}

export default function ResearchLab() {
  const [state, setState] = useState({ data: {}, errors: [], loading: true })
  const [refresh, setRefresh] = useState(0)

  const load = useCallback(() => setRefresh(value => value + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    let active = true
    const read = async () => {
      setState(old => ({...old, loading:true}))
      const results = await Promise.all(Object.entries(ENDPOINTS).map(async ([key,endpoint]) => {
        try {
          const response = await fetch(endpoint, {cache:'no-store',signal:controller.signal})
          if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
            throw new Error('Data unavailable')
          }
          const value = await response.json()
          if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid research snapshot')
          return {key,value}
        } catch (error) {
          if (controller.signal.aborted) return null
          return {key,error:error instanceof Error ? error.message : 'Data unavailable'}
        }
      }))
      if (!active) return
      const data = {}
      const errors = []
      for(const row of results){
        if (!row) continue
        if (row.error) errors.push(row.key)
        else data[row.key] = row.value
      }
      setState({data,errors,loading:false})
    }
    read()
    return () => {active=false;controller.abort()}
  }, [refresh])

  const summary = useMemo(() => researchSummary(state.data), [state.data])
  const official = summary.official
  const forward = summary.forward
  const calibration = summary.calibration
  const ask = summary.ask
  const loadingEmpty = state.loading && !Object.keys(state.data).length

  return (
    <div className="min-w-0 space-y-5">
      <section className="rounded-[30px] border border-slate-800 bg-slate-950 px-5 py-6 text-white shadow-soft sm:p-8">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
          <div className="max-w-3xl">
            <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.16em] text-sky-300"><FlaskConical size={16} /> Sports Zenith Research Lab</div>
            <h1 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">See the evidence behind the brain.</h1>
            <p className="mt-3 text-sm leading-6 text-slate-300">Inspect published results, forward evaluation, calibration experiments and data-source checks. Research findings do not automatically become betting recommendations.</p>
          </div>
          <button type="button" onClick={load} disabled={state.loading}
            className="inline-flex min-h-11 items-center justify-center gap-2 self-start rounded-xl border border-white/20 bg-white/10 px-4 py-2 text-xs font-black text-white hover:bg-white/20 disabled:opacity-50">
            <RefreshCw size={15} className={state.loading ? 'animate-spin' : ''} />
            {state.loading ? 'Checking…' : 'Refresh evidence'}
          </button>
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          <a href="#brain-record" className="inline-flex min-h-11 items-center gap-1.5 rounded-xl bg-white px-4 py-2 text-xs font-black text-slate-950">Full Brain Record <ArrowRight size={14} /></a>
          <a href="#best-bets" className="inline-flex min-h-11 items-center gap-1.5 rounded-xl border border-white/20 px-4 py-2 text-xs font-black text-white">Best Bets <ArrowRight size={14} /></a>
          <a href="#ask" className="inline-flex min-h-11 items-center gap-1.5 rounded-xl border border-white/20 px-4 py-2 text-xs font-black text-white">Ask the Brain <ArrowRight size={14} /></a>
        </div>
      </section>

      {loadingEmpty ? (
        <div role="status" className="rounded-2xl border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600"><RefreshCw size={17} className="mr-2 inline animate-spin" /> Loading verified research snapshots…</div>
      ) : (
        <>
          {state.errors.length > 0 && (
            <div role="status" className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900">
              Some research data is unavailable ({state.errors.join(', ')}). Missing values are shown as —, never as zero.
            </div>
          )}

          <div className="grid min-w-0 gap-4 lg:grid-cols-2">
            <Section eyebrow="Verified published decisions" title="Official picks · separate permanent record" icon={ShieldCheck}>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <Metric label="Published" value={fmt(official.published)} />
                <Metric label="Settled" value={fmt(official.settled)} />
                <Metric label="Wins" value={fmt(official.wins)} />
                <Metric label="Losses" value={fmt(official.losses)} />
              </div>
              <p className="mt-3 text-xs leading-5 text-slate-600">Official results count only picks actually published to the permanent record. They do not include historical research or shadow picks. Units: {official.units == null ? '—' : `${official.units > 0 ? '+' : ''}${official.units.toFixed(2)}u`}. Status: {official.status.replaceAll('_',' ')}.</p>
              <Stamp value={official.generatedAt} />
            </Section>

            <Section eyebrow="Frozen forward evaluation" title="Results settling across research lanes" icon={TrendingUp}>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                <Metric label="Tracked" value={fmt(forward.tracked)} />
                <Metric label="Settled" value={fmt(forward.settled)} />
                <Metric label="Overdue 48h" value={fmt(forward.overdue48h)} />
              </div>
              <p className="mt-3 text-xs leading-5 text-slate-600">This is a sum across multiple forward research families, not unique wagers or the official record. Pending results stay pending until source-verified; status: {forward.status.replaceAll('_',' ')}.</p>
              <Stamp value={forward.generatedAt} />
            </Section>

            <Section eyebrow="Research-only model evaluation" title="Calibration and threshold experiments" icon={BarChart3}>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                <Metric label="Threshold tests" value={fmt(calibration.thresholdTests)} />
                <Metric label="Research candidates" value={fmt(calibration.researchCandidates)} />
                <Metric label="Auto-promoted" value={calibration.automaticallyChanged ? 'YES' : 'NO'} />
              </div>
              <p className="mt-3 text-xs leading-5 text-slate-600">Method: {calibration.method?.replaceAll('_',' ') || 'Unavailable'}. Candidate thresholds are retrospective diagnostics, not automatically approved picks or proven future win rates.</p>
              <details className="mt-3 rounded-xl bg-slate-50 p-3">
                <summary className="cursor-pointer text-xs font-black text-slate-900">View researched threshold cohorts ({calibration.candidates.length})</summary>
                {calibration.candidates.length ? (
                  <div className="mt-3 divide-y divide-slate-200">
                    {calibration.candidates.map((row, i) => (
                      <div key={`${row.sport}-${row.lane}-${row.market}-${i}`} className="flex flex-wrap items-center justify-between gap-2 py-2 text-xs">
                        <span className="font-semibold text-slate-700">{row.sport} · {row.lane} {row.market || ''}</span>
                        <span className="font-black text-slate-900">{fmt(row.sample)} historical examples</span>
                      </div>
                    ))}
                  </div>
                ) : <p className="mt-2 text-xs text-slate-500">No cohort summaries available.</p>}
              </details>
              <Stamp value={calibration.generatedAt} />
            </Section>

            <Section eyebrow="Analyst answer quality" title="Grounded responses are measured" icon={Brain}>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                <Metric label="Answers reviewed" value={fmt(ask.evaluated)} />
                <Metric label="Grounded now" value={fmt(ask.grounded)} />
                <Metric label="Withheld" value={fmt(ask.withheld)} />
              </div>
              <p className="mt-3 text-xs leading-5 text-slate-600">Measured reporting claims: {fmt(ask.claimSamples)}; backed by cited evidence: {fmt(ask.supportedClaims)}. Retrieval fixtures: {fmt(ask.retrievalPasses)}/{fmt(ask.retrievalCases)}. These tests measure groundedness on a limited sample—not betting accuracy.</p>
            </Section>
          </div>

          <Section eyebrow="Personalized decision research" title="Fantasy lanes are earning their proof" icon={Target}>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
              {summary.fantasy.lanes.map(row => (
                <div key={row.key} className="min-w-0 rounded-2xl bg-slate-50 p-3">
                  <div className="text-xs font-black text-slate-950">{row.label}</div>
                  <div className="mt-2 text-xl font-black tabular-nums text-slate-900">{fmt(row.settled)} / {fmt(row.tracked)}</div>
                  <div className="mt-1 text-[11px] text-slate-600">Settled / tracked</div>
                  <div className="mt-2 text-[10px] font-bold uppercase tracking-wide text-blue-700">{row.proofStatus.replaceAll('_',' ')}</div>
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs leading-5 text-slate-500">Forward results are judged against appropriate baselines as enough independent weeks settle. Draft rankings are not official fantasy point projections.</p>
            <Stamp value={summary.fantasy.generatedAt} />
          </Section>

          <Section eyebrow="Data availability, not freshness" title="Which source files exist?" icon={Activity}>
            {summary.sources.length ? (
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                {summary.sources.map(source => (
                  <div key={source.key} className="flex min-w-0 items-center justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <span className="min-w-0 break-words text-[11px] font-bold text-slate-700">{source.key.replaceAll('_',' ')}</span>
                    <span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-black ${source.present ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-100 text-amber-900'}`}>
                      {source.present ? 'Present' : 'Missing'}
                    </span>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-slate-500">Source availability is not available right now.</p>}
            <p className="mt-3 text-xs leading-5 text-slate-500">“Present” means a data source was loaded; it does not guarantee that scores, markets or lineup statuses are current. Individual pages enforce their own freshness and eligibility checks.</p>
            <Stamp value={summary.sourceCheckedAt} />
          </Section>

          <section className="rounded-2xl border border-blue-100 bg-blue-50 p-5">
            <div className="flex items-start gap-3">
              <CheckCircle2 size={20} className="mt-0.5 shrink-0 text-blue-700" />
              <div>
                <h2 className="text-base font-black text-slate-950">How Sports Zenith earns trust</h2>
                <p className="mt-2 text-xs leading-6 text-slate-700">Research is not an official bet. Replay is not forward proof. Missing results are not losses. A candidate model is not promoted just because a small historical sample looks promising. You can always inspect the full public Brain Record or ask for the reasons behind a decision.</p>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
