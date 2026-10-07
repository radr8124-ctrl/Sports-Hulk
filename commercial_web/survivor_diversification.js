import { survivorGameKey } from './survivor_concentration.js'

function num(value, fallback = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

export function diversifySurvivorEntries(entries = [], candidates = [], poolWeek = null) {
  const ranked = [...(Array.isArray(candidates) ? candidates : [])]
    .filter(row => row?.team)
    .sort((a, b) => num(b.strategy_index) - num(a.strategy_index))

  const assignedTeams = new Set()
  const assignedGames = new Set()
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
    const independent = eligible.find(row => {
      const key = survivorGameKey(row.team, row.opponent)
      return !assignedTeams.has(row.team) && (!key || !assignedGames.has(key))
    })
    const uniqueTeam = eligible.find(row => !assignedTeams.has(row.team))
    const selected = independent || uniqueTeam || eligible[0] || null

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

    const selectedGameKey = survivorGameKey(selected.team, selected.opponent)
    const sameGameAcrossEntries = Boolean(selectedGameKey && assignedGames.has(selectedGameKey))
    const reusedTeamAcrossEntries = assignedTeams.has(selected.team)
    assignedTeams.add(selected.team)
    if (selectedGameKey) assignedGames.add(selectedGameKey)
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
      reused_team_across_entries: reusedTeamAcrossEntries,
      same_game_across_entries: sameGameAcrossEntries,
    })
  }

  return allocations
}
