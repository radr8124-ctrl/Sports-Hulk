// Verified, research-only Survivor market shortlist.
// The model's personal recommendation is gated separately by original pool
// rules and primary odds freshness. This never makes an external pool pick.
import { sourceResearchForGame } from './nfl_research_source_display.js'

const normalize = x => String(x || '').toLowerCase().replace(/[^a-z0-9]/g, '')
const toDecimal = odds => Number.isFinite(odds) && Math.abs(odds) >= 100
  ? odds > 0 ? 100 / (100 + odds) : -odds / (100 - odds)
  : null

const clean = (x) => String(x || '').trim()
const resolvedRisk = value => [...new Set(clean(value).split('|').map(v => v.trim()).filter(v =>
  v && !v.includes('STALE_PRIMARY_MARKET') && !v.includes('PRIMARY_MARKET_PRICE_STALE') && v !== 'nan'
))].slice(0, 5)

const matchupMatches = (candidate, game) => {
  const teams = [normalize(candidate?.team), normalize(candidate?.opponent)].sort()
  const official = [normalize(game?.away), normalize(game?.home)].sort()
  return teams[0] === official[0] && teams[1] === official[1]
}

export function survivorSourceReview({
  scores = {}, references = {}, candidates = [], usedTeams = [], nowMs = Date.now(),
  poolWeek = null,
} = {}) {
  if (references?.status !== 'RESEARCH_ONLY' ||
      references?.book_prices_live_or_executable_verified !== false ||
      references?.model_advantage_proven !== false ||
      !Array.isArray(scores?.next_games) ||
      !Array.isArray(candidates) || !Number.isFinite(nowMs)) return []
  const burned = new Set((Array.isArray(usedTeams) ? usedTeams : []).map(normalize))
  const results = []
  const seen = new Set()
  for (const game of scores.next_games) {
    const id = clean(game?.event_id)
    if (!id || seen.has(id)) continue
    seen.add(id)
    const match = candidates.filter(candidate => matchupMatches(candidate, game))
    if (match.length !== 1) continue  // require this week's original research board
    const source = sourceResearchForGame(references, game, nowMs)
    if (!source?.markets?.MONEYLINE) continue
    const quote = source.markets.MONEYLINE
    const home = toDecimal(quote.home_price)
    const away = toDecimal(quote.away_price)
    if (home === null || away === null || !(home + away > 1 && home + away <= 1.16)) continue
    const both = [
      { team: clean(game.home), opponent: clean(game.away), pct: 100 * home / (home + away), side: 'HOME' },
      { team: clean(game.away), opponent: clean(game.home), pct: 100 * away / (home + away), side: 'AWAY' },
    ].filter(v => v.team && v.opponent && !burned.has(normalize(v.team)))
    if (!both.length) continue
    const chosen = both.sort((a,b)=>b.pct-a.pct)[0]
    // An already-burned favorite does not make its opponent a sensible
    // Survivor shortlist selection. Only source-backed outright favorites
    // belong in this comparison; an underdog is never silently promoted.
    if (chosen.pct <= 50) continue
    const contextual = normalize(match[0].team) === normalize(chosen.team) ? match[0] : null
    results.push({
      game_id: id,
      game_key: clean(references.fixtures.find(r => String(r.official_espn_event_id) === id)?.game_key),
      start: game.start_time,
      team: chosen.team,
      opponent: chosen.opponent,
      side: chosen.side,
      no_vig_market_pct: Math.round(chosen.pct * 10) / 10,
      sportsbook: quote.book,
      updated_at: quote.source_updated_at,
      captured_at: quote.source_captured_at,
      away_american_odds: quote.away_price,
      home_american_odds: quote.home_price,
      future_value_index: contextual?.future_value_index ?? null,
      future_value_label: contextual?.future_value_label || 'NOT_VERIFIED_FOR_TEAM',
      future_schedule: contextual?.future_schedule || '',
      risk_signals: contextual ? resolvedRisk(contextual.risk_signals) : [],
      is_verified_main_line: false,
      is_executable_current_offer: false,
      is_approved_survivor_pick: false,
      model_edge_proven: false,
      source_only: true,
      pool_week: poolWeek,
    })
  }
  return results.sort((a,b)=>b.no_vig_market_pct-a.no_vig_market_pct ||
    Date.parse(a.start)-Date.parse(b.start) || a.team.localeCompare(b.team))
}
