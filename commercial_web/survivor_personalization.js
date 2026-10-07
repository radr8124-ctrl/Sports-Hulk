export function buildPersonalizedSurvivorSource(entryName, entry = {}, survivorState = {}, baseSource = {}) {
  const poolWeek = Number(
    survivorState?.pool_current_week
    || entry?.current_week
    || baseSource?.pool_current_week
    || 0
  ) || null

  const weekState = poolWeek ? entry?.[`week_${poolWeek}`] || {} : {}
  const usedTeams = Array.isArray(entry?.used_teams) ? entry.used_teams : []
  const ruleConfirmed = Boolean(weekState?.official_pool_sheet_confirmed)
  const ruleStatus = weekState?.rule_status
    || (ruleConfirmed ? 'CONFIRMED_FROM_LINKED_ENTRY' : 'AWAITING_OFFICIAL_POOL_SHEET')

  return {
    ...(baseSource || {}),
    active_entry: entryName || null,
    active_entry_status: entry?.status || null,
    used_teams: usedTeams,
    pool_current_week: poolWeek,
    rule_confirmed: ruleConfirmed,
    rule_status: ruleStatus,
    recommendation_status: entry?.status === 'ELIMINATED'
      ? 'ENTRY_ELIMINATED'
      : ruleConfirmed ? 'PERSONALIZED_READY' : 'PERSONAL_CONTEXT_WAITING',
    ownership: {
      ...(baseSource?.ownership || {}),
      status: ruleConfirmed ? 'LINKED_ENTRY_RULE_CONFIRMED' : 'LINKED_ENTRY_WAITING_FOR_RULE',
      official_pool_week: ruleConfirmed ? poolWeek : null,
    },
  }
}
