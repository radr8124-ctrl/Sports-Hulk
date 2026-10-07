import { useEffect, useState } from 'react'
import { AlertTriangle, Gauge, Target } from 'lucide-react'
import { AccountButton, useAuth } from './AuthShell'
import FantasyResearchFreshness from './FantasyResearchFreshness'

function humanize(value) {
  return String(value || '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function playerStatusTone(value) {
  const status = String(value || 'UNKNOWN').toUpperCase()
  if (['OUT', 'IR', 'PUP', 'DOUBTFUL'].includes(status)) return 'bg-rose-50 text-rose-700'
  if (['QUESTIONABLE', 'DAY_TO_DAY'].includes(status)) return 'bg-amber-50 text-amber-700'
  if (status === 'AVAILABLE') return 'bg-blue-50 text-blue-700'
  return 'bg-slate-100 text-slate-600'
}

function LoadingPanel({ label = 'Loading' }) {
  return (
    <section role="status" aria-live="polite" className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="text-sm font-black text-slate-600">{label}…</div>
    </section>
  )
}

export default function PersonalWaiverPanel({ onOpenMyTeams, leagueId = null }) {
  const { user, getAccessToken } = useAuth()
  const [loading, setLoading] = useState(false)
  const [payload, setPayload] = useState(null)
  const [error, setError] = useState('')
  const [retryKey, setRetryKey] = useState(0)

  useEffect(() => {
    let active = true

    if (!user) {
      setPayload(null)
      setError('')
      setLoading(false)
      return () => { active = false }
    }

    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const token = await getAccessToken()
        if (!token) throw new Error('Your session expired. Sign in again.')

        const endpoint = leagueId ? '/api/fantasy/waivers?league_id=' + encodeURIComponent(leagueId) : '/api/fantasy/waivers'
        const response = await fetch(endpoint, {
          cache: 'no-store',
          headers: { Authorization: `Bearer ${token}` },
        })
        const body = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(body.message || 'Could not load your roster-aware waiver research.')
        if (active) setPayload(body)
      } catch (err) {
        if (active) {
          setPayload(null)
          setError(err?.message || 'Could not load your roster-aware waiver research.')
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    load()
    return () => { active = false }
  }, [user, getAccessToken, leagueId, retryKey])

  if (!user) {
    return (
      <section className="rounded-3xl border border-amber-200 bg-amber-50 p-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="eyebrow text-amber-700">My Waiver Targets</p>
            <h2 className="mt-2 text-xl font-black text-slate-950">Sign in for roster-aware waiver research</h2>
            <p className="mt-2 text-sm leading-6 text-amber-950">Sports Zenith can compare waiver research against the weaker areas of your saved roster.</p>
          </div>
          <div className="shrink-0"><AccountButton /></div>
        </div>
      </section>
    )
  }

  if (loading) return <LoadingPanel label="Loading your waiver targets" />

  if (error) {
    return (
      <section className="rounded-3xl border border-rose-200 bg-rose-50 p-5">
        <div className="text-sm font-black text-rose-800">Your roster-aware waiver research could not load.</div>
        <div className="mt-1 text-xs font-semibold leading-5 text-rose-700">{error}</div>
        <button type="button" onClick={() => setRetryKey((value) => value + 1)} className="mt-3 rounded-xl bg-rose-700 px-3 py-2 text-xs font-black text-white">Try again</button>
      </section>
    )
  }

  if (!payload || payload.status === 'AUTHENTICATED_NO_TEAM' || payload.status === 'SAVED_TEAM_NO_ROSTER') {
    return (
      <section className="rounded-3xl border border-blue-200 bg-blue-50 p-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="eyebrow">My Waiver Targets</p>
            <h2 className="mt-2 text-xl font-black text-slate-950">Save your roster first</h2>
            <p className="mt-2 text-sm leading-6 text-blue-950">Once a team is saved, Sports Zenith can compare waiver candidates against your roster’s relative weak spots.</p>
          </div>
          <button type="button" onClick={onOpenMyTeams} className="shrink-0 rounded-2xl bg-slate-950 px-4 py-3 text-sm font-black text-white">Open My Teams</button>
        </div>
      </section>
    )
  }

  const needs = Array.isArray(payload.position_needs) ? payload.position_needs : []
  const targets = Array.isArray(payload.targets) ? payload.targets : []
  const cautions = Array.isArray(payload.availability_cautions) ? payload.availability_cautions : []
  const league = payload.league || {}
  const budget = payload.budget_context || {}
  const formatFaab = (value) => {
    const number = Number(value)
    if (!Number.isFinite(number)) return '—'
    return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
  }

  return (
    <section className="min-w-0 max-w-full rounded-[28px] border border-violet-200 bg-violet-50/50 p-5 md:p-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="eyebrow text-violet-700">My Waiver Targets</p>
            <span className="rounded-full bg-white px-3 py-1 text-[10px] font-black uppercase tracking-[0.1em] text-violet-700">Roster-aware research</span>
          </div>
          <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-950">{league.team_name || league.league_name || 'My Team'}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-violet-950">These are waiver candidates to check based on your roster’s current research profile. Sports Zenith has not verified that they are actually available in your league.</p>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-2xl border border-violet-100 bg-white px-4 py-3 text-center">
            <div className="text-xl font-black text-slate-950">{targets.length}</div>
            <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">Targets to check</div>
          </div>
          <div className="rounded-2xl border border-violet-100 bg-white px-4 py-3 text-center">
            <div className="text-xl font-black text-slate-950">{budget.connected ? '$' + formatFaab(budget.remaining_budget) : '—'}</div>
            <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">FAAB remaining</div>
          </div>
        </div>
      </div>

      <FantasyResearchFreshness freshness={payload.research_freshness} />

      {budget.connected && (
        <div className="mt-5 grid gap-3 sm:grid-cols-4">
          <div className="rounded-2xl border border-violet-100 bg-white p-3">
            <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">Total budget</div>
            <div className="mt-1 text-lg font-black text-slate-950">{'$'}{formatFaab(budget.total_budget)}</div>
          </div>
          <div className="rounded-2xl border border-violet-100 bg-white p-3">
            <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">Remaining</div>
            <div className="mt-1 text-lg font-black text-slate-950">{'$'}{formatFaab(budget.remaining_budget)}</div>
          </div>
          <div className="rounded-2xl border border-violet-100 bg-white p-3">
            <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">Spent</div>
            <div className="mt-1 text-lg font-black text-slate-950">{'$'}{formatFaab(budget.spent_budget)}</div>
          </div>
          <div className="rounded-2xl border border-violet-100 bg-white p-3">
            <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">Budget left</div>
            <div className="mt-1 text-lg font-black text-slate-950">{budget.remaining_pct_of_total ?? '—'}%</div>
          </div>
        </div>
      )}

      <div className="mt-5">
        <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Roster need research</div>
        {needs.length > 0 ? (
          <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
            {needs.map((need) => (
              <div key={need.position} className="min-w-[150px] rounded-2xl border border-violet-100 bg-white p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-black text-slate-950">{need.position}</div>
                  <div className="text-sm font-black text-violet-700">{need.roster_need_score}</div>
                </div>
                <div className="mt-1 text-[10px] font-bold uppercase tracking-wide text-slate-400">{humanize(need.roster_need_tier)}</div>
                <div className="mt-2 text-[10px] font-semibold text-slate-500">{need.roster_count} scored roster {need.roster_count === 1 ? 'player' : 'players'}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-2 rounded-2xl border border-dashed border-slate-200 bg-white px-4 py-4 text-xs font-semibold text-slate-500">
            No scored QB/RB/WR/TE roster-need rows are available for this saved team right now.
          </div>
        )}
      </div>

      {targets.length === 0 && (
        <div className="mt-5 rounded-2xl border border-dashed border-violet-200 bg-white px-4 py-4 text-xs font-semibold leading-5 text-slate-600">
          <span className="font-black text-slate-950">No personalized waiver target cleared the current filter.</span> That is a valid result. Sports Zenith is not filling the page with low-quality adds just to produce a recommendation.
        </div>
      )}

      <div className="mt-5 grid min-w-0 max-w-full gap-3 lg:grid-cols-2 xl:grid-cols-4">
        {targets.map((row) => (
          <div key={row.player_key || row.player} className="min-w-0 max-w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex min-w-0 items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-[10px] font-black uppercase tracking-[0.12em] text-violet-700">{row.position} · {row.team || '—'}</div>
                <div className="mt-1 truncate text-lg font-black text-slate-950">{row.player}</div>
              </div>
              <span className={`max-w-[48%] rounded-full px-2.5 py-1 text-center text-[9px] font-black uppercase leading-4 tracking-wide ${playerStatusTone(row.player_status || row.availability_status)}`}>Player status · {humanize(row.player_status || row.availability_status || 'UNKNOWN')}</span>
            </div>

            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-lg bg-slate-50 px-2 py-2"><div className="text-sm font-black text-slate-950">{row.roster_fit_research_score ?? '—'}</div><div className="text-[9px] font-bold text-slate-400">Roster fit</div></div>
              <div className="rounded-lg bg-slate-50 px-2 py-2"><div className="text-sm font-black text-slate-950">{row.waiver_research_score ?? '—'}</div><div className="text-[9px] font-bold text-slate-400">Waiver research</div></div>
              <div className="rounded-lg bg-slate-50 px-2 py-2"><div className="text-sm font-black text-slate-950">{row.roster_need_score ?? '—'}</div><div className="text-[9px] font-bold text-slate-400">Need</div></div>
            </div>

            <div className="mt-3 flex items-center justify-between gap-3">
              <span className="rounded-full bg-violet-50 px-2.5 py-1 text-[9px] font-black uppercase tracking-wide text-violet-700">{humanize(row.waiver_priority)}</span>
              <span className="text-[11px] font-black text-slate-600">{row.research_faab_low_pct ?? '—'}–{row.research_faab_high_pct ?? '—'}% research FAAB</span>
            </div>

            {row.budget_planning?.connected && (
              <div className="mt-3 rounded-xl border border-blue-100 bg-blue-50 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-[9px] font-black uppercase tracking-[0.1em] text-blue-700">Saved-budget translation</div>
                    <div className="mt-1 text-sm font-black text-slate-950">
                      {'$'}{formatFaab(row.budget_planning.research_low_units)}–{'$'}{formatFaab(row.budget_planning.research_high_units)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">Pressure</div>
                    <div className="mt-1 text-[10px] font-black text-slate-700">{humanize(row.budget_planning.budget_pressure)}</div>
                  </div>
                </div>
                <div className="mt-2 text-[10px] font-semibold leading-4 text-blue-900">
                  {humanize(row.budget_planning.range_status)} · upper range = {row.budget_planning.high_as_pct_of_remaining ?? '—'}% of remaining FAAB.
                </div>
              </div>
            )}

            <div className="mt-3 text-[10px] font-semibold leading-4 text-slate-400">Check availability in your league before acting. Percentage and dollar translation are research planning ranges—not predicted winning bids.</div>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-700" />
          <div className="text-xs font-semibold leading-5 text-amber-950">
            <span className="font-black">League availability is not connected.</span> These are candidates to check, not confirmed free agents.
          </div>
        </div>
        <div className="flex gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4">
          <Gauge size={18} className="mt-0.5 shrink-0 text-blue-700" />
          <div className="text-xs font-semibold leading-5 text-blue-950">
            <span className="font-black">FAAB remains research, not a winning-bid prediction.</span> {payload.budget_context_connected ? 'Sports Zenith now translates the generic percentage range against your saved total and remaining budget, but it does not change the player ranking or claim that the translated amount will win.' : 'Save FAAB total and remaining balance in League Settings to add budget-pressure context.'}
          </div>
        </div>
      </div>

      {cautions.length > 0 && (
        <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
          <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Player-status cautions</div>
          <div className="mt-2 text-xs font-semibold leading-5 text-slate-600">
            {cautions.slice(0, 5).map((row) => `${row.player} (${humanize(row.player_status || row.availability_status || 'UNKNOWN')})`).join(' · ')}
          </div>
        </div>
      )}
    </section>
  )
}
