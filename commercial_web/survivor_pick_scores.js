// Private Survivor game cards. This reads an already authorized linked entry.
// Research scoreboards cannot mark a real pool submission or grade a pick.
const FINALS = new Set(['WIN', 'LOSS', 'SURVIVED', 'LOST'])
const firstNumber = value => {
  if (value === null || value === undefined || value === '') return null
  const n = Number(value)
  return Number.isInteger(n) && n >= 0 ? n : null
}
const cleanTeam = team => String(team || '').trim()

function matchingScore(team, feed, at) {
  const games = [...(Array.isArray(feed?.games) ? feed.games : []),
    ...(Array.isArray(feed?.next_games) ? feed.next_games : [])]
  return games.find(game => {
    if (team !== cleanTeam(game?.away) && team !== cleanTeam(game?.home)) return false
    const start = Date.parse(String(game?.start_time || ''))
    // Don't accidentally attach a previous/next week's match to the current
    // saved entry. The live current scoreboard is not a historical schedule.
    return Number.isFinite(start) && Math.abs(start - at) <= 8 * 24 * 3600 * 1000
  }) || null
}

function scoredGameCard(team, game) {
  if (!game) return { state: 'SCORE_WAITING', score_line: null, clock: null, opponent: null }
  const isAway = cleanTeam(game.away) === team
  const opponent = isAway ? cleanTeam(game.home) : cleanTeam(game.away)
  const awayScore = firstNumber(game.away_score)
  const homeScore = firstNumber(game.home_score)
  const isLive = Boolean(game.live || String(game.state || '').toLowerCase() === 'in')
  const isFinal = Boolean(game.final || String(game.state || '').toLowerCase() === 'post')
  const clock = String(game.status || '').slice(0, 100) || null
  let state = isFinal ? 'FINAL_UNSETTLED_POOL' : isLive ? 'LIVE' : 'UPCOMING'
  if (isLive && awayScore !== null && homeScore !== null) {
    const us = isAway ? awayScore : homeScore
    const them = isAway ? homeScore : awayScore
    state = us === them ? 'LIVE_TIED' : us > them ? 'LIVE_AHEAD' : 'LIVE_BEHIND'
  }
  return {
    state,
    score_line: awayScore === null || homeScore === null
      ? null : `${game.away} ${awayScore} – ${game.home} ${homeScore}`,
    clock,
    opponent,
  }
}

export function survivorPersonalScoreCards(entry, poolWeek, nflScores, { at = Date.now(), maxWeeks = 2 } = {}) {
  if (!entry || typeof entry !== 'object' || !Number.isInteger(poolWeek) || poolWeek < 1) return []
  const weeks = []
  for (let week = poolWeek; week > 0; week--) {
    const weekState = entry[`week_${week}`]
    let picks = Array.isArray(weekState?.picks) ? weekState.picks.filter(v => v && typeof v === 'object') : []
    if (!picks.length && week === poolWeek && Number(entry.current_week) === poolWeek) {
      picks = (Array.isArray(entry.current_picks) ? entry.current_picks : [])
        .map(team => ({ team, result: 'PENDING' }))
    }
    if (!picks.length) continue
    weeks.push({ week, picks, submitted: weekState?.submitted === true })
    if (weeks.length >= Math.min(Math.max(maxWeeks, 1), 4)) break
  }
  const cards = []
  for (const { week, picks, submitted } of weeks) {
    for (const [index, pick] of picks.entries()) {
      const team = cleanTeam(pick.team)
      if (!team) continue
      const result = String(pick.result || 'PENDING').trim().toUpperCase()
      const settled = FINALS.has(result)
      const scoreGame = week === poolWeek && !settled ? matchingScore(team, nflScores, at) : null
      const score = scoredGameCard(team, scoreGame)
      const savedStatus = String(pick.game_status || '').trim()
      cards.push({
        week,
        pick_number: index + 1,
        team,
        pool_result: settled ? ['WIN', 'SURVIVED'].includes(result) ? 'SURVIVED' : 'LOST' : 'PENDING',
        game_state: settled ? 'FINAL_SAVED_RESULT' : score.state,
        score_line: settled
          ? savedStatus.startsWith('FINAL:') ? savedStatus.slice(6).trim() : null
          : score.score_line,
        game_clock: settled ? 'FINAL' : score.clock,
        opponent: score.opponent,
        source: settled ? 'SAVED_ENTRY_GRADE' : scoreGame ? 'CURRENT_ESPN_SCORE_FEED' : 'ENTRY_PENDING',
        pool_submitted: week === poolWeek && submitted,
      })
    }
  }
  return cards.slice(0, 12)
}
