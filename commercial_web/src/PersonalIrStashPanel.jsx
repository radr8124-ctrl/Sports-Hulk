import { useEffect, useState } from 'react'
import { AlertTriangle, ShieldCheck } from 'lucide-react'
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

export default function PersonalIrStashPanel({ onOpenMyTeams }) {
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

        const response = await fetch('/api/fantasy/ir-stash', {
          cache: 'no-store',
          headers: { Authorization: `Bearer ${token}` },
        })
        const body = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(body.message || 'Could not load your roster-aware IR stash research.')
        if (active) setPayload(body)
      } catch (err) {
        if (active) {
          setPayload(null)
          setError(err?.message || 'Could not load your roster-aware IR stash research.')
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    load()
    return () => { active = false }
  }, [user, getAccessToken])

  if (!user) {
    return (
      <section className="rounded-3xl border border-amber-200 bg-amber-50 p-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="eyebrow text-amber-700">My IR / Stash</p>
            <h2 className="mt-2 text-xl font-black text-slate-950">Sign in for roster-aware IR research</h2>
            <p className="mt-2 text-sm leading-6 text-amber-950">Sports Zenith can match injury/stash research to your saved roster and IR-slot count.</p>
          </div>
          <div className="shrink-0"><AccountButton /></div>
        </div>
      </section>
    )
  }

  if (loading) return <LoadingPanel label="Loading your IR stash research" />

  if (error) {
    return (
      <section className="rounded-3xl border border-rose-200 bg-rose-50 p-5">
        <div className="text-sm font-black text-rose-800">Your roster-aware IR stash research could not load.</div>
        <div className="mt-1 text-xs font-semibold leading-5 text-rose-700">{error}</div>
      </section>
    )
  }

  if (!payload || payload.status === 'AUTHENTICATED_NO_TEAM' || payload.status === 'SAVED_TEAM_NO_ROSTER') {
    return (
      <section className="rounded-3xl border border-blue-200 bg-blue-50 p-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="eyebrow">My IR / Stash</p>
            <h2 className="mt-2 text-xl font-black text-slate-950">Save your roster first</h2>
            <p className="mt-2 text-sm leading-6 text-blue-950">Once your team is saved, Sports Zenith can identify injured roster players and IR-stash research candidates.</p>
          </div>
          <button type="button" onClick={onOpenMyTeams} className="shrink-0 rounded-2xl bg-slate-950 px-4 py-3 text-sm font-black text-white">Open My Teams</button>
        </div>
      </section>
    )
  }

  const league = payload.league || {}
  const capacity = payload.ir_capacity || {}
  const rosterInjured = Array.isArray(payload.roster_injured) ? payload.roster_injured : []
  const outside = Array.isArray(payload.outside_targets_to_check) ? payload.outside_targets_to_check : []
  const conflicts = Array.isArray(payload.outside_source_conflicts) ? payload.outside_source_conflicts : []

  return (
    <section className="rounded-[28px] border border-amber-200 bg-amber-50/50 p-5 md:p-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="eyebrow text-amber-700">My IR / Stash</p>
            <span className="rounded-full bg-white px-3 py-1 text-[10px] font-black uppercase tracking-[0.1em] text-amber-700">Roster-aware research</span>
          </div>
          <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-950">{league.team_name || league.league_name || 'My Team'}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-amber-950">Saved IR slots are used for capacity planning only. Actual IR eligibility still depends on the fantasy platform and league rules.</p>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <div className="rounded-xl bg-white px-3 py-2 text-center">
            <div className="text-lg font-black text-slate-950">{capacity.saved_ir_slots ?? 0}</div>
            <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">IR slots</div>
          </div>
          <div className="rounded-xl bg-white px-3 py-2 text-center">
            <div className="text-lg font-black text-slate-950">{rosterInjured.length}</div>
            <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">Injured roster</div>
          </div>
          <div className="rounded-xl bg-white px-3 py-2 text-center">
            <div className="text-lg font-black text-slate-950">{capacity.likely_open_slots ?? 0}</div>
            <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">Likely open</div>
          </div>
        </div>
      </div>

      <div className="mt-5">
        <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Players already on your roster</div>
        {rosterInjured.length ? (
          <div className="mt-2 grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
            {rosterInjured.map((row) => (
              <div key={row.player_key || row.player} className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-[10px] font-black uppercase tracking-[0.12em] text-amber-700">{row.position || '—'} · {row.team || '—'}</div>
                    <div className="mt-1 truncate text-lg font-black text-slate-950">{row.player}</div>
                  </div>
                  <span className="shrink-0 rounded-full bg-amber-50 px-2.5 py-1 text-[9px] font-black uppercase tracking-wide text-amber-700">{humanize(row.status || 'UNKNOWN')}</span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-center">
                  <div className="rounded-lg bg-slate-50 px-2 py-2"><div className="text-sm font-black text-slate-950">{row.stash_research_score ?? '—'}</div><div className="text-[9px] font-bold text-slate-400">Stash research</div></div>
                  <div className="rounded-lg bg-slate-50 px-2 py-2"><div className="text-sm font-black text-slate-950">{row.source_count ?? '—'}</div><div className="text-[9px] font-bold text-slate-400">Sources</div></div>
                </div>
                <div className="mt-3 rounded-xl bg-slate-50 px-3 py-2 text-[10px] font-black uppercase tracking-wide text-slate-600">{humanize(row.roster_action_research)}</div>
                <div className="mt-2 text-[10px] font-semibold leading-4 text-slate-500">{humanize(row.ir_capacity_class)} · return window {humanize(row.return_window || 'UNKNOWN')}.</div>
                {row.source_disagreement && <div className="mt-2 text-[10px] font-black text-rose-700">Sources disagree — review before acting.</div>}
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-2 rounded-2xl border border-dashed border-slate-200 bg-white px-4 py-4 text-xs font-semibold text-slate-500">No current NFL injury/stash row matched a player on this saved roster.</div>
        )}
      </div>

      <div className="mt-5">
        <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Outside stash names to check</div>
        <div className="mt-2 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {outside.length ? outside.map((row) => (
            <div key={row.player_key || row.player} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[10px] font-black uppercase tracking-[0.12em] text-blue-700">{row.position} · {row.team || '—'}</div>
                  <div className="mt-1 text-base font-black text-slate-950">{row.player}</div>
                </div>
                <span className="rounded-full bg-slate-50 px-2 py-1 text-[9px] font-black uppercase tracking-wide text-slate-600">{humanize(row.status)}</span>
              </div>
              <div className="mt-3 text-sm font-black text-slate-950">{row.stash_research_score ?? '—'} <span className="text-[10px] font-semibold text-slate-400">stash research</span></div>
              <div className="mt-2 text-[10px] font-semibold leading-4 text-slate-500">{humanize(row.stash_tier)} · {humanize(row.return_window || 'UNKNOWN')} return window.</div>
              <div className="mt-2 text-[10px] font-semibold leading-4 text-slate-400">Check league availability and platform IR eligibility before adding.</div>
            </div>
          )) : (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-4 py-4 text-xs font-semibold text-slate-500">No positive, non-conflicted outside stash candidates cleared this conservative filter.</div>
          )}
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="flex gap-3 rounded-2xl border border-amber-200 bg-white p-4">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-700" />
          <div className="text-xs font-semibold leading-5 text-slate-700"><span className="font-black">IR eligibility is not verified.</span> IR, PUP and OUT tags are research inputs, not a guarantee that your platform allows the player in an IR slot.</div>
        </div>
        <div className="flex gap-3 rounded-2xl border border-blue-200 bg-white p-4">
          <ShieldCheck size={18} className="mt-0.5 shrink-0 text-blue-700" />
          <div className="text-xs font-semibold leading-5 text-slate-700"><span className="font-black">Return dates are not guarantees.</span> Source conflicts stay visible and are never silently resolved.</div>
        </div>
      </div>

      {conflicts.length > 0 && (
        <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-xs font-semibold leading-5 text-rose-800">
          Outside source-conflict review: {conflicts.map((row) => row.player).join(' · ')}
        </div>
      )}
    </section>
  )
}
