function gameKey(team, opponent) {
  const sides = [String(team || '').trim(), String(opponent || '').trim()].filter(Boolean).sort()
  return sides.length === 2 ? sides.join('::') : null
}

export function survivorConcentrationAudit(allocations = []) {
  const actionable = (Array.isArray(allocations) ? allocations : []).filter(row => row?.team)
  if (actionable.length <= 1) {
    return {
      status: 'CLEAR',
      actionable_entries: actionable.length,
      unique_teams: actionable.length,
      duplicate_team_count: 0,
      same_game_collision_count: 0,
      max_team_exposure_pct: actionable.length ? 100 : 0,
    }
  }

  const teamCounts = new Map()
  const gameCounts = new Map()

  for (const row of actionable) {
    teamCounts.set(row.team, (teamCounts.get(row.team) || 0) + 1)
    const key = gameKey(row.team, row.opponent)
    if (key) gameCounts.set(key, (gameCounts.get(key) || 0) + 1)
  }

  const duplicateTeamCount = [...teamCounts.values()].filter(count => count > 1).length
  const sameGameCollisionCount = [...gameCounts.values()].filter(count => count > 1).length
  const maxTeamCount = Math.max(...teamCounts.values())
  const maxTeamExposurePct = Number(((maxTeamCount / actionable.length) * 100).toFixed(1))

  const status = duplicateTeamCount > 0 || sameGameCollisionCount > 0
    ? 'HIGH'
    : maxTeamExposurePct > 50
      ? 'ELEVATED'
      : 'CLEAR'

  return {
    status,
    actionable_entries: actionable.length,
    unique_teams: teamCounts.size,
    duplicate_team_count: duplicateTeamCount,
    same_game_collision_count: sameGameCollisionCount,
    max_team_exposure_pct: maxTeamExposurePct,
  }
}

export function survivorGameKey(team, opponent) {
  return gameKey(team, opponent)
}
