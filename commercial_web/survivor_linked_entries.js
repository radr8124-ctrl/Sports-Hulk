export function selectLinkedSurvivorEntry(linkedNames = [], requestedEntry = '') {
  const unique = [...new Set((Array.isArray(linkedNames) ? linkedNames : [])
    .map(value => String(value || '').trim())
    .filter(Boolean))]
  const requested = String(requestedEntry || '').trim()
  return requested && unique.includes(requested) ? requested : (unique[0] || null)
}

export function buildLinkedSurvivorSummaries(linkedNames = [], survivorState = {}) {
  const unique = [...new Set((Array.isArray(linkedNames) ? linkedNames : [])
    .map(value => String(value || '').trim())
    .filter(Boolean))]

  return unique.map(name => {
    const entry = (survivorState?.entries || {})[name] || {}
    const usedTeams = Array.isArray(entry.used_teams) ? entry.used_teams : []
    const currentPicks = Array.isArray(entry.current_picks) ? entry.current_picks : []
    return {
      entry_name: name,
      entry_status: entry.status || null,
      used_team_count: usedTeams.length,
      used_teams: usedTeams,
      current_picks: currentPicks,
      current_week: Number(survivorState?.pool_current_week || entry.current_week || 0) || null,
    }
  })
}
