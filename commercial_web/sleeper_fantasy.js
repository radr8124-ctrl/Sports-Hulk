// Sleeper public NFL fantasy import. The public API does not authenticate
// ownership and is read-only. Never label this an OAuth/login connection.
import { resilientFetch } from './resilient_fetch.js'

const API_ROOT = 'https://api.sleeper.app/v1'
const LEAGUE_ID = /^\d{1,24}$/
const USERNAME = /^[a-zA-Z0-9_.-]{2,40}$/
const ABBR = {
  ARI: 'Arizona Cardinals', ATL: 'Atlanta Falcons', BAL: 'Baltimore Ravens',
  BUF: 'Buffalo Bills', CAR: 'Carolina Panthers', CHI: 'Chicago Bears',
  CIN: 'Cincinnati Bengals', CLE: 'Cleveland Browns', DAL: 'Dallas Cowboys',
  DEN: 'Denver Broncos', DET: 'Detroit Lions', GB: 'Green Bay Packers',
  HOU: 'Houston Texans', IND: 'Indianapolis Colts', JAX: 'Jacksonville Jaguars',
  KC: 'Kansas City Chiefs', LV: 'Las Vegas Raiders', LAC: 'Los Angeles Chargers',
  LAR: 'Los Angeles Rams', MIA: 'Miami Dolphins', MIN: 'Minnesota Vikings',
  NE: 'New England Patriots', NO: 'New Orleans Saints', NYG: 'New York Giants',
  NYJ: 'New York Jets', PHI: 'Philadelphia Eagles', PIT: 'Pittsburgh Steelers',
  SF: 'San Francisco 49ers', SEA: 'Seattle Seahawks', TB: 'Tampa Bay Buccaneers',
  TEN: 'Tennessee Titans', WAS: 'Washington Commanders',
}
const nowSeason = () => new Date().getUTCFullYear()
let playersCache = { expires: 0, mapping: null }

export const fantasyProviderStatus = Object.freeze([
  { id: 'sleeper', label: 'Sleeper', status: 'PUBLIC_READ_ONLY',
    note: 'Connect a public NFL roster by username. No Sleeper password or authorization is collected.',
    external_url: 'https://sleeper.com/' },
  { id: 'yahoo', label: 'Yahoo Fantasy', status: 'OAUTH_NOT_CONFIGURED',
    note: 'Yahoo requires an approved Fantasy API integration and OAuth authorization. Automatic connection is not active.',
    external_url: 'https://football.fantasysports.yahoo.com/' },
  { id: 'espn', label: 'ESPN Fantasy', status: 'PRIVATE_SIGN_IN_NOT_CONFIGURED',
    note: 'ESPN account sign-in is separate. Private league linking is not active in Sports Zenith.',
    external_url: 'https://fantasy.espn.com/' },
])

function inputError(message) {
  const err = new Error(message)
  err.code = 'INVALID_INPUT'
  return err
}

export function validateSleeperUsername(username) {
  if (typeof username !== 'string' || !USERNAME.test(username.trim())) {
    throw inputError('Enter a valid Sleeper username (2–40 letters, numbers, dot, hyphen or underscore).')
  }
  return username.trim()
}

export function validateSleeperLeagueId(value) {
  const id = String(value ?? '').trim()
  if (!LEAGUE_ID.test(id)) throw inputError('Choose a valid Sleeper league.')
  return id
}

function validSeason(value) {
  const season = Number(value ?? nowSeason())
  if (!Number.isInteger(season) || season < 2018 || season > nowSeason() + 1) {
    throw inputError('Choose a supported Sleeper season.')
  }
  return season
}

async function apiGet(path, fetchImpl = globalThis.fetch, {timeoutMs = 10000} = {}) {
  const response = await resilientFetch(API_ROOT + path, {
    headers: { accept: 'application/json', 'user-agent': 'SportsZenith/1.0' },
  }, {fetchImpl, timeoutMs, retries: 1, retryDelayMs: 150, breakerKey: 'sleeper-public-api'})
  if (!response.ok) {
    const err = new Error(response.status === 404 ? 'Sleeper account or league not found.' : 'Sleeper is temporarily unavailable.')
    err.code = 'SLEEPER_UPSTREAM_ERROR'
    throw err
  }
  return response.json()
}

export async function lookupSleeperLeagues(username, {season, fetchImpl = globalThis.fetch} = {}) {
  const cleanName = validateSleeperUsername(username)
  const year = validSeason(season)
  const user = await apiGet('/user/' + encodeURIComponent(cleanName), fetchImpl)
  if (!user || !LEAGUE_ID.test(String(user.user_id || ''))) {
    const err = new Error('Sleeper username not found. Verify the exact username.')
    err.code = 'SLEEPER_USER_NOT_FOUND'
    throw err
  }
  const leagues = await apiGet('/user/' + user.user_id + '/leagues/nfl/' + year, fetchImpl)
  if (!Array.isArray(leagues)) {
    throw new Error('Sleeper returned an invalid leagues response.')
  }
  return {
    status: 'READY',
    access: 'SLEEPER_PUBLIC_READ_ONLY_NO_IDENTITY_VERIFICATION',
    user: { user_id: String(user.user_id), username: String(user.username || cleanName).slice(0,80) },
    season: year,
    leagues: leagues.filter(item => item && LEAGUE_ID.test(String(item.league_id || ''))).slice(0,50)
      .map(item => ({
        league_id: String(item.league_id),
        name: String(item.name || 'Sleeper league').slice(0,120),
        season: Number(item.season) || year,
        status: String(item.status || 'unknown').slice(0,30),
        team_count: Number(item.total_rosters) || 0,
      })),
  }
}

export function mapSleeperScoring(league) {
  const rec = Number(league?.scoring_settings?.rec)
  const preset = Number.isFinite(rec)
    ? rec >= .9 ? 'ppr' : rec >= .4 ? 'half_ppr' : 'standard'
    : null
  const slots = {qb:0,rb:0,wr:0,te:0,flex:0,superflex:0,dst:0,k:0,dl:0,lb:0,db:0,idp_flex:0}
  let bench = 0, ir = 0
  const mapping = {QB:'qb',RB:'rb',WR:'wr',TE:'te',FLEX:'flex',SUPER_FLEX:'superflex',DEF:'dst',K:'k',DL:'dl',LB:'lb',DB:'db',IDP_FLEX:'idp_flex'}
  for (const name of Array.isArray(league?.roster_positions) ? league.roster_positions : []) {
    const slot = mapping[String(name)]
    if (slot) slots[slot]++
    else if (name === 'BN') bench++
    else if (name === 'IR') ir++
  }
  return {
    scoring: {preset, reception_points: Number.isFinite(rec) ? rec : null, source:'SLEEPER_PUBLIC_API'},
    roster_settings: {starting_slots:slots, bench_slots:bench, ir_slots:ir,
      source:'SLEEPER_PUBLIC_API'},
  }
}

export function resolveSleeperRoster(roster, directory) {
  const playerIds = Array.isArray(roster?.players) ? roster.players.map(String).filter(id => id && id !== '0') : []
  const startingIds = new Set((Array.isArray(roster?.starters) ? roster.starters : []).map(String))
  const player = id => {
    if (ABBR[id]) return ABBR[id] + ' D/ST'
    const d = directory?.[id]
    const name = String(d?.full_name || [d?.first_name,d?.last_name].filter(Boolean).join(' ')).trim()
    return name || null
  }
  const rosterNames = playerIds.map(player)
  const unmatchedIds = playerIds.filter((id,i) => !rosterNames[i])
  return {
    roster: rosterNames.filter(Boolean),
    starters: playerIds.filter(id => startingIds.has(id)).map(player).filter(Boolean),
    bench: playerIds.filter(id => !startingIds.has(id)).map(player).filter(Boolean),
    unavailable_player_count: unmatchedIds.length,
    total_player_ids: playerIds.length,
  }
}

async function playerDirectory(fetchImpl, now) {
  if (playersCache.mapping && playersCache.expires > now) return playersCache.mapping
  const directory = await apiGet('/players/nfl', fetchImpl, {timeoutMs:20000})
  if (!directory || typeof directory !== 'object' || Array.isArray(directory)) {
    throw new Error('Sleeper NFL player directory is unavailable.')
  }
  const names = {}
  for (const [id, row] of Object.entries(directory)) {
    if (!row || typeof row !== 'object') continue
    const fullName = String(row.full_name || [row.first_name,row.last_name].filter(Boolean).join(' ')).trim()
    if (fullName) names[id] = { full_name:fullName.slice(0,150) }
  }
  playersCache = {mapping:names, expires:now+12*60*60*1000}
  return names
}

export async function fetchSleeperRosterByLeague({username, league_id, season}, {
  fetchImpl=globalThis.fetch, now=Date.now(),
}={}) {
  const lookup = await lookupSleeperLeagues(username, {season,fetchImpl})
  const id = validateSleeperLeagueId(league_id)
  const selected = lookup.leagues.find(item => item.league_id === id)
  if (!selected) throw inputError('That Sleeper league is not listed for this username and season.')
  const rosterRows = await apiGet('/league/' + id + '/rosters', fetchImpl)
  const league = await apiGet('/league/' + id, fetchImpl)
  if (!Array.isArray(rosterRows) || !league || String(league.league_id) !== id) {
    throw new Error('Sleeper roster or league information is incomplete.')
  }
  const selectedRoster = rosterRows.find(row => row &&
    (String(row.owner_id || '') === lookup.user.user_id ||
      (Array.isArray(row.co_owners) && row.co_owners.map(String).includes(lookup.user.user_id))))
  if (!selectedRoster || selectedRoster.roster_id == null) {
    throw inputError('No owned roster is listed for this Sleeper username in that league.')
  }
  const directory = await playerDirectory(fetchImpl, now)
  const players = resolveSleeperRoster(selectedRoster,directory)
  if (players.total_player_ids && players.unavailable_player_count) {
    throw new Error('Sleeper player names are incomplete; please retry roster import later.')
  }
  const {scoring,roster_settings} = mapSleeperScoring(league)
  return {
    status:'READY',
    access:'SLEEPER_PUBLIC_READ_ONLY_NO_IDENTITY_VERIFICATION',
    source:'SLEEPER_PUBLIC_API',
    user_id:lookup.user.user_id,
    username:lookup.user.username,
    league_id:id,
    league_name:selected.name,
    season:lookup.season,
    roster_id:String(selectedRoster.roster_id),
    team_name:String(selectedRoster.metadata?.team_name || selected.name).slice(0,120),
    ...players, scoring, roster_settings,
  }
}

export function resetSleeperPlayerCacheForTests() {
  playersCache = {expires:0,mapping:null}
}
