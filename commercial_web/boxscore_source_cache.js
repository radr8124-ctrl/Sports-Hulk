// Short-lived, in-process deduplication of official ESPN box score reads.
// Cached responses retain ORIGINAL provider fetch timestamp; no stale read is
// represented as a new live update. Nothing persists across service restarts.
export function createBoxscoreSourceCache(fetcher, options = {}) {
  if (typeof fetcher !== 'function') throw new TypeError('A trusted source reader is required')
  const now = typeof options.now === 'function' ? options.now : Date.now
  const limit = Number.isInteger(options.maxEntries) && options.maxEntries > 0
    ? Math.min(options.maxEntries, 500) : 150
  const ttlMs = {
    FINAL: 5 * 60 * 1000,
    LIVE: 45 * 1000,
    PREGAME: 2 * 60 * 1000,
    UNKNOWN: 30 * 1000,
  }
  const cache = new Map()
  const prune = () => {
    const time = now()
    for (const [key, value] of cache) {
      if (!value.pending && value.expiresAt <= time) cache.delete(key)
    }
    while (cache.size > limit) {
      const oldest = cache.keys().next().value
      if (oldest === undefined) break
      // Entries are disposable, but a pending request still completes for
      // callers even if evicted from the bounded cache.
      cache.delete(oldest)
    }
  }
  return {
    async get(league, eventId) {
      const sport = String(league || '').toUpperCase()
      const event = String(eventId || '')
      if (!['NBA','NHL','CFB','CBB'].includes(sport) || !/^\d{5,12}$/.test(event)) {
        throw Error('Unsupported official boxscore event')
      }
      const key = sport + ':' + event
      const prior = cache.get(key)
      if (prior?.pending) return prior.pending
      if (prior?.result && prior.expiresAt > now()) return prior.result
      cache.delete(key)
      const pending = Promise.resolve()
        .then(() => fetcher(sport,event))
        .then(result => {
          if (!result || result.status !== 'READY' || result.league !== sport ||
              result.event_id !== event || !Array.isArray(result.player_tables) ||
              !['FINAL','LIVE','PREGAME','UNKNOWN'].includes(result.official_game_state) ||
              !Number.isFinite(Date.parse(result.generated_at || ''))) {
            throw Error('Official boxscore source result was not verified')
          }
          if (cache.get(key)?.pending === pending) {
            cache.set(key,{result,expiresAt:now()+ttlMs[result.official_game_state]})
            prune()
          }
          return result
        })
        .catch(error => {
          if (cache.get(key)?.pending === pending) cache.delete(key)
          throw error
        })
      cache.set(key,{pending,expiresAt:0})
      prune()
      return pending
    },
    // Intentionally no raw cache data exposed; tests can inspect only count.
    size() { prune(); return cache.size },
  }
}
