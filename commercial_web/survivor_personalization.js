import { resolveWeekPickRule } from './survivor_rules.js'
export function buildPersonalizedSurvivorSource(entryName, entry = {}, survivorState = {}, baseSource = {}) {
  const poolWeek = Number(
    survivorState?.pool_current_week
    || entry?.current_week
    || baseSource?.pool_current_week
    || 0
  ) || null

  const weekState = poolWeek ? entry?.[`week_${poolWeek}`] || {} : {}
  const usedTeams = Array.isArray(entry?.used_teams) ? entry.used_teams : []
  const resolved = resolveWeekPickRule(poolWeek, weekState)
  const ruleConfirmed = resolved.rule_confirmed
  const ruleStatus = resolved.rule_status
  const hasCurrentSheet = Boolean(resolved.official_pool_sheet_confirmed)

  return {
    ...(baseSource || {}),
    active_entry: entryName || null,
    active_entry_status: entry?.status || null,
    used_teams: usedTeams,
    pool_current_week: poolWeek,
    rule_confirmed: ruleConfirmed,
    rule_status: ruleStatus,
    required_picks: resolved.required_picks,
    rule_source: resolved.rule_source,
    recommendation_status: entry?.status === 'ELIMINATED'
      ? 'ENTRY_ELIMINATED'
      : ruleConfirmed ? 'PERSONALIZED_READY' : 'PERSONAL_CONTEXT_WAITING',
    ownership: {
      ...(baseSource?.ownership || {}),
      status: hasCurrentSheet ? 'LINKED_ENTRY_RULE_CONFIRMED' : (baseSource?.ownership?.status || 'WAITING_CURRENT_WEEK_OFFICIAL_SHEET'),
      official_pool_week: hasCurrentSheet ? poolWeek : (baseSource?.ownership?.official_pool_week ?? null),
    },
  }
}

// Authorized personal Ask is allowed to use the private model outcome for
// its one linked entry. Never join a generic user's page to another entry.
export function mergeGovernedSurvivorSource(personal = {}, governed = {}) {
 const sameEntry = Boolean(personal.active_entry && personal.active_entry === governed?.active_entry)
 const sameWeek = Number(personal.pool_current_week) === Number(governed?.pool_current_week)
   && Number(governed?.active_entry_week) === Number(personal.pool_current_week)
 const matchingRule = personal.rule_confirmed && governed?.rule_confirmed
   && Number(personal.required_picks) === Number(governed?.required_picks)
 const alive = String(personal.active_entry_status || '').toUpperCase() === 'ALIVE'
 if (!(sameEntry && sameWeek && matchingRule && alive)) return personal
 return {
   ...personal,
   generated_at: governed.generated_at || personal.generated_at,
   recommendation_status: governed.recommendation_status || personal.recommendation_status,
   shadow_recommendation: governed.shadow_recommendation || [],
   candidates: Array.isArray(governed.candidates) ? governed.candidates : personal.candidates,
   ownership: { ...(personal.ownership || {}), ...(governed.ownership || {}) },
 }
}
