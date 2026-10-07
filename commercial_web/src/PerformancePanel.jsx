import React, { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle, BarChart3, Brain, CheckCircle2, Clock3, Gauge,
  ShieldCheck, Target, TrendingUp, Trophy, Zap,
} from 'lucide-react'
import { allMarketsProofRows } from './allMarketsProofRows.js'

const SPORTS = ['ALL', 'NFL', 'CFB', 'MLB', 'NBA', 'NHL']

const pct = value => value == null ? '—' : Number(value).toFixed(1) + '%'
const integer = value => Number(value || 0).toLocaleString()
const pretty = value => String(value || '').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase())

function StatusPill({ value }) {
  const text = String(value || 'WAITING')
  const upper = text.toUpperCase()
  const tone =
    upper.includes('MATUR') || upper.includes('READY') || upper.includes('HOLD')
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : upper.includes('WAIT') || upper.includes('TINY')
        ? 'border-amber-200 bg-amber-50 text-amber-700'
        : upper.includes('SELECT') || upper.includes('CANDIDATE')
          ? 'border-rose-200 bg-rose-50 text-rose-700'
          : 'border-blue-200 bg-blue-50 text-blue-700'
  return (
    <span className={`rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-wide ${tone}`}>
      {pretty(text)}
    </span>
  )
}

function OfficialRecord({ data }) {
  const official = data.official || {}
  const policy = data.policy || {}
  const recent = data.official_recent || []
  const pendingPicks = recent.filter(row => String(row.grade || 'PENDING').toUpperCase() === 'PENDING')
  const hasSettled = Number(official.settled || 0) > 0
  const unitLabel = official.units == null
    ? 'WAITING'
    : `${Number(official.units) >= 0 ? '+' : ''}${Number(official.units).toFixed(2)}u${official.roi_pct == null ? '' : ` · ${pct(official.roi_pct)} ROI`}`

  return (
    <section className="rounded-[30px] border border-slate-800 bg-slate-950 p-6 text-white shadow-soft md:p-8">
      <div className="grid gap-6 lg:grid-cols-[1fr_360px] lg:items-end">
        <div className="max-w-3xl">
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.18em] text-emerald-300">
            <Brain size={16} /> Permanent Accountability Record
          </div>
          <h2 className="mt-3 text-4xl font-black tracking-tight md:text-5xl">How good is the brain?</h2>
          <p className="mt-3 text-lg font-black text-emerald-300">Fewer bets. Better bets. Proven results.</p>
          <p className="mt-4 text-sm leading-6 text-slate-300">
            The public record begins with picks explicitly published as OFFICIAL. Historical research is shown below,
            but it is never backfilled into this headline record.
          </p>
        </div>
        <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">Official published record</div>
            <span className={`rounded-full border px-3 py-1 text-[10px] font-black ${hasSettled ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300' : 'border-amber-300/30 bg-amber-300/10 text-amber-200'}`}>
              {pretty(official.status || 'BUILDING SAMPLE')}
            </span>
          </div>
          <div className="mt-3 text-4xl font-black">{official.hit_rate_pct == null ? 'WAITING' : pct(official.hit_rate_pct)}</div>
          <div className="mt-2 text-sm font-bold text-slate-300">
            {integer(official.wins)}-{integer(official.losses)}-{integer(official.pushes)} · {integer(official.settled)} settled
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
        {[
          ['Published', integer(official.published)],
          ['Pending', integer(official.pending)],
          ['Settled', integer(official.settled)],
          ['Record', `${integer(official.wins)}-${integer(official.losses)}-${integer(official.pushes)}`],
          ['Hit Rate', pct(official.hit_rate_pct)],
          ['Units / ROI', unitLabel],
        ].map(([label, value]) => (
          <div key={label} className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-[11px] font-black uppercase tracking-[0.13em] text-slate-500">{label}</div>
            <div className="mt-2 text-2xl font-black text-white">{value}</div>
          </div>
        ))}
      </div>

      {!!pendingPicks.length && (
        <div className="mt-5">
          <div className="text-[11px] font-black uppercase tracking-[0.14em] text-emerald-300">Current official pick{pendingPicks.length === 1 ? '' : 's'}</div>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {pendingPicks.slice(0, 4).map(pick => (
              <div key={pick.pick_id} className="rounded-2xl border border-emerald-300/20 bg-emerald-300/5 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-xs font-black uppercase tracking-wide text-slate-500">{pick.game_key}</div>
                  <span className="rounded-full border border-emerald-300/25 bg-emerald-300/10 px-2.5 py-1 text-[10px] font-black text-emerald-200">FROZEN PRE-GAME</span>
                </div>
                <div className="mt-2 text-xl font-black text-white">{pick.selection} ML {Number(pick.american_odds) > 0 ? '+' : ''}{pick.american_odds}</div>
                <div className="mt-2 text-xs leading-5 text-slate-400">
                  Evidence {pick.hulk_score ?? '—'} · {pick.book_count ?? '—'} books · published {pick.published_at ? new Date(pick.published_at).toLocaleString() : '—'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!hasSettled && (
        <div className="mt-5 flex gap-3 rounded-2xl border border-amber-300/15 bg-amber-300/5 p-4 text-sm leading-6 text-slate-300">
          <Clock3 size={18} className="mt-0.5 shrink-0 text-amber-300" />
          <div>
            <b className="text-white">The official sample starts now.</b> No old winners are being pulled forward to make the launch record look better.
          </div>
        </div>
      )}

      <div className="mt-5 grid gap-2 text-xs font-semibold text-slate-400 md:grid-cols-2">
        {(policy.rules || []).map(rule => (
          <div key={rule} className="flex gap-2">
            <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-emerald-300" />
            <span>{rule}</span>
          </div>
        ))}
      </div>

      <div className="mt-4 text-[11px] font-semibold text-slate-500">
        Official record policy started {policy.record_started_at ? new Date(policy.record_started_at).toLocaleString() : '—'}
      </div>
    </section>
  )
}

function AskQualityPanel({ data, trace }) {
  const ready = String(data?.status || '').toUpperCase() === 'READY'
  const tracked = Number(data?.tracked || 0)
  const citation = data?.citation_coverage_pct
  const claimEvidence = data?.claim_evidence_coverage_pct
  const retrievalRecall = data?.retrieval_recall_pct
  const retrievalPrecision = data?.retrieval_precision_pct
  const answerRelevance = data?.answer_relevance_pct
  const semanticAnswers = data?.semantic_answer_pass_pct
  const latency = data?.avg_latency_ms
  const traceReady = String(trace?.status || '').toUpperCase() === 'READY'

  return (
    <section className="rounded-[30px] border border-slate-200 bg-white p-6 shadow-soft md:p-8">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.16em] text-blue-700">
            <ShieldCheck size={16} /> Ask Quality
          </div>
          <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-950">Is the sports analyst staying grounded?</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            This is chatbot answer quality, not betting performance. Unsupported, stale and conflicting answers are counted as flagged rather than hidden.
          </p>
        </div>
        <StatusPill value={ready ? 'TRACKING' : 'WAITING'} />
      </div>

      {ready ? (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
            {[
              ['Questions tracked', integer(tracked)],
              ['Grounded / current', pct(data.grounded_current_pct)],
              ['Flagged / withheld', pct(data.withheld_or_flagged_pct)],
              ['Clickable citations', citation == null ? '—' : pct(citation)],
              ['Claim evidence', claimEvidence == null ? '—' : pct(claimEvidence)],
              ['Source click rate', data.source_click_rate_pct == null ? '—' : pct(data.source_click_rate_pct)],
              ['Avg response time', latency == null ? '—' : `${integer(latency)} ms`],
            ].map(([label, value]) => (
              <div key={label} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">{label}</div>
                <div className="mt-2 text-2xl font-black text-slate-950">{value}</div>
              </div>
            ))}
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-5">
            {[
              ['Insufficient evidence', data.insufficient_evidence],
              ['Stale source', data.stale_source],
              ['Source conflict', data.source_conflict],
              ['Unsupported claims', data.unsupported_reporting_claim_count],
              ['Unknown / errors', Number(data.unknown || 0) + Number(data.errors || 0)],
            ].map(([label, value]) => (
              <div key={label} className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="text-xs font-black text-slate-500">{label}</div>
                <div className="mt-1 text-xl font-black text-slate-950">{integer(value)}</div>
              </div>
            ))}
          </div>

          {(retrievalRecall != null || retrievalPrecision != null || answerRelevance != null || semanticAnswers != null) && (
            <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-xs font-black uppercase tracking-[0.12em] text-blue-700">Deterministic Ask benchmark</div>
                <div className="text-[10px] font-black uppercase tracking-[0.12em] text-blue-600">
                  Retrieval {data.retrieval_golden_passed || 0}/{data.retrieval_golden_cases || 0} · Semantic {data.semantic_golden_passed || 0}/{data.semantic_golden_cases || 0}
                </div>
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  ['Retrieval recall', retrievalRecall == null ? '—' : pct(retrievalRecall)],
                  ['Retrieval precision', retrievalPrecision == null ? '—' : pct(retrievalPrecision)],
                  ['Answer relevance', answerRelevance == null ? '—' : pct(answerRelevance)],
                  ['Semantic answers', semanticAnswers == null ? '—' : pct(semanticAnswers)],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-xl border border-blue-100 bg-white p-3">
                    <div className="text-[10px] font-black uppercase tracking-[0.1em] text-slate-400">{label}</div>
                    <div className="mt-1 text-xl font-black text-slate-950">{value}</div>
                  </div>
                ))}
              </div>
              <div className="mt-2 text-[10px] font-semibold leading-4 text-blue-700">
                Synthetic known-answer cases verify that expected evidence is recovered, unrelated evidence stays out, and the final answer uses the correct current / stale / conflict / insufficient-evidence behavior. This is a code-quality benchmark, not live sports performance.
              </div>
            </div>
          )}

          {traceReady && (
            <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-xs font-black uppercase tracking-[0.12em] text-slate-600">Trace health</div>
                <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Privacy-safe · hashed questions only</div>
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-3 lg:grid-cols-6">
                {[
                  ['Requests traced', integer(trace.tracked)],
                  ['Validation failures', integer(trace.validation_failures)],
                  ['Errors', integer(trace.error_count)],
                  ['Session resolves', integer(trace.session_reference_resolved_count)],
                  ['Avg latency', trace.avg_latency_ms == null ? '—' : `${integer(trace.avg_latency_ms)} ms`],
                  ['P95 latency', trace.p95_latency_ms == null ? '—' : `${integer(trace.p95_latency_ms)} ms`],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-xl border border-slate-200 bg-white p-3">
                    <div className="text-[10px] font-black uppercase tracking-[0.1em] text-slate-400">{label}</div>
                    <div className="mt-1 text-lg font-black text-slate-950">{value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mt-4 text-[11px] font-semibold leading-5 text-slate-400">
            Recent append-only evaluation window · clickable citations measure source-link presence, while claim evidence measures exact take/why claims mapped to a specific reporting evidence record · these metrics measure restraint and traceability, not whether every sports opinion is correct.
          </div>
        </>
      ) : (
        <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900">
          Ask quality tracking is connected, but there are not enough recorded questions yet to calculate a useful snapshot.
        </div>
      )}
    </section>
  )
}

function BrainMetricCard({ item, icon: Icon }) {
  const decisions = Number(item?.decisions || 0)
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
          <Icon size={19} />
        </div>
        <StatusPill value={item?.maturity} />
      </div>
      <div className="mt-4 text-xs font-black uppercase tracking-[0.14em] text-slate-400">{item?.label || 'Research'}</div>
      <div className="mt-2 flex items-end gap-3">
        <div className="text-3xl font-black tracking-tight text-slate-950">{pct(item?.hit_rate_pct)}</div>
        <div className="pb-1 text-sm font-extrabold text-slate-500">
          {item?.wins || 0}-{item?.losses || 0}{item?.pushes ? `-${item.pushes}` : ''}
        </div>
      </div>
      <div className="mt-2 text-xs leading-5 text-slate-500">
        {integer(decisions)} qualified settled decisions
        {item?.wilson_low_pct != null && item?.wilson_high_pct != null
          ? ` · 95% range ${pct(item.wilson_low_pct)}–${pct(item.wilson_high_pct)}`
          : ''}
      </div>
      <div className="mt-4 border-t border-slate-100 pt-3 text-[11px] font-semibold text-slate-400">
        Historical validation · not the official public record
      </div>
    </div>
  )
}

function ResearchTable({ rows }) {
  return (
    <div className="overflow-x-auto rounded-3xl border border-slate-200 bg-white shadow-soft">
      <table className="min-w-[860px] w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
            <th className="px-4 py-3">Sport</th>
            <th className="px-4 py-3">Lane</th>
            <th className="px-4 py-3">Distinct settled</th>
            <th className="px-4 py-3">W-L-P</th>
            <th className="px-4 py-3">Hit rate</th>
            <th className="px-4 py-3">85+ sample</th>
            <th className="px-4 py-3">85+ hit rate</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(row => (
            <tr key={`${row.sport}-${row.lane}`} className="border-b border-slate-100">
              <td className="px-4 py-3 font-black text-slate-950">{row.sport}</td>
              <td className="px-4 py-3 font-extrabold text-slate-700">{pretty(row.lane)}</td>
              <td className="px-4 py-3 font-semibold text-slate-600">{integer(row.settled_distinct)}</td>
              <td className="px-4 py-3 font-semibold text-slate-700">{row.wins}-{row.losses}-{row.pushes}</td>
              <td className="px-4 py-3 font-black text-slate-950">{pct(row.hit_rate_pct)}</td>
              <td className="px-4 py-3 font-semibold text-slate-600">{integer(row.score85_settled)}</td>
              <td className="px-4 py-3 font-black text-slate-950">{pct(row.score85_hit_rate_pct)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function BettingV2Panel({ brain }) {
  const v2 = brain?.betting_v2 || {}
  const current = v2.current || {}
  const clv = v2.clv || {}
  const forward = v2.forward || {}
  const validation = v2.validation?.validation || {}
  const sportValidation = v2.validation?.by_sport || {}
  const metrics = validation.metrics || {}
  const summary = current.summary || {}
  const sportSummary = summary.by_sport || {}
  const clvSummary = clv.summary || {}
  const forwardAll = forward.all_predictions || {}
  const forwardMonitor = forward.monitor_selection || {}
  const forwardPromotion = forward.promotion || {}
  const picks = (current.picks || []).slice(0, 10)
  const source = current.probability_source || 'WAITING'
  const hulkAddsValue = current.hulk_score_adds_out_of_sample_value === true

  const metricCell = (label, key) => {
    const row = metrics[key] || {}
    return (
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">{label}</div>
        <div className="mt-2 text-lg font-black text-slate-950">
          Brier {row.brier == null ? '—' : Number(row.brier).toFixed(3)}
        </div>
        <div className="mt-1 text-xs font-semibold text-slate-500">
          Log loss {row.log_loss == null ? '—' : Number(row.log_loss).toFixed(3)}
        </div>
      </div>
    )
  }

  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Betting Score V2</p>
          <h2>Probability + price + EV before PLAY</h2>
        </div>
        <span className="health-pill">SHADOW ONLY · LIVE PICKS UNCHANGED</span>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
        <div className={`flex gap-3 rounded-2xl border p-4 text-sm leading-6 ${hulkAddsValue ? 'border-emerald-200 bg-emerald-50 text-emerald-950' : 'border-amber-200 bg-amber-50 text-amber-950'}`}>
          <ShieldCheck size={20} className="mt-0.5 shrink-0" />
          <div>
            {source === 'SPORT_SPECIFIC' ? (
              <>
                <b>Every sport must now prove its own betting edge.</b>
                {' '}NFL, CFB, CBB, MLB, NBA and NHL are validated independently; one league can no longer lend confidence to another.
              </>
            ) : (
              <>
                <b>{hulkAddsValue ? 'The evidence score added out-of-sample value.' : 'The legacy evidence score has not beaten the market baseline out of sample yet.'}</b>
                {' '}V2 therefore uses <b>{pretty(source)}</b> for probability and refuses to manufacture betting edge from the evidence score alone.
              </>
            )}
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Qualified moneylines</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(summary.qualified_moneylines)}</div>
          </div>
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-emerald-700">Shadow plays</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(summary.shadow_plays)}</div>
          </div>
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-rose-700">Passes</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(summary.passes)}</div>
          </div>
          <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-blue-700">No-vig fair market</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(summary.fair_probability_available)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">games/sides with two-sided price coverage</div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Forward frozen</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{integer(forwardAll.tracked)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">{integer(forwardAll.pending)} pending · {integer(forwardAll.settled)} settled</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Forward V2 Brier</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{forwardAll.v2_brier == null ? 'WAITING' : Number(forwardAll.v2_brier).toFixed(3)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">Fair market {forwardAll.market_brier == null ? '—' : Number(forwardAll.market_brier).toFixed(3)}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Forward selection rule</div>
            <div className="mt-2 text-xl font-black text-slate-950">{pretty(forwardMonitor.proof_status || 'BUILDING FORWARD SAMPLE')}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">{integer(forwardMonitor.tracked)} frozen shadow selections</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Promotion gate</div>
            <div className="mt-2 text-xl font-black text-slate-950">{pretty(forwardPromotion.recommendation || 'HOLD')}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">No automatic promotion</div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">CLV tracked</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{integer(clvSummary.tracked)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">{integer(clvSummary.open)} open · {integer(clvSummary.closed)} closed</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Beat closing line</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{pct(clvSummary.positive_clv_rate_pct)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">{integer(clvSummary.beat_close)} beat · {integer(clvSummary.lost_to_close)} lost</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Avg fair CLV</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{clvSummary.avg_fair_clv_probability_pp == null ? 'WAITING' : `${Number(clvSummary.avg_fair_clv_probability_pp) >= 0 ? '+' : ''}${Number(clvSummary.avg_fair_clv_probability_pp).toFixed(2)} pts`}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">Closing no-vig probability minus entry</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Entry-price CLV EV</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{pct(clvSummary.avg_entry_price_clv_ev_pct)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">Uses closing fair probability at entry price</div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          {['NFL', 'CFB', 'CBB', 'MLB', 'NBA', 'NHL'].map(sport => {
            const sv = sportValidation[sport] || {}
            const ss = sportSummary[sport] || {}
            return (
              <div key={sport} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-black uppercase tracking-wide text-slate-400">{sport} Best Bets</div>
                <div className="mt-2 text-xl font-black text-slate-950">{integer(ss.history_n ?? sv.history_n ?? sv.n)}</div>
                <div className="mt-1 text-xs font-semibold text-slate-500">settled training rows</div>
                <div className="mt-2 text-[10px] font-black uppercase tracking-wide text-slate-600">
                  {pretty(ss.probability_source || sv.deployment_probability_source || sv.status || 'WAITING')}
                </div>
                <div className="mt-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">
                  {pretty(ss.historical_edge_confidence || sv.historical_edge_confidence || 'INSUFFICIENT HISTORY')}
                </div>
              </div>
            )
          })}
        </div>

        <div className="mt-5">
          <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">Pooled diagnostic only · not used for deployment · lower is better</div>
          <div className="mt-3 grid gap-3 md:grid-cols-4">
            {metricCell('Raw market baseline', 'market_raw')}
            {metricCell('Fair/reference market', 'market_reference')}
            {metricCell('Market + legacy evidence', 'market_plus_hulk')}
            {metricCell('Legacy evidence only', 'score_only')}
          </div>
        </div>

        <div className="mt-5 overflow-x-auto rounded-2xl border border-slate-200">
          <table className="min-w-[1080px] w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="px-4 py-3">Sport</th>
                <th className="px-4 py-3">Pick</th>
                <th className="px-4 py-3">Price</th>
                <th className="px-4 py-3">Evidence score</th>
                <th className="px-4 py-3">Fair market</th>
                <th className="px-4 py-3">Probability baseline</th>
                <th className="px-4 py-3">EV</th>
                <th className="px-4 py-3">Data</th>
                <th className="px-4 py-3">V2 decision</th>
              </tr>
            </thead>
            <tbody>
              {picks.map((row, index) => (
                <tr key={`${row.sport}-${row.game_key}-${row.side || row.selection}-${index}`} className="border-b border-slate-100 align-top">
                  <td className="px-4 py-3 font-black text-slate-950">{row.sport}</td>
                  <td className="px-4 py-3">
                    <div className="font-black text-slate-950">{row.selection}</div>
                    <div className="mt-1 text-[11px] text-slate-400">{row.game_key}</div>
                  </td>
                  <td className="px-4 py-3 font-bold text-slate-700">
                    {Number(row.american_odds) > 0 ? '+' : ''}{row.american_odds}
                  </td>
                  <td className="px-4 py-3 font-black text-slate-950">{row.hulk_evidence_score ?? '—'}</td>
                  <td className="px-4 py-3">
                    <div className="font-semibold text-slate-700">{pct(row.market_reference_probability_pct ?? row.market_fair_probability_pct)}</div>
                    <div className="mt-1 text-[10px] font-bold uppercase tracking-wide text-slate-400">{pretty(row.market_reference_type || 'RAW FALLBACK')}</div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-black text-blue-700">{pct(row.calibrated_win_probability_pct)}</div>
                    <div className="mt-1 text-[10px] font-bold uppercase tracking-wide text-slate-400">{pretty(row.probability_source || 'WAITING')}</div>
                  </td>
                  <td className="px-4 py-3 font-black text-slate-950">{pct(row.expected_value_pct)}</td>
                  <td className="px-4 py-3"><StatusPill value={`GRADE ${row.data_quality_grade || '—'}`} /></td>
                  <td className="px-4 py-3"><StatusPill value={row.shadow_decision} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-5 border-t border-slate-100 pt-4 text-xs leading-5 text-slate-500">
          Evidence Score remains a research-quality score. It is <b>not</b> a win probability. V2 will only move from PASS to PLAY after an independently validated model creates positive conservative EV at the available price.
        </div>
      </div>
    </section>
  )
}

function AllMarketsV2Panel({ brain }) {
  const bundle = brain?.betting_v2_all_markets || {}
  const current = bundle.current || {}
  const forward = bundle.forward || {}
  const summary = current.summary || {}
  const forwardAll = forward.all_predictions || {}
  const gameChallengers = bundle.challengers?.lanes || {}
  const cfbTotalChallenger = gameChallengers.CFB_TOTAL || {}
  const challengerForward = bundle.challenger_forward?.forward || {}

  const lanes = allMarketsProofRows(bundle)
    .filter(row => {
      const v = row.validation || {}
      const live = row.live || {}
      return Number(v.history_n ?? live.history_n ?? 0) > 0 || Number(live.candidates || 0) > 0
    })

  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Best Bets V2 · All Markets</p>
          <h2>Moneyline, spread and total must earn edge separately</h2>
        </div>
        <span className="health-pill">SPORT + MARKET SPECIFIC · SHADOW ONLY</span>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
        <div className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
          <ShieldCheck size={20} className="mt-0.5 shrink-0" />
          <div>
            Alternate lines cannot multiply historical evidence. Opposite sides of the same exact market are blocked,
            and at most one shadow bet per game can survive the exposure gate. Spread/total numbers are never treated as odds.
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Current candidates</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(summary.candidates)}</div>
          </div>
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-emerald-700">Shadow plays</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(summary.shadow_plays)}</div>
          </div>
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-rose-700">Passes</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(summary.passes)}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Forward frozen</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(forwardAll.tracked)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">{integer(forwardAll.settled)} settled</div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Opposite-side blocks</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{integer(summary.opposite_side_conflicts)}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Alternate-line variants</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{integer(summary.duplicate_line_variants)}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Same-game exposure blocks</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{integer(summary.same_game_exposure_blocks)}</div>
          </div>
        </div>

        <div className="mt-5 rounded-2xl border border-sky-200 bg-sky-50 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-xs font-black uppercase tracking-wide text-sky-700">CFB Total challenger lab</div>
              <div className="mt-1 text-lg font-black text-slate-950">{pretty(cfbTotalChallenger.status || 'WAITING')}</div>
              <div className="mt-1 text-sm leading-6 text-slate-600">
                Rich context beats current V2 and both market baselines on average, but remains forward-only until whole-game confidence proves the edge.
              </div>
            </div>
            <div className="text-right text-xs font-semibold text-slate-600">
              <div>{integer(cfbTotalChallenger.independent_blocks)} historical games</div>
              <div>{integer(challengerForward.tracked)} forward frozen · {integer(challengerForward.settled)} settled</div>
              <div>{pretty(challengerForward.proof_status || 'BUILDING FORWARD SAMPLE')}</div>
            </div>
          </div>
        </div>

        <div className="mt-5 overflow-x-auto rounded-2xl border border-slate-200">
          <table className="min-w-[1100px] w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="px-4 py-3">Lane</th>
                <th className="px-4 py-3">History</th>
                <th className="px-4 py-3">Games</th>
                <th className="px-4 py-3">Probability source</th>
                <th className="px-4 py-3">Confidence</th>
                <th className="px-4 py-3">Current</th>
                <th className="px-4 py-3">Forward</th>
                <th className="px-4 py-3">Promotion</th>
              </tr>
            </thead>
            <tbody>
              {lanes.map(row => {
                const key = row.key
                const v = row.validation || {}
                const live = row.live || {}
                const fw = row.forward || {}
                const all = fw.all_predictions || {}
                const promo = fw.promotion || {}
                return (
                  <tr key={key} className="border-b border-slate-100 align-top">
                    <td className="px-4 py-3">
                      <div className="font-black text-slate-950">{pretty(row.laneKey || key)}</div>
                      {row.competitionRegime ? (
                        <div className="mt-1 text-[10px] font-black uppercase tracking-wide text-blue-600">
                          {pretty(row.competitionRegime)}
                        </div>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-700">{integer(v.history_n ?? live.history_n)}</td>
                    <td className="px-4 py-3 font-semibold text-slate-700">{integer(v.independent_blocks ?? live.independent_blocks)}</td>
                    <td className="px-4 py-3 text-xs font-black uppercase tracking-wide text-slate-600">{pretty(v.deployment_probability_source || live.probability_source || 'WAITING')}</td>
                    <td className="px-4 py-3 text-xs font-black uppercase tracking-wide text-slate-600">{pretty(v.historical_edge_confidence || live.historical_edge_confidence || 'INSUFFICIENT HISTORY')}</td>
                    <td className="px-4 py-3 font-semibold text-slate-700">{integer(live.candidates)} · {integer(live.shadow_plays)} shadow</td>
                    <td className="px-4 py-3 font-semibold text-slate-700">{integer(all.tracked)} frozen · {integer(all.settled)} settled</td>
                    <td className="px-4 py-3 text-xs font-black uppercase tracking-wide text-slate-600">{pretty(promo.recommendation || 'BUILDING FORWARD PROOF')}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}


function ParlayV2Panel({ brain }) {
  const bundle = brain?.parlay_v2 || {}
  const current = bundle.current || {}
  const validation = bundle.validation?.by_sport || {}
  const forward = bundle.forward || {}
  const bySport = current.by_sport || {}
  const forwardBySport = forward.by_sport || {}
  const summary = current.summary || {}
  const forwardAll = forward.all_predictions || {}
  const sports = ['NFL', 'CFB', 'CBB', 'MLB', 'NBA', 'NHL']
    .filter(sport => {
      const live = bySport[sport] || {}
      const hist = validation[sport] || {}
      return Number(live.candidates || 0) > 0 || Number(hist.settled_unique_combos || 0) > 0
    })

  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Parlays V2</p>
          <h2>Every leg must earn its way into the combination</h2>
        </div>
        <span className="health-pill">SOURCE-PROOFED · FORWARD ONLY</span>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
        <div className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
          <ShieldCheck size={20} className="mt-0.5 shrink-0" />
          <div>
            Old parlay scores are <b>not probabilities</b>. Same-game legs are never multiplied as independent,
            cross-game products are research-only until forward calibration proves them, and no EV is claimed
            without a captured combined parlay price or platform payout.
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Current combos</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(summary.candidates)}</div>
          </div>
          <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-sky-700">Exact V2 leg resolution</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(summary.resolved_all_legs)}</div>
          </div>
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-emerald-700">Source legs forward-proven</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(summary.all_source_legs_forward_proven)}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Captured parlay prices</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(summary.captured_parlay_price)}</div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Research joint probability</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{integer(summary.research_joint_probability_available)}</div>
          </div>
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-emerald-700">Shadow monitors</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{integer(summary.shadow_monitors)}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Forward frozen</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{integer(forwardAll.tracked)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">{integer(forwardAll.settled)} settled</div>
          </div>
        </div>

        <div className="mt-5 overflow-x-auto rounded-2xl border border-slate-200">
          <table className="min-w-[1050px] w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="px-4 py-3">Sport</th>
                <th className="px-4 py-3">Legacy settled</th>
                <th className="px-4 py-3">Legacy hit rate</th>
                <th className="px-4 py-3">Old score vs base</th>
                <th className="px-4 py-3">Current</th>
                <th className="px-4 py-3">Resolved</th>
                <th className="px-4 py-3">Forward</th>
                <th className="px-4 py-3">Promotion</th>
              </tr>
            </thead>
            <tbody>
              {sports.map(sport => {
                const live = bySport[sport] || {}
                const hist = validation[sport] || {}
                const diag = hist.legacy_score_diagnostic || {}
                const fw = forwardBySport[sport] || {}
                const all = fw.all_predictions || {}
                const promo = fw.promotion || {}
                return (
                  <tr key={sport} className="border-b border-slate-100 align-top">
                    <td className="px-4 py-3 font-black text-slate-950">{sport}</td>
                    <td className="px-4 py-3 font-semibold text-slate-700">{integer(hist.settled_unique_combos)}</td>
                    <td className="px-4 py-3 font-semibold text-slate-700">{pct(hist.hit_rate_pct)}</td>
                    <td className="px-4 py-3 text-xs font-black uppercase tracking-wide text-slate-600">
                      {diag.old_score_beats_base_rate === true ? 'MEAN IMPROVEMENT ONLY' : diag.status === 'READY' ? 'NO' : pretty(diag.status || 'WAITING')}
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-700">{integer(live.candidates)} combos</td>
                    <td className="px-4 py-3 font-semibold text-slate-700">{integer(live.resolved_all_legs)} / {integer(live.candidates)}</td>
                    <td className="px-4 py-3 font-semibold text-slate-700">{integer(all.tracked)} frozen · {integer(all.settled)} settled</td>
                    <td className="px-4 py-3 text-xs font-black uppercase tracking-wide text-slate-600">{pretty(promo.recommendation || 'BUILDING FORWARD PROOF')}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-4 text-xs font-semibold leading-5 text-slate-500">
          Forward proof uses non-overlapping combinations for confidence testing so repeated use of the same game cannot inflate the sample.
          Profitability stays locked until real combined parlay prices or platform payouts are captured.
        </div>
      </div>
    </section>
  )
}

function PropV2Panel({ brain }) {
  const prop = brain?.prop_v2 || {}
  const current = prop.current || {}
  const validation = prop.validation?.lanes || {}
  const byLane = current.by_lane || {}
  const forward = prop.forward || {}
  const forwardAll = forward.all_predictions || {}
  const forwardMonitor = forward.monitor_selection || {}
  const devig = prop.devig || {}
  const challengers = prop.challengers?.lanes || {}
  const marketSegments = prop.market_segments?.lanes || {}

  const lanes = [
    ['NFL_PROP', 'NFL Props'],
    ['NFL_PRIZEPICKS', 'NFL PrizePicks'],
    ['NBA_PROP', 'NBA Props'],
    ['NBA_PRIZEPICKS', 'NBA PrizePicks'],
    ['NHL_PROP', 'NHL Props'],
    ['NHL_PRIZEPICKS', 'NHL PrizePicks'],
    ['MLB_PROP', 'MLB Props'],
    ['MLB_PRIZEPICKS', 'MLB PrizePicks'],
  ]

  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Props + PrizePicks V2</p>
          <h2>Lane-specific models must beat the market first</h2>
        </div>
        <span className="health-pill">SHADOW ONLY · NO AUTO PROMOTION</span>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
        <div className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
          <ShieldCheck size={20} className="mt-0.5 shrink-0 text-amber-700" />
          <div>
            A better probability model does <b>not</b> automatically become a betting rule.
            V2 keeps calibration, independent model edge, and PLAY/PASS validation separate.
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Current candidates</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(current.summary?.candidates)}</div>
          </div>
          <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-sky-700">Shadow monitors</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(current.summary?.shadow_monitors)}</div>
          </div>
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-rose-700">Passes</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(current.summary?.passes)}</div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Forward frozen</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{integer(forwardAll.tracked)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">{integer(forwardAll.pending)} pending · {integer(forwardAll.settled)} settled</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Forward V2 Brier</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{forwardAll.v2_brier == null ? 'WAITING' : Number(forwardAll.v2_brier).toFixed(3)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">Market {forwardAll.market_brier == null ? '—' : Number(forwardAll.market_brier).toFixed(3)}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Monitor rule</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{integer(forwardMonitor.tracked)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">{pretty(forwardMonitor.proof_status || 'BUILDING FORWARD SAMPLE')}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Forward rule ROI</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{pct(forwardMonitor.roi_pct)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">{integer(forwardMonitor.priced_settled)} priced settled</div>
          </div>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          {lanes.map(([key, label]) => {
            const lane = validation[key] || {}
            const live = byLane[key] || {}
            const raw = lane.metrics?.market_raw || {}
            const reference = lane.metrics?.market_reference || raw
            const chosenKey =
              lane.deployment_probability_source === 'LANE_CORE_MODEL' ? 'core_model'
                : lane.deployment_probability_source === 'LANE_CORE_PLUS_OLD_SCORE' ? 'core_plus_old_score'
                  : lane.deployment_probability_source === 'MARKET_CALIBRATED' ? 'market_calibrated'
                    : 'market_reference'
            const chosen = lane.metrics?.[chosenKey] || reference
            const independent = String(lane.deployment_probability_source || '').startsWith('LANE_CORE')
            const historicalConfidence = lane.historical_edge_confidence || 'WAITING'
            const historicallySupported = historicalConfidence === 'SUPPORTED'
            const laneForward = forward.by_lane?.[key] || {}
            const promotion = laneForward.promotion || {}
            const coreVsRaw = lane.paired_comparisons?.core_vs_reference || lane.paired_comparisons?.core_vs_raw || {}
            const coreVsCal = lane.paired_comparisons?.core_vs_calibrated || {}
            const challenger = challengers[key] || {}
            const segmentCount = marketSegments[key]?.eligible_segment_count || 0

            return (
              <div key={key} className={`rounded-3xl border p-5 ${historicallySupported ? 'border-emerald-200 bg-emerald-50' : independent ? 'border-amber-200 bg-amber-50' : 'border-slate-200 bg-slate-50'}`}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">{label}</div>
                    <div className="mt-2 text-xl font-black text-slate-950">{pretty(lane.deployment_probability_source || 'WAITING')}</div>
                  </div>
                  <StatusPill value={lane.selection_rule_status || 'WAITING'} />
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-2xl bg-white/80 p-3">
                    <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Market reference</div>
                    <div className="mt-1 text-base font-black text-slate-950">Brier {reference.brier == null ? '—' : Number(reference.brier).toFixed(3)}</div>
                    <div className="mt-1 text-xs text-slate-500">Log loss {reference.log_loss == null ? '—' : Number(reference.log_loss).toFixed(3)}</div>
                    <div className="mt-1 text-[10px] font-semibold text-slate-400">Raw Brier {raw.brier == null ? '—' : Number(raw.brier).toFixed(3)}</div>
                  </div>
                  <div className="rounded-2xl bg-white/80 p-3">
                    <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Chosen V2</div>
                    <div className="mt-1 text-base font-black text-slate-950">Brier {chosen.brier == null ? '—' : Number(chosen.brier).toFixed(3)}</div>
                    <div className="mt-1 text-xs text-slate-500">Log loss {chosen.log_loss == null ? '—' : Number(chosen.log_loss).toFixed(3)}</div>
                  </div>
                </div>

                <div className="mt-4 text-sm leading-6 text-slate-700">
                  <b>Old score:</b> {pretty(lane.old_score_status || 'WAITING')}.
                  {' '}History: {integer(lane.history_n)} · walk-forward: {integer(lane.walk_forward_n)}.
                </div>
                <div className="mt-3 text-xs font-semibold text-slate-500">
                  Current: {integer(live.candidates)} candidates · {integer(live.shadow_monitors)} monitors · {integer(live.passes)} passes
                </div>
                <div className="mt-2 text-xs font-semibold text-slate-600">
                  Historical confidence: <b>{pretty(historicalConfidence)}</b>
                  {independent ? ` · ${integer(coreVsRaw.independent_blocks)} game blocks` : ''}
                </div>
                <div className="mt-2 text-xs font-semibold text-slate-600">
                  Promotion: <b>{pretty(promotion.recommendation || 'BUILDING FORWARD PROOF')}</b>
                </div>
                <div className="mt-2 text-xs font-semibold text-slate-600">
                  Phase 2: de-vig {lane.devig_history_pct == null ? 'waiting' : Number(lane.devig_history_pct).toFixed(1) + '% history'}
                  {' '}· challenger <b>{pretty(challenger.status || 'WAITING')}</b>
                  {' '}· subtype tests {integer(segmentCount)}
                </div>
                {challenger.recency_decay_status ? (
                  <div className="mt-1 text-[10px] font-black uppercase tracking-wide text-slate-400">
                    Recency decay: {pretty(challenger.recency_decay_status)}
                  </div>
                ) : null}

                {historicallySupported ? (
                  <div className="mt-3 text-xs font-black uppercase tracking-wide text-emerald-800">
                    Historical edge survived paired game-block confidence checks · forward selection proof still required
                  </div>
                ) : independent ? (
                  <div className="mt-3 text-xs font-black uppercase tracking-wide text-amber-800">
                    Promising walk-forward signal, not proven · Brier LCB {coreVsRaw.brier_lcb90 == null ? '—' : Number(coreVsRaw.brier_lcb90).toFixed(3)} / calibrated {coreVsCal.brier_lcb90 == null ? '—' : Number(coreVsCal.brier_lcb90).toFixed(3)}
                  </div>
                ) : (
                  <div className="mt-3 text-xs font-black uppercase tracking-wide text-slate-500">
                    No independent betting edge proven yet
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}



function SurvivorV2Panel({ brain }) {
  const bundle = brain?.survivor || {}
  const current = bundle.current || {}
  const summary = bundle.forward || {}
  const forward = summary.forward || {}
  const saved = current.current_saved_picks || []
  const used = current.used_teams || []

  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Survivor V2</p>
          <h2>Saved picks and model proof stay separate</h2>
        </div>
        <span className="health-pill">FORWARD ONLY · NO RETROACTIVE PICKS</span>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
        <div className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
          <ShieldCheck size={20} className="mt-0.5 shrink-0" />
          <div>
            Historical pool choices are never relabeled as model picks. A model Survivor recommendation is only scored
            after the current-week rules are confirmed and the recommendation is frozen before kickoff. It is compared with the
            safest eligible market-favorite baseline from that same week.
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Pool week</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(current.pool_current_week)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">{current.active_entry || 'No active entry'}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Used teams</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(used.length)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">{saved.length ? `${saved.length} current saved pick(s)` : 'No current saved pick'}</div>
          </div>
          <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-sky-700">Recommendation gate</div>
            <div className="mt-2 text-sm font-black text-slate-950">{pretty(current.recommendation_status || 'WAITING')}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">{current.rule_confirmed ? 'Rules confirmed' : 'Official rule confirmation required'}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Forward proof</div>
            <div className="mt-2 text-sm font-black text-slate-950">{pretty(forward.proof_status || 'BUILDING FORWARD SAMPLE')}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">{integer(forward.independent_weeks)} independent weeks</div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Frozen model record</div>
            <div className="mt-2 text-2xl font-black text-slate-950">
              {integer(forward.hulk_survived)} survived · {integer(forward.hulk_lost)} lost
            </div>
            <div className="mt-1 text-xs font-semibold text-slate-500">Survival rate {pct(forward.hulk_survival_rate_pct)}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Safest-market baseline</div>
            <div className="mt-2 text-2xl font-black text-slate-950">
              {integer(forward.market_baseline_survived)} survived · {integer(forward.market_baseline_lost)} lost
            </div>
            <div className="mt-1 text-xs font-semibold text-slate-500">
              Survival rate {pct(forward.market_baseline_survival_rate_pct)} · {integer(forward.distinct_from_market_baseline_weeks)} distinct week(s)
            </div>
          </div>
        </div>

        <div className="mt-4 text-xs leading-5 text-slate-500">
          Current ownership sheet: {pretty(current.ownership?.status || 'WAITING')}. At least 10 independent weeks and 3 weeks
          where the model differs from the market baseline are required before Survivor can become a review candidate.
        </div>
      </div>
    </section>
  )
}

function FantasyV2Panel({ brain }) {
  const bundle = brain?.fantasy_v2 || {}
  const current = bundle.current?.lanes || {}
  const forward = bundle.forward || {}
  const weekly = forward.weekly || {}
  const faab = forward.faab || {}
  const stash = forward.ir_stash || {}
  const defense = forward.defense_streaming || {}
  const idp = forward.idp || {}
  const order = ['WEEKLY', 'FAAB', 'IR_STASH', 'DEFENSE_STREAMING', 'IDP', 'TRADE_RATE_TEAM']
  const proofRows = [
    ['Weekly', weekly, weekly.independent_weeks, 'Position-normalized PPR rank'],
    ['Waiver / FAAB quality', faab, faab.independent_weeks, 'Next-game PPR; bid % not graded'],
    ['IR stash utility', stash, stash.independent_capture_weeks, '4-NFL-week return + first-return PPR'],
    ['Defense streaming', defense, defense.independent_weeks, 'Generic D/ST benchmark'],
    ['IDP usage', idp, idp.independent_weeks, 'Generic IDP production index'],
  ]

  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Fantasy V3</p>
          <h2>Generic research and league-specific advice are not the same thing</h2>
        </div>
        <span className="health-pill">FORWARD PROOF · NO AUTO PROMOTION</span>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
        <div className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
          <ShieldCheck size={20} className="mt-0.5 shrink-0" />
          <div>
            Weekly, waiver-add quality, source-supported stash utility, defense streaming and IDP usage have separate
            forward proof ledgers. Private saved-team context now powers Rate My Team, Start/Sit, waiver need and FAAB-budget translation,
            IR capacity, Defense and IDP usage research. Live league free-agent availability, winning-bid prediction, full custom IDP
            point scoring, trades and automatic provider sync remain separate unresolved dependencies.
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Weekly frozen</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(weekly.tracked)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">{integer(weekly.settled)} settled</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Defense frozen</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(defense.tracked)}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">{integer(defense.settled)} settled</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Weekly proof</div>
            <div className="mt-2 text-sm font-black text-slate-950">{pretty(weekly.proof_status || 'BUILDING FORWARD SAMPLE')}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Defense proof</div>
            <div className="mt-2 text-sm font-black text-slate-950">{pretty(defense.proof_status || 'BUILDING FORWARD SAMPLE')}</div>
          </div>
        </div>

        <div className="mt-5 overflow-x-auto rounded-2xl border border-slate-200">
          <table className="min-w-[980px] w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="px-4 py-3">Lane</th>
                <th className="px-4 py-3">Rows</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">What it can honestly say</th>
              </tr>
            </thead>
            <tbody>
              {order.map(key => {
                const row = current[key] || {}
                return (
                  <tr key={key} className="border-b border-slate-100 align-top">
                    <td className="px-4 py-3 font-black text-slate-950">{pretty(key)}</td>
                    <td className="px-4 py-3 font-semibold text-slate-700">{integer(row.rows)}</td>
                    <td className="px-4 py-3 text-xs font-black uppercase tracking-wide text-slate-600">{pretty(row.status || 'WAITING')}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{pretty(row.actionability || 'RESEARCH ONLY')}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-5 overflow-x-auto rounded-2xl border border-slate-200">
          <table className="min-w-[980px] w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="px-4 py-3">Forward lane</th>
                <th className="px-4 py-3">Frozen</th>
                <th className="px-4 py-3">Settled</th>
                <th className="px-4 py-3">Independent weeks</th>
                <th className="px-4 py-3">Proof status</th>
                <th className="px-4 py-3">What is graded</th>
              </tr>
            </thead>
            <tbody>
              {proofRows.map(([label, row, weeks, basis]) => (
                <tr key={label} className="border-b border-slate-100 align-top">
                  <td className="px-4 py-3 font-black text-slate-950">{label}</td>
                  <td className="px-4 py-3 font-semibold text-slate-700">{integer(row.tracked)}</td>
                  <td className="px-4 py-3 font-semibold text-slate-700">{integer(row.settled)}</td>
                  <td className="px-4 py-3 font-semibold text-slate-700">{integer(weeks)}</td>
                  <td className="px-4 py-3 text-xs font-black uppercase tracking-wide text-slate-600">
                    {pretty(row.proof_status || 'BUILDING FORWARD SAMPLE')}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600">{basis}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 text-xs leading-5 text-slate-500">
          Review-candidate status requires at least six independent weeks in every forward-tested Fantasy lane.
          Personalized roster research and saved-budget FAAB translation are live, but actual league free-agent availability and winning-bid prediction are not.
          Full custom IDP fantasy-point scoring, trades and automatic provider sync remain blocked until the required data is connected.
          No Fantasy lane changes recommendations automatically.
        </div>
      </div>
    </section>
  )
}

function DfsAccountability({ brain }) {
  const rows = brain?.dfs?.replay_modes || []
  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">DFS accountability</p>
          <h2>Did the optimizer beat harder, realistic baselines?</h2>
        </div>
        <span className="health-pill">PRE-LOCK REPLAY</span>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
        <div className="flex gap-3 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm leading-6 text-blue-950">
          <BarChart3 size={19} className="mt-0.5 shrink-0 text-blue-700" />
          <div>
            Historical lineups are reconstructed only from data that existed before slate lock, then graded after the games.
            V3 compares them with <b>salary-efficient random lineups using at least 94% of the cap</b> and with a same-slate
            <b> Max Projection</b> lineup. Mode collisions are exposed instead of counting identical builds as separate strategy proof.
            <b>None of these are real contest percentiles or cash rates.</b>
          </div>
        </div>

        {rows.length ? (
          <div className="mt-5 overflow-x-auto">
            <table className="min-w-[1120px] w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
                  <th className="px-4 py-3">Site</th>
                  <th className="px-4 py-3">Mode</th>
                  <th className="px-4 py-3">Replay slates</th>
                  <th className="px-4 py-3">Avg actual pts</th>
                  <th className="px-4 py-3">94%+ cap random pct.</th>
                  <th className="px-4 py-3">Actual vs Max Projection</th>
                  <th className="px-4 py-3">Distinct lineup rate</th>
                  <th className="px-4 py-3">Evidence</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(row => (
                  <tr key={`${row.platform}-${row.mode}`} className="border-b border-slate-100">
                    <td className="px-4 py-3 font-black text-slate-950">{row.platform === 'DRAFTKINGS' ? 'DraftKings' : 'FanDuel'}</td>
                    <td className="px-4 py-3 font-extrabold text-slate-700">{pretty(row.mode)}</td>
                    <td className="px-4 py-3 font-semibold text-slate-600">{integer(row.replay_slates)}</td>
                    <td className="px-4 py-3 font-black text-slate-950">{row.avg_actual_points ?? '—'}</td>
                    <td className="px-4 py-3 font-black text-blue-700">{pct(row.avg_random_baseline_percentile)}</td>
                    <td className="px-4 py-3 font-semibold text-slate-700">
                      {row.avg_actual_minus_max_projection == null ? '—' : `${Number(row.avg_actual_minus_max_projection) > 0 ? '+' : ''}${Number(row.avg_actual_minus_max_projection).toFixed(2)} pts`}
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-700">
                      {pct(row.distinct_lineup_rate_pct)}
                      {Number(row.mode_collision_slates || 0) > 0 ? ` · ${integer(row.mode_collision_slates)} collision${Number(row.mode_collision_slates) === 1 ? '' : 's'}` : ''}
                    </td>
                    <td className="px-4 py-3"><StatusPill value={row.replay_evidence_status || row.maturity} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="mt-5 text-sm font-semibold text-slate-500">No valid pre-lock replay sample yet.</div>
        )}

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Live-forward frozen lineups</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{integer(brain?.dfs?.forward_official_snapshots)}</div>
            <div className="mt-2 text-xs leading-5 text-slate-500">Only snapshots captured before lock can ever enter the forward record.</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Real DFS cash rate</div>
            <div className="mt-2 text-2xl font-black text-slate-950">WAITING</div>
            <div className="mt-2 text-xs leading-5 text-slate-500">{brain?.dfs?.contest_metrics_status}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Current evidence status</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{pretty(brain?.dfs?.status || 'WAITING')}</div>
            <div className="mt-2 text-xs leading-5 text-slate-500">Replay evidence stays separate from future live-forward results.</div>
          </div>
        </div>
      </div>
    </section>
  )
}

function ThresholdLab({ brain }) {
  const analysis = brain?.selectivity || {}
  const shadow = brain?.selectivity_shadow || {}
  const experiments = shadow.experiments || []
  const actionable = analysis.actionable || []
  const weakSegments = (analysis.segments || [])
    .filter(row => String(row.status || '').includes('NEGATIVE_EVIDENCE'))
    .slice(0, 5)

  if (!actionable.length && !weakSegments.length && !experiments.length) return null

  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Threshold lab</p>
          <h2>Can fewer picks actually perform better?</h2>
        </div>
        <span className="health-pill">TRAIN → HOLDOUT · SHADOW ONLY</span>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
        <div className="flex gap-3 rounded-2xl border border-violet-100 bg-violet-50 p-4 text-sm leading-6 text-violet-950">
          <Brain size={19} className="mt-0.5 shrink-0 text-violet-700" />
          <div>
            The research process chooses a candidate threshold using older settled results, then tests that exact threshold on newer results.
            A threshold that only wins on the training sample is rejected. <b>Nothing here changes the live model automatically.</b>
          </div>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          {actionable.map((row, index) => {
            const candidate = row.candidate || {}
            const validated = String(row.status || '').startsWith('VALIDATED')
            const rejected = String(row.status || '').includes('REJECTED')
            return (
              <div
                key={`${row.sport}-${row.lane}-${row.market || 'ALL'}-${index}`}
                className={`rounded-3xl border p-5 ${validated ? 'border-emerald-200 bg-emerald-50' : rejected ? 'border-rose-200 bg-rose-50' : 'border-amber-200 bg-amber-50'}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-500">
                      {row.sport} · {pretty(row.lane)} · {pretty(row.market || 'ALL MARKETS')}
                    </div>
                    <div className="mt-2 text-xl font-black text-slate-950">
                      {candidate.minimum_score != null
                        ? `Test Evidence ${candidate.minimum_score}+ only`
                        : 'No threshold candidate'}
                    </div>
                  </div>
                  <StatusPill value={row.status} />
                </div>

                {candidate.minimum_score != null && (
                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <div className="rounded-2xl border border-black/5 bg-white/70 p-3">
                      <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Older training</div>
                      <div className="mt-1 text-lg font-black text-slate-950">
                        {pct(row.train_baseline?.hit_rate_pct)} → {pct(candidate.train?.hit_rate_pct)}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        {candidate.train?.wins || 0}-{candidate.train?.losses || 0} at threshold
                      </div>
                    </div>
                    <div className="rounded-2xl border border-black/5 bg-white/70 p-3">
                      <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Newer holdout</div>
                      <div className="mt-1 text-lg font-black text-slate-950">
                        {pct(row.holdout_baseline?.hit_rate_pct)} → {pct(candidate.holdout?.hit_rate_pct)}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        {candidate.holdout?.wins || 0}-{candidate.holdout?.losses || 0} at threshold
                      </div>
                    </div>
                  </div>
                )}

                <div className="mt-4 text-sm leading-6 text-slate-700">{row.reason}</div>
                {validated && (
                  <div className="mt-3 text-xs font-black uppercase tracking-wide text-emerald-800">
                    Next step: forward shadow test · no user-facing suppression yet
                  </div>
                )}
                {rejected && (
                  <div className="mt-3 text-xs font-black uppercase tracking-wide text-rose-800">
                    Rejected · do not use this threshold
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {!!experiments.length && (
          <div className="mt-6">
            <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">Forward shadow experiment</div>
            <div className="mt-3 grid gap-4 lg:grid-cols-2">
              {experiments.map(exp => (
                <div key={exp.experiment_id} className="rounded-3xl border border-sky-200 bg-sky-50 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="text-xs font-black uppercase tracking-wide text-sky-700">
                        {exp.sport} · {pretty(exp.market)}
                      </div>
                      <div className="mt-2 text-xl font-black text-slate-950">
                        Shadow: Evidence {exp.candidate_min_score}+ only
                      </div>
                    </div>
                    <StatusPill value={exp.promotion_status || exp.status} />
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <div className="rounded-2xl border border-sky-100 bg-white/80 p-3">
                      <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Normal baseline</div>
                      <div className="mt-1 text-2xl font-black text-slate-950">{exp.baseline?.published || 0}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        {exp.baseline?.pending || 0} pending · {exp.baseline?.wins || 0}-{exp.baseline?.losses || 0} settled W-L
                      </div>
                    </div>
                    <div className="rounded-2xl border border-sky-100 bg-white/80 p-3">
                      <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Stricter rule kept</div>
                      <div className="mt-1 text-2xl font-black text-slate-950">{exp.candidate?.published || 0}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        {exp.candidate?.pending || 0} pending · {exp.candidate?.wins || 0}-{exp.candidate?.losses || 0} settled W-L
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 text-sm leading-6 text-slate-700">
                    Forward retention: {pct(exp.forward_retention_pct)}. The live model has <b>not</b> changed.
                    This experiment only asks whether passing on lower-score picks improves future results and price-aware units.
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!!weakSegments.length && (
          <div className="mt-6">
            <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">Weak-segment watch</div>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {weakSegments.map((row, index) => (
                <div key={`${row.sport}-${row.lane}-${row.market}-${row.side}-${index}`} className="rounded-2xl border border-rose-100 bg-rose-50 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-black text-slate-950">
                      {row.sport} · {pretty(row.market)}
                    </div>
                    <StatusPill value={row.status} />
                  </div>
                  <div className="mt-2 text-sm font-bold text-slate-700">
                    {pretty(row.side)} · {row.wins}-{row.losses} · {pct(row.hit_rate_pct)}
                  </div>
                  <div className="mt-2 text-xs leading-5 text-slate-500">
                    {row.decisions} settled decisions. Research warning only; no automatic exclusion.
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-5 border-t border-slate-100 pt-4 text-xs leading-5 text-slate-500">
          Moneyline threshold tests are accuracy research only until publish-time prices prove ROI. Parlays are not threshold-optimized from hit rate because payout economics matter.
        </div>
      </div>
    </section>
  )
}

function ScoreCalibrationAudit({ brain }) {
  const rows = brain?.selectivity?.calibration_audit || []
  if (!rows.length) return null

  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Score calibration</p>
          <h2>Does a higher evidence score actually mean better results?</h2>
        </div>
        <span className="health-pill">EVIDENCE SCORE · NOT PROBABILITY</span>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
        <div className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
          <AlertTriangle size={19} className="mt-0.5 shrink-0 text-amber-700" />
          <div>
            An Evidence Score of 90 is a ranking score, <b>not a 90% chance to win</b>.
            This audit checks whether higher scores are at least ordering outcomes better than lower scores.
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {rows.slice(0, 8).map(row => (
            <div key={`${row.sport}-${row.lane}`} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="font-black text-slate-950">{row.sport} · {pretty(row.lane)}</div>
                <StatusPill value={row.status} />
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                <div className="rounded-xl bg-white p-3">
                  <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Lower half</div>
                  <div className="mt-1 text-lg font-black text-slate-950">{pct(row.lower_half?.hit_rate_pct)}</div>
                </div>
                <div className="rounded-xl bg-white p-3">
                  <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Upper half</div>
                  <div className="mt-1 text-lg font-black text-slate-950">{pct(row.upper_half?.hit_rate_pct)}</div>
                </div>
                <div className="rounded-xl bg-white p-3">
                  <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Rank corr.</div>
                  <div className="mt-1 text-lg font-black text-slate-950">
                    {row.spearman_rank_correlation == null ? '—' : Number(row.spearman_rank_correlation).toFixed(2)}
                  </div>
                </div>
              </div>
              <div className="mt-3 text-sm leading-6 text-slate-600">{row.reason}</div>
              <div className="mt-2 text-xs font-semibold text-slate-400">
                {row.decisions} settled decisions · top quartile vs rest {row.top_quartile_minus_rest_hit_rate_pp == null ? '—' : `${row.top_quartile_minus_rest_hit_rate_pp > 0 ? '+' : ''}${row.top_quartile_minus_rest_hit_rate_pp} pts`}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function SelectivityWatch({ brain }) {
  const categories = new Set(['Best Bets', 'Props', 'Parlays', 'PrizePicks'])
  const rows = (brain?.selectivity_watch || []).filter(row => categories.has(row.label))
  if (!rows.length) return null

  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Selectivity watch</p>
          <h2>Where should the brain get more selective?</h2>
        </div>
        <span className="health-pill">NO AUTO CHANGES</span>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {rows.map(row => (
          <div key={row.label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="font-black text-slate-950">{row.label}</div>
              <StatusPill value={row.status} />
            </div>
            <div className="mt-2 text-xs font-semibold text-slate-500">{integer(row.decisions)} decisions · {pct(row.hit_rate_pct)}</div>
            <div className="mt-3 text-sm leading-6 text-slate-600">{row.reason}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

function ExperimentRegistryPanel({ brain }) {
  const registry = brain?.experiment_registry || {}
  const counts = registry.decision_counts || {}

  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Experiment accountability</p>
          <h2>Failed tests stay in the record</h2>
        </div>
        <span className="health-pill">APPEND-ONLY RESEARCH RECORD</span>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Registered</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(registry.registered_experiments)}</div>
          </div>
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-amber-700">Hold</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(counts.HOLD)}</div>
          </div>
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-rose-700">Rejected</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(counts.REJECTED)}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-black uppercase tracking-wide text-slate-400">Unresolved</div>
            <div className="mt-2 text-3xl font-black text-slate-950">{integer(registry.unresolved_experiments)}</div>
          </div>
        </div>

        <div className="mt-4 flex gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-700">
          <ShieldCheck size={19} className="mt-0.5 shrink-0 text-slate-600" />
          <div>
            Failed thresholds, rejected challengers and held research models remain in the permanent experiment ledger.
            The system cannot improve its apparent record by forgetting unsuccessful tests.
          </div>
        </div>
      </div>
    </section>
  )
}

function ProductProofCard({ title, status, current, detail, history, tone = 'blue' }) {
  const tones = {
    blue: 'border-blue-100 bg-blue-50 text-blue-700',
    emerald: 'border-emerald-100 bg-emerald-50 text-emerald-700',
    amber: 'border-amber-100 bg-amber-50 text-amber-700',
    violet: 'border-violet-100 bg-violet-50 text-violet-700',
    slate: 'border-slate-200 bg-slate-100 text-slate-700',
  }
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">{title}</div>
        <span className={`rounded-full border px-2.5 py-1 text-[10px] font-black ${tones[tone] || tones.blue}`}>{status}</span>
      </div>
      <div className="mt-4 text-2xl font-black tracking-tight text-slate-950">{current}</div>
      <div className="mt-2 text-sm font-semibold leading-6 text-slate-500">{detail}</div>
      <div className="mt-4 border-t border-slate-100 pt-3 text-xs font-bold leading-5 text-slate-400">{history}</div>
    </div>
  )
}

function BrainRecordProductGrid({ brain, categoryMap }) {
  const bets = brain.betting_v2_all_markets?.current?.summary || {}
  const propCurrent = brain.prop_v2?.current || {}
  const propSummary = propCurrent.summary || {}
  const lanes = propCurrent.by_lane || {}
  const ppCandidates = Object.entries(lanes).filter(([key]) => key.endsWith('_PRIZEPICKS')).reduce((sum, [, value]) => sum + Number(value?.candidates || 0), 0)
  const ppMonitors = Object.entries(lanes).filter(([key]) => key.endsWith('_PRIZEPICKS')).reduce((sum, [, value]) => sum + Number(value?.shadow_monitors || 0), 0)
  const propCandidates = Object.entries(lanes).filter(([key]) => key.endsWith('_PROP')).reduce((sum, [, value]) => sum + Number(value?.candidates || 0), 0)
  const parlays = brain.parlay_v2?.current?.summary || {}
  const survivor = brain.survivor?.current || {}
  const fantasyLanes = brain.fantasy_v2?.current?.lanes || {}
  const forwardFantasy = Object.values(fantasyLanes).filter((lane) => lane?.forward_grade_available).length
  const dfs = brain.dfs || {}
  const experiments = brain.experiment_registry || {}

  const historical = (label) => {
    const item = categoryMap[label]
    if (!item) return 'Historical validation is still building.'
    return `Historical: ${item.wins || 0}-${item.losses || 0}${item.pushes ? `-${item.pushes}` : ''} · ${pct(item.hit_rate_pct)} · archive, not official`
  }

  const cards = [
    {
      title: 'Best Bets',
      status: (bets.shadow_plays || 0) > 0 ? 'PLAYING' : 'PROVING',
      current: `${bets.candidates || 0} current · ${bets.shadow_plays || 0} plays`,
      detail: `${bets.passes || 0} candidates failed at least one proof gate. No play is forced.`,
      history: historical('Best Bets'),
      tone: (bets.shadow_plays || 0) > 0 ? 'emerald' : 'blue',
    },
    {
      title: 'Props',
      status: 'FORWARD TEST',
      current: `${propCandidates} current · 0 plays`,
      detail: 'Sport and market-subtype models must beat their market references before promotion.',
      history: historical('Props'),
      tone: 'blue',
    },
    {
      title: 'PrizePicks',
      status: ppMonitors ? 'MONITORING' : 'FORWARD TEST',
      current: `${ppCandidates} current · ${ppMonitors} monitors`,
      detail: 'Leg probability is separated from entry payout economics. Monitors are not PLAYs.',
      history: historical('PrizePicks'),
      tone: ppMonitors ? 'amber' : 'blue',
    },
    {
      title: 'Parlays',
      status: 'PROOF GATE',
      current: `${parlays.candidates || 0} current · ${parlays.shadow_monitors || 0} monitors`,
      detail: `${parlays.resolved_all_legs || 0} have exact V2 legs; ${parlays.all_source_legs_forward_proven || 0} have proven source legs.`,
      history: historical('Parlays'),
      tone: 'violet',
    },
    {
      title: 'Survivor',
      status: survivor.rule_confirmed ? 'READY' : 'RULE WAIT',
      current: `Week ${survivor.pool_current_week ?? '—'} · ${survivor.candidate_count || 0} candidates`,
      detail: survivor.rule_confirmed ? 'Pool rules are confirmed for recommendation scoring.' : 'Recommendation stays locked until the official pool sheet confirms the current-week rule.',
      history: 'Saved pool choices and model recommendations remain separate records.',
      tone: survivor.rule_confirmed ? 'emerald' : 'amber',
    },
    {
      title: 'Fantasy',
      status: 'BUILDING',
      current: `${forwardFantasy} forward-tested lanes`,
      detail: 'Weekly, FAAB, IR stash, defense streaming and IDP are tracked against explicit baselines.',
      history: 'Trade and Rate My Team require connected league context.',
      tone: 'blue',
    },
    {
      title: 'DFS',
      status: 'SMALL SAMPLE',
      current: `${dfs.forward_official_snapshots || 0} forward slates`,
      detail: 'Replay results are useful diagnostics, but replay never counts as forward proof.',
      history: 'Tournament replay has shown promise, but the sample is still too small for promotion.',
      tone: 'amber',
    },
    {
      title: 'Experiment Registry',
      status: experiments.unresolved_experiments ? 'CHECK' : 'CLEAN',
      current: `${experiments.registered_experiments || 0} registered tests`,
      detail: `${experiments.decision_counts?.HOLD || 0} HOLD · ${experiments.decision_counts?.REJECTED || 0} rejected · ${experiments.unresolved_experiments || 0} unresolved`,
      history: 'Failed and rejected experiments stay in the permanent record.',
      tone: experiments.unresolved_experiments ? 'amber' : 'emerald',
    },
  ]

  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Proof by product</p>
          <h2>What is proven, what is promising, what is still building</h2>
        </div>
        <span className="health-pill">NO CHERRY-PICKING</span>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => <ProductProofCard key={card.title} {...card} />)}
      </div>
    </section>
  )
}

function PromisingSignals({ brain }) {
  const challenge = brain.betting_v2_all_markets?.challenger_forward || {}
  const current = challenge.current || {}
  const forward = challenge.forward || {}
  const historicalLane = brain.betting_v2_all_markets?.challengers?.lanes?.CFB_TOTAL || {}
  const pp = brain.prop_v2?.current || {}
  const monitors = (pp.picks || []).filter((row) => row.lane === 'PRIZEPICKS' && row.shadow_decision === 'SHADOW_MONITOR')

  return (
    <section>
      <div className="section-heading">
        <div><p className="eyebrow">Promising, not proven</p><h2>Signals worth watching</h2></div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-3xl border border-amber-200 bg-amber-50 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs font-black uppercase tracking-[0.14em] text-amber-700">CFB Total challenger</div>
            <StatusPill value={current.historical_status || 'BUILDING'} />
          </div>
          <div className="mt-3 text-2xl font-black text-slate-950">{historicalLane.history_n || 0} historical rows · {historicalLane.independent_blocks || 0} independent games</div>
          <div className="mt-2 text-sm leading-6 text-amber-950">The richer challenger has earned continued testing, but its confidence interval still does not justify a live model change.</div>
          <div className="mt-4 text-xs font-bold text-amber-800">Forward: {forward.tracked || 0} tracked · {forward.settled || 0} settled · review gate {forward.minimum_settled_for_review || 50} settled / {forward.minimum_independent_games_for_review || 30} games</div>
        </div>
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="text-xs font-black uppercase tracking-[0.14em] text-violet-700">PrizePicks shadow monitors</div>
          <div className="mt-3 text-2xl font-black text-slate-950">{monitors.length} promising leg{monitors.length === 1 ? '' : 's'}</div>
          <div className="mt-3 space-y-2">
            {monitors.slice(0, 3).map((row) => (
              <div key={`${row.event_id}-${row.player_key}-${row.market_subtype}`} className="rounded-2xl bg-slate-50 p-3 text-sm font-bold text-slate-700">
                {row.player} · {row.side} {row.line} {pretty(row.market_subtype)} · model {pct(row.v2_probability_pct)}
              </div>
            ))}
            {!monitors.length && <div className="text-sm text-slate-500">No current shadow monitors.</div>}
          </div>
          <div className="mt-4 text-xs leading-5 text-slate-500">A shadow monitor is deliberately not shown as a PLAY. Entry-level payout economics still have to prove themselves.</div>
        </div>
      </div>
    </section>
  )
}

export default function PerformancePanel() {
  const [data, setData] = useState({ official: {}, policy: {}, research_validation: [] })
  const [brain, setBrain] = useState({ categories: [], dfs: {}, selectivity_watch: [] })
  const [askQuality, setAskQuality] = useState({ status: 'NO_DATA', tracked: 0 })
  const [askTrace, setAskTrace] = useState({ status: 'NO_DATA', tracked: 0 })
  const [sport, setSport] = useState('ALL')
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const [performanceResponse, brainResponse, askQualityResponse, askTraceResponse] = await Promise.all([
          fetch(`/performance_snapshot.json?ts=${Date.now()}`, { cache: 'no-store' }),
          fetch(`/brain_performance.json?ts=${Date.now()}`, { cache: 'no-store' }),
          fetch(`/api/ask/evaluation-summary?limit=500&ts=${Date.now()}`, { cache: 'no-store' }),
          fetch(`/api/ask/trace-summary?limit=500&ts=${Date.now()}`, { cache: 'no-store' }),
        ])
        if (!performanceResponse.ok) throw new Error('Official performance snapshot is unavailable')
        const performancePayload = await performanceResponse.json()
        const brainPayload = brainResponse.ok ? await brainResponse.json() : { categories: [], dfs: {}, selectivity_watch: [] }
        const askQualityPayload = askQualityResponse.ok ? await askQualityResponse.json() : { status: 'NO_DATA', tracked: 0 }
        const askTracePayload = askTraceResponse.ok ? await askTraceResponse.json() : { status: 'NO_DATA', tracked: 0 }
        if (!cancelled) {
          setData(performancePayload)
          setBrain(brainPayload)
          setAskQuality(askQualityPayload)
          setAskTrace(askTracePayload)
          setError('')
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Performance record is unavailable')
      }
    }

    load()
    const timer = window.setInterval(load, 60000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  const rows = useMemo(() => {
    const all = data.research_validation || []
    return sport === 'ALL' ? all : all.filter(row => row.sport === sport)
  }, [data, sport])

  const categoryMap = useMemo(
    () => Object.fromEntries((brain.categories || []).map(item => [item.label, item])),
    [brain]
  )

  const bestResearch = useMemo(() => {
    return [...(data.research_validation || [])]
      .filter(row => Number(row.score85_settled || 0) >= 25 && row.score85_hit_rate_pct != null)
      .sort((a, b) => Number(b.score85_hit_rate_pct || 0) - Number(a.score85_hit_rate_pct || 0))[0]
  }, [data])

  return (
    <div className="space-y-8">
      <OfficialRecord data={data} />
      <AskQualityPanel data={askQuality} trace={askTrace} />

      {error && (
        <div className="flex gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-rose-800">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <BrainRecordProductGrid brain={brain} categoryMap={categoryMap} />
      <PromisingSignals brain={brain} />

      <details className="group rounded-[30px] border border-slate-200 bg-white p-5 shadow-soft md:p-6">
        <summary className="cursor-pointer list-none">
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="text-xs font-black uppercase tracking-[0.16em] text-blue-700">Advanced validation</div>
              <div className="mt-1 text-2xl font-black tracking-tight text-slate-950">Models, baselines, experiments & diagnostics</div>
              <div className="mt-2 text-sm leading-6 text-slate-500">Open this when you want the research detail underneath the commercial summary.</div>
            </div>
            <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-black text-slate-600 group-open:bg-slate-950 group-open:text-white">Open diagnostics</span>
          </div>
        </summary>

        <div className="mt-8 space-y-8 border-t border-slate-100 pt-8">
          <section>
            <div className="section-heading">
              <div>
                <p className="eyebrow">Historical validation</p>
                <h2>Archived wins and losses</h2>
              </div>
              <span className="health-pill">ARCHIVE · NOT OFFICIAL</span>
            </div>
            <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
              These are retrospective, deduplicated research decisions. They help decide what deserves future testing, but they never replace the official forward record.
            </div>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <BrainMetricCard item={categoryMap['Best Bets']} icon={Target} />
              <BrainMetricCard item={categoryMap['Props']} icon={Gauge} />
              <BrainMetricCard item={categoryMap['PrizePicks']} icon={Trophy} />
              <BrainMetricCard item={categoryMap['Parlays']} icon={Zap} />
            </div>
          </section>

          <ExperimentRegistryPanel brain={brain} />
          <BettingV2Panel brain={brain} />
          <AllMarketsV2Panel brain={brain} />
          <PropV2Panel brain={brain} />
          <ParlayV2Panel brain={brain} />
          <SurvivorV2Panel brain={brain} />
          <FantasyV2Panel brain={brain} />
          <DfsAccountability brain={brain} />
          <ThresholdLab brain={brain} />
          <ScoreCalibrationAudit brain={brain} />
          <SelectivityWatch brain={brain} />

          <section>
            <div className="section-heading">
              <div>
                <p className="eyebrow">Deep validation</p>
                <h2>Research record by sport and lane</h2>
              </div>
              <span className="health-pill">NOT THE OFFICIAL RECORD</span>
            </div>

            {bestResearch && (
              <div className="mb-5 grid gap-3 lg:grid-cols-3">
                <div className="rounded-3xl border border-emerald-200 bg-emerald-50 p-5">
                  <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-emerald-700">
                    <TrendingUp size={16} /> Strongest 85+ research sample
                  </div>
                  <div className="mt-3 text-2xl font-black text-slate-950">{bestResearch.sport} · {pretty(bestResearch.lane)}</div>
                  <div className="mt-2 text-sm font-bold text-slate-700">{bestResearch.score85_wins}-{bestResearch.score85_losses}-{bestResearch.score85_pushes} · {pct(bestResearch.score85_hit_rate_pct)}</div>
                  <div className="mt-2 text-xs leading-5 text-slate-500">Research signal only. It still needs forward validation before it earns a public performance claim.</div>
                </div>
                <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
                  <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-slate-400"><ShieldCheck size={16} /> Accountability rule</div>
                  <div className="mt-3 text-lg font-black text-slate-950">Freeze before the game</div>
                  <div className="mt-2 text-sm leading-6 text-slate-500">A future official pick must be published before the event and remains in the ledger after settlement.</div>
                </div>
                <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
                  <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-slate-400"><BarChart3 size={16} /> Practice learning</div>
                  <div className="mt-3 text-lg font-black text-slate-950">Fake bankroll stays separate</div>
                  <div className="mt-2 text-sm leading-6 text-slate-500">Practice betting can teach process without contaminating the official public record.</div>
                </div>
              </div>
            )}

            <div className="mb-4 flex gap-2 overflow-x-auto pb-1">
              {SPORTS.map(item => (
                <button key={item} type="button" onClick={() => setSport(item)} className={`whitespace-nowrap rounded-xl px-4 py-2 text-xs font-black ${sport === item ? 'bg-slate-950 text-white' : 'border border-slate-200 bg-white text-slate-600'}`}>{item}</button>
              ))}
            </div>
            <ResearchTable rows={rows} />
            <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
              <b>Important:</b> historical hit rate alone is not proof of future profitability. Small samples stay labeled small, and parlay performance cannot be evaluated correctly without payout odds.
            </div>
          </section>
        </div>
      </details>
    </div>
  )
}
