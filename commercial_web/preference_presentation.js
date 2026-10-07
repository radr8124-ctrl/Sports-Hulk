function normalized(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
}

function haystackForAnswer(answer = {}) {
  const pieces = [
    answer.take,
    ...(Array.isArray(answer.why) ? answer.why : []),
    ...(Array.isArray(answer.cards)
      ? answer.cards.flatMap(card => [
          card?.title,
          card?.selection,
          card?.team,
          card?.opponent,
          card?.away,
          card?.home,
          card?.player,
        ])
      : []),
  ]
  return normalized(pieces.filter(Boolean).join(' '))
}

export function preferencePresentation(answer = {}, preferences = {}) {
  const haystack = haystackForAnswer(answer)
  const favoriteTeams = Array.isArray(preferences.favorite_teams) ? preferences.favorite_teams : []
  const watchedPlayers = Array.isArray(preferences.watched_players) ? preferences.watched_players : []
  const sportsFollowed = Array.isArray(preferences.sports_followed) ? preferences.sports_followed : []
  const riskPreference = String(preferences.risk_preference || 'BALANCED').toUpperCase()

  const matchedTeams = favoriteTeams.filter(team => {
    const needle = normalized(team)
    return needle && haystack.includes(needle)
  }).slice(0, 3)

  const matchedPlayers = watchedPlayers.filter(player => {
    const needle = normalized(player)
    return needle && haystack.includes(needle)
  }).slice(0, 3)

  return {
    status: 'OPT_IN',
    favorite_teams: favoriteTeams,
    sports_followed: sportsFollowed,
    watched_players: watchedPlayers,
    risk_preference: riskPreference,
    matched_favorite_teams: matchedTeams,
    matched_watched_players: matchedPlayers,
    presentation_only: true,
    model_adjustment: false,
  }
}
