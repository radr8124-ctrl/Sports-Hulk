// Source-grounded Best Bets UI: market tabs are navigation, NOT betting signals.
export const BET_SPORT_FILTERS = Object.freeze(['NFL', 'CFB', 'NBA', 'NHL', 'MLB', 'CBB'])
export const BET_MARKET_FILTERS = Object.freeze([
  { id: 'ALL', label: 'All markets' },
  { id: 'MONEYLINE', label: 'Moneyline' },
  { id: 'SPREAD', label: 'Point spreads' },
  { id: 'TOTAL', label: 'Totals' },
])

export function sourceMarketStatus({ sport = 'ALL', market = 'ALL', picks = [], byProofLane = {}, marketBoard = [] } = {}) {
  const allowedMarkets = market === 'ALL' ? ['MONEYLINE','SPREAD','TOTAL'] : [market]
  const allowedSports = sport === 'ALL' ? BET_SPORT_FILTERS : [sport]
  const verified = (Array.isArray(picks) ? picks : []).filter(p =>
    (sport === 'ALL' || p.sport === sport) && (market === 'ALL' || p.market === market))
  const shadow = verified.filter(p => p.shadow_decision === 'SHADOW_PLAY')
  const allCurrent = verified.length

  const rows = allowedSports.flatMap(s => allowedMarkets.map(m => {
    const key = `${s}_${m}`
    const variants = Object.entries(byProofLane || {})
      .filter(([id, item]) => id === key || id.startsWith(key + '|'))
      .map(([id, item]) => ({ ...item, proof_lane_key: id }))
    const historyCount = variants.reduce((n, x) => Math.max(n, Number(x.history_n) || 0), 0)
    const independent = variants.reduce((n, x) => Math.max(n, Number(x.independent_blocks) || 0), 0)
    const candidates = verified.filter(p => p.sport === s && p.market === m)
    const playable = candidates.filter(p => p.shadow_decision === 'SHADOW_PLAY')
    return {
      sport: s, market: m, historyCount, independent, countedOriginalObservations: variants.length > 0,
      candidateCount: candidates.length, approvedPlayCount: playable.length,
      testedEdgeProven: Boolean(playable.length),
      historicalOnly: !playable.length && historyCount > 0,
      noVerifiedCurrentSelection: playable.length === 0,
    }
  }))

  // These are a separate, upstream MONEYLINE-only board. They must not be
  // called spread candidates or promoted to live sportsbook prices.
  const nflMoneylineStale = (Array.isArray(marketBoard) ? marketBoard : [])
    .filter(item => item.sport === 'NFL' && item.decision_current === 'PASS_STALE_MARKET')
  const nflMarketRows = marketBoard.filter?.(item => item.sport === 'NFL') || []
  return {
    filterSport: sport, filterMarket: market, candidateCount: allCurrent,
    approvedPlayCount: shadow.length, researchCount: allCurrent - shadow.length,
    nflStaleUpstreamMoneylineCount: nflMoneylineStale.length,
    nflUpstreamMoneylineCount: nflMarketRows.length,
    categories: rows,
    requiredIndependentGames: 25,
    researchNotApproved: shadow.length === 0,
  }
}

export function nflUpcomingSchedule(source = {}, atMs = Date.now(), limit = 6) {
  const raw = Array.isArray(source.next_games) ? source.next_games : []
  const seen = new Set()
  return raw.filter(game => {
    const id = String(game?.event_id || '')
    const time = Date.parse(game?.start_time || '')
    if (!id || seen.has(id) || !Number.isFinite(time) || time < atMs ||
      game.final === true || game.state === 'post') return false
    seen.add(id)
    return true
  }).sort((a,b) => Date.parse(a.start_time) - Date.parse(b.start_time))
    .slice(0,Math.max(0,Math.min(15,Number(limit)||0)))
}
