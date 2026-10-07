export function normalizePreferenceList(value, limit = 20) {
  const source = Array.isArray(value) ? value : []
  const seen = new Set()
  const out = []
  for (const item of source) {
    const clean = String(item || '').trim().replace(/\s+/g, ' ').slice(0, 80)
    if (!clean) continue
    const key = clean.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    out.push(clean)
    if (out.length >= limit) break
  }
  return out
}

export function sanitizeAccountPreferences(value = {}) {
  const allowedSports = new Set(['NFL', 'MLB', 'NBA', 'NHL', 'CFB', 'CBB'])
  const sports = normalizePreferenceList(value.sports_followed, 6)
    .map(item => item.toUpperCase())
    .filter(item => allowedSports.has(item))

  const riskRaw = String(value.risk_preference || 'BALANCED')
    .toUpperCase()
    .replace(/[^A-Z_ -]/g, '')
    .trim()

  const risk = ['CONSERVATIVE', 'BALANCED', 'AGGRESSIVE'].includes(riskRaw)
    ? riskRaw
    : 'BALANCED'

  return {
    favorite_teams: normalizePreferenceList(value.favorite_teams, 20),
    sports_followed: [...new Set(sports)],
    watched_players: normalizePreferenceList(value.watched_players, 30),
    risk_preference: risk,
  }
}
