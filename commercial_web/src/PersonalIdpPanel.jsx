import { useEffect, useState } from 'react'
import { Activity, AlertTriangle, ShieldCheck } from 'lucide-react'
import { AccountButton, useAuth } from './AuthShell'

function humanize(value) {
  return String(value || '')
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function LoadingPanel() {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex items-center gap-3 text-sm font-black text-slate-600">
        <Activity size={17} className="animate-pulse text-blue-600" />
        Loading your IDP research
      </div>
    </section>
  )
}

function scoreTone(tier) {
  const value = String(tier || '')
  if (value === 'IDP_CORE_USAGE') return 'bg-emerald-50 text-emerald-700'
  if (value === 'IDP_STRONG_USAGE') return 'bg-blue-50 text-blue-700'
  if (value === 'IDP_WATCH') return 'bg-amber-50 text-amber-700'
  if (value === 'INACTIVE_NO_START') return 'bg-rose-50 text-rose-700'
  return 'bg-slate-100 text-slate-600'
}

function UsageCard({ row, slotLabel = null }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            {slotLabel && (
              <span className="rounded-full bg-slate-950 px-2 py-0.5 text-[9px] font-black uppercase tracking-wide text-white">
                {slotLabel}
              </span>
            )}
            <span className="text-[10px] font-black uppercase tracking-[0.12em] text-sky-700">
              {row.idp_group || row.position || 'IDP'} · {row.team || '—'}
            </span>
          </div>
          <div className="mt-1 truncate text-base font-black text-slate-950">{row.player}</div>
          <div className="mt-1 text-[11px] font-semibold text-slate-400">
            {row.position || '—'} · vs {row.next_opponent || '—'}
          </div>
        </div>
        <span className={`shrink-0 rounded-full px-2.5 py-1 text-[9px] font-black uppercase tracking-wide ${scoreTone(row.idp_usage_tier)}`}>
          {humanize(row.idp_usage_tier || 'UNKNOWN')}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg bg-slate-50 p-2">
          <div className="text-sm font-black text-slate-950">{row.idp_usage_score ?? '—'}</div>
          <div className="text-[9px] font-bold text-slate-400">Usage</div>
        </div>
        <div className="rounded-lg bg-slate-50 p-2">
          <div className="text-sm font-black text-slate-950">{row.snap_pct == null ? '—' : row.snap_pct + '%'}</div>
          <div className="text-[9px] font-bold text-slate-400">Snaps</div>
        </div>
        <div className="rounded-lg bg-slate-50 p-2">
          <div className="text-sm font-black text-slate-950">
            {row.snap_pct_change == null ? '—' : (row.snap_pct_change > 0 ? '+' : '') + row.snap_pct_change + ' pts'}
          </div>
          <div className="text-[9px] font-bold text-slate-400">Snap change</div>
        </div>
      </div>

      <div className="mt-3 text-[10px] font-semibold leading-4 text-slate-500">
        {humanize(row.role_signal || 'UNKNOWN ROLE')} · {humanize(row.usage_action_research || 'USAGE RESEARCH')}
      </div>
      {row.availability_status && row.availability_status !== 'UNKNOWN' && (
        <div className={`mt-2 text-[10px] font-black uppercase tracking-wide ${String(row.availability_status).toUpperCase() === 'QUESTIONABLE' ? 'text-amber-700' : 'text-slate-500'}`}>
          {humanize(row.availability_status)}
          {row.injury_type ? ' · ' + row.injury_type : ''}
        </div>
      )}
    </div>
  )
}

export default function PersonalIdpPanel({ onOpenMyTeams }) {
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

        const response = await fetch('/api/fantasy/idp', {
          cache: 'no-store',
          headers: { Authorization: `Bearer ${token}` },
        })
        const body = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(body.message || 'Could not load your roster-aware IDP research.')
        if (active) setPayload(body)
      } catch (err) {
        if (active) {
          setPayload(null)
          setError(err?.message || 'Could not load your roster-aware IDP research.')
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
            <p className="eyebrow text-amber-700">My IDP</p>
            <h2 className="mt-2 text-xl font-black text-slate-950">Sign in for roster-aware IDP research</h2>
            <p className="mt-2 text-sm leading-6 text-amber-950">
              Sports Zenith can match DL/LB/DB usage and snap research to the defensive players saved on your team.
            </p>
          </div>
          <div className="shrink-0"><AccountButton /></div>
        </div>
      </section>
    )
  }

  if (loading) return <LoadingPanel />

  if (error) {
    return (
      <section className="rounded-3xl border border-rose-200 bg-rose-50 p-5">
        <div className="text-sm font-black text-rose-800">Your roster-aware IDP research could not load.</div>
        <div className="mt-1 text-xs font-semibold leading-5 text-rose-700">{error}</div>
      </section>
    )
  }

  if (!payload || payload.status === 'AUTHENTICATED_NO_TEAM' || payload.status === 'SAVED_TEAM_NO_ROSTER') {
    return (
      <section className="rounded-3xl border border-blue-200 bg-blue-50 p-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="eyebrow">My IDP</p>
            <h2 className="mt-2 text-xl font-black text-slate-950">Save your roster first</h2>
            <p className="mt-2 text-sm leading-6 text-blue-950">
              Once your team is saved, Sports Zenith can match your IDP players to current usage research.
            </p>
          </div>
          <button type="button" onClick={onOpenMyTeams} className="shrink-0 rounded-2xl bg-slate-950 px-4 py-3 text-sm font-black text-white">
            Open My Teams
          </button>
        </div>
      </section>
    )
  }

  const league = payload.league || {}
  const slotAware = Boolean(payload.slot_aware)
  const slots = payload.idp_slots || {}
  const matched = Array.isArray(payload.matched_idp) ? payload.matched_idp : []
  const starters = Array.isArray(payload.starter_candidates) ? payload.starter_candidates : []
  const bench = Array.isArray(payload.bench_candidates) ? payload.bench_candidates : []
  const unavailable = Array.isArray(payload.unavailable_roster) ? payload.unavailable_roster : []
  const openSlots = Array.isArray(payload.open_slots) ? payload.open_slots : []
  const groups = Array.isArray(payload.group_summary) ? payload.group_summary : []
  const targets = Array.isArray(payload.outside_targets_to_check) ? payload.outside_targets_to_check : []
  const unmatched = Array.isArray(payload.unmatched_idp) ? payload.unmatched_idp : []

  return (
    <section className="rounded-[28px] border border-sky-200 bg-sky-50/40 p-5 md:p-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="eyebrow text-sky-700">My IDP</p>
            <span className="rounded-full bg-white px-3 py-1 text-[10px] font-black uppercase tracking-[0.1em] text-sky-700">Usage + snap research</span>
          </div>
          <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-950">
            {league.team_name || league.league_name || 'My Team'}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-sky-950">
            This uses current snap share, snap change, role and IDP usage research. It is not a fantasy-points projection and does not apply custom tackle/sack/turnover scoring.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[
            ['DL', slots.DL ?? slots.dl ?? 0],
            ['LB', slots.LB ?? slots.lb ?? 0],
            ['DB', slots.DB ?? slots.db ?? 0],
            ['IDP FLEX', slots.IDP_FLEX ?? slots.idp_flex ?? 0],
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl bg-white px-3 py-2 text-center">
              <div className="text-lg font-black text-slate-950">{value}</div>
              <div className="text-[9px] font-black uppercase tracking-[0.1em] text-slate-400">{label}</div>
            </div>
          ))}
        </div>
      </div>

      {!slotAware && (
        <div className="mt-4 flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-700" />
          <div className="text-xs font-semibold leading-5 text-amber-950">
            <span className="font-black">IDP starter slots are not saved yet.</span> Add DL/LB/DB/IDP FLEX counts in My Teams → League Settings to unlock slot-aware IDP starter candidates.
          </div>
        </div>
      )}

      <div className="mt-5">
        <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Saved IDP coverage</div>
        <div className="mt-2 grid gap-2 sm:grid-cols-3">
          {groups.map((group) => (
            <div key={group.idp_group} className="rounded-2xl border border-sky-100 bg-white p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-black text-slate-950">{group.idp_group}</div>
                <div className="text-sm font-black text-sky-700">{group.active_saved_count}/{group.saved_slot_count}</div>
              </div>
              <div className="mt-1 text-[10px] font-semibold text-slate-500">
                {group.saved_count} saved · best usage {group.best_saved_usage_score ?? '—'}
              </div>
              {group.slot_shortfall > 0 && (
                <div className="mt-2 text-[10px] font-black uppercase tracking-wide text-amber-700">
                  {group.slot_shortfall} slot shortfall
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {slotAware && (
        <div className="mt-5">
          <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Starter candidates by saved slots</div>
          <div className="mt-2 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {starters.map((row) => (
              <UsageCard
                key={[row.assigned_slot, row.slot_index, row.player_key || row.player].join('-')}
                row={row}
                slotLabel={row.assigned_slot + (row.slot_index > 1 ? ' ' + row.slot_index : '')}
              />
            ))}
          </div>
          {openSlots.length > 0 && (
            <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-3 text-xs font-semibold leading-5 text-amber-950">
              <span className="font-black">Open IDP research slots:</span> {openSlots.map((row) => row.slot + (row.slot_index > 1 ? ' ' + row.slot_index : '')).join(', ')}.
            </div>
          )}
        </div>
      )}

      {!slotAware && matched.length > 0 && (
        <div className="mt-5">
          <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Players on your saved roster</div>
          <div className="mt-2 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {matched.slice(0, 12).map((row) => <UsageCard key={row.player_key || row.player} row={row} />)}
          </div>
        </div>
      )}

      {bench.length > 0 && (
        <div className="mt-5">
          <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Bench / depth candidates</div>
          <div className="mt-2 flex gap-3 overflow-x-auto pb-1">
            {bench.map((row) => (
              <div key={row.player_key || row.player} className="min-w-[210px]">
                <UsageCard row={row} />
              </div>
            ))}
          </div>
        </div>
      )}

      {unavailable.length > 0 && (
        <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-4">
          <div className="text-[10px] font-black uppercase tracking-[0.12em] text-rose-700">Unavailable / injury-blocked roster IDP</div>
          <div className="mt-2 text-xs font-semibold leading-5 text-rose-800">
            {unavailable.map((row) => row.player + ' (' + humanize(row.availability_status) + ')').join(' · ')}
          </div>
        </div>
      )}

      <div className="mt-5">
        <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Outside IDP names to check</div>
        <div className="mt-2 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {targets.slice(0, 8).map((row) => (
            <div key={row.player_key || row.player} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[10px] font-black uppercase tracking-[0.12em] text-violet-700">
                    {row.idp_group} · {row.team || '—'}
                  </div>
                  <div className="mt-1 text-base font-black text-slate-950">{row.player}</div>
                </div>
                <span className={`rounded-full px-2 py-1 text-[9px] font-black uppercase tracking-wide ${scoreTone(row.idp_usage_tier)}`}>
                  {humanize(row.idp_usage_tier)}
                </span>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-center">
                <div className="rounded-lg bg-slate-50 p-2">
                  <div className="text-sm font-black text-slate-950">{row.idp_usage_score ?? '—'}</div>
                  <div className="text-[9px] font-bold text-slate-400">Usage</div>
                </div>
                <div className="rounded-lg bg-slate-50 p-2">
                  <div className="text-sm font-black text-slate-950">{row.snap_pct == null ? '—' : row.snap_pct + '%'}</div>
                  <div className="text-[9px] font-bold text-slate-400">Snaps</div>
                </div>
              </div>
              <div className="mt-2 text-[10px] font-semibold leading-4 text-slate-500">
                {humanize(row.target_reason)} · {humanize(row.role_signal || 'UNKNOWN ROLE')}
              </div>
              <div className="mt-2 text-[10px] font-semibold leading-4 text-slate-400">
                Check your league before acting. Sports Zenith has not verified this player is available.
              </div>
            </div>
          ))}
        </div>
      </div>

      {!!unmatched.length && (
        <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 text-xs font-semibold leading-5 text-slate-600">
          IDP roster names that need review: {unmatched.map((row) => row.input).join(' · ')}
        </div>
      )}

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="flex gap-3 rounded-2xl border border-amber-200 bg-white p-4">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-700" />
          <div className="text-xs font-semibold leading-5 text-slate-700">
            <span className="font-black">No IDP fantasy-point projection.</span> Current IDP intelligence is usage/snap/role research only until stat-based custom scoring is modeled.
          </div>
        </div>
        <div className="flex gap-3 rounded-2xl border border-blue-200 bg-white p-4">
          <ShieldCheck size={18} className="mt-0.5 shrink-0 text-blue-700" />
          <div className="text-xs font-semibold leading-5 text-slate-700">
            <span className="font-black">Availability is not verified.</span> Outside defenders are research names to check, not confirmed free agents in your league.
          </div>
        </div>
      </div>
    </section>
  )
}
