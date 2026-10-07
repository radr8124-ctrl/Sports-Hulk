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

export function watchlistNewsHits(articles = [], preferences = {}, nowMs = Date.now()) {
  const favoriteTeams = Array.isArray(preferences.favorite_teams) ? preferences.favorite_teams : []
  const watchedPlayers = Array.isArray(preferences.watched_players) ? preferences.watched_players : []

  const teamNeedles = favoriteTeams.flatMap(team => {
    const full = normalized(team)
    const parts = full.split(/\s+/).filter(Boolean)
    const nickname = parts.length > 1 ? parts[parts.length - 1] : ''
    return [
      full ? { type: 'favorite_team', label: team, needle: full } : null,
      nickname.length >= 4 ? { type: 'favorite_team', label: team, needle: nickname } : null,
    ].filter(Boolean)
  })

  const playerNeedles = watchedPlayers
    .map(player => ({ type: 'watched_player', label: player, needle: normalized(player) }))
    .filter(item => item.needle)

  const needles = [...playerNeedles, ...teamNeedles]
  const seen = new Set()
  const hits = []

  for (const article of articles) {
    const title = String(article?.title || '')
    const haystack = normalized(title)
    const publishedAt = article?.published_at || article?.published_or_effective_at || null
    const publishedMs = Date.parse(publishedAt || '')
    if (Number.isFinite(publishedMs) && nowMs - publishedMs > 48 * 60 * 60 * 1000) continue

    const match = needles.find(item => haystack.includes(item.needle))
    if (!match) continue

    const key = `${title.toLowerCase()}|${String(article?.url || article?.source_url || '')}`
    if (seen.has(key)) continue
    seen.add(key)

    hits.push({
      type: match.type,
      matched_preference: match.label,
      title,
      source: article?.source || null,
      url: article?.url || article?.source_url || null,
      published_at: publishedAt,
    })
    if (hits.length >= 3) break
  }

  return hits
}

export function preferencePresentation(answer = {}, preferences = {}, watchlistHits = []) {
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
    watchlist_hits: Array.isArray(watchlistHits) ? watchlistHits.slice(0, 3) : [],
    presentation_only: true,
    model_adjustment: false,
  }
}
