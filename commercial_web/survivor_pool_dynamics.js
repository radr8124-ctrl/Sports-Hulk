function finiteNumber(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null
}

function weekCount(weekState = {}, week) {
  const start =
    finiteNumber(weekState?.[`pool_entries_start_week${week}`])
    ?? finiteNumber(weekState?.pool_entries_start)
    ?? finiteNumber(weekState?.pool_entries_total)
    ?? finiteNumber(weekState?.pool_entry_count)

  let lost =
    finiteNumber(weekState?.pool_lost_before_sunday)
    ?? finiteNumber(weekState?.pool_eliminated)
    ?? finiteNumber(weekState?.eliminated_entries)

  let alive =
    finiteNumber(weekState?.pool_alive_before_sunday)
    ?? finiteNumber(weekState?.pool_alive)
    ?? finiteNumber(weekState?.remaining_entries)

  if (start != null && lost == null && alive != null) lost = Math.max(0, start - alive)
  if (start != null && alive == null && lost != null) alive = Math.max(0, start - lost)

  if (start == null || alive == null || lost == null) return null

  return {
    week,
    start_entries: start,
    alive_entries: alive,
    lost_entries: lost,
    survival_pct: start > 0 ? Number(((alive / start) * 100).toFixed(1)) : null,
    eliminated_pct: start > 0 ? Number(((lost / start) * 100).toFixed(1)) : null,
  }
}

export function survivorPoolDynamics(poolState = {}) {
  const currentWeek = finiteNumber(poolState?.pool_current_week)
  const snapshots = []

  for (const [entryName, entry] of Object.entries(poolState?.entries || {})) {
    for (const [key, value] of Object.entries(entry || {})) {
      const match = /^week_(\d+)$/.exec(key)
      if (!match || !value || typeof value !== 'object') continue
      const week = Number(match[1])
      if (value.official_pool_sheet_confirmed !== true) continue
      const counts = weekCount(value, week)
      if (counts) snapshots.push({ entry_name: entryName, ...counts })
    }
  }

  if (!snapshots.length) {
    return {
      status: 'NO_VERIFIED_POOL_COUNTS',
      current_week: currentWeek,
      source_week: null,
      current: false,
      start_entries: null,
      alive_entries: null,
      lost_entries: null,
      survival_pct: null,
      eliminated_pct: null,
    }
  }

  const latestWeek = Math.max(...snapshots.map(row => row.week))
  const latest = snapshots.filter(row => row.week === latestWeek)
  const signatures = [...new Set(latest.map(row => [
    row.start_entries,
    row.alive_entries,
    row.lost_entries,
  ].join('|')))]

  if (signatures.length > 1) {
    return {
      status: 'POOL_COUNT_CONFLICT',
      current_week: currentWeek,
      source_week: latestWeek,
      current: false,
      start_entries: null,
      alive_entries: null,
      lost_entries: null,
      survival_pct: null,
      eliminated_pct: null,
      source_entry_count: latest.length,
    }
  }

  const source = latest[0]
  const current = currentWeek != null && latestWeek === currentWeek

  return {
    status: current ? 'CURRENT_VERIFIED' : 'HISTORICAL_VERIFIED',
    current_week: currentWeek,
    source_week: latestWeek,
    current,
    start_entries: source.start_entries,
    alive_entries: source.alive_entries,
    lost_entries: source.lost_entries,
    survival_pct: source.survival_pct,
    eliminated_pct: source.eliminated_pct,
    source_entry_count: latest.length,
  }
}
