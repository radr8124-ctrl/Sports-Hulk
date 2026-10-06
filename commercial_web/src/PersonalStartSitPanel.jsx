import { useEffect, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { AccountButton, useAuth } from './AuthShell'

function humanize(value) {
  return String(value || '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function LoadingPanel({ label = 'Loading' }) {
  return (
    <section role="status" aria-live="polite" className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="text-sm font-black text-slate-600">{label}…</div>
    </section>
  )
}

export default function PersonalStartSitPanel({ onOpenMyTeams, leagueId = null }) {
  const { user, getAccessToken } = useAuth()
  const [loading, setLoading] = useState(false)
  const [payload, setPayload] = useState(null)
  const [error, setError] = useState('')

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

        const endpoint = leagueId ? '/api/fantasy/start-sit?league_id=' + encodeURIComponent(leagueId) : '/api/fantasy/start-sit'
        const response = await fetch(endpoint, {
          cache: 'no-store',
          headers: { Authorization: `Bearer ${token}` },
        })
        const body = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(body.message || 'Could not load your roster-aware Start/Sit research.')
        if (active) setPayload(body)
      } catch (err) {
        if (active) {
          setPayload(null)
          setError(err?.message || 'Could not load your roster-aware Start/Sit research.')
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    load()
    return () => { active = false }
  }, [user, getAccessToken, leagueId])

  if (!user) {
    return (
      <section className="rounded-3xl border border-amber-200 bg-amber-50 p-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="eyebrow text-amber-700">My Start / Sit</p>
            <h2 className="mt-2 text-xl font-black text-slate-950">Sign in for roster-aware research</h2>
            <p className="mt-2 text-sm leading-6 text-amber-950">Sports Zenith can filter this week’s research to only the players saved on your team.</p>
          </div>
          <div className="shrink-0"><AccountButton /></div>
        </div>
      </section>
    )
  }

  if (loading) {
    return <LoadingPanel label="Loading your Start / Sit research" />
  }

  if (error) {
    return (
      <section className="rounded-3xl border border-rose-200 bg-rose-50 p-5">
        <div className="text-sm font-black text-rose-800">Your roster-aware Start/Sit research could not load.</div>
        <div className="mt-1 text-xs font-semibold leading-5 text-rose-700">{error}</div>
      </section>
    )
  }

  if (!payload || payload.status === 'AUTHENTICATED_NO_TEAM' || payload.status === 'SAVED_TEAM_NO_ROSTER') {
    return (
      <section className="rounded-3xl border border-blue-200 bg-blue-50 p-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="eyebrow">My Start / Sit</p>
            <h2 className="mt-2 text-xl font-black text-slate-950">Save your roster first</h2>
            <p className="mt-2 text-sm leading-6 text-blue-950">Once a team is saved, this section will automatically show weekly research for only your players.</p>
          </div>
          <button type="button" onClick={onOpenMyTeams} className="shrink-0 rounded-2xl bg-slate-950 px-4 py-3 text-sm font-black text-white">Open My Teams</button>
        </div>
      </section>
    )
  }

  const groups = Array.isArray(payload.groups) ? payload.groups : []
  const coverage = payload.coverage || {}
  const league = payload.league || {}
  const lineup = payload.lineup_research || {}
  const starterCandidates = Array.isArray(lineup.starter_candidates) ? lineup.starter_candidates : []
  const benchCandidates = Array.isArray(lineup.bench_candidates) ? lineup.bench_candidates : []
  const openSlots = Array.isArray(lineup.open_slots) ? lineup.open_slots : []
  const unscoredSlots = Array.isArray(lineup.unscored_slots) ? lineup.unscored_slots : []
  const tiebreakers = Array.isArray(lineup.tiebreakers) ? lineup.tiebreakers : []
  const appliedTiebreakers = tiebreakers.filter((row) => row.applied)
  const slotAware = lineup.status === 'SLOT_AWARE_RESEARCH'

  const tierTone = (tier) => {
    const value = String(tier || '')
    if (value.includes('CORE_START')) return 'bg-emerald-50 text-emerald-700'
    if (value.includes('START_LEAN')) return 'bg-blue-50 text-blue-700'
    if (value.includes('FLEX')) return 'bg-sky-50 text-sky-700'
    if (value.includes('MATCHUP')) return 'bg-amber-50 text-amber-700'
    return 'bg-rose-50 text-rose-700'
  }

  return (
    <section className="rounded-[28px] border border-blue-200 bg-blue-50/60 p-5 md:p-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="eyebrow">My Start / Sit</p>
            <span className="rounded-full bg-white px-3 py-1 text-[10px] font-black uppercase tracking-[0.1em] text-blue-700">Roster-aware research</span>
          </div>
          <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-950">{league.team_name || league.league_name || 'My Team'}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-blue-950">{payload.note}</p>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <div className="rounded-xl bg-white px-3 py-2 text-center">
            <div className="text-lg font-black text-slate-950">{coverage.matched_count ?? 0}/{coverage.roster_size ?? 0}</div>
            <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">Matched</div>
          </div>
          <div className="rounded-xl bg-white px-3 py-2 text-center">
            <div className="text-lg font-black text-slate-950">{coverage.coverage_pct ?? 0}%</div>
            <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">Coverage</div>
          </div>
          <div className="hidden rounded-xl bg-white px-3 py-2 text-center sm:block">
            <div className="text-lg font-black text-slate-950">{groups.length}</div>
            <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">Positions</div>
          </div>
        </div>
      </div>

      {slotAware && (
        <div className="mt-5 rounded-2xl border border-blue-200 bg-white p-4">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
            <div>
              <div className="text-xs font-black uppercase tracking-[0.12em] text-blue-700">Slot-aware lineup research</div>
              <div className="mt-1 text-sm font-semibold leading-5 text-slate-500">
                Weekly research stays primary. {league.scoring_format ? humanize(league.scoring_format) + ' historical context can only break close calls within ' + (lineup.close_call_weekly_window ?? 3) + ' weekly-score points.' : 'Save a scoring format to enable close-call format context.'} These are not fantasy-point projections.
              </div>
            </div>
            <div className="flex flex-wrap justify-end gap-2">
              {tiebreakers.length > 0 && (
                <span className="rounded-full bg-blue-50 px-3 py-1 text-[10px] font-black uppercase tracking-[0.1em] text-blue-700">{tiebreakers.length} format {tiebreakers.length === 1 ? 'check' : 'checks'}</span>
              )}
              {appliedTiebreakers.length > 0 && (
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-[10px] font-black uppercase tracking-[0.1em] text-emerald-700">{appliedTiebreakers.length} changed {appliedTiebreakers.length === 1 ? 'slot' : 'slots'}</span>
              )}
              <span className="rounded-full bg-slate-950 px-3 py-1 text-[10px] font-black uppercase tracking-[0.1em] text-white">Not official lineup</span>
            </div>
          </div>

          <div className="mt-4">
            <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Starter candidates</div>
            <div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
              {starterCandidates.map((row) => (
                <div key={[row.assigned_slot, row.slot_index, row.player_key || row.player].join('-')} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[9px] font-black uppercase tracking-wide text-blue-700">{row.assigned_slot}{row.slot_index > 1 ? ' ' + row.slot_index : ''}</span>
                    <span className="text-sm font-black text-slate-950">{row.weekly_research_score ?? '—'}</span>
                  </div>
                  <div className="mt-2 truncate text-sm font-black text-slate-950">{row.player}</div>
                  <div className="mt-1 text-[10px] font-semibold text-slate-400">{row.position} · {row.team || '—'} · vs {row.opponent || '—'}</div>
                  <div className="mt-2 text-[9px] font-black uppercase tracking-wide text-slate-500">{humanize(row.weekly_tier || 'UNKNOWN')}</div>
                  {row.format_context_available && (
                    <div className="mt-2 rounded-lg border border-slate-200 bg-white px-2 py-2 text-[10px] font-semibold leading-4 text-slate-500">
                      <div>{humanize(row.format_context_scoring || league.scoring_format || 'SCORING')} historical context: {row.historical_format_points_per_game ?? '—'} pts/game · {row.format_context_position_percentile ?? '—'}th position percentile</div>
                      {row.close_call_tiebreaker_considered && (
                        <div className={row.close_call_tiebreaker_applied ? 'mt-1 font-black text-emerald-700' : 'mt-1 font-black text-blue-700'}>
                          {row.close_call_tiebreaker_applied ? 'Close-call format tiebreaker changed this slot.' : 'Format checked; weekly research order held.'}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {benchCandidates.length > 0 && (
            <div className="mt-4">
              <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Bench candidates</div>
              <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
                {benchCandidates.map((row) => (
                  <div key={row.player_key || row.player} className="min-w-[165px] rounded-xl border border-slate-200 bg-white p-3">
                    <div className="truncate text-sm font-black text-slate-950">{row.player}</div>
                    <div className="mt-1 text-[10px] font-semibold text-slate-400">{row.position} · {row.team || '—'}</div>
                    <div className="mt-2 flex items-center justify-between gap-2">
                      <span className="text-[9px] font-black uppercase tracking-wide text-slate-500">{humanize(row.weekly_tier || 'UNKNOWN')}</span>
                      <span className="text-sm font-black text-slate-700">{row.weekly_research_score ?? '—'}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!!(openSlots.length || unscoredSlots.length) && (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-semibold leading-5 text-amber-950">
              {openSlots.length > 0 && <div><span className="font-black">Open scored slots:</span> {openSlots.map((slot) => slot.slot + (slot.slot_index > 1 ? ' ' + slot.slot_index : '')).join(', ')}</div>}
              {unscoredSlots.length > 0 && <div className={openSlots.length ? 'mt-1' : ''}><span className="font-black">Unscored slots:</span> {unscoredSlots.map((slot) => slot.slot + (slot.player ? ' — ' + slot.player : '')).join(', ')}.</div>}
            </div>
          )}

          <div className="mt-3 text-[10px] font-semibold leading-4 text-slate-400">{lineup.note}</div>
        </div>
      )}

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        {groups.map((group) => (
          <div key={group.position} className="rounded-2xl border border-blue-100 bg-white p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-500">{group.position}</div>
              <div className="text-[10px] font-black text-slate-400">{group.count} roster {group.count === 1 ? 'option' : 'options'}</div>
            </div>
            <div className="mt-3 space-y-2">
              {(group.players || []).map((row) => (
                <div key={row.player_key || row.player} className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="truncate text-sm font-black text-slate-950">{row.player}</div>
                        {row.roster_position_rank === 1 && group.count > 1 && (
                          <span className="rounded-full bg-slate-950 px-2 py-0.5 text-[9px] font-black uppercase tracking-wide text-white">Top roster option</span>
                        )}
                      </div>
                      <div className="mt-1 text-[11px] font-semibold text-slate-400">{row.team || '—'} · vs {row.opponent || '—'} · #{row.roster_position_rank} of {row.roster_position_count}</div>
                    </div>
                    <span className={`shrink-0 rounded-full px-2.5 py-1 text-[9px] font-black uppercase tracking-wide ${tierTone(row.weekly_tier)}`}>{humanize(row.weekly_tier || 'UNKNOWN')}</span>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                    <div className="rounded-lg bg-white px-2 py-2"><div className="text-sm font-black text-slate-950">{row.weekly_research_score ?? '—'}</div><div className="text-[9px] font-bold text-slate-400">Weekly</div></div>
                    <div className="rounded-lg bg-white px-2 py-2"><div className="text-sm font-black text-slate-950">{row.ros_research_score ?? '—'}</div><div className="text-[9px] font-bold text-slate-400">ROS</div></div>
                    <div className="rounded-lg bg-white px-2 py-2"><div className="text-[11px] font-black text-slate-950">{humanize(row.role_signal || 'UNKNOWN')}</div><div className="text-[9px] font-bold text-slate-400">Role</div></div>
                  </div>
                  {row.research_reasons && <div className="mt-2 text-[11px] font-semibold leading-5 text-slate-500">{row.research_reasons}</div>}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {(!league.scoring_connected || !league.slot_context_connected) && (
        <div className="mt-4 flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-700" />
          <div className="text-xs font-semibold leading-5 text-amber-950">
            <span className="font-black">Not an official lineup yet.</span> Add league scoring and starter-slot settings later so Sports Zenith can compare players against the actual rules of your league.
          </div>
        </div>
      )}
    </section>
  )
}
