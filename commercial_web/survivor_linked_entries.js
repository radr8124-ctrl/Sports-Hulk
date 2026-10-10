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
    const completed = Object.keys(entry)
      .map(key => /^week_(\d+)$/.exec(key))
      .filter(Boolean)
      .map(match => Number(match[1]))
      .filter(week => week < Number(survivorState?.pool_current_week || 0))
      .sort((a, b) => b - a)
      .find(week => {
        const past=entry[`week_${week}`]||{}
        const picks=Array.isArray(past.picks)?past.picks:[]
        const terminal=['WIN','LOSS','SURVIVED','LOST']
        // Never call an OPEN week completed because one pick was entered or
        // one leg of a multi-pick week finished while another is pending.
        return picks.length>0 && (
          ['WIN','LOSS'].includes(String(past.entry_result||'').toUpperCase()) ||
          picks.every(pick=>terminal.includes(String(pick?.result||'').toUpperCase()))
        )
      })
    const lastPicks = completed == null ? [] : entry[`week_${completed}`].picks
    return {
      entry_name: name,
      entry_status: entry.status || null,
      used_team_count: usedTeams.length,
      used_teams: usedTeams,
      current_picks: currentPicks,
      last_completed_week: completed ?? null,
      last_completed_picks: lastPicks.map(pick => ({
        team: String(pick.team || ''),
        result: ['WIN', 'SURVIVED'].includes(String(pick.result).toUpperCase()) ? 'SURVIVED' :
          ['LOSS', 'LOST'].includes(String(pick.result).toUpperCase()) ? 'LOST' : 'PENDING',
      })),
      current_week: Number(survivorState?.pool_current_week || entry.current_week || 0) || null,
    }
  })
}
