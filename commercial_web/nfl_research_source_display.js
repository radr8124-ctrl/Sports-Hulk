// Explicit read-only NFL sportsbook quote references for the Bets page.
// These are NOT executable odds, selected main lines, or betting advice.
const KNOWN_MARKETS = ['MONEYLINE', 'SPREAD', 'TOTAL']
const VALID_SOURCE = 'SPORTWIZZARD_ARCHIVED_SAME_BOOK_TWO_SIDED_RESEARCH'
const millis = value => {
  const result = Date.parse(value || '')
  return Number.isFinite(result) ? result : null
}
const price = value => typeof value === 'number' && Number.isInteger(value) &&
  (value >= 100 || value <= -100)

export function sourceResearchForGame(payload, game, nowMs = Date.now()) {
  if (payload?.status !== 'RESEARCH_ONLY' ||
      payload?.original_source !== VALID_SOURCE ||
      payload?.book_prices_live_or_executable_verified !== false ||
      payload?.betting_decision_created !== false ||
      payload?.model_advantage_proven !== false ||
      !Number.isFinite(nowMs) || !Array.isArray(payload?.fixtures)) return null

  const gameTime = millis(game?.start_time)
  const eventId = String(game?.event_id || '')
  if (!gameTime || !eventId || gameTime <= nowMs ||
      game?.final === true || game?.state === 'post') return null

  const matches = payload.fixtures.filter(f => {
    const fixtureTime = millis(f.official_start)
    return String(f.official_espn_event_id || '') === eventId &&
      fixtureTime !== null && Math.abs(gameTime - fixtureTime) <= 3 * 60 * 1000 &&
      f.approved_play === false
  })
  if (matches.length !== 1) return null

  const found = matches[0]
  const research = {}
  const allowedMs = gameTime - nowMs <= 24 * 60 * 60 * 1000
    ? 6 * 60 * 60 * 1000 : 24 * 60 * 60 * 1000

  for (const market of KNOWN_MARKETS) {
    const quote = found?.markets?.[market]
    if (!quote || quote.market !== market ||
        quote.quote_type !== 'TWO_SIDED_ARCHIVED_RESEARCH_SNAPSHOT' ||
        quote.is_executable_current_offer !== false ||
        quote.is_verified_main_line !== false ||
        quote.is_approved_bet !== false ||
        quote.source_event_id !== found.source_event_id ||
        !quote.book) continue
    const updated = millis(quote.source_updated_at)
    const collected = millis(quote.source_captured_at)
    if (!updated || !collected || updated > collected || collected > nowMs ||
        nowMs - updated > allowedMs || nowMs - collected > allowedMs) continue

    const hasSides = market === 'TOTAL'
      ? Number.isFinite(quote.line) && price(quote.over_price) && price(quote.under_price)
      : market === 'SPREAD'
        ? Number.isFinite(quote.line) && Number.isFinite(quote.away_line) &&
          Number.isFinite(quote.home_line) &&
          Math.abs(quote.away_line + quote.home_line) < 0.001 &&
          price(quote.away_price) && price(quote.home_price)
        : quote.line == null && price(quote.away_price) && price(quote.home_price)
    if (hasSides) research[market] = quote
  }

  return Object.keys(research).length ? {
    official_espn_event_id: eventId,
    away: game.away_abbr || found.away,
    home: game.home_abbr || found.home,
    markets: research,
  } : null
}

export const american = value => {
  if (!price(value)) return '—'
  return value > 0 ? '+' + value : String(value)
}

export const signedLine = value => {
  if (!Number.isFinite(value)) return '—'
  return value > 0 ? '+' + value : String(value)
}

export function describeQuote(reference, market) {
  const q = reference?.markets?.[market]
  if (!q) return ''
  if (market === 'MONEYLINE') {
    return reference.away + ' ' + american(q.away_price) + ' · ' + reference.home + ' ' + american(q.home_price)
  }
  if (market === 'SPREAD') {
    return reference.away + ' ' + signedLine(q.away_line) + ' (' + american(q.away_price) + ') · ' +
      reference.home + ' ' + signedLine(q.home_line) + ' (' + american(q.home_price) + ')'
  }
  if (market === 'TOTAL') {
    return 'Over ' + q.line + ' (' + american(q.over_price) + ') · Under ' + q.line + ' (' + american(q.under_price) + ')'
  }
  return ''
}
