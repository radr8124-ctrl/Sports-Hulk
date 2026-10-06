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

export default function PersonalDefenseStreamingPanel({ onOpenMyTeams }) {
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

        const response = await fetch('/api/fantasy/defense-streaming', {
          cache: 'no-store',
          headers: { Authorization: `Bearer ${token}` },
        })
        const body = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(body.message || 'Could not load your defense streaming research.')
        if (active) setPayload(body)
      } catch (err) {
        if (active) {
          setPayload(null)
          setError(err?.message || 'Could not load your defense streaming research.')
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
            <p className="eyebrow text-amber-700">My Defense Streaming</p>
            <h2 className="mt-2 text-xl font-black text-slate-950">Sign in for roster-aware D/ST research</h2>
            <p className="mt-2 text-sm leading-6 text-amber-950">Sports Zenith can compare the defense saved on your team against weekly and multi-week streaming research.</p>
          </div>
          <div className="shrink-0"><AccountButton /></div>
        </div>
      </section>
    )
  }

  if (loading) return <LoadingPanel label="Loading your defense streaming research" />

  if (error) {
    return (
      <section className="rounded-3xl border border-rose-200 bg-rose-50 p-5">
        <div className="text-sm font-black text-rose-800">Your roster-aware defense streaming research could not load.</div>
        <div className="mt-1 text-xs font-semibold leading-5 text-rose-700">{error}</div>
      </section>
    )
  }

  if (!payload || payload.status === 'AUTHENTICATED_NO_TEAM' || payload.status === 'SAVED_TEAM_NO_ROSTER') {
    return (
      <section className="rounded-3xl border border-blue-200 bg-blue-50 p-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="eyebrow">My Defense Streaming</p>
            <h2 className="mt-2 text-xl font-black text-slate-950">Save your roster first</h2>
            <p className="mt-2 text-sm leading-6 text-blue-950">Once your team is saved, Sports Zenith can compare your D/ST against the current 32-team streaming board.</p>
          </div>
          <button type="button" onClick={onOpenMyTeams} className="shrink-0 rounded-2xl bg-slate-950 px-4 py-3 text-sm font-black text-white">Open My Teams</button>
        </div>
      </section>
    )
  }

  const league = payload.league || {}
  const savedDefenses = Array.isArray(payload.saved_defenses) ? payload.saved_defenses : []
  const alternatives = Array.isArray(payload.alternatives_to_check) ? payload.alternatives_to_check : []

  const actionTone = (action) => {
    const value = String(action || '')
    if (value.includes('HOLD_RESEARCH_STRONG')) return 'bg-emerald-50 text-emerald-700'
    if (value.includes('HOLD_RESEARCH')) return 'bg-blue-50 text-blue-700'
    if (value.includes('COMPARE')) return 'bg-amber-50 text-amber-700'
    return 'bg-slate-100 text-slate-600'
  }

  return (
    <section className="rounded-[28px] border border-emerald-200 bg-emerald-50/40 p-5 md:p-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="eyebrow text-emerald-700">My Defense Streaming</p>
            <span className="rounded-full bg-white px-3 py-1 text-[10px] font-black uppercase tracking-[0.1em] text-emerald-700">Roster-aware research</span>
          </div>
          <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-950">{league.team_name || league.league_name || 'My Team'}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-emerald-950">Your saved D/ST is compared with the current weekly and multi-week defense board. Outside defenses are candidates to check, not confirmed free agents.</p>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-xl bg-white px-3 py-2 text-center">
            <div className="text-lg font-black text-slate-950">{savedDefenses.length}</div>
            <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">Saved D/ST</div>
          </div>
          <div className="rounded-xl bg-white px-3 py-2 text-center">
            <div className="text-lg font-black text-slate-950">{league.dst_slots ?? 0}</div>
            <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">Starter slots</div>
          </div>
        </div>
      </div>

      <div className="mt-5">
        <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Your saved defense</div>
        {savedDefenses.length ? (
          <div className="mt-2 grid gap-3 lg:grid-cols-2">
            {savedDefenses.map((row) => (
              <div key={row.team || row.player} className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                  <div>
                    <div className="text-[10px] font-black uppercase tracking-[0.12em] text-emerald-700">{row.team} D/ST</div>
                    <div className="mt-1 text-xl font-black text-slate-950">vs {row.next_opponent || '—'}</div>
                    <div className="mt-1 text-[11px] font-semibold text-slate-400">{humanize(row.future_schedule_signal || 'UNKNOWN')} · {row.rest_days ?? '—'} rest days</div>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-[9px] font-black uppercase tracking-wide ${actionTone(row.research_action)}`}>{humanize(row.research_action)}</span>
                </div>

                <div className="mt-4 grid grid-cols-4 gap-2 text-center">
                  <div className="rounded-lg bg-slate-50 p-2"><div className="text-sm font-black text-slate-950">{row.weekly_stream_score ?? '—'}</div><div className="text-[9px] font-bold text-slate-400">Weekly</div></div>
                  <div className="rounded-lg bg-slate-50 p-2"><div className="text-sm font-black text-slate-950">#{row.weekly_rank ?? '—'}</div><div className="text-[9px] font-bold text-slate-400">Weekly rank</div></div>
                  <div className="rounded-lg bg-slate-50 p-2"><div className="text-sm font-black text-slate-950">{row.multiweek_hold_score ?? '—'}</div><div className="text-[9px] font-bold text-slate-400">Multi-week</div></div>
                  <div className="rounded-lg bg-slate-50 p-2"><div className="text-sm font-black text-slate-950">#{row.multiweek_rank ?? '—'}</div><div className="text-[9px] font-bold text-slate-400">Hold rank</div></div>
                </div>

                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-[10px] font-semibold leading-4 text-slate-600">
                    <span className="font-black">Weekly tier:</span> {humanize(row.weekly_stream_tier || 'UNKNOWN')} · best outside gap {row.best_outside_weekly_gap ?? '—'} pts
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-[10px] font-semibold leading-4 text-slate-600">
                    <span className="font-black">Hold tier:</span> {humanize(row.multiweek_hold_tier || 'UNKNOWN')} · best outside gap {row.best_outside_multiweek_gap ?? '—'} pts
                  </div>
                </div>

                {row.market_data_available && (
                  <div className="mt-3 text-[10px] font-semibold leading-4 text-slate-400">Generic market context: {humanize(row.market_activity_signal || 'AVAILABLE')} · this does not verify league availability.</div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-2 rounded-2xl border border-dashed border-slate-200 bg-white px-4 py-4 text-xs font-semibold text-slate-500">No D/ST was recognized on this saved roster. Add your defense in My Teams to enable direct comparison.</div>
        )}
      </div>

      <div className="mt-5">
        <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Alternatives to check</div>
        <div className="mt-2 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {alternatives.slice(0, 8).map((row) => (
            <div key={row.team} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[10px] font-black uppercase tracking-[0.12em] text-blue-700">{row.team} D/ST</div>
                  <div className="mt-1 text-base font-black text-slate-950">vs {row.next_opponent || '—'}</div>
                </div>
                <span className="rounded-full bg-emerald-50 px-2 py-1 text-[9px] font-black uppercase tracking-wide text-emerald-700">{humanize(row.weekly_stream_tier || 'UNKNOWN')}</span>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-center">
                <div className="rounded-lg bg-slate-50 p-2"><div className="text-sm font-black text-slate-950">{row.weekly_stream_score ?? '—'}</div><div className="text-[9px] font-bold text-slate-400">Weekly #{row.weekly_rank ?? '—'}</div></div>
                <div className="rounded-lg bg-slate-50 p-2"><div className="text-sm font-black text-slate-950">{row.multiweek_hold_score ?? '—'}</div><div className="text-[9px] font-bold text-slate-400">Hold #{row.multiweek_rank ?? '—'}</div></div>
              </div>
              <div className="mt-3 text-[10px] font-semibold leading-4 text-slate-500">{humanize(row.future_schedule_signal || 'UNKNOWN')} · {humanize(row.multiweek_hold_tier || 'UNKNOWN')}</div>
              <div className="mt-2 text-[10px] font-semibold leading-4 text-slate-400">Check your league before acting. Sports Zenith has not verified this defense is available.</div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="flex gap-3 rounded-2xl border border-amber-200 bg-white p-4">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-700" />
          <div className="text-xs font-semibold leading-5 text-slate-700"><span className="font-black">No automatic drop command.</span> “Compare streamers” means the saved D/ST trails current research alternatives enough to warrant checking the league pool.</div>
        </div>
        <div className="flex gap-3 rounded-2xl border border-blue-200 bg-white p-4">
          <ShieldCheck size={18} className="mt-0.5 shrink-0 text-blue-700" />
          <div className="text-xs font-semibold leading-5 text-slate-700"><span className="font-black">Availability is not verified.</span> Generic add/drop market data does not prove a defense is a free agent in your league.</div>
        </div>
      </div>
    </section>
  )
}
