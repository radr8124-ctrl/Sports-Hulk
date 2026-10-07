export function buildLinkedSurvivorSummaries(linkedNames = [], survivorState = {}) {
  const unique = [...new Set((Array.isArray(linkedNames) ? linkedNames : [])
    .map(value => String(value || '').trim())
    .filter(Boolean))]

  return unique.map(name => {
    const entry = (survivorState?.entries || {})[name] || {}
    return {
      entry_name: name,
      entry_status: entry.status || null,
      used_team_count: Array.isArray(entry.used_teams) ? entry.used_teams.length : 0,
      current_week: Number(survivorState?.pool_current_week || entry.current_week || 0) || null,
    }
  })
}
