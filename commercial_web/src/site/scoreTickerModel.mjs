const LEAGUES = ['nfl', 'mlb', 'nba', 'nhl', 'cfb', 'cbb']
const validText = value => typeof value === 'string' || typeof value === 'number' ? String(value).trim() : ''

function gameStatus(game) {
  const raw = validText(game.status || game.state || game.status_type).toLowerCase()
  if (game.final || /final|completed|finished|postponed|cancelled/.test(raw)) return 'FINAL'
  if (game.live || /live|in progress|in_progress|halftime|intermission|period|quarter/.test(raw)) return 'LIVE'
  return 'UPCOMING'
}

export function buildScoreTickerItems(feeds = {}, limit = 24) {
  const rows = []
  for (const league of LEAGUES) {
    const feed = feeds?.[league]
    const games = league === 'mlb' && Array.isArray(feed?.today_games)
      ? feed.today_games
      : feed?.games
    if (!Array.isArray(games)) continue
    for (const game of games) {
      if (!game || typeof game !== 'object') continue
      const away = validText(game.away_abbr || game.away || game.away_team)
      const home = validText(game.home_abbr || game.home || game.home_team)
      if (!away || !home) continue
      const status = gameStatus(game)
      const awayScore = game.away_score ?? game.awayScore
      const homeScore = game.home_score ?? game.homeScore
      const hasScores = awayScore !== undefined && awayScore !== null && homeScore !== undefined && homeScore !== null
      rows.push({
        id: `${league}-${validText(game.event_id || game.gamePk || game.id || `${away}-${home}`)}`,
        league: league.toUpperCase(), away, home, status,
        score: status !== 'UPCOMING' && hasScores ? `${awayScore}–${homeScore}` : null,
        detail: validText(game.clock || game.period || game.start_time || game.time || game.date || ''),
      })
    }
  }
  const priority = { LIVE: 0, UPCOMING: 1, FINAL: 2 }
  return rows.sort((a, b) => priority[a.status] - priority[b.status]).slice(0, limit)
}
