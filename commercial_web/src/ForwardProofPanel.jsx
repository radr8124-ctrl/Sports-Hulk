import React, { useEffect, useState } from 'react'
import { Activity, AlertTriangle, Clock3, ShieldCheck } from 'lucide-react'
import { brierDescription, forwardProofView, researchRoi } from './forwardProofPresentation.js'

const count = n => Number(n || 0).toLocaleString('en-US')
const percent = n => typeof n === 'number' ? `${n.toFixed(1)}%` : 'Waiting'
const score = n => typeof n === 'number' ? n.toFixed(5) : '—'

function ResearchLane({ title, stats }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-black uppercase tracking-wide text-slate-600">{title}</span>
        <span className="text-[10px] font-bold text-slate-500">{count(stats.settled)} settled</span>
      </div>
      <div className="mt-3 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-2xl font-black tabular-nums text-slate-950">{percent(stats.hit_rate_pct)}</span>
        <span className="text-xs font-semibold text-slate-600">
          {count(stats.wins)}W–{count(stats.losses)}L
        </span>
      </div>
      <div className="mt-2 text-sm font-bold text-slate-900">
        {researchRoi(stats.source_book_quoted_paper_roi_pct)} <span className="font-medium text-slate-500">source-price paper ROI</span>
      </div>
      <div className="mt-2 text-xs text-slate-600">
        Brier: model {score(stats.model_brier)} · market {score(stats.source_market_brier)}
      </div>
      <div className="mt-1 text-[11px] leading-5 text-slate-500">{brierDescription(stats)}</div>
    </div>
  )
}

function ProofDetail({ label, value, secondary }) {
  return (
    <div className="rounded-xl border border-slate-200 px-3 py-3">
      <div className="text-[10px] font-black uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-lg font-black tabular-nums text-slate-900">{value}</div>
      <div className="mt-1 text-[11px] leading-4 text-slate-500">{secondary}</div>
    </div>
  )
}

export default function ForwardProofPanel() {
  const [evidence, setEvidence] = useState(null)
  const [status, setStatus] = useState('LOADING')

  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        const response = await fetch(`/forward_proof_current.json?ts=${Date.now()}`, { cache: 'no-store' })
        if (!response.ok) throw new Error('No verified forward scorecard')
        const raw = await response.json()
        const validated = forwardProofView(raw)
        if (!validated) throw new Error('Forward source proof failed validation')
        if (active) {
          setEvidence(validated)
          setStatus('READY')
        }
      } catch {
        if (active) setStatus('UNAVAILABLE')
      }
    }
    load()
    const timer = window.setInterval(load, 60000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  if (!evidence) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs font-semibold text-slate-500">
        {status === 'LOADING' ? 'Loading source-verified forward research…' : 'Forward research record is temporarily unavailable; official settled records remain below.'}
      </div>
    )
  }

  const asOf = new Date(evidence.updated_at_utc).toLocaleString('en-US', {
    timeZone: 'America/New_York', month: 'short', day: 'numeric', hour: 'numeric',
    minute: '2-digit', timeZoneName: 'short',
  })

  return (
    <section aria-label="Hourly verified forward betting research, not real winnings" className="rounded-3xl border border-slate-200 bg-white p-4 shadow-soft md:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-[11px] font-black uppercase tracking-[0.12em] text-slate-600">
            <Activity size={15} /> Forward research · model vs sportsbook
          </div>
          <h2 className="mt-1 text-xl font-black tracking-tight text-slate-950">How is the brain performing now?</h2>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-600">
            Frozen forward tests only. Prices and returns are simulated research, not placed bets or guaranteed profit.
          </p>
        </div>
        <div className="flex flex-col items-start gap-1 text-[11px] font-semibold text-slate-500">
          <span className="inline-flex items-center gap-1"><Clock3 size={12} /> Source checkpoint {asOf}</span>
          <span>{count(evidence.verified_append_only_history_checkpoints)} verified history checkpoints</span>
          {evidence.isStale && <span className="font-black text-amber-700">Source report is older than 95 minutes</span>}
          {status === 'UNAVAILABLE' && <span className="font-black text-amber-700">Feed unavailable; showing last validated snapshot</span>}
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <ResearchLane title="Game lines" stats={evidence.game_lines} />
        <ResearchLane title="Props / Pick'em" stats={evidence.props_and_pickem} />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
        <ProofDetail label="MLB Full16"
          value={`${count(evidence.mlb_full16.completed_independent_game_blocks)} game`}
          secondary="First completed forward test only" />
        <ProofDetail label="MLB price movement"
          value={count(evidence.mlb_price_movement.frozen_source_observations)}
          secondary={`${count(evidence.mlb_price_movement.independent_upcoming_games)} games · ${count(evidence.mlb_price_movement.graded_official_player_results)} graded`} />
        <ProofDetail label="NFL forward"
          value={`${count(evidence.nfl_forward.pregame_frozen_games)} frozen`}
          secondary={`${count(evidence.nfl_forward.source_grade_pending)} pending · ${count(evidence.nfl_forward.fixed_seventy_pct_plus_value_qualifiers)} pass value filter`} />
        <ProofDetail label="CFB research"
          value={count(evidence.cfb_research.historically_settled_research_grades)}
          secondary={`Historical grades of ${count(evidence.cfb_research.latest_distinct_recommendations)} recommendations`} />
      </div>

      <div className="mt-3 flex items-start gap-2 border-t border-slate-100 pt-3 text-[11px] leading-5 text-slate-600">
        <ShieldCheck size={16} className="mt-0.5 shrink-0" />
        <span>
          <b>Not proven profitable.</b> Sportsbook Brier is the benchmark; a higher win rate or positive paper ROI alone does not establish a betting advantage. MLB movement observations within the same game are correlated, not independent games.
          <span className="ml-1 whitespace-nowrap text-slate-400">Source receipt {evidence.source_receipt_hash_prefix}</span>
        </span>
      </div>
    </section>
  )
}
