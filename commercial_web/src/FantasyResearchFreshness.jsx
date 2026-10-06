function statusMeta(status) {
  const value = String(status || 'UNKNOWN').toUpperCase()
  if (value === 'FRESH') {
    return {
      label: 'Research current',
      badge: 'bg-emerald-50 text-emerald-700',
      panel: 'border-emerald-200 bg-emerald-50/60 text-emerald-950',
    }
  }
  if (value === 'AGING') {
    return {
      label: 'Research aging',
      badge: 'bg-amber-50 text-amber-700',
      panel: 'border-amber-200 bg-amber-50/70 text-amber-950',
    }
  }
  if (value === 'STALE') {
    return {
      label: 'Research stale',
      badge: 'bg-rose-50 text-rose-700',
      panel: 'border-rose-200 bg-rose-50/70 text-rose-950',
    }
  }
  if (value === 'MISSING') {
    return {
      label: 'Research source missing',
      badge: 'bg-rose-50 text-rose-700',
      panel: 'border-rose-200 bg-rose-50/70 text-rose-950',
    }
  }
  return {
    label: 'Freshness unknown',
    badge: 'bg-slate-100 text-slate-600',
    panel: 'border-slate-200 bg-slate-50 text-slate-700',
  }
}

function ageLabel(minutes) {
  const value = Number(minutes)
  if (!Number.isFinite(value)) return 'age unavailable'
  if (value < 1) return 'less than 1 min old'
  if (value < 60) return `${Math.round(value)} min old`
  const hours = value / 60
  if (hours < 24) return `${hours.toFixed(hours < 10 ? 1 : 0)} hr old`
  const days = hours / 24
  return `${days.toFixed(days < 10 ? 1 : 0)} days old`
}

function formatTimestamp(value) {
  if (!value) return null
  try {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return null
    return date.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  } catch {
    return null
  }
}

export default function FantasyResearchFreshness({ freshness }) {
  if (!freshness || typeof freshness !== 'object') return null

  const meta = statusMeta(freshness.status)
  const sourceTime = formatTimestamp(freshness.source_timestamp)
  const maxAge = Number(freshness.max_age_minutes)
  const rowCount = Number(freshness.row_count)
  const rosterNewer = freshness.roster_newer_than_research === true
  const rosterAhead = Number(freshness.roster_ahead_minutes)
  const rowState = String(freshness.row_state || 'UNKNOWN').toUpperCase()
  const sourceEmpty = Number.isFinite(rowCount) && rowCount === 0

  return (
    <div className={`mt-4 rounded-2xl border px-4 py-3 ${meta.panel}`}>
      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full px-2.5 py-1 text-[9px] font-black uppercase tracking-[0.1em] ${meta.badge}`}>
            {meta.label}
          </span>
          <span className="text-[11px] font-bold">
            {freshness.source_available === false
              ? 'Source file unavailable'
              : ageLabel(freshness.age_minutes)}
          </span>
          {Number.isFinite(maxAge) && (
            <span className="text-[10px] font-semibold opacity-70">target ≤ {maxAge} min</span>
          )}
        </div>
        <div className="text-[10px] font-semibold opacity-70">
          {sourceTime ? `Snapshot ${sourceTime}` : 'Snapshot time unavailable'}
          {Number.isFinite(rowCount) ? ` · ${rowCount.toLocaleString()} rows` : ''}
        </div>
      </div>

      {rosterNewer && (
        <div className="mt-2 text-[11px] font-black leading-5 text-amber-800">
          Your saved roster is newer than this research snapshot{Number.isFinite(rosterAhead) && rosterAhead > 0 ? ` by about ${Math.max(1, Math.round(rosterAhead))} min` : ''}. Recent roster changes may not be reflected yet.
        </div>
      )}

      {(sourceEmpty || (rowState !== 'HAS_ROWS' && rowState !== 'UNKNOWN')) && (
        <div className="mt-2 text-[10px] font-semibold leading-4">
          Source state: {rowState.replaceAll('_', ' ')}. Sports Zenith will not treat an empty source as a normal recommendation set.
        </div>
      )}
    </div>
  )
}
