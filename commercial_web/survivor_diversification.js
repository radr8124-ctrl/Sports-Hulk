function num(value, fallback = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

export function diversifySurvivorEntries(entries = [], candidates = [], poolWeek = null) {
  const ranked = [...(Array.isArray(candidates) ? candidates : [])]
    .filter(row => row?.team)
    .sort((a, b) => num(b.strategy_index) - num(a.strategy_index))

  const assignedTeams = new Set()
  const allocations = []

  for (const item of Array.isArray(entries) ? entries : []) {
    const entryName = String(item?.entry_name || '').trim()
    const entry = item?.entry || {}
    const status = String(entry?.status || '').toUpperCase()
    const used = new Set(Array.isArray(entry?.used_teams) ? entry.used_teams : [])
    const weekState = poolWeek ? entry?.[`week_${poolWeek}`] || {} : {}
    const ruleConfirmed = Boolean(weekState?.official_pool_sheet_confirmed)

    if (!entryName) continue

    if (status === 'ELIMINATED') {
      allocations.push({
        entry_name: entryName,
        entry_status: 'ELIMINATED',
        status: 'ENTRY_ELIMINATED',
        team: null,
        reason: 'Entry eliminated.',
      })
      continue
    }

    if (!ruleConfirmed) {
      allocations.push({
        entry_name: entryName,
        entry_status: status || null,
        status: weekState?.rule_status || 'AWAITING_OFFICIAL_POOL_SHEET',
        team: null,
        reason: 'Current pool rule not confirmed.',
      })
      continue
    }

    const eligible = ranked.filter(row => !used.has(row.team))
    const unique = eligible.find(row => !assignedTeams.has(row.team))
    const selected = unique || eligible[0] || null

    if (!selected) {
      allocations.push({
        entry_name: entryName,
        entry_status: status || null,
        status: 'WAITING',
        team: null,
        reason: 'No eligible governed candidate.',
      })
      continue
    }

    assignedTeams.add(selected.team)
    allocations.push({
      entry_name: entryName,
      entry_status: status || null,
      status: 'DIVERSIFIED_RESEARCH',
      team: selected.team,
      opponent: selected.opponent || null,
      market_prob_pct: selected.market_prob_pct ?? null,
      strategy_index: selected.strategy_index ?? null,
      decision_tier: selected.decision_tier || null,
      future_value_label: selected.future_value_label || null,
      risk_signals: selected.risk_signals || null,
      reused_team_across_entries: !unique && assignedTeams.has(selected.team),
    })
  }

  return allocations
}
