// Anonymous history of previously used teams from the most recent official
// pool import. NEVER infer current-week pick popularity from older sheets.
export function parseCsv(text) {
  if (typeof text !== 'string' || text.length > 5_000_000) throw Error('CSV unavailable')
  const rows = []
  let cells = [], cell = '', quoted = false, closedQuote = false
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++ }
      else if (ch === '"') { quoted = false; closedQuote = true }
      else cell += ch
    } else if (ch === '"' && cell === '' && !closedQuote) {
      quoted = true
    } else if (ch === ',') {
      cells.push(cell); cells = [...cells]; cell = ''; closedQuote = false
    } else if (ch === '\n') {
      cells.push(cell)
      if (cells.some(value => value !== '')) rows.push(cells)
      cells = []; cell = ''; closedQuote = false
    } else if (ch === '\r') {
      // CRLF outside a quote is a field terminator, not part of the value.
    } else if (closedQuote || ch === '"') {
      throw Error('Malformed CSV quoting')
    } else cell += ch
  }
  if (quoted) throw Error('Unclosed CSV quote')
  if (cell || cells.length) {
    cells.push(cell)
    if (cells.some(value => value !== '')) rows.push(cells)
  }
  return rows
}

const unavailable = (status, sourceWeek = null) => ({
  status, source_week: sourceWeek, sample_size: null, teams: [],
})

export function survivorHistoricalAvailability({ csvText, meta, currentWeek, teamNames } = {}) {
  const sourceWeek = Number(meta?.max_week_in_file)
  const activeWeek = Number(currentWeek)
  if (!Number.isInteger(sourceWeek) || sourceWeek < 1 || sourceWeek > 25 ||
      !Number.isInteger(activeWeek) || activeWeek < 1 || activeWeek > 25 ||
      !/^[a-f0-9]{64}$/i.test(String(meta?.source_sha256 || '')) ||
      typeof meta?.source_filename !== 'string' || !meta.source_filename.trim()) {
    return unavailable('SOURCE_UNVERIFIED')
  }
  if (sourceWeek >= activeWeek) {
    return unavailable('PRIOR_WEEK_SNAPSHOT_REQUIRED', sourceWeek)
  }
  if (!Number.isInteger(Number(meta?.parsed_entries)) ||
      Number(meta.parsed_entries) < 1 || Number(meta.parsed_entries) > 20_000 ||
      !Array.isArray(teamNames) || teamNames.length > 40) {
    return unavailable('SOURCE_UNVERIFIED', sourceWeek)
  }

  try {
    const rows = parseCsv(csvText)
    const headers = rows.shift()
    const required = ['entry_name', 'status', 'used_teams', 'source_filename']
    if (!headers || headers.length < required.length ||
        new Set(headers).size !== headers.length ||
        !required.every(key => headers.includes(key)) ||
        rows.length !== Number(meta.parsed_entries)) {
      return unavailable('SOURCE_CONFLICT', sourceWeek)
    }
    const indices = Object.fromEntries(headers.map((name, index) => [name, index]))
    const usable = []
    let excluded = 0
    for (const columns of rows) {
      if (columns.length !== headers.length ||
          columns[indices.source_filename] !== meta.source_filename ||
          !String(columns[indices.entry_name] || '').trim()) {
        return unavailable('SOURCE_CONFLICT', sourceWeek)
      }
      const status = columns[indices.status]
      if (status === 'ELIMINATED') { excluded++; continue }
      if (status !== 'ACTIVE_OR_UNCONFIRMED') return unavailable('SOURCE_CONFLICT', sourceWeek)
      usable.push(new Set(String(columns[indices.used_teams] || '')
        .split('|').map(value => value.trim()).filter(Boolean)))
    }
    if (!usable.length) return unavailable('NO_ACTIVE_OR_UNCONFIRMED_ROWS', sourceWeek)
    const uniqueTeams = [...new Set(teamNames.filter(team =>
      typeof team === 'string' && team.trim().length >= 3 && team.trim().length <= 90))]
    const teams = uniqueTeams.map(team => {
      const usedCount = usable.filter(entry => entry.has(team)).length
      return {
        team,
        used_count: usedCount,
        not_previously_used_count: usable.length - usedCount,
        previously_used_share_pct: Math.round(1000 * usedCount / usable.length) / 10,
      }
    })
    return {
      status: 'HISTORICAL_PRIOR_WEEK_ONLY',
      source_week: sourceWeek,
      current_week: activeWeek,
      sample_size: usable.length,
      excluded_eliminated_rows: excluded,
      population: 'ENTRIES_MARKED_ACTIVE_OR_UNCONFIRMED_IN_IMPORTED_SHEET',
      provenance_sha256: meta.source_sha256,
      // No participant names, ticket IDs, or current-week picks leave the server.
      teams,
    }
  } catch {
    return unavailable('SOURCE_CONFLICT', sourceWeek)
  }
}
