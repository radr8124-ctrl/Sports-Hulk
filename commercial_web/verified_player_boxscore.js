// ESPN team/player identity and game-state proof for Game Center box scores.
// Never make DNP or pregame roster rows look like recorded player statistics.
const SUPPORTED = new Set(['NBA', 'NHL', 'CFB', 'CBB'])
const code = value => String(value ?? '').trim()
const safe = (value, max=150) => code(value).slice(0, max)
const empty = (status, officialState='UNKNOWN') => ({
  official_game_state: officialState,
  player_source_status: status,
  player_stat_rows: 0,
  player_dnp_count: 0,
  player_rows_omitted: 0,
  player_tables: [],
})

export function verifiedEspnPlayerTables(payload, league, eventId) {
  const sport = code(league).toUpperCase()
  const event = code(eventId)
  if (!SUPPORTED.has(sport) || !/^\d{5,12}$/.test(event)) {
    throw Error('Unsupported official boxscore event')
  }
  const header = payload?.header
  if (code(header?.id) !== event || !Array.isArray(header?.competitions) ||
      header.competitions.length !== 1) {
    throw Error('Official ESPN event identity did not match')
  }
  const competition = header.competitions[0]
  const competitors = competition?.competitors
  if (!Array.isArray(competitors) || competitors.length !== 2) {
    throw Error('Official ESPN teams were not verified')
  }
  const teamIds = competitors.map(item => code(item?.team?.id))
  if (teamIds.some(id => !/^\d+$/.test(id)) || teamIds[0] === teamIds[1]) {
    throw Error('Official ESPN team identities conflict')
  }

  const status = competition?.status?.type
  const stage = status?.completed === true && status?.state === 'post'
    ? 'FINAL'
    : status?.completed !== true && status?.state === 'in'
      ? 'LIVE'
      : status?.completed !== true && status?.state === 'pre'
        ? 'PREGAME' : 'UNKNOWN'
  if (stage === 'UNKNOWN') return empty('GAME_STATE_UNVERIFIED')
  if (stage === 'PREGAME') return empty('PREGAME_NO_PLAYER_STATS', stage)

  const sides = payload?.boxscore?.players
  if (!Array.isArray(sides) || !sides.length) return empty('NO_VERIFIED_PLAYER_STATS', stage)
  if (sides.length > 2) throw Error('Conflicting official boxscore teams')
  const seenSides = new Set()
  for (const side of sides) {
    const teamId = code(side?.team?.id)
    if (!teamIds.includes(teamId) || seenSides.has(teamId)) {
      throw Error('Player boxscore is not tied to the official competitors')
    }
    seenSides.add(teamId)
  }

  let rows=0, omitted=0, dnp=0
  const tables=[]
  for (const side of sides) {
    const teamId = code(side.team.id)
    const official = competitors.find(item => code(item.team.id) === teamId)?.team || {}
    const team = safe(official.displayName || official.shortDisplayName || official.name)
    const abbreviation = safe(official.abbreviation, 12)
    const categories = Array.isArray(side.statistics) ? side.statistics : []
    if (categories.length > 30) throw Error('Too many boxscore stat groups')
    const groups=[]
    for (const category of categories) {
      const sourceLabels = category?.labels
      const sourceAthletes = category?.athletes
      if (!Array.isArray(sourceLabels) || sourceLabels.length < 1 ||
          sourceLabels.length > 26 || !sourceLabels.every(label =>
            typeof label === 'string' && label.trim().length > 0 && label.length <= 45)) {
        if (Array.isArray(sourceAthletes)) omitted += sourceAthletes.length
        continue
      }
      if (!Array.isArray(sourceAthletes) || !sourceAthletes.length) continue
      if (sourceAthletes.length > 170) throw Error('Too many player rows')
      const seenAthletes = new Set()
      const players=[]
      for (const athleteRow of sourceAthletes) {
        if (athleteRow?.didNotPlay === true) { dnp++; continue }
        const playerId = code(athleteRow?.athlete?.id)
        const name = safe(athleteRow?.athlete?.displayName)
        const stats = athleteRow?.stats
        if (!/^\d+$/.test(playerId) || !name || seenAthletes.has(playerId) ||
            !Array.isArray(stats) || stats.length !== sourceLabels.length ||
            stats.some(v => (typeof v !== 'string' && typeof v !== 'number') ||
              code(v).length > 35) ||
            stats.every(v => !code(v) || /^(?:-|--|—|na|n\/a)$/i.test(code(v)))) {
          omitted++
          continue
        }
        seenAthletes.add(playerId)
        players.push({
          id: playerId,
          name,
          position: safe(athleteRow.athlete?.position?.abbreviation, 9),
          starter: athleteRow.starter === true,
          stats: stats.map(v => safe(v, 35)),
        })
      }
      if (players.length) {
        const categoryName = safe(category?.displayName || category?.name ||
          (sport === 'NBA' || sport === 'CBB' ? 'Player stats' : 'Other stats'), 60)
        groups.push({
          category: categoryName.replace(/([a-z])([A-Z])/g, '$1 $2'),
          labels: sourceLabels.map(label => safe(label, 45)),
          players,
        })
        rows+=players.length
      }
    }
    if (groups.length) tables.push({team_id:teamId,team,abbreviation,groups})
  }
  if (rows > 300) throw Error('Too many official player statistics')
  return {
    official_game_state: stage,
    player_source_status: rows ? 'VERIFIED_PLAYER_STATS' : 'NO_VERIFIED_PLAYER_STATS',
    player_stat_rows: rows,
    player_dnp_count: dnp,
    player_rows_omitted: omitted,
    player_tables: tables,
  }
}
