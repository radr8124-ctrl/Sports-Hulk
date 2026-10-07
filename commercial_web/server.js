import http from 'node:http'
import { createReadStream, readFileSync } from 'node:fs'
import { readFile, rename, stat, writeFile } from 'node:fs/promises'
import { spawn } from 'node:child_process'
import { createHash, timingSafeEqual } from 'node:crypto'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createAdminClient, createClient } from '@insforge/sdk'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const DIST = path.join(__dirname, 'dist')
const PORT = Number(process.env.PORT || 8510)
const SPORTS_ROOT = path.resolve(__dirname, '..')
const DFS_BRIDGE = path.join(__dirname, 'dfs_optimizer_bridge.py')
const RATE_MY_TEAM_BRIDGE = path.join(__dirname, 'rate_my_team_bridge.py')
const WAIVER_FIT_BRIDGE = path.join(__dirname, 'waiver_fit_bridge.py')
const IR_STASH_FIT_BRIDGE = path.join(__dirname, 'ir_stash_fit_bridge.py')
const DEFENSE_STREAM_FIT_BRIDGE = path.join(__dirname, 'defense_stream_fit_bridge.py')
const IDP_FIT_BRIDGE = path.join(__dirname, 'idp_fit_bridge.py')
const FORMAT_CONTEXT_BRIDGE = path.join(__dirname, 'format_context_bridge.py')
const SPORTS_PYTHON = path.join(SPORTS_ROOT, '.venv', 'bin', 'python')
const SURVIVOR_ENTRIES_PATH = '/home/ubuntu/sports-hulk/nfl_live/derived/SURVIVOR_ENTRIES.json'
const SURVIVOR_V2_PRIVATE_PATH = '/home/ubuntu/sports-hulk/intelligence_warehouse/survivor_accountability/SURVIVOR_V2_CURRENT.json'
const DATASET_FRESHNESS_PATH = path.join(SPORTS_ROOT, 'intelligence_warehouse', 'freshness', 'DATASET_FRESHNESS_CURRENT.csv')

const JSON_FILES = {
  nflScores: 'nfl_scores.json',
  nflDecisions: 'nfl_decisions.json',
  mlbScores: 'mlb_scores.json',
  nbaScores: 'nba_scores.json',
  nhlScores: 'nhl_scores.json',
  cfbScores: 'cfb_scores.json',
  cbbScores: 'cbb_scores.json',
  fantasyNews: 'fantasy_news.json',
  askContext: 'ask_context.json',
  askRetrieval: 'ask_retrieval.json',
  bettingV2: 'betting_v2_all_markets_current.json',
  propV2: 'prop_v2_current.json',
  parlayV2: 'parlay_v2_current.json',
  survivorV2: 'survivor_v2_current.json',
  performance: 'performance_snapshot.json',
}

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg', '.ico': 'image/x-icon',
}

const SECURITY_HEADERS = {
  'x-content-type-options': 'nosniff',
  'x-frame-options': 'DENY',
  'referrer-policy': 'strict-origin-when-cross-origin',
  'permissions-policy': 'camera=(), microphone=(), geolocation=()',
}

function json(res, status, payload, extraHeaders = {}) {
  const body = JSON.stringify(payload)
  res.writeHead(status, {
    ...SECURITY_HEADERS,
    ...extraHeaders,
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(body),
    'cache-control': 'no-store',
  })
  res.end(body)
}

async function loadJson(name) {
  const filename = JSON_FILES[name]
  if (!filename) return null
  try { return JSON.parse(await readFile(path.join(DIST, filename), 'utf8')) }
  catch { return null }
}

async function loadExternalJson(filename) {
  try { return JSON.parse(await readFile(filename, 'utf8')) }
  catch { return null }
}


function parseSimpleCsvLine(line) {
  return String(line || '').split(',')
}

async function fantasyResearchFreshness(lane, rosterUpdatedAt = null) {
  const requestedLane = String(lane || '').trim().toLowerCase()
  const unknown = {
    lane: requestedLane || null,
    status: 'UNKNOWN',
    source_available: false,
    source_timestamp: null,
    age_minutes: null,
    max_age_minutes: null,
    row_count: null,
    row_state: 'UNKNOWN',
    manifest_checked_at: null,
    roster_updated_at: rosterUpdatedAt || null,
    roster_newer_than_research: null,
    roster_ahead_minutes: null,
    freshness_basis: 'ACTUAL_SOURCE_FILE_MTIME_AT_REQUEST_WITH_DATASET_FRESHNESS_POLICY',
  }

  if (!requestedLane) return unknown

  try {
    const raw = await readFile(DATASET_FRESHNESS_PATH, 'utf8')
    const lines = raw.split(/\r?\n/).filter(Boolean)
    if (lines.length < 2) return unknown

    const headers = parseSimpleCsvLine(lines[0])
    let match = null
    for (const line of lines.slice(1)) {
      const values = parseSimpleCsvLine(line)
      const row = Object.fromEntries(headers.map((key, index) => [key, values[index] ?? '']))
      if (
        String(row.sport || '').toUpperCase() === 'FANTASY_DECISIONS' &&
        String(row.lane || '').toLowerCase() === requestedLane
      ) {
        match = row
        break
      }
    }

    if (!match) return unknown

    const rosterMs = Date.parse(rosterUpdatedAt || '')
    const maxAge = Number(match.max_age_minutes)
    const nowMs = Date.now()
    const relativeSourcePath = String(match.path || '').trim()
    const resolvedSourcePath = relativeSourcePath ? path.resolve(SPORTS_ROOT, relativeSourcePath) : ''
    const rootPrefix = path.resolve(SPORTS_ROOT) + path.sep
    let sourceMs = Number.NaN
    let exists = false

    if (resolvedSourcePath && resolvedSourcePath.startsWith(rootPrefix)) {
      try {
        const sourceStat = await stat(resolvedSourcePath)
        exists = sourceStat.isFile()
        if (exists) sourceMs = sourceStat.mtimeMs
      } catch {}
    }

    const ageMinutes = Number.isFinite(sourceMs)
      ? Math.max(0, (nowMs - sourceMs) / 60000)
      : null

    let status = 'UNKNOWN'
    if (!exists) {
      status = 'MISSING'
    } else if (ageMinutes != null && Number.isFinite(maxAge)) {
      status = ageMinutes <= maxAge
        ? 'FRESH'
        : ageMinutes <= maxAge * 2
          ? 'AGING'
          : 'STALE'
    }

    const rosterNewer = Number.isFinite(sourceMs) && Number.isFinite(rosterMs)
      ? rosterMs > sourceMs
      : null
    const rosterAheadMinutes = rosterNewer
      ? Math.max(0, (rosterMs - sourceMs) / 60000)
      : 0

    return {
      lane: requestedLane,
      status,
      source_available: exists,
      source_timestamp: Number.isFinite(sourceMs) ? new Date(sourceMs).toISOString() : null,
      age_minutes: ageMinutes == null ? null : Math.round(ageMinutes * 10) / 10,
      max_age_minutes: Number.isFinite(maxAge) ? maxAge : null,
      row_count: Number.isFinite(Number(match.row_count)) ? Number(match.row_count) : null,
      row_state: match.row_state || 'UNKNOWN',
      manifest_checked_at: match.checked_at || null,
      roster_updated_at: Number.isFinite(rosterMs) ? new Date(rosterMs).toISOString() : (rosterUpdatedAt || null),
      roster_newer_than_research: rosterNewer,
      roster_ahead_minutes: rosterNewer ? Math.round(rosterAheadMinutes * 10) / 10 : 0,
      freshness_basis: 'ACTUAL_SOURCE_FILE_MTIME_AT_REQUEST_WITH_DATASET_FRESHNESS_POLICY',
    }
  } catch {
    return unknown
  }
}

const MEMBER_LINKS_PATH = path.join(__dirname, 'private_member_links.json')

function readLocalEnv() {
  const values = {}
  try {
    for (const line of readFileSync(path.join(__dirname, '.env.local'), 'utf8').split(/\r?\n/)) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue
      const index = trimmed.indexOf('=')
      values[trimmed.slice(0, index).trim()] = trimmed.slice(index + 1).trim()
    }
  } catch {}
  return values
}

const LOCAL_ENV = readLocalEnv()
const INSFORGE_URL = process.env.INSFORGE_URL || LOCAL_ENV.VITE_INSFORGE_URL || ''

function readInsForgeAdminKey() {
  try {
    const metadata = JSON.parse(readFileSync(path.join(SPORTS_ROOT, '.insforge', 'project.parent.json'), 'utf8'))
    return String(metadata?.api_key || '').trim()
  } catch {
    return ''
  }
}

const INSFORGE_API_KEY = process.env.INSFORGE_API_KEY || readInsForgeAdminKey()
const INSFORGE_ADMIN = INSFORGE_URL && INSFORGE_API_KEY
  ? createAdminClient({ baseUrl: INSFORGE_URL, apiKey: INSFORGE_API_KEY })
  : null

function bearerToken(req) {
  const value = String(req.headers.authorization || '')
  const match = value.match(/^Bearer\s+(.+)$/i)
  return match ? match[1].trim() : null
}

function scopedInsForgeClient(req) {
  const token = bearerToken(req)
  if (!token || !INSFORGE_URL) return null
  return createClient({ baseUrl: INSFORGE_URL, accessToken: token, isServerMode: true })
}

async function authenticatedUser(req) {
  const client = scopedInsForgeClient(req)
  if (!client) return null
  try {
    const { data, error } = await client.auth.getCurrentUser()
    if (error || !data?.user) return null
    return data.user
  } catch {
    return null
  }
}

async function linkedSurvivorEntry(req, userId) {
  if (!userId) return null

  const client = scopedInsForgeClient(req)
  if (client) {
    try {
      const { data, error } = await client.database
        .from('survivor_entries')
        .select('entry_name')
        .eq('owner_id', userId)
        .eq('is_active', true)
        .limit(1)
      if (!error && Array.isArray(data) && data[0]?.entry_name) return data[0].entry_name
    } catch {}
  }

  const links = await loadExternalJson(MEMBER_LINKS_PATH)
  return links?.survivor_entries?.[userId] || null
}

function sha256(value) {
  return createHash('sha256').update(String(value || '')).digest('hex')
}

function secureHashEqual(a, b) {
  try {
    const left = Buffer.from(String(a || ''), 'hex')
    const right = Buffer.from(String(b || ''), 'hex')
    return left.length > 0 && left.length === right.length && timingSafeEqual(left, right)
  } catch {
    return false
  }
}

async function saveMemberLinks(links) {
  const tmp = MEMBER_LINKS_PATH + '.tmp'
  await writeFile(tmp, JSON.stringify(links, null, 2) + '\n', { mode: 0o600 })
  await rename(tmp, MEMBER_LINKS_PATH)
}

async function loadAll() {
  const names = Object.keys(JSON_FILES)
  const values = await Promise.all(names.map(loadJson))
  const data = Object.fromEntries(names.map((name, i) => [name, values[i]]))
  data.survivorUser = await loadExternalJson(SURVIVOR_ENTRIES_PATH)
  return data
}

const qtext = value => String(value || '').trim().toLowerCase()
const nice = value => String(value || '').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase())
function num(value, fallback = null) { const n = Number(value); return Number.isFinite(n) ? n : fallback }

function updatedSources(data, labels) {
  const map = {
    nflScores: ['NFL scores', data.nflScores?.generated_at, data.nflScores?.source || 'ESPN Core'],
    nflDecisions: ['NFL decisions', data.nflDecisions?.generated_at, 'Decision engine'],
    mlbScores: ['MLB scores', data.mlbScores?.generated_at, data.mlbScores?.source || 'MLB StatsAPI'],
    nbaScores: ['NBA scores', data.nbaScores?.generated_at, data.nbaScores?.source || 'ESPN NBA'],
    nhlScores: ['NHL scores', data.nhlScores?.generated_at, data.nhlScores?.source || 'ESPN NHL'],
    cfbScores: ['CFB scores', data.cfbScores?.generated_at, data.cfbScores?.source || 'ESPN FBS'],
    cbbScores: ['CBB scores', data.cbbScores?.generated_at, data.cbbScores?.source || 'ESPN Division I'],
    fantasyNews: ['Fantasy news', data.fantasyNews?.generated_at, 'News collector'],
    askContext: ['Sports intelligence', data.askContext?.generated_at, data.askContext?.source || 'Governed warehouse'],
    askRetrieval: ['Reporting graph', data.askRetrieval?.generated_at, data.askRetrieval?.source || 'Structured news/event graph'],
    survivorUser: ['My Survivor entry', data.survivorUser?.manual_state_updated_at || data.survivorUser?.last_result_refresh_at, 'Saved Survivor state'],
    bettingV2: ['Best Bets V2', data.bettingV2?.generated_at, data.bettingV2?.model_version || 'Proof-gated game markets'],
    propV2: ['Props V2', data.propV2?.generated_at, data.propV2?.model_version || 'Proof-gated player markets'],
    parlayV2: ['Parlays V2', data.parlayV2?.generated_at, data.parlayV2?.model_version || 'Source-proof parlay model'],
    survivorV2: ['Survivor V2', data.survivorV2?.generated_at, data.survivorV2?.model_version || 'Governed Survivor model'],
    performance: ['Official Brain Record', data.performance?.generated_at, 'Append-only official record'],
  }
  return labels.map(k => map[k]).filter(Boolean).map(([label, updated_at, source]) => ({ label, updated_at, source }))
}

function response({ intent, take, confidence = 'HIGH', why = [], risk = [], sources = [], cards = [], updated_at = null, followups = [], status = 'CURRENT' }) {
  return { intent, take, confidence, why, risk, sources, cards, updated_at, followups, status }
}

function gameAliases(game) {
  const values = [game.away, game.home, game.away_abbr, game.home_abbr, game.away_team, game.home_team].filter(Boolean)
  const aliases = []
  for (const value of values) {
    const text = String(value).toLowerCase().trim()
    if (!text) continue
    aliases.push(text)
    const parts = text.split(/\s+/)
    const last = parts[parts.length - 1]
    if (last && last.length >= 3) aliases.push(last)
    if (parts.length >= 2) {
      aliases.push(parts.slice(0, 2).join(' '))
      aliases.push(parts.slice(-2).join(' '))
    }
  }
  return [...new Set(aliases)]
}
function findGame(question, games = []) {
  const q = qtext(question)
  return games.find(g => gameAliases(g).some(alias => alias.length >= 3 && q.includes(alias)))
}
function matchPlayers(question, rows = []) {
  const q = qtext(question), seen = new Set(), matches = []
  for (const row of rows) {
    const player = String(row.player || row.player_dfs || row.player_sportsbook || '').trim()
    if (!player) continue
    const key = player.toLowerCase()
    if (!seen.has(key) && q.includes(key)) { seen.add(key); matches.push(row) }
  }
  return matches
}

function scoreCard(game, league) {
  const away = game.away || game.away_team || '', home = game.home || game.home_team || ''
  const state = game.final ? 'FINAL' : game.live ? 'LIVE' : 'UPCOMING'
  return { type:'score', league, title:`${away} @ ${home}`, state, away, home, away_score:game.away_score, home_score:game.home_score, status:game.status || '', start_time:game.start_time || game.gameDate || game.start || null }
}

function scoreAnswer(question, data) {
  const q = qtext(question)
  const leagueConfig = [
    { league:'CBB', key:'cbbScores', rx:/\b(cbb|college basketball|ncaab|mens college basketball)\b/ },
    { league:'CFB', key:'cfbScores', rx:/\b(cfb|college football|ncaaf)\b/ },
    { league:'NBA', key:'nbaScores', rx:/\b(nba|basketball)\b/ },
    { league:'NHL', key:'nhlScores', rx:/\b(nhl|hockey)\b/ },
    { league:'MLB', key:'mlbScores', rx:/\b(mlb|baseball)\b/ },
    { league:'NFL', key:'nflScores', rx:/\b(nfl|football)\b/ },
  ]
  let selected = leagueConfig.find(item => item.rx.test(q)) || null
  let matched = null

  if (!selected) {
    for (const item of leagueConfig) {
      const candidateSource = data[item.key] || {}
      const candidateGames = item.league === 'MLB'
        ? (candidateSource.today_games || candidateSource.games || [])
        : (candidateSource.games || [])
      const candidateMatch = findGame(question, candidateGames)
      if (candidateMatch) {
        selected = item
        matched = candidateMatch
        break
      }
    }
  }

  selected = selected || leagueConfig[5]
  const source = data[selected.key] || {}
  const games = selected.league === 'MLB'
    ? (source.today_games || source.games || [])
    : (source.games || [])
  matched = matched || findGame(question, games)

  if (matched) {
    const card = scoreCard(matched, selected.league)
    const scoreKnown = !(!matched.live && !matched.final) && matched.away_score != null && matched.home_score != null
    return response({
      intent:'live_score',
      take: scoreKnown
        ? `${card.away} ${card.away_score}, ${card.home} ${card.home_score} — ${card.state}.`
        : `${card.away} at ${card.home} is ${card.state.toLowerCase()}${card.status ? ' — '+card.status : ''}.`,
      confidence:'VERIFIED',
      why:[card.status || 'Current structured score snapshot'],
      risk:card.state === 'UPCOMING' ? ['Game has not started yet.'] : [],
      cards:[card],
      sources:updatedSources(data,[selected.key]),
      updated_at:source.generated_at,
      followups:card.state === 'UPCOMING'
        ? ['What time does it start?','Any injury news?','Show the full slate']
        : ['Show the box score','What changed in this game?','Any injury news?'],
    })
  }

  const live = games.filter(g => g.live)
  const upcoming = games.filter(g => !g.live && !g.final)
  const finals = games.filter(g => g.final)
  const current = live.length
    ? live.slice(0,8)
    : upcoming.length
      ? upcoming.slice(0,8)
      : finals.slice(-8)

  const take = live.length
    ? `${live.length} ${selected.league} game${live.length===1?'':'s'} currently live.`
    : upcoming.length
      ? `No ${selected.league} game is live right now. Here are the next ${Math.min(upcoming.length,8)} upcoming games in the current window.`
      : finals.length
        ? `No ${selected.league} game is live right now. Here are the most recent finals.`
        : `No ${selected.league} games are scheduled in the current score window.`

  return response({
    intent:'live_scores',
    take,
    confidence:'VERIFIED',
    why:['Current structured score feed'],
    cards:current.map(g=>scoreCard(g,selected.league)),
    sources:updatedSources(data,[selected.key]),
    updated_at:source.generated_at,
    status:games.length ? 'CURRENT' : 'NO_GAMES',
  })
}

function bettingAnswer(question, data) {
  const q = qtext(question)
  const source = data.bettingV2 || {}
  let board = [...(source.picks || [])]

  const sports = ['NFL','NBA','NHL','MLB','CFB','CBB']
  const requestedSport = sports.find(sport => q.includes(sport.toLowerCase()))
  if (requestedSport) board = board.filter(row => String(row.sport).toUpperCase() === requestedSport)

  if (q.includes('spread')) board = board.filter(row => String(row.market).toUpperCase() === 'SPREAD')
  else if (q.includes('total') || q.includes('over') || q.includes('under')) board = board.filter(row => String(row.market).toUpperCase() === 'TOTAL')
  else if (q.includes('moneyline') || q.includes(' ml')) board = board.filter(row => String(row.market).toUpperCase() === 'MONEYLINE')

  const requestedSelection = board.find(row => {
    const selection = qtext(row.selection)
    return selection && selection.length >= 2 && q.includes(selection)
  })
  if (requestedSelection) board = [requestedSelection, ...board.filter(row => row !== requestedSelection)]

  const decisionRank = row => row.shadow_decision === 'SHADOW_PLAY' ? 3 : row.shadow_decision === 'SHADOW_MONITOR' ? 2 : 1
  board.sort((a,b) =>
    decisionRank(b)-decisionRank(a)
    || num(b.conservative_expected_value_pct,-999)-num(a.conservative_expected_value_pct,-999)
    || num(b.edge_pct_points,-999)-num(a.edge_pct_points,-999)
  )

  const plays = board.filter(row => row.shadow_decision === 'SHADOW_PLAY')
  const research = board.slice(0,5)

  if (!board.length) return response({
    intent:'best_bet',
    take:'No current V2 game-market candidate matches that request.',
    confidence:'WAITING',
    status:'WAITING',
    risk:['No candidate is being invented to fill an empty market.'],
    sources:updatedSources(data,['bettingV2']),
    updated_at:source.generated_at,
  })

  if (!plays.length) {
    const top = research[0]
    return response({
      intent:'best_bet',
      take:`No current${requestedSport ? ' '+requestedSport : ''} bet has cleared the V2 PLAY gate.`,
      confidence:'WAITING / NO PLAY',
      status:'RESEARCH_ONLY',
      why:[
        `${board.length} matching candidate${board.length===1?'':'s'} evaluated; none has independently proven edge plus price proof.`,
        top ? `Top research row is ${top.selection} · ${nice(top.market)} — ${nice(top.selection_rule_status)}.` : null,
        top?.market_reference_probability_pct != null ? `Market reference ${top.market_reference_probability_pct}% vs model ${top.calibrated_win_probability_pct ?? '—'}%.` : null,
      ].filter(Boolean),
      risk:[
        'PASS is an intentional model decision, not missing output.',
        'Research cards below are not recommendations.',
      ],
      cards:research.map(row=>({
        type:'bet_research',
        title:`${row.sport} · ${nice(row.market)}`,
        selection:row.selection,
        market:nice(row.market),
        line:row.line ?? row.american_odds,
        decision:nice(row.shadow_decision),
        model_probability:row.calibrated_win_probability_pct,
        market_probability:row.market_reference_probability_pct,
        conservative_ev:row.conservative_expected_value_pct,
      })),
      sources:updatedSources(data,['bettingV2']),
      updated_at:source.generated_at,
      followups:['Why did these bets fail the proof gate?','Show me props','Show me the Brain Record'],
    })
  }

  const top=plays[0]
  const price = top.market === 'MONEYLINE' ? top.american_odds : top.line
  return response({
    intent:'best_bet',
    take:`${top.selection} · ${nice(top.market)} ${price ?? ''}`.trim(),
    confidence:'V2 PLAY',
    status:'PLAY',
    why:[
      `Model ${top.calibrated_win_probability_pct ?? '—'}% vs market reference ${top.market_reference_probability_pct ?? '—'}%.`,
      `Conservative EV ${top.conservative_expected_value_pct ?? '—'}%.`,
      `${top.book_count ?? '—'} books · data quality ${top.data_quality_grade || '—'}.`,
    ],
    risk:['Verify the currently available price before acting; price changes can remove edge.'],
    cards:plays.slice(0,5).map(row=>({
      type:'bet',
      title:`${row.sport} · ${nice(row.market)}`,
      selection:row.selection,
      market:nice(row.market),
      line:row.line ?? row.american_odds,
      decision:'PLAY',
    })),
    sources:updatedSources(data,['bettingV2']),
    updated_at:source.generated_at,
    followups:['Why is this a PLAY?','Show me the best props','Open Brain Record'],
  })
}

function propsAnswer(question, data) {
  const q=qtext(question)
  const source=data.propV2||{}
  const wantsPrize=q.includes('prizepicks') || q.includes('pick em') || q.includes('pick-em')
  let rows=[...(source.picks||[])].filter(row=>row.lane === (wantsPrize?'PRIZEPICKS':'PROP'))

  const sports=['NFL','NBA','NHL','MLB']
  const requestedSport=sports.find(sport=>q.includes(sport.toLowerCase()))
  if(requestedSport) rows=rows.filter(row=>String(row.sport).toUpperCase()===requestedSport)

  const matched=matchPlayers(question,rows)
  if(matched.length) rows=matched

  const decisionRank=row=>row.shadow_decision==='SHADOW_PLAY'?3:row.shadow_decision==='SHADOW_MONITOR'?2:1
  rows.sort((a,b)=>
    decisionRank(b)-decisionRank(a)
    || num(b.conservative_edge_pct_points,-999)-num(a.conservative_edge_pct_points,-999)
    || num(b.edge_pct_points,-999)-num(a.edge_pct_points,-999)
  )

  if(!rows.length) return response({
    intent:wantsPrize?'prizepicks':'props',
    take:`No current ${wantsPrize?'PrizePicks':'prop'} candidate matches that request.`,
    confidence:'WAITING',
    status:'WAITING',
    sources:updatedSources(data,['propV2']),
    updated_at:source.generated_at,
  })

  const plays=rows.filter(row=>row.shadow_decision==='SHADOW_PLAY')
  const monitors=rows.filter(row=>row.shadow_decision==='SHADOW_MONITOR')
  const chosen=(plays.length?plays:monitors.length?monitors:rows).slice(0,6)
  const top=chosen[0]

  if(!plays.length) return response({
    intent:wantsPrize?'prizepicks':'props',
    take:monitors.length
      ? `${monitors.length} ${wantsPrize?'PrizePicks':'prop'} shadow monitor${monitors.length===1?' is':'s are'} promising, but no PLAY has cleared the proof gate.`
      : `No current ${wantsPrize?'PrizePicks':'prop'} has cleared the V2 PLAY gate.`,
    confidence:monitors.length?'MONITOR / NOT PLAY':'WAITING / NO PLAY',
    status:'RESEARCH_ONLY',
    why:[
      top ? `${top.player} ${top.side} ${top.line} ${nice(top.market_subtype)}: model ${top.v2_probability_pct ?? '—'}% vs market ${top.market_reference_probability_pct ?? '—'}%.` : null,
      top ? `Conservative probability ${top.conservative_probability_pct ?? '—'}% · ${nice(top.selection_rule_status)}.` : null,
      monitors.length ? 'Shadow monitors are frozen for forward learning, not promoted as recommendations.' : 'No candidate has enough independent proof to promote.',
    ].filter(Boolean),
    risk:[
      wantsPrize?'A good leg is not the same as a profitable multi-pick entry; payout economics must also be proven.':'Prop prices and lines can move quickly; recheck the current market.',
      'PASS and MONITOR labels are not PLAYs.',
    ],
    cards:chosen.map(row=>({
      type:wantsPrize?'prizepicks_research':'prop_research',
      title:row.player,
      side:row.side,
      line:row.line,
      market:nice(row.market_subtype),
      decision:row.shadow_decision,
      model_probability:row.v2_probability_pct,
      market_probability:row.market_reference_probability_pct,
    })),
    sources:updatedSources(data,['propV2']),
    updated_at:source.generated_at,
    followups:['Why is this only a monitor?','Show me another sport','Show the Brain Record'],
  })

  return response({
    intent:wantsPrize?'prizepicks':'props',
    take:`${top.player} ${top.side} ${top.line} ${nice(top.market_subtype)}`,
    confidence:'V2 PLAY',
    status:'PLAY',
    why:[
      `Model ${top.v2_probability_pct ?? '—'}% vs market ${top.market_reference_probability_pct ?? '—'}%.`,
      `Conservative probability ${top.conservative_probability_pct ?? '—'}%.`,
      `Quality ${top.data_quality_grade || '—'} · ${top.data_quality_book_count ?? '—'} books.`,
    ],
    risk:[wantsPrize?'Entry payout economics still determine whether a multi-pick card is profitable.':'Verify the live line and price before acting.'],
    cards:plays.slice(0,6).map(row=>({type:'prop',title:row.player,side:row.side,line:row.line,market:nice(row.market_subtype),decision:'PLAY'})),
    sources:updatedSources(data,['propV2']),
    updated_at:source.generated_at,
  })
}

function survivorAnswer(data) {
  const source = data.survivorV2 || {}
  const candidates = [...(source.candidates || [])]
    .filter(row => !(source.used_teams || []).includes(row.team))
    .sort((a,b) => num(b.strategy_index,0)-num(a.strategy_index,0))
  const shadowRec = source.shadow_recommendation && !Array.isArray(source.shadow_recommendation) && source.shadow_recommendation.team
    ? source.shadow_recommendation
    : null
  const top = shadowRec || candidates[0] || null
  const week = source.pool_current_week || null
  const entry = source.active_entry || 'Active entry'
  const used = source.used_teams || []

  if (String(source.active_entry_status || '').toUpperCase() === 'ELIMINATED') {
    return response({
      intent:'survivor',
      take:`${entry} is eliminated. No new recommendation will be created until a valid buyback or re-entry state is recorded.`,
      confidence:'BLOCKED',
      status:'ENTRY_ELIMINATED',
      risk:['An eliminated entry is never silently reactivated.'],
      sources:updatedSources(data,['survivorV2']),
      updated_at:source.generated_at,
    })
  }

  if (!top) {
    return response({
      intent:'survivor',
      take:`No eligible Week ${week || 'current'} Survivor candidate is available in the governed board.`,
      confidence:'WAITING',
      status:'WAITING',
      risk:['No candidate is being invented to fill an empty board.'],
      sources:updatedSources(data,['survivorV2']),
      updated_at:source.generated_at,
    })
  }

  const cards = candidates.slice(0,5).map(row=>({
    type:'survivor',
    title:row.team,
    opponent:row.opponent,
    market_prob:row.market_prob_pct,
    spread:row.spread,
    context_score:row.hulk_context_score,
    tier:row.decision_tier,
    strategy_index:row.strategy_index,
    positives:row.positive_signals,
    risks:row.risk_signals,
  }))

  if (!source.rule_confirmed) {
    return response({
      intent:'survivor',
      take:`Week ${week || 'current'} recommendation is locked until the official pool sheet confirms the required pick count and current-week ownership.`,
      confidence:'WAITING FOR POOL RULE',
      status:source.rule_status || 'AWAITING_OFFICIAL_POOL_SHEET',
      why:[
        `${entry} is ${source.active_entry_status || 'active'} with ${used.length} team${used.length===1?'':'s'} already used.`,
        used.length ? `Already used: ${used.join(', ')}.` : null,
        `Current research leader: ${top.team} vs ${top.opponent} · ${top.market_prob_pct ?? '—'}% market survival · strategy index ${top.strategy_index ?? '—'}.`,
        `Ownership state: ${nice(source.ownership?.status || 'WAITING')}.`,
      ].filter(Boolean),
      risk:[
        `Latest official pool sheet is Week ${source.ownership?.official_pool_week ?? '—'} while the active pool week is ${week ?? '—'}.`,
        'The research leader is not a final pick recommendation until the rule gate clears.',
      ],
      cards,
      sources:updatedSources(data,['survivorV2']),
      updated_at:source.generated_at,
      followups:['Why is Dallas the research leader?','What teams have I already used?','What needs to update before the pick unlocks?'],
    })
  }

  const rec = shadowRec || top
  return response({
    intent:'survivor',
    take:`${rec.team} is the current Week ${week || 'current'} governed Survivor recommendation.`,
    confidence:nice(rec.decision_tier || 'RESEARCH'),
    status:source.recommendation_status || 'READY',
    why:[
      `Market survival ${rec.market_prob_pct ?? '—'}%.`,
      `Strategy index ${rec.strategy_index ?? '—'} · ${nice(rec.future_value_label || 'UNKNOWN FUTURE VALUE')}.`,
      rec.positive_signals ? `Positive: ${nice(String(rec.positive_signals).replaceAll('|',' '))}.` : null,
    ].filter(Boolean),
    risk:[rec.risk_signals ? nice(String(rec.risk_signals).replaceAll('|',' ')) : 'No explicit risk signal listed.'],
    cards,
    sources:updatedSources(data,['survivorV2']),
    updated_at:source.generated_at,
    followups:['Why this Survivor pick?','What team should I save for later?','Show the next five eligible options'],
  })
}

function parlayAnswer(data) {
  const source=data.parlayV2||{}
  const rows=[...(source.picks||[])]
  const plays=rows.filter(row=>row.shadow_decision==='SHADOW_PLAY')
  const monitors=rows.filter(row=>row.shadow_decision==='SHADOW_MONITOR')
  const resolved=rows.filter(row=>row.resolved_legs===row.leg_count)
  const chosen=(plays.length?plays:monitors.length?monitors:resolved).slice(0,5)

  const legLabel=leg=>{
    if(!leg) return 'Unknown leg'
    const who=leg.player||leg.selection||''
    const market=nice(leg.market||'')
    const line=leg.line==null?'':String(leg.line)
    return `${who} ${leg.selection||''} ${line} ${market}`.replace(/\s+/g,' ').trim()
  }

  if(!plays.length) return response({
    intent:'parlay',
    take:'No current parlay has cleared source-leg proof, correlation and payout-price gates.',
    confidence:'WAITING / NO PLAY',
    status:'RESEARCH_ONLY',
    why:[
      `${source.summary?.candidates ?? rows.length} combinations evaluated.`,
      `${source.summary?.resolved_all_legs ?? resolved.length} have exact V2 leg resolution.`,
      `${source.summary?.all_source_legs_forward_proven ?? 0} have all source legs forward-proven; ${source.summary?.captured_parlay_price ?? 0} have captured combined prices.`,
    ],
    risk:[
      'Research joint probability is not a payout claim.',
      'Same-game combinations require correlation proof; cross-game combinations still need source-leg and price proof.',
    ],
    cards:chosen.map(row=>({
      type:'parlay_research',
      title:`${row.sport} · ${nice(row.correlation_status)}`,
      selection:(row.legs||[]).map(legLabel).join(' + '),
      market:'Research only',
      line:'',
    })),
    sources:updatedSources(data,['parlayV2']),
    updated_at:source.generated_at,
    followups:['Why are parlays being withheld?','Show me Props','Show the Brain Record'],
  })

  const top=plays[0]
  return response({
    intent:'parlay',
    take:(top.legs||[]).map(legLabel).join(' + '),
    confidence:'V2 PLAY',
    status:'PLAY',
    why:[
      `Joint conservative probability ${top.joint_conservative_probability_pct ?? '—'}%.`,
      `Captured parlay price ${top.captured_parlay_american_odds ?? '—'}.`,
      `Correlation status: ${nice(top.correlation_status)}.`,
    ],
    risk:['Verify every leg and the combined payout immediately before use.'],
    cards:plays.slice(0,5).map(row=>({type:'parlay',title:`${row.sport} parlay`,selection:(row.legs||[]).map(legLabel).join(' + '),market:nice(row.correlation_status),line:row.captured_parlay_american_odds})),
    sources:updatedSources(data,['parlayV2']),
    updated_at:source.generated_at,
  })
}

const weeklyRows = data => data.askContext?.datasets?.weekly_fantasy || []
function startSitAnswer(question, data) {
  const rows=weeklyRows(data), matches=matchPlayers(question,rows); let chosen=matches
  if(!chosen.length){ const positions=['QB','RB','WR','TE']; chosen=positions.map(pos=>rows.find(row=>String(row.position).toUpperCase()===pos && String(row.weekly_tier)!=='INACTIVE')).filter(Boolean) }
  if(!chosen.length) return response({intent:'start_sit',take:'The weekly fantasy decision board is not available.',confidence:'WAITING',status:'WAITING',sources:updatedSources(data,['askContext'])})
  chosen=[...chosen].sort((a,b)=>num(b.weekly_research_score,0)-num(a.weekly_research_score,0)); const top=chosen[0], comparison=chosen.length>1?` over ${chosen[1].player}`:''
  return response({ intent:'start_sit', take:`Start ${top.player}${comparison}.`, confidence:nice(top.weekly_tier||'RESEARCH'), why:[top.research_reasons||null,`Role: ${nice(top.role_signal||'UNKNOWN')}`,top.defensive_pressure_context?`Matchup pressure: ${nice(top.defensive_pressure_context)}`:null,top.snap_pct!=null?`Snap share ${Number(top.snap_pct*(top.snap_pct<=1?100:1)).toFixed(0)}%`:null].filter(Boolean), risk:[top.availability_status&&!['ACTIVE','CLEAR','NONE'].includes(String(top.availability_status).toUpperCase())?`Player status: ${nice(top.availability_status)}`:'Recheck inactives and late news before lock.'], cards:chosen.slice(0,5).map(row=>({type:'fantasy',title:row.player,team:row.team,position:row.position,opponent:row.opponent,tier:row.weekly_tier,score:row.weekly_research_score,role:row.role_signal,matchup:row.defensive_pressure_context,reasons:row.research_reasons})), sources:updatedSources(data,['askContext']), updated_at:data.askContext?.generated_at, followups:['Show me waiver adds','Who is an IR stash?','Best defense to stream?'] })
}

function waiversAnswer(data) {
  const rows=[...(data.askContext?.datasets?.waivers||[])].filter(row=>!String(row.waiver_priority||'').includes('STASH')).sort((a,b)=>num(b.waiver_research_score,0)-num(a.waiver_research_score,0)).slice(0,6), top=rows[0]
  if(!top) return response({intent:'waivers',take:'No waiver board is available.',confidence:'WAITING',status:'WAITING'})
  return response({ intent:'waivers', take:`${top.player} is the top current waiver/FAAB research candidate to check.`, confidence:nice(top.waiver_priority), why:[`FAAB research range ${top.suggested_faab_low_pct ?? 0}–${top.suggested_faab_high_pct ?? 0}%`,top.add_rank_24h!=null?`24h add rank ${top.add_rank_24h}`:null,`Role: ${nice(top.role_signal||'UNKNOWN')}`].filter(Boolean), risk:['FAAB range is a research budget range, not a prediction of league bidding.','League free-agent availability is not verified in generic Ask.',top.availability_status?`Player status: ${nice(top.availability_status)}`:null].filter(Boolean), cards:rows.map(row=>({type:'waiver',title:row.player,team:row.team,position:row.position,priority:row.waiver_priority,faab_low:row.suggested_faab_low_pct,faab_high:row.suggested_faab_high_pct,add_rank:row.add_rank_24h,role:row.role_signal})), sources:updatedSources(data,['askContext']), updated_at:data.askContext?.generated_at })
}

function stashAnswer(data) {
  const rows=[...(data.askContext?.datasets?.stash||[])].sort((a,b)=>num(b.stash_research_score,0)-num(a.stash_research_score,0)).slice(0,6), top=rows[0]
  if(!top) return response({intent:'stash',take:'No stash board is available.',confidence:'WAITING',status:'WAITING'})
  return response({ intent:'stash', take:`${top.player} is the top current return/stash research candidate.`, confidence:nice(top.stash_tier), why:[`Return window: ${nice(top.return_window||'UNKNOWN')}`,`Status: ${nice(top.status||'UNKNOWN')}`,top.role_signal?`Role: ${nice(top.role_signal)}`:null].filter(Boolean), risk:[top.source_disagreement?'Injury sources disagree; treat return timing cautiously.':'Return timing is research, not a guarantee.'], cards:rows.map(row=>({type:'stash',title:row.player,team:row.team,position:row.position,status:row.status,return_window:row.return_window,tier:row.stash_tier,source_disagreement:row.source_disagreement})), sources:updatedSources(data,['askContext']), updated_at:data.askContext?.generated_at })
}

function defenseAnswer(data) {
  const rows=[...(data.askContext?.datasets?.defense_streaming||[])].sort((a,b)=>num(b.weekly_stream_score,0)-num(a.weekly_stream_score,0)).slice(0,6), top=rows[0]
  if(!top) return response({intent:'defense_stream',take:'No defense streaming board is available.',confidence:'WAITING',status:'WAITING'})
  return response({ intent:'defense_stream', take:`${top.dst_player||top.team} is the top current D/ST streaming research option to check.`, confidence:nice(top.weekly_stream_tier), why:[`Next opponent: ${top.next_opponent||'—'}`,`Weekly stream score ${top.weekly_stream_score ?? '—'}`,`Multi-week hold score ${top.multiweek_hold_score ?? '—'}`], risk:[top.market_data_available?'Generic market/add-drop context is available, but your league availability is not verified.':'Market add/drop context is not available for this team; league availability is not verified.'], cards:rows.map(row=>({type:'defense',title:row.dst_player||row.team,opponent:row.next_opponent,weekly_score:row.weekly_stream_score,weekly_tier:row.weekly_stream_tier,hold_score:row.multiweek_hold_score,hold_tier:row.multiweek_hold_tier})), sources:updatedSources(data,['askContext']), updated_at:data.askContext?.generated_at })
}

function dfsAnswer(question, data) {
  const q=qtext(question), platform=q.includes('draftkings')||q.includes(' dk ')?'DRAFTKINGS':q.includes('fanduel')?'FANDUEL':null
  let rows=[...(data.askContext?.datasets?.dfs||[])].filter(row=>String(row.sport).toUpperCase()==='NFL' && row.projected_fantasy_points!=null)
  if(platform) rows=rows.filter(row=>String(row.platform).toUpperCase()===platform)
  rows.sort((a,b)=>num(b.projected_fantasy_points,0)-num(a.projected_fantasy_points,0)); rows=rows.slice(0,8); const top=rows[0]
  if(!top) return response({intent:'dfs',take:'No current projected DFS pool is available.',confidence:'WAITING',status:'WAITING'})
  return response({ intent:'dfs', take:`${top.player} has the highest current ${platform?nice(platform)+' ':''}projection in the Ask snapshot.`, confidence:'PROJECTED', why:[`${top.projected_fantasy_points} projected points`,`${top.salary ?? '—'} salary`,top.audit_value_per_1000!=null?`${Number(top.audit_value_per_1000).toFixed(2)} pts/$1K`:null,nice(top.contest_archetype||'')].filter(Boolean), risk:['DFS projections can move with late news, inactives and lineup changes.'], cards:rows.map(row=>({type:'dfs',title:row.player,platform:row.platform,team:row.team,position:row.position,salary:row.salary,projection:row.projected_fantasy_points,value:row.audit_value_per_1000,archetype:row.contest_archetype})), sources:updatedSources(data,['askContext']), updated_at:data.askContext?.generated_at })
}

function newsAnswer(question, data) {
  const articles=data.fantasyNews?.articles||[], q=qtext(question), words=q.split(/\s+/).filter(w=>w.length>=4)
  const matched=articles.filter(article=>{const text=`${article.title||''} ${(article.impact_tags||[]).join(' ')}`.toLowerCase(); return words.some(word=>text.includes(word))})
  const rows=(matched.length?matched:articles).slice(0,8), top=rows[0]
  if(!top) return response({intent:'news',take:'No current article feed is available.',confidence:'WAITING',status:'WAITING'})
  return response({ intent:'news', take:top.title, confidence:'REPORTING', why:[`Source: ${top.source}`,...(top.impact_tags||[]).map(tag=>`Impact: ${tag}`)], risk:['Article/reporting context can be superseded by newer official status updates.'], cards:rows.map(row=>({type:'news',title:row.title,source:row.source,url:row.url,published_at:row.published_at,tags:row.impact_tags||[]})), sources:updatedSources(data,['fantasyNews']), updated_at:data.fantasyNews?.generated_at })
}

function startSitAnswerV2(question, data) {
  const rows=weeklyRows(data)
  const matches=matchPlayers(question,rows)

  if(!rows.length) return response({
    intent:'start_sit',
    take:'The weekly fantasy decision board is not available.',
    confidence:'WAITING',
    status:'WAITING',
    sources:updatedSources(data,['askContext'])
  })

  const cardFor=row=>({
    type:'fantasy',
    title:row.player,
    team:row.team,
    position:row.position,
    opponent:row.opponent,
    tier:row.weekly_tier,
    score:row.weekly_research_score,
    role:row.role_signal,
    matchup:row.defensive_pressure_context,
    reasons:row.research_reasons,
  })

  if(!matches.length){
    const chosen=[]
    for(const pos of ['QB','RB','WR','TE']){
      const candidate=rows.find(row=>
        String(row.position).toUpperCase()===pos &&
        String(row.weekly_tier).toUpperCase()!=='INACTIVE'
      )
      if(candidate) chosen.push(candidate)
    }
    return response({
      intent:'start_sit',
      take:"Tell me the players you're deciding between. Until your roster/scoring format is connected, here are the top current start candidates by position.",
      confidence:'NEEDS PLAYER CONTEXT',
      why:[
        'The current weekly fantasy board is loaded.',
        'Give me the player names and I’ll compare role, matchup, availability and usage directly.',
      ],
      risk:['No league roster or scoring format is connected to this commercial session yet.'],
      cards:chosen.map(cardFor),
      sources:updatedSources(data,['askContext']),
      updated_at:data.askContext?.generated_at,
      followups:['Top waiver adds','Who is an IR stash?','Best defense to stream?'],
    })
  }

  const chosen=[...matches].sort((a,b)=>num(b.weekly_research_score,0)-num(a.weekly_research_score,0))
  const top=chosen[0]
  const take=chosen.length>1
    ? 'Start ' + top.player + ' over ' + chosen[1].player + '.'
    : 'Start ' + top.player + '.'

  return response({
    intent:'start_sit',
    take,
    confidence:nice(top.weekly_tier||'RESEARCH'),
    why:[
      top.research_reasons||null,
      'Role: ' + nice(top.role_signal||'UNKNOWN'),
      top.defensive_pressure_context ? 'Matchup pressure: ' + nice(top.defensive_pressure_context) : null,
      top.snap_pct!=null ? 'Snap share ' + Number(top.snap_pct*(top.snap_pct<=1?100:1)).toFixed(0) + '%' : null,
    ].filter(Boolean),
    risk:[
      top.availability_status&&!['ACTIVE','CLEAR','NONE'].includes(String(top.availability_status).toUpperCase())
        ? 'Player status: ' + nice(top.availability_status)
        : 'Recheck inactives and late news before lock.'
    ],
    cards:chosen.slice(0,5).map(cardFor),
    sources:updatedSources(data,['askContext']),
    updated_at:data.askContext?.generated_at,
    followups:['Show me waiver adds','Who is an IR stash?','Best defense to stream?'],
  })
}

function startSitAnswerV3(question, data) {
  const weekly=weeklyRows(data)
  const weeklyMatches=matchPlayers(question,weekly)

  if(weeklyMatches.length){
    const chosen=[...weeklyMatches].sort((a,b)=>num(b.weekly_research_score,0)-num(a.weekly_research_score,0))
    const top=chosen[0]
    const take=chosen.length>1
      ? 'Start ' + top.player + ' over ' + chosen[1].player + '.'
      : 'Start ' + top.player + '.'
    return response({
      intent:'start_sit',
      take,
      confidence:nice(top.weekly_tier||'RESEARCH'),
      why:[
        top.research_reasons||null,
        'Role: ' + nice(top.role_signal||'UNKNOWN'),
        top.defensive_pressure_context ? 'Matchup pressure: ' + nice(top.defensive_pressure_context) : null,
      ].filter(Boolean),
      risk:[
        top.availability_status&&!['ACTIVE','CLEAR','NONE'].includes(String(top.availability_status).toUpperCase())
          ? 'Player status: ' + nice(top.availability_status)
          : 'Recheck inactives and late news before lock.'
      ],
      cards:chosen.slice(0,5).map(row=>({
        type:'fantasy',
        title:row.player,
        team:row.team,
        position:row.position,
        opponent:row.opponent,
        tier:row.weekly_tier,
        score:row.weekly_research_score,
        role:row.role_signal,
        matchup:row.defensive_pressure_context,
        reasons:row.research_reasons,
      })),
      sources:updatedSources(data,['askContext']),
      updated_at:data.askContext?.generated_at,
      followups:['Show me waiver adds','Who is an IR stash?','Best defense to stream?'],
    })
  }

  const dfsRows=(data.askContext?.datasets?.dfs||[])
    .filter(row=>String(row.sport).toUpperCase()==='NFL' && String(row.platform).toUpperCase()==='FANDUEL')
  const projectionMatches=matchPlayers(question,dfsRows)

  if(projectionMatches.length){
    const chosen=[...projectionMatches].sort((a,b)=>num(b.projected_fantasy_points,0)-num(a.projected_fantasy_points,0))
    const top=chosen[0]
    const take=chosen.length>1
      ? 'Start ' + top.player + ' over ' + chosen[1].player + ' based on the current projection fallback.'
      : top.player + ' has the stronger current projection context.'
    return response({
      intent:'start_sit',
      take,
      confidence:'PROJECTION-BASED FALLBACK',
      why:[
        String(top.projected_fantasy_points ?? '—') + ' projected points',
        top.audit_value_per_1000!=null ? Number(top.audit_value_per_1000).toFixed(2) + ' pts/$1K' : null,
        top.context_signal ? 'Context: ' + nice(top.context_signal) : null,
        top.role_signal ? 'Role: ' + nice(top.role_signal) : null,
      ].filter(Boolean),
      risk:[
        'These players are missing from the weekly Start/Sit decision board, so I’m using the current projection/role context instead.',
        'League scoring format and roster context are not connected to this commercial session yet.',
      ],
      cards:chosen.slice(0,5).map(row=>({
        type:'fantasy',
        title:row.player,
        team:row.team,
        position:row.position,
        tier:'PROJECTION FALLBACK',
        score:row.projected_fantasy_points,
        role:row.role_signal,
        matchup:row.context_signal,
        reasons:'Projection ' + String(row.projected_fantasy_points ?? '—') + ' · value ' + String(row.audit_value_per_1000 ?? '—') + ' pts/$1K',
      })),
      sources:updatedSources(data,['askContext']),
      updated_at:data.askContext?.generated_at,
      followups:['Top waiver adds','Best defense to stream?','Show DFS projections'],
    })
  }

  return startSitAnswerV2(question,data)
}

function reportingRetrieval(question, data) {
  const retrieval=data.askRetrieval||{}
  const events=retrieval.news_events||[]
  const facts=retrieval.facts||[]
  const entityIndex=retrieval.entity_index||{}
  const q=qtext(question)

  const stop=new Set([
    'what','which','about','saying','reporters','reporter','writer','writers',
    'beat','news','latest','today','right','now','update','updates','tell','show',
    'player','team','injury','status'
  ])
  const words=q.split(/\s+/)
    .map(w=>w.replace(/[^a-z0-9'-]/g,''))
    .filter(w=>w.length>=3&&!stop.has(w))

  const exactIds=new Set()
  for(const [entity, ids] of Object.entries(entityIndex)){
    const key=String(entity||'').toLowerCase().trim()
    if(key.length>=3 && q.includes(key)){
      for(const id of ids||[]) exactIds.add(String(id))
    }
  }

  const eventScore=event=>{
    const title=String(event.title||'').toLowerCase()
    const detail=String(event.detail||'').toLowerCase()
    const type=String(event.event_type||'').toUpperCase()
    let score=exactIds.has(String(event.event_node_id))?40:0

    for(const word of words){
      if(title.includes(word)) score+=7
      if(detail.includes(word)) score+=3
    }

    if(/\b(injur|practice|inactive|active|return|ir\b|questionable|doubtful|out\b)/.test(q) && type==='INJURY') score+=12
    if(/\b(role|starter|depth|snap|usage)/.test(q) && ['LINEUP_ROLE','DEPTH_CHART'].includes(type)) score+=10

    const tier=String(event.source_tier||'').toUpperCase()
    if(tier.includes('OFFICIAL')) score+=5
    else if(tier.includes('EXTERNAL_NEWS')) score+=2

    const promo=/\b(promo|bonus|claim|sportsbook|betting app|deposit|free bet)/.test(title)
    if(promo && !/\b(promo|bonus|sportsbook offer)/.test(q)) score-=30

    const when=Date.parse(event.published_or_effective_at||'')||0
    return {event,score,when}
  }

  const rankedEvents=events.map(eventScore)
    .filter(x=>x.score>0)
    .sort((a,b)=>b.score-a.score||b.when-a.when)

  const factScore=fact=>{
    const subject=String(fact.subject||'').toLowerCase()
    const team=String(fact.team||'').toLowerCase()
    const text=String(fact.fact_text||'').toLowerCase()
    let score=0

    if(subject.length>=3 && q.includes(subject)) score+=35
    if(team.length>=3 && q.includes(team)) score+=25

    for(const word of words){
      if(subject.includes(word)) score+=7
      if(team.includes(word)) score+=5
      if(text.includes(word)) score+=3
    }

    const type=String(fact.fact_type||'').toUpperCase()
    if(/\b(injur|practice|inactive|active|return|ir\b|questionable|doubtful|out\b)/.test(q) && type==='INJURY') score+=12

    const tier=String(fact.source_tier||'').toUpperCase()
    if(tier.includes('OFFICIAL')) score+=6

    const when=Date.parse(fact.effective_at||'')||0
    return {fact,score,when}
  }

  const rankedFacts=facts.map(factScore)
    .filter(x=>x.score>0)
    .sort((a,b)=>b.score-a.score||b.when-a.when)

  return {
    events: rankedEvents.slice(0,8).map(x=>x.event),
    facts: rankedFacts.slice(0,6).map(x=>x.fact),
    exact_entity_match: exactIds.size>0,
  }
}

function reportingAnswer(question, data) {
  const hit=reportingRetrieval(question,data)
  const events=hit.events
  const facts=hit.facts

  if(!events.length && !facts.length) return null

  const topEvent=events[0]
  const topFact=facts[0]
  const subject=(topEvent?.title || topFact?.subject || 'Current reporting')
  const why=[]

  for(const fact of facts.slice(0,2)){
    if(fact.fact_text) why.push(fact.fact_text)
  }
  for(const event of events.slice(0,3)){
    if(event.detail && !why.includes(event.detail)) why.push(event.detail)
  }

  const cards=events.slice(0,6).map(event=>({
    type:'news',
    title:event.title,
    source:event.source,
    source_tier:event.source_tier,
    url:event.source_url,
    published_at:event.published_or_effective_at,
    detail:event.detail,
    event_type:event.event_type,
  }))

  const sources=[]
  const seen=new Set()
  for(const event of events.slice(0,6)){
    const label=String(event.source||'Sports reporting')
    const key=label+'|'+String(event.source_url||'')
    if(seen.has(key)) continue
    seen.add(key)
    sources.push({
      label,
      source:label,
      url:event.source_url||null,
      updated_at:event.published_or_effective_at||null,
      tier:event.source_tier||null,
    })
  }
  if(!sources.length) sources.push(...updatedSources(data,['askRetrieval']))

  return response({
    intent:'reporting',
    take:topEvent ? topEvent.title : topFact.fact_text,
    confidence:hit.exact_entity_match?'ENTITY-LINKED REPORTING':'ATTRIBUTED REPORTING',
    why:why.slice(0,4),
    risk:['Reporting can be superseded by newer official status updates. Structured verified facts take precedence when they conflict.'],
    cards,
    sources,
    updated_at:data.askRetrieval?.generated_at,
    followups:['What does this mean for fantasy?','Any injury update?','What changed most recently?'],
  })
}

function newsAnswerV2(question, data) {
  const articles=data.fantasyNews?.articles||[]
  const q=qtext(question)
  const stop=new Set(['what','which','player','players','news','matters','most','right','now','latest','today','about'])
  const words=q.split(/\s+/).map(w=>w.replace(/[^a-z0-9'-]/g,'')).filter(w=>w.length>=4&&!stop.has(w))
  const wantsPromo=/\b(promo|bonus|sportsbook|betting app|offer)\b/.test(q)
  const impactTags=['INJURY','START/SIT WATCH','WAIVER WATCH','DEPTH CHART','TRADE']

  const scored=articles.map(article=>{
    const title=String(article.title||'').toLowerCase()
    const tags=(article.impact_tags||[]).map(t=>String(t).toUpperCase())
    const hay=title+' '+tags.join(' ').toLowerCase()
    let score=0

    for(const word of words){
      if(title.includes(word)) score+=5
      else if(hay.includes(word)) score+=2
    }

    if(tags.some(tag=>impactTags.includes(tag))) score+=6
    if(/\b(injur|practice|questionable|doubtful|out\b|ir\b|depth chart|starter|snap|role|waiver|trade)/.test(title)) score+=5

    const promo=/\b(promo|bonus|claim|sportsbook|betting app|deposit|bonus bet|free bet)\b/.test(title)
    if(promo&&!wantsPromo) score-=30

    if(q.includes('injury')&&tags.includes('INJURY')) score+=8
    if((q.includes('start')||q.includes('sit'))&&tags.includes('START/SIT WATCH')) score+=8
    if(q.includes('waiver')&&tags.includes('WAIVER WATCH')) score+=8
    if(q.includes('trade')&&tags.includes('TRADE')) score+=8
    if(q.includes('depth')&&tags.includes('DEPTH CHART')) score+=8

    const published=Date.parse(article.published_at||'')||0
    return {article,score,published}
  })

  scored.sort((a,b)=>b.score-a.score||b.published-a.published)
  let rows=scored.filter(x=>x.score>0).slice(0,8).map(x=>x.article)

  if(!rows.length){
    rows=scored
      .filter(x=>!(/\b(promo|bonus|claim|sportsbook|betting app|deposit|free bet)\b/.test(String(x.article.title||'').toLowerCase())))
      .slice(0,8)
      .map(x=>x.article)
  }

  const top=rows[0]
  if(!top) return response({intent:'news',take:'No current article feed is available.',confidence:'WAITING',status:'WAITING'})

  return response({
    intent:'news',
    take:top.title,
    confidence:'REPORTING',
    why:['Source: '+top.source,...(top.impact_tags||[]).map(tag=>'Impact: '+tag)],
    risk:['Article/reporting context can be superseded by newer official status updates.'],
    cards:rows.map(row=>({
      type:'news',
      title:row.title,
      source:row.source,
      url:row.url,
      published_at:row.published_at,
      tags:row.impact_tags||[],
    })),
    sources:updatedSources(data,['fantasyNews']),
    updated_at:data.fantasyNews?.generated_at,
  })
}

const gameToken=value=>String(value||'').toLowerCase().replace(/[^a-z0-9]/g,'')
const gameIsoDate=value=>{ const ms=Date.parse(value||''); return Number.isFinite(ms)?new Date(ms).toISOString().slice(0,10):'' }
const gameCloseTime=(left,right,minutes=10)=>{ const a=Date.parse(left||''), b=Date.parse(right||''); return Number.isFinite(a)&&Number.isFinite(b)&&Math.abs(a-b)<=minutes*60000 }

function gameContextTeamMatches(value, game, side) {
  const prefix=side==='AWAY'?'away':'home'
  const token=gameToken(value)
  return Boolean(token && [gameToken(game?.[prefix]),gameToken(game?.[prefix+'_abbr'])].filter(Boolean).includes(token))
}

function contextGameKeyMatches(gameKey, game) {
  const parts=String(gameKey||'').split('|')
  if(parts.length<3 || !/^\d{4}-\d{2}-\d{2}$/.test(parts[0])) return false
  return gameIsoDate(game?.start_time)===parts[0]
    && gameContextTeamMatches(parts[1],game,'AWAY')
    && gameContextTeamMatches(parts[2],game,'HOME')
}

function contextGameMarketMatches(row, game) {
  if(String(row?.sport||'').toUpperCase()!==String(game?.league||'').toUpperCase()) return false
  if(contextGameKeyMatches(row?.game_key,game)) return true
  const side=String(row?.selection_key||'').toUpperCase()
  if(!['HOME','AWAY'].includes(side) || !gameCloseTime(row?.event_start,game?.start_time,10)) return false
  return gameContextTeamMatches(row?.selection,game,side)
}

function contextNflBridgeMatches(row, bridge, game) {
  if(!gameContextTeamMatches(bridge?.away_team,game,'AWAY')) return false
  if(!gameContextTeamMatches(bridge?.home_team,game,'HOME')) return false
  if(!gameCloseTime(row?.event_start,bridge?.start_dfs,10)) return false
  if(gameToken(row?.player)!==gameToken(bridge?.player_dfs)) return false
  if(gameToken(row?.market_subtype)!==gameToken(bridge?.market)) return false
  if(String(row?.side||'').toUpperCase()!==String(bridge?.side||'').toUpperCase()) return false
  const left=num(row?.line), right=num(bridge?.sportsbook_line??bridge?.dfs_line)
  return left!=null && right!=null && Math.abs(left-right)<0.0001
}

function contextPropRows(data, game) {
  const sport=String(game?.league||'').toUpperCase()
  const rows=(data.propV2?.picks||[]).filter(row=>
    String(row?.sport||'').toUpperCase()===sport && String(row?.lane||'').toUpperCase()==='PROP'
  )
  if(['NBA','NHL'].includes(sport)) return rows.filter(row=>contextGameKeyMatches(row?.game_key,game))
  if(sport==='NFL'){
    const bridges=data.nflDecisions?.props||[]
    const ids=new Set()
    for(const row of rows){
      if(bridges.some(bridge=>contextNflBridgeMatches(row,bridge,game))) ids.add(String(row.event_id||''))
    }
    return rows.filter(row=>ids.has(String(row.event_id||'')))
  }
  return []
}

function contextNewsRows(data, game) {
  const id=String(game?.event_id||'')
  const sport=String(game?.league||'').toUpperCase()
  return (data.askRetrieval?.news_events||[])
    .filter(row=>String(row?.sport||'').toUpperCase()===sport && String(row?.game_event_id??'')===id)
    .sort((a,b)=>(Date.parse(b?.published_or_effective_at||'')||0)-(Date.parse(a?.published_or_effective_at||'')||0))
    .slice(0,8)
}

function gameScopedAnswer(question, data, context = {}) {
  const raw=context?.game_context
  if(String(raw?.surface||'').toUpperCase()!=='GAME_CENTER' || !raw?.event_id || !raw?.league) return null
  const game={...raw,league:String(raw.league).toUpperCase(),event_id:String(raw.event_id)}
  const q=qtext(question)
  if(/\b(survivor|waiver|waivers|faab|free agent|stash|ir stash|defense stream|d\/st|dst|dfs|fanduel|draftkings|daily fantasy|start\/sit|start or sit|parlay|two leg|2 leg)\b/.test(q)) return null
  const gameRows=(data.bettingV2?.picks||[]).filter(row=>contextGameMarketMatches(row,game))
  const propRows=contextPropRows(data,game)
  const newsRows=contextNewsRows(data,game)
  const decisionRank=row=>String(row?.shadow_decision||'').toUpperCase()==='SHADOW_PLAY'?3:String(row?.shadow_decision||'').toUpperCase()==='SHADOW_MONITOR'?2:1
  gameRows.sort((a,b)=>decisionRank(b)-decisionRank(a)||num(b.conservative_expected_value_pct,-999)-num(a.conservative_expected_value_pct,-999))
  propRows.sort((a,b)=>decisionRank(b)-decisionRank(a)||num(b.conservative_edge_pct_points,-999)-num(a.conservative_edge_pct_points,-999))

  if(/\b(score|scores|who is winning|box score|game score)\b/.test(q)){
    const key={NFL:'nflScores',MLB:'mlbScores',NBA:'nbaScores',NHL:'nhlScores',CFB:'cfbScores',CBB:'cbbScores'}[game.league]
    const source=data[key]||{}
    const games=game.league==='MLB'
      ? [...(source.today_games||[]),...(source.recent_games||[]),...(source.next_games||[]),...(source.games||[])]
      : (source.games||[])
    const found=games.find(row=>String(row?.event_id??row?.gamePk??'')===game.event_id)
    if(found) return response({intent:'game_score',take:`${found.away||found.away_abbr} @ ${found.home||found.home_abbr} · ${found.status||'Current game status'}`,confidence:'VERIFIED',cards:[scoreCard(found,game.league)],sources:updatedSources(data,[key]),status:found.final?'FINAL':found.live?'LIVE':'UPCOMING'})
  }

  if(/\b(prop|props|passing yards|rushing yards|receiving yards|receptions|touchdown|interceptions)\b/.test(q)){
    if(!propRows.length) return response({intent:'game_props',take:'No exact-game sportsbook prop is attached to this matchup right now.',confidence:'WAITING',status:'NO_EXACT_PROPS',risk:['Game Scout will not substitute props from another matchup.'],sources:updatedSources(data,['propV2'])})
    const top=propRows[0]
    const plays=propRows.filter(row=>String(row.shadow_decision).toUpperCase()==='SHADOW_PLAY')
    return response({intent:'game_props',take:plays.length?`${top.player} ${top.side} ${top.line} ${nice(top.market_subtype)}`:'No exact-game prop has cleared the V2 PLAY gate.',confidence:plays.length?'V2 PLAY':'WAITING / NO PLAY',status:plays.length?'PLAY':'RESEARCH_ONLY',why:[`${propRows.length} exact-game prop candidate${propRows.length===1?'':'s'} matched this matchup.`,`${top.player} ${top.side} ${top.line} · ${nice(top.selection_rule_status||top.shadow_decision)}.`],risk:['Only props tied to this matchup are shown. PASS and MONITOR are not PLAYs.'],cards:propRows.slice(0,6).map(row=>({type:'prop',title:row.player,side:row.side,line:row.line,market:nice(row.market_subtype),decision:String(row.shadow_decision||'').replace('SHADOW_','')})),sources:updatedSources(data,['propV2'])})
  }

  if(/\b(news|injury|practice|report|reporter|what changed)\b/.test(q)){
    if(!newsRows.length) return response({intent:'game_news',take:'No exact-game news item is attached to this matchup right now.',confidence:'WAITING',status:'NO_EXACT_NEWS',risk:['Game Scout will not pull unrelated team news into this game.'],sources:updatedSources(data,['askRetrieval'])})
    return response({intent:'game_news',take:newsRows[0].title,confidence:'MATCHUP-LINKED REPORTING',why:newsRows.slice(0,4).map(row=>row.detail).filter(Boolean),risk:['Reporting can be superseded by newer official status updates.'],cards:newsRows.slice(0,6).map(row=>({type:'news',title:row.title,source:row.source,url:row.source_url,published_at:row.published_or_effective_at})),sources:updatedSources(data,['askRetrieval'])})
  }

  const plays=[...gameRows,...propRows].filter(row=>String(row.shadow_decision).toUpperCase()==='SHADOW_PLAY')
  const monitors=[...gameRows,...propRows].filter(row=>String(row.shadow_decision).toUpperCase()==='SHADOW_MONITOR')
  const tracked=gameRows.length+propRows.length
  const label=`${game.away||game.away_abbr} @ ${game.home||game.home_abbr}`
  return response({
    intent:'game_zenith',
    take:plays.length?`Sports Zenith has ${plays.length} PLAY${plays.length===1?'':'s'} for ${label}.`:monitors.length?`No PLAY for ${label}; ${monitors.length} exact-game monitor${monitors.length===1?' is':'s are'} still being tracked.`:`No exact-game market has cleared the PLAY gate for ${label}.`,
    confidence:plays.length?'V2 PLAY':monitors.length?'MONITOR / NOT PLAY':'WAITING / NO PLAY',
    status:plays.length?'PLAY':'RESEARCH_ONLY',
    why:[`${gameRows.length} game-market row${gameRows.length===1?'':'s'} and ${propRows.length} sportsbook prop row${propRows.length===1?'':'s'} tied exactly to this matchup.`,tracked?'Sports Zenith uses the same matchup matching rules as the Game Center panels.':'No governed V2 row is attached to this matchup right now.'],
    risk:['Game Scout will not borrow a bet, prop, or player line from another matchup.','PASS and MONITOR remain research states, not recommendations.'],
    cards:[...gameRows.slice(0,3).map(row=>({type:'game_market',title:`${row.selection} · ${nice(row.market)}`,selection:row.selection,market:nice(row.market),line:row.line??row.american_odds,decision:String(row.shadow_decision||'').replace('SHADOW_','')})),...propRows.slice(0,3).map(row=>({type:'prop',title:row.player,side:row.side,line:row.line,market:nice(row.market_subtype),decision:String(row.shadow_decision||'').replace('SHADOW_','')}))],
    sources:updatedSources(data,['bettingV2','propV2','askRetrieval']),
  })
}

function routeAsk(question, data, context = {}) {
  const q=qtext(question)
  const page=String(context?.page||'').trim()
  if(!q) return response({intent:'help',take:'Ask about live scores, betting research, props, Survivor, fantasy, waivers, DFS or player news.',confidence:'READY',followups:['What are the best NFL bets?','Best props today','Who should I start?','Top waiver adds','Survivor pick','Live scores'],sources:updatedSources(data,['nflScores','bettingV2','propV2','survivorV2','askContext','fantasyNews'])})
  const scopedGameAnswer=gameScopedAnswer(question,data,context)
  if(scopedGameAnswer) return scopedGameAnswer
  if(/\b(score|scores|live score|who is winning|box score|game score)\b/.test(q)) return scoreAnswer(question,data)
  if(/\b(parlay|two leg|2 leg)\b/.test(q)) return parlayAnswer(data)
  if(/\b(survivor|survivor pick|pool pick|survivor research|research leader)\b/.test(q)) return survivorAnswer(data)
  if(/\b(waiver|waivers|faab|free agent)\b/.test(q)) return waiversAnswer(data)
  if(/\b(stash|ir stash|returning from ir|return window)\b/.test(q)) return stashAnswer(data)
  if(
    /\b(defense stream|d\/st|dst|streaming defense|defense to stream)\b/.test(q)
    || (/\b(defense|d\/st|dst)\b/.test(q) && /\b(stream|streaming)\b/.test(q))
  ) return defenseAnswer(data)
  if(/\b(dfs|fanduel|draftkings|lineup|daily fantasy)\b/.test(q)) return dfsAnswer(question,data)
  if(/\b(start|sit|flex|start\/sit)\b/.test(q)) return startSitAnswerV3(question,data)
  if(/\b(prizepicks|pick em|pick-em)\b/.test(q)) return propsAnswer(question,data)
  if(/\b(prop|props|passing yards|rushing yards|receiving yards|receptions|touchdown|interceptions)\b/.test(q)) return propsAnswer(question,data)
  if(/\b(best bet|best bets|bets?|picks?|moneyline|spread|total|odds)\b/.test(q)) return bettingAnswer(question,data)

  if(page==='Best Bets') return bettingAnswer(question+' best bet',data)
  if(page==='Props') return propsAnswer(question+' props',data)
  if(page==='PrizePicks') return propsAnswer(question+' prizepicks',data)
  if(page==='Parlays') return parlayAnswer(data)
  if(page==='Survivor') return survivorAnswer(data)
  if(page==='Scores'){
    const feeds=[
      ['NFL','nflScores'],['MLB','mlbScores'],['NBA','nbaScores'],
      ['NHL','nhlScores'],['CFB','cfbScores'],['CBB','cbbScores']
    ]
    const rows=[]
    for(const [league,key] of feeds){
      const source=data[key]||{}
      const games=league==='MLB'?(source.today_games||source.games||[]):(source.games||[])
      for(const game of games) rows.push({league,game})
    }
    const live=rows.filter(item=>item.game.live)
    const upcoming=rows.filter(item=>!item.game.live&&!item.game.final)
    const chosen=(live.length?live:upcoming).slice(0,8)
    return response({
      intent:'score_center',
      take:live.length
        ? live.length+' game'+(live.length===1?' is':'s are')+' live across the connected score center right now.'
        : upcoming.length
          ? 'No game is live right now. '+upcoming.length+' upcoming game'+(upcoming.length===1?' is':'s are')+' in the connected score window.'
          : 'No live or upcoming game is in the current connected score window.',
      confidence:'VERIFIED',
      cards:chosen.map(item=>scoreCard(item.game,item.league)),
      sources:updatedSources(data,['nflScores','mlbScores','nbaScores','nhlScores','cfbScores','cbbScores']),
      status:rows.length?'CURRENT':'NO_GAMES',
      followups:['NBA scores','NHL scores','CFB scores','Show the full score center']
    })
  }
  if(page==='News & Insights') return newsAnswerV2(question,data)
  if(page==='Fantasy') return response({
    intent:'fantasy_context',
    take:'Fantasy research is live. Signed-in users with an active saved team get private roster-aware context where that lane supports it; otherwise Sports Zenith stays on the generic research board.',
    confidence:'FANTASY RESEARCH',
    why:['Weekly, FAAB, IR stash, defense streaming and IDP lanes are connected.','Start/Sit, Waivers, IR, Defense and IDP can use the active saved team when authenticated.'],
    risk:['Generic rankings are never silently presented as personalized start/sit, free-agent availability or bid instructions.'],
    followups:['Top waiver adds','Best defense stream','Who should I start?','Show IR stash candidates'],
    sources:updatedSources(data,['askContext']),
    updated_at:data.askContext?.generated_at,
    status:'RESEARCH_ONLY'
  })
  if(page==='Brain Record'){
    const official=data.performance?.official||{}
    return response({
      intent:'brain_record',
      take:`Official record: ${official.wins??0}-${official.losses??0}-${official.pushes??0} with ${official.units==null?'units still calculating':Number(official.units).toFixed(2)+'u'}.`,
      confidence:'OFFICIAL RECORD',
      why:[
        `${official.published??0} published · ${official.pending??0} pending · ${official.settled??0} settled.`,
        official.roi_pct==null?'ROI waits for settled priced picks.':`ROI ${Number(official.roi_pct).toFixed(1)}% from captured official prices.`,
        'Historical research is shown separately and is never backfilled into the official headline record.'
      ],
      risk:['Small forward samples can move sharply; official results are not a guarantee of future performance.'],
      followups:['How is the official record calculated?','What is promising but not proven?','Why are there no Best Bet PLAYs?'],
      sources:updatedSources(data,['performance']),
      updated_at:data.performance?.generated_at,
      status:official.status||'TRACKING'
    })
  }

  if(/\b(player news|latest news|news matters|news today|what matters today)\b/.test(q)) {
    return newsAnswerV2(question,data)
  }
  if(/\b(news|injury|practice|report|reporter|reporting|beat writer|what changed|saying)\b/.test(q)) {
    const reporting=reportingAnswer(question,data)
    return reporting || newsAnswerV2(question,data)
  }
  if(/\b(mlb|baseball)\b/.test(q)) return scoreAnswer(question,data)
  const playerMatches=matchPlayers(question,weeklyRows(data)); if(playerMatches.length) return startSitAnswerV3(question,data)
  const reporting=reportingAnswer(question,data); if(reporting) return reporting
  return response({intent:'help',take:'I can answer this once it maps to a connected data lane. Try a score, player, bet, prop, Survivor, fantasy, waiver, DFS or news question.',confidence:'UNKNOWN',why:['No connected intent matched this question yet.'],risk:['The analyst will not invent an answer when the required data lane is not wired.'],followups:['Best NFL bets','Best props','Live scores','Top waiver adds','Survivor pick'],sources:updatedSources(data,['nflScores','bettingV2','propV2','survivorV2','askContext','fantasyNews']),status:'UNKNOWN'})
}

const ESPN_SUMMARY_ENDPOINTS = {
  NBA: 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=',
  NHL: 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary?event=',
  CFB: 'https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event=',
  CBB: 'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary?event=',
}

async function fetchEspnBoxscore(league, eventId) {
  const base = ESPN_SUMMARY_ENDPOINTS[String(league || '').toUpperCase()]
  if (!base || !/^\d+$/.test(String(eventId || ''))) throw new Error('Unsupported box score request')
  const resp = await fetch(base + encodeURIComponent(String(eventId)), {
    headers: { 'user-agent': 'Mozilla/5.0 SportsZenith/1.0' },
  })
  if (!resp.ok) throw new Error(`ESPN summary returned ${resp.status}`)
  const payload = await resp.json()
  const box = payload.boxscore || {}

  const preferred = {
    NBA: ['fieldGoalPct','threePointFieldGoalPct','freeThrowPct','totalRebounds','assists','turnovers','steals','blocks'],
    CBB: ['fieldGoalPct','threePointFieldGoalPct','freeThrowPct','totalRebounds','assists','turnovers','steals','blocks'],
    NHL: ['shots','hits','powerPlay','faceoffPercent','blockedShots','giveaways','takeaways','penaltyMinutes'],
    CFB: ['firstDowns','thirdDownEff','totalYards','netPassingYards','rushingYards','turnovers','possessionTime','sacksYardsLost'],
  }[String(league).toUpperCase()] || []

  const teams = (box.teams || []).map(row => {
    const team = row.team || {}
    const stats = row.statistics || []
    const byName = Object.fromEntries(stats.map(stat => [stat.name, stat]))
    const chosen = preferred.map(name => byName[name]).filter(Boolean)
    const display = (chosen.length ? chosen : stats.slice(0, 8)).map(stat => ({
      name: stat.name,
      label: stat.abbreviation || stat.label || stat.name,
      value: stat.displayValue ?? stat.value ?? '—',
    }))
    return {
      team: team.displayName || team.shortDisplayName || team.name,
      abbreviation: team.abbreviation,
      logo: team.logo,
      homeAway: row.homeAway,
      stats: display,
    }
  })

  const leaders = []
  for (const side of payload.leaders || []) {
    const team = side.team || {}
    for (const category of side.leaders || []) {
      const lead = (category.leaders || [])[0]
      if (!lead) continue
      const athlete = lead.athlete || {}
      leaders.push({
        team: team.abbreviation || team.displayName,
        category: category.displayName || category.name,
        player: athlete.displayName || athlete.fullName,
        value: lead.displayValue ?? lead.value ?? '—',
        headshot: athlete.headshot?.href || null,
      })
    }
  }

  return {
    status: 'READY',
    league: String(league).toUpperCase(),
    event_id: String(eventId),
    teams,
    leaders: leaders.slice(0, 12),
    venue: payload.gameInfo?.venue?.fullName || null,
    attendance: payload.gameInfo?.attendance || null,
    weather: payload.gameInfo?.weather || null,
    source: 'ESPN',
    generated_at: new Date().toISOString(),
  }
}

const RATE_LIMIT_BUCKETS = new Map()

function clientIp(req) {
  const forwarded = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim()
  return forwarded || req.socket?.remoteAddress || 'unknown'
}

function consumeRateLimit(key, limit, windowMs) {
  const now = Date.now()
  const current = RATE_LIMIT_BUCKETS.get(key)
  if (!current || current.resetAt <= now) {
    RATE_LIMIT_BUCKETS.set(key, { count: 1, resetAt: now + windowMs })
    return { ok: true, remaining: limit - 1, retryAfterMs: 0 }
  }

  if (current.count >= limit) {
    return { ok: false, remaining: 0, retryAfterMs: Math.max(1, current.resetAt - now) }
  }

  current.count += 1
  return { ok: true, remaining: Math.max(0, limit - current.count), retryAfterMs: 0 }
}

async function readBody(req) {
  let body=''
  for await (const chunk of req) { body+=chunk; if(body.length>1_000_000) throw new Error('request too large') }
  return body ? JSON.parse(body) : {}
}

function runDfsOptimizer(payload) {
  return new Promise((resolve, reject) => {
    const child = spawn(SPORTS_PYTHON, [DFS_BRIDGE], {
      cwd: SPORTS_ROOT,
      stdio: ['pipe', 'pipe', 'pipe'],
    })

    let stdout = ''
    let stderr = ''
    const timer = setTimeout(() => {
      child.kill('SIGKILL')
      reject(new Error('DFS optimizer timed out'))
    }, 15000)

    child.stdout.on('data', chunk => { stdout += chunk.toString() })
    child.stderr.on('data', chunk => { stderr += chunk.toString() })

    child.on('error', err => {
      clearTimeout(timer)
      reject(err)
    })

    child.on('close', code => {
      clearTimeout(timer)
      let parsed = null
      try { parsed = JSON.parse(stdout || '{}') } catch {}
      if (code !== 0 || !parsed || parsed.status === 'ERROR') {
        reject(new Error(parsed?.error || stderr.trim() || 'DFS optimizer failed'))
        return
      }
      resolve(parsed)
    })

    child.stdin.end(JSON.stringify(payload || {}))
  })
}

function runRateMyTeam(payload) {
  return new Promise((resolve, reject) => {
    const child = spawn(SPORTS_PYTHON, [RATE_MY_TEAM_BRIDGE], {
      cwd: SPORTS_ROOT,
      stdio: ['pipe', 'pipe', 'pipe'],
    })

    let stdout = ''
    let stderr = ''
    const timer = setTimeout(() => {
      child.kill('SIGKILL')
      reject(new Error('Rate My Team timed out'))
    }, 12000)

    child.stdout.on('data', chunk => {
      stdout += chunk.toString()
      if (stdout.length > 2_000_000) {
        child.kill('SIGKILL')
        reject(new Error('Rate My Team response exceeded limit'))
      }
    })
    child.stderr.on('data', chunk => {
      stderr += chunk.toString()
      if (stderr.length > 200_000) stderr = stderr.slice(-200_000)
    })

    child.on('error', err => {
      clearTimeout(timer)
      reject(err)
    })

    child.on('close', code => {
      clearTimeout(timer)
      let parsed = null
      try { parsed = JSON.parse(stdout || '{}') } catch {}
      if (code !== 0 || !parsed || parsed.status === 'ERROR') {
        reject(new Error(parsed?.error || stderr.trim() || 'Rate My Team failed'))
        return
      }
      resolve(parsed)
    })

    child.stdin.end(JSON.stringify(payload || {}))
  })
}

function runWaiverFit(payload) {
  return new Promise((resolve, reject) => {
    const child = spawn(SPORTS_PYTHON, [WAIVER_FIT_BRIDGE], {
      cwd: SPORTS_ROOT,
      stdio: ['pipe', 'pipe', 'pipe'],
    })

    let stdout = ''
    let stderr = ''
    const timer = setTimeout(() => {
      child.kill('SIGKILL')
      reject(new Error('Waiver fit timed out'))
    }, 12000)

    child.stdout.on('data', chunk => {
      stdout += chunk.toString()
      if (stdout.length > 2_000_000) {
        child.kill('SIGKILL')
        reject(new Error('Waiver fit response exceeded limit'))
      }
    })
    child.stderr.on('data', chunk => {
      stderr += chunk.toString()
      if (stderr.length > 200_000) stderr = stderr.slice(-200_000)
    })

    child.on('error', err => {
      clearTimeout(timer)
      reject(err)
    })

    child.on('close', code => {
      clearTimeout(timer)
      let parsed = null
      try { parsed = JSON.parse(stdout || '{}') } catch {}
      if (code !== 0 || !parsed || parsed.status === 'ERROR') {
        reject(new Error(parsed?.error || stderr.trim() || 'Waiver fit failed'))
        return
      }
      resolve(parsed)
    })

    child.stdin.end(JSON.stringify(payload || {}))
  })
}

function runIrStashFit(payload) {
  return new Promise((resolve, reject) => {
    const child = spawn(SPORTS_PYTHON, [IR_STASH_FIT_BRIDGE], {
      cwd: SPORTS_ROOT,
      stdio: ['pipe', 'pipe', 'pipe'],
    })

    let stdout = ''
    let stderr = ''
    const timer = setTimeout(() => {
      child.kill('SIGKILL')
      reject(new Error('IR stash fit timed out'))
    }, 12000)

    child.stdout.on('data', chunk => {
      stdout += chunk.toString()
      if (stdout.length > 2_000_000) {
        child.kill('SIGKILL')
        reject(new Error('IR stash fit response exceeded limit'))
      }
    })
    child.stderr.on('data', chunk => {
      stderr += chunk.toString()
      if (stderr.length > 200_000) stderr = stderr.slice(-200_000)
    })

    child.on('error', err => {
      clearTimeout(timer)
      reject(err)
    })

    child.on('close', code => {
      clearTimeout(timer)
      let parsed = null
      try { parsed = JSON.parse(stdout || '{}') } catch {}
      if (code !== 0 || !parsed || parsed.status === 'ERROR') {
        reject(new Error(parsed?.error || stderr.trim() || 'IR stash fit failed'))
        return
      }
      resolve(parsed)
    })

    child.stdin.end(JSON.stringify(payload || {}))
  })
}

function runDefenseStreamFit(payload) {
  return new Promise((resolve, reject) => {
    const child = spawn(SPORTS_PYTHON, [DEFENSE_STREAM_FIT_BRIDGE], {
      cwd: SPORTS_ROOT,
      stdio: ['pipe', 'pipe', 'pipe'],
    })

    let stdout = ''
    let stderr = ''
    const timer = setTimeout(() => {
      child.kill('SIGKILL')
      reject(new Error('Defense streaming fit timed out'))
    }, 12000)

    child.stdout.on('data', chunk => {
      stdout += chunk.toString()
      if (stdout.length > 2_000_000) {
        child.kill('SIGKILL')
        reject(new Error('Defense streaming fit response exceeded limit'))
      }
    })
    child.stderr.on('data', chunk => {
      stderr += chunk.toString()
      if (stderr.length > 200_000) stderr = stderr.slice(-200_000)
    })

    child.on('error', err => {
      clearTimeout(timer)
      reject(err)
    })

    child.on('close', code => {
      clearTimeout(timer)
      let parsed = null
      try { parsed = JSON.parse(stdout || '{}') } catch {}
      if (code !== 0 || !parsed || parsed.status === 'ERROR') {
        reject(new Error(parsed?.error || stderr.trim() || 'Defense streaming fit failed'))
        return
      }
      resolve(parsed)
    })

    child.stdin.end(JSON.stringify(payload || {}))
  })
}

function runIdpFit(payload) {
  return new Promise((resolve, reject) => {
    const child = spawn(SPORTS_PYTHON, [IDP_FIT_BRIDGE], {
      cwd: SPORTS_ROOT,
      stdio: ['pipe', 'pipe', 'pipe'],
    })

    let stdout = ''
    let stderr = ''
    const timer = setTimeout(() => {
      child.kill('SIGKILL')
      reject(new Error('IDP fit timed out'))
    }, 12000)

    child.stdout.on('data', chunk => {
      stdout += chunk.toString()
      if (stdout.length > 2_000_000) {
        child.kill('SIGKILL')
        reject(new Error('IDP fit response exceeded limit'))
      }
    })
    child.stderr.on('data', chunk => {
      stderr += chunk.toString()
      if (stderr.length > 200_000) stderr = stderr.slice(-200_000)
    })

    child.on('error', err => {
      clearTimeout(timer)
      reject(err)
    })

    child.on('close', code => {
      clearTimeout(timer)
      let parsed = null
      try { parsed = JSON.parse(stdout || '{}') } catch {}
      if (code !== 0 || !parsed || parsed.status === 'ERROR') {
        reject(new Error(parsed?.error || stderr.trim() || 'IDP fit failed'))
        return
      }
      resolve(parsed)
    })

    child.stdin.end(JSON.stringify(payload || {}))
  })
}

function runFormatContext(payload) {
  return new Promise((resolve, reject) => {
    const child = spawn(SPORTS_PYTHON, [FORMAT_CONTEXT_BRIDGE], {
      cwd: SPORTS_ROOT,
      stdio: ['pipe', 'pipe', 'pipe'],
    })

    let stdout = ''
    let stderr = ''
    const timer = setTimeout(() => {
      child.kill('SIGKILL')
      reject(new Error('Scoring-format context timed out'))
    }, 12000)

    child.stdout.on('data', chunk => {
      stdout += chunk.toString()
      if (stdout.length > 2_000_000) {
        child.kill('SIGKILL')
        reject(new Error('Scoring-format context response exceeded limit'))
      }
    })
    child.stderr.on('data', chunk => {
      stderr += chunk.toString()
      if (stderr.length > 200_000) stderr = stderr.slice(-200_000)
    })

    child.on('error', err => {
      clearTimeout(timer)
      reject(err)
    })

    child.on('close', code => {
      clearTimeout(timer)
      let parsed = null
      try { parsed = JSON.parse(stdout || '{}') } catch {}
      if (code !== 0 || !parsed || parsed.status === 'ERROR') {
        reject(new Error(parsed?.error || stderr.trim() || 'Scoring-format context failed'))
        return
      }
      resolve(parsed)
    })

    child.stdin.end(JSON.stringify(payload || {}))
  })
}


function personalFantasyIntent(question) {
  const q=qtext(question)
  if(
    /\b(defense stream|d\/st|dst|streaming defense|defense to stream)\b/.test(q)
    || (/\b(defense|d\/st|dst)\b/.test(q) && /\b(stream|streaming|hold|drop|rotate|add)\b/.test(q))
  ) return 'defense_streaming'
  if(/\b(ir stash|stash|stashes|returning from ir|return window|ir slot|ir spots?|room on ir|injured reserve)\b/.test(q)) return 'ir_stash'
  if(/\b(idp|linebacker|linebackers|defensive back|defensive backs|edge rusher|edge rushers|defensive line|dl\b|lb\b|db\b)\b/.test(q)) return 'idp'
  if(/\b(start|starts|sit|sits|flex|start\/sit|lineup)\b/.test(q)) return 'start_sit'
  if(/\b(waiver|waivers|faab|free agent|free agents|add|adds|drop|drops|cut|cuts)\b/.test(q)) return 'waivers'
  return null
}

async function privateFantasySnapshot(req, endpoint, leagueId) {
  const authorization=String(req.headers.authorization||'').trim()
  const id=String(leagueId||'').trim()
  if(!authorization||!id) return null
  try{
    const response=await fetch(
      `http://127.0.0.1:${PORT}${endpoint}?league_id=${encodeURIComponent(id)}`,
      {headers:{authorization}}
    )
    if(!response.ok) return null
    const payload=await response.json()
    return payload?.status==='READY'?payload:null
  }catch{
    return null
  }
}

function privateFantasySource(snapshot, lane) {
  const team=snapshot?.league?.team_name||snapshot?.league?.league_name||'Saved team'
  return [{
    label:`${team} · ${lane}`,
    source:'PRIVATE_SAVED_FANTASY_TEAM',
  }]
}

function personalizedStartSitAnswer(question, snapshot) {
  const q=qtext(question)
  const league=snapshot.league||{}
  const team=league.team_name||league.league_name||'your saved team'
  const lineup=snapshot.lineup_research||{}
  const players=Array.isArray(snapshot.players)?snapshot.players:[]
  const matched=players.filter(row=>{
    const name=String(row.player||'').trim().toLowerCase()
    return name&&name.length>=3&&q.includes(name)
  }).sort((a,b)=>num(b.weekly_research_score,-999)-num(a.weekly_research_score,-999))

  if(matched.length){
    const top=matched[0]
    const second=matched[1]||null
    const starter=(lineup.starter_candidates||[]).find(row=>String(row.player_key||row.player)===String(top.player_key||top.player))
    return response({
      intent:'personal_start_sit',
      take:second
        ? `For ${team}, start ${top.player} over ${second.player} on the current personalized research.`
        : `For ${team}, ${top.player} is the stronger current Start/Sit research option.`,
      confidence:'PERSONAL ROSTER RESEARCH',
      status:'PERSONALIZED_RESEARCH',
      why:[
        `Weekly research score ${top.weekly_research_score??'—'} · ${nice(top.weekly_tier||'UNKNOWN')}.`,
        starter?`Fits your saved ${starter.assigned_slot}${starter.slot_index>1?' '+starter.slot_index:''} research slot.`:null,
        top.research_reasons||null,
      ].filter(Boolean),
      risk:[
        'This is research, not a fantasy-point projection or guaranteed result.',
        lineup.scoring_format_used_as_tiebreaker
          ? `${nice(lineup.scoring_format)} historical context was only allowed to break close calls within the saved guardrail.`
          : 'Weekly research remains the primary signal.',
      ],
      cards:matched.slice(0,5).map(row=>({
        type:'personal_fantasy',
        title:row.player,
        opponent:row.opponent,
        score:row.weekly_research_score,
        tier:row.weekly_tier,
        role:row.role_signal,
      })),
      sources:privateFantasySource(snapshot,'Start / Sit'),
      updated_at:league.last_synced_at,
    })
  }

  const starters=Array.isArray(lineup.starter_candidates)?lineup.starter_candidates:[]
  if(starters.length){
    const labels=starters.slice(0,8).map(row=>`${row.assigned_slot}: ${row.player}`)
    return response({
      intent:'personal_start_sit',
      take:`For ${team}, your current slot-aware starter research is ${labels.join(' · ')}.`,
      confidence:'PERSONAL SLOT-AWARE RESEARCH',
      status:'PERSONALIZED_RESEARCH',
      why:[
        `${starters.length} starter candidate${starters.length===1?'':'s'} filled from your saved roster and starter slots.`,
        `Saved scoring format: ${nice(lineup.scoring_format||'NOT SET')}.`,
      ],
      risk:['These are research-ranked starter candidates, not fantasy-point projections or an official platform lineup.'],
      cards:starters.slice(0,6).map(row=>({
        type:'personal_fantasy',
        title:row.player,
        selection:row.assigned_slot,
        opponent:row.opponent,
        score:row.weekly_research_score,
        tier:row.weekly_tier,
      })),
      sources:privateFantasySource(snapshot,'Start / Sit'),
      updated_at:league.last_synced_at,
    })
  }

  return response({
    intent:'personal_start_sit',
    take:`I found ${team}, but I need saved starter-slot context or specific player names to make this Start/Sit comparison personal.`,
    confidence:'PERSONAL CONTEXT PARTIAL',
    status:'PERSONALIZED_RESEARCH',
    risk:['No generic player is being substituted for your saved roster.'],
    sources:privateFantasySource(snapshot,'Start / Sit'),
    updated_at:league.last_synced_at,
  })
}

async function personalizedWaiverAnswer(req, question, snapshot, leagueId) {
  const q=qtext(question)
  const league=snapshot.league||{}
  const team=league.team_name||league.league_name||'your saved team'
  const wantsDrop=/\b(drop|drops|cut|cuts|who should i get rid|who can i drop)\b/.test(q)

  if(wantsDrop){
    const startSit=await privateFantasySnapshot(req,'/api/fantasy/start-sit',leagueId)
    const bench=startSit?.lineup_research?.bench_candidates||[]
    const pool=(bench.length?bench:(startSit?.players||[]))
      .filter(row=>row&&row.player)
      .sort((a,b)=>
        num(a.research_index,999)-num(b.research_index,999)
        || num(a.ros_research_score,999)-num(b.ros_research_score,999)
        || num(a.weekly_research_score,999)-num(b.weekly_research_score,999)
      )
    const candidate=pool[0]||null
    if(candidate){
      return response({
        intent:'personal_drop_review',
        take:`For ${team}, ${candidate.player} is the first drop-review candidate from your current roster research — not an automatic drop.`,
        confidence:'DROP REVIEW RESEARCH',
        status:'PERSONALIZED_RESEARCH',
        why:[
          candidate.research_index!=null?`Roster research index ${candidate.research_index}.`:null,
          candidate.ros_research_score!=null?`ROS research score ${candidate.ros_research_score}.`:null,
          candidate.weekly_research_score!=null?`Weekly research score ${candidate.weekly_research_score}.`:null,
        ].filter(Boolean),
        risk:[
          'A low research rank does not automatically mean the player should be dropped.',
          'Sports Zenith has not verified which waiver replacements are actually available in your league.',
        ],
        cards:[{
          type:'personal_drop_review',
          title:candidate.player,
          team:candidate.team,
          position:candidate.position,
          score:candidate.research_index??candidate.ros_research_score??candidate.weekly_research_score,
        }],
        sources:privateFantasySource(snapshot,'Waivers / Drop review'),
        updated_at:league.last_synced_at,
      })
    }
  }

  const targets=Array.isArray(snapshot.targets)?snapshot.targets:[]
  const top=targets[0]||null
  if(!top){
    return response({
      intent:'personal_waivers',
      take:`I loaded ${team}, but no roster-aware waiver target cleared the current filter.`,
      confidence:'WAITING / NO TARGET',
      status:'PERSONALIZED_RESEARCH',
      risk:['No waiver add is being invented to fill an empty result.'],
      sources:privateFantasySource(snapshot,'Waivers'),
      updated_at:league.last_synced_at,
    })
  }

  const budget=top.budget_planning||{}
  return response({
    intent:'personal_waivers',
    take:`For ${team}, ${top.player} is the top roster-aware waiver target to check right now.`,
    confidence:'PERSONAL WAIVER RESEARCH',
    status:'PERSONALIZED_RESEARCH',
    why:[
      `${top.position||'—'} roster need score ${top.roster_need_score??'—'} · waiver research ${top.waiver_research_score??'—'}.`,
      `Generic FAAB research range ${top.research_faab_low_pct??'—'}–${top.research_faab_high_pct??'—'}%.`,
      budget.connected?`Saved-budget translation ${budget.research_low_units??'—'}–${budget.research_high_units??'—'} units · ${nice(budget.budget_pressure)}.`:null,
    ].filter(Boolean),
    risk:[
      'Sports Zenith has not verified that this player is available in your league.',
      'FAAB percentage and budget translation are research planning ranges, not winning-bid predictions.',
    ],
    cards:targets.slice(0,6).map(row=>({
      type:'personal_waiver',
      title:row.player,
      team:row.team,
      position:row.position,
      score:row.roster_fit_research_score,
      priority:row.waiver_priority,
    })),
    sources:privateFantasySource(snapshot,'Waivers'),
    updated_at:league.last_synced_at,
  })
}

function personalizedIrAnswer(question, snapshot) {
  const q=qtext(question)
  const league=snapshot.league||{}
  const team=league.team_name||league.league_name||'your saved team'
  const capacity=snapshot.ir_capacity||{}
  const wantsRoom=/\b(room|open|space|slot|spot|spots|capacity)\b/.test(q)
  if(wantsRoom){
    const open=Number(capacity.likely_open_slots||0)
    return response({
      intent:'personal_ir_capacity',
      take:open>0
        ? `For ${team}, you appear to have ${open} likely open IR slot${open===1?'':'s'} based on your saved settings.`
        : `For ${team}, there are no likely open IR slots based on the current saved roster and IR-slot count.`,
      confidence:'PERSONAL IR CAPACITY RESEARCH',
      status:'PERSONALIZED_RESEARCH',
      why:[
        `${capacity.saved_ir_slots??0} saved IR slot${Number(capacity.saved_ir_slots||0)===1?'':'s'}.`,
        `${capacity.likely_ir_designation_count??0} roster player${Number(capacity.likely_ir_designation_count||0)===1?'':'s'} with likely IR/PUP designation context.`,
      ],
      risk:['Actual IR eligibility depends on the fantasy platform and league rules and is not verified here.'],
      sources:privateFantasySource(snapshot,'IR / Stash'),
      updated_at:league.last_synced_at,
    })
  }

  const rosterInjured=Array.isArray(snapshot.roster_injured)?snapshot.roster_injured:[]
  const top=rosterInjured[0]||null
  const outside=(snapshot.outside_targets_to_check||[])[0]||null
  return response({
    intent:'personal_ir_stash',
    take:top
      ? `For ${team}, ${top.player} is the first roster injury/stash case to review: ${nice(top.roster_action_research)}.`
      : outside
        ? `Your saved roster has no matched stash case; ${outside.player} is the top outside stash name to check.`
        : `No current IR/stash target cleared the personalized filter for ${team}.`,
    confidence:'PERSONAL IR/STASH RESEARCH',
    status:'PERSONALIZED_RESEARCH',
    why:top?[
      `Status ${nice(top.status||'UNKNOWN')} · stash research ${top.stash_research_score??'—'}.`,
      `Return window ${nice(top.return_window||'UNKNOWN')}.`,
    ]:[],
    risk:[
      'Return dates are not guarantees.',
      'Platform IR eligibility and outside-player league availability are not verified.',
    ],
    cards:rosterInjured.slice(0,5).map(row=>({
      type:'personal_ir',
      title:row.player,
      team:row.team,
      position:row.position,
      status:row.status,
      score:row.stash_research_score,
    })),
    sources:privateFantasySource(snapshot,'IR / Stash'),
    updated_at:league.last_synced_at,
  })
}

function personalizedDefenseAnswer(snapshot) {
  const league=snapshot.league||{}
  const team=league.team_name||league.league_name||'your saved team'
  const saved=(snapshot.saved_defenses||[])[0]||null
  const alternative=(snapshot.alternatives_to_check||[])[0]||null
  if(!saved){
    return response({
      intent:'personal_defense_stream',
      take:`I loaded ${team}, but no D/ST was recognized on the saved roster.`,
      confidence:'PERSONAL CONTEXT PARTIAL',
      status:'PERSONALIZED_RESEARCH',
      risk:['Add the defense to My Teams to enable a direct personalized comparison.'],
      sources:privateFantasySource(snapshot,'Defense streaming'),
      updated_at:league.last_synced_at,
    })
  }

  const compare=String(saved.research_action||'').includes('COMPARE')
  return response({
    intent:'personal_defense_stream',
    take:compare&&alternative
      ? `For ${team}, ${saved.player} is a ${nice(saved.research_action)} case; ${alternative.player} is the top outside defense to check.`
      : `For ${team}, ${saved.player} currently rates ${nice(saved.research_action||'HOLD OR COMPARE RESEARCH')}.`,
    confidence:'PERSONAL DEFENSE RESEARCH',
    status:'PERSONALIZED_RESEARCH',
    why:[
      `Weekly stream score ${saved.weekly_stream_score??'—'} · rank #${saved.weekly_rank??'—'}.`,
      `Multi-week hold score ${saved.multiweek_hold_score??'—'} · rank #${saved.multiweek_rank??'—'}.`,
      `Next opponent ${saved.next_opponent||'—'} · ${nice(saved.future_schedule_signal||'UNKNOWN')} future schedule.`,
    ],
    risk:[
      'This is not an automatic drop command.',
      'Sports Zenith has not verified that any outside defense is available in your league.',
    ],
    cards:[
      {type:'personal_defense',title:saved.player,opponent:saved.next_opponent,score:saved.weekly_stream_score,tier:saved.weekly_stream_tier},
      ...(alternative?[{type:'defense_to_check',title:alternative.player,opponent:alternative.next_opponent,score:alternative.weekly_stream_score,tier:alternative.weekly_stream_tier}]:[]),
    ],
    sources:privateFantasySource(snapshot,'Defense streaming'),
    updated_at:league.last_synced_at,
  })
}

function personalizedIdpAnswer(snapshot) {
  const league=snapshot.league||{}
  const team=league.team_name||league.league_name||'your saved team'
  const starters=Array.isArray(snapshot.starter_candidates)?snapshot.starter_candidates:[]
  const open=Array.isArray(snapshot.open_slots)?snapshot.open_slots:[]
  const targets=Array.isArray(snapshot.outside_targets_to_check)?snapshot.outside_targets_to_check:[]
  const top=starters[0]||snapshot.matched_idp?.[0]||null
  return response({
    intent:'personal_idp',
    take:top
      ? `For ${team}, ${top.player} is your strongest current IDP usage research signal${top.assigned_slot?' for '+top.assigned_slot:''}.`
      : `I loaded ${team}, but no saved IDP player matched the current usage board.`,
    confidence:'PERSONAL IDP USAGE RESEARCH',
    status:'PERSONALIZED_RESEARCH',
    why:top?[
      `IDP usage score ${top.idp_usage_score??'—'} · ${nice(top.idp_usage_tier||'UNKNOWN')}.`,
      `Snap share ${top.snap_pct??'—'}% · snap change ${top.snap_pct_change??'—'} points.`,
      open.length?`${open.length} saved IDP slot${open.length===1?' is':'s are'} still open in the research lineup.`:null,
    ].filter(Boolean):[],
    risk:[
      'IDP output is usage/snap research, not a fantasy-points projection.',
      'Custom tackle/sack/turnover scoring and outside-player availability are not verified.',
    ],
    cards:[
      ...starters.slice(0,5).map(row=>({type:'personal_idp',title:row.player,selection:row.assigned_slot,score:row.idp_usage_score,tier:row.idp_usage_tier})),
      ...targets.slice(0,1).map(row=>({type:'idp_to_check',title:row.player,score:row.idp_usage_score,tier:row.idp_usage_tier})),
    ],
    sources:privateFantasySource(snapshot,'IDP'),
    updated_at:league.last_synced_at,
  })
}


function attachPersonalFantasyFreshness(answer, snapshot) {
  if (!answer || typeof answer !== 'object') return answer
  const freshness = snapshot?.research_freshness
  if (!freshness || typeof freshness !== 'object') return answer

  const status = String(freshness.status || 'UNKNOWN').toUpperCase()
  const age = freshness.age_minutes == null || freshness.age_minutes === '' ? null : Number(freshness.age_minutes)
  const maxAge = freshness.max_age_minutes == null || freshness.max_age_minutes === '' ? null : Number(freshness.max_age_minutes)
  const why = [...(Array.isArray(answer.why) ? answer.why : [])]
  const risk = [...(Array.isArray(answer.risk) ? answer.risk : [])]

  const ageText = Number.isFinite(age) ? `${age} min old` : 'age unknown'
  why.push(
    `Research freshness: ${status} · ${ageText}${Number.isFinite(maxAge) ? ` · target ≤ ${maxAge} min` : ''}.`
  )

  if (['AGING','STALE','MISSING','UNKNOWN'].includes(status)) {
    risk.push(
      status === 'AGING'
        ? 'This Fantasy research is aging past its normal freshness target; newer source data may change the result.'
        : status === 'STALE'
          ? 'This Fantasy research is stale; treat the recommendation as provisional until the source refreshes.'
          : status === 'MISSING'
            ? 'The Fantasy research source is missing, so this answer may be incomplete.'
            : 'The Fantasy research source freshness could not be verified.'
    )
  }

  if (freshness.roster_newer_than_research === true) {
    const delta = Number(freshness.roster_ahead_minutes)
    risk.push(
      `Your saved roster changed${Number.isFinite(delta) ? ` ${delta} min` : ''} after this research snapshot; the roster selection is current, but the player research predates that edit.`
    )
  }

  return {
    ...answer,
    why,
    risk,
    updated_at:freshness.source_timestamp || answer.updated_at || null,
    research_freshness:freshness,
  }
}

async function personalizedFantasyAsk(req, question, context={}) {
  const intent=personalFantasyIntent(question)
  const leagueId=String(context?.fantasy_league_id||'').trim()
  if(!intent||!leagueId||!bearerToken(req)) return null

  const endpoint={
    start_sit:'/api/fantasy/start-sit',
    waivers:'/api/fantasy/waivers',
    ir_stash:'/api/fantasy/ir-stash',
    defense_streaming:'/api/fantasy/defense-streaming',
    idp:'/api/fantasy/idp',
  }[intent]
  if(!endpoint) return null

  const snapshot=await privateFantasySnapshot(req,endpoint,leagueId)
  if(!snapshot) return null

  let answer=null
  if(intent==='start_sit') answer=personalizedStartSitAnswer(question,snapshot)
  else if(intent==='waivers') answer=await personalizedWaiverAnswer(req,question,snapshot,leagueId)
  else if(intent==='ir_stash') answer=personalizedIrAnswer(question,snapshot)
  else if(intent==='defense_streaming') answer=personalizedDefenseAnswer(snapshot)
  else if(intent==='idp') answer=personalizedIdpAnswer(snapshot)

  return answer ? attachPersonalFantasyFreshness(answer,snapshot) : null
}

async function serveStatic(req,res,pathname) {
  let requested=pathname==='/'?'/index.html':pathname, filePath=path.resolve(DIST,'.'+requested)
  if(!filePath.startsWith(path.resolve(DIST))){res.writeHead(403,SECURITY_HEADERS);res.end('Forbidden');return}
  try{const info=await stat(filePath); if(info.isDirectory()) filePath=path.join(filePath,'index.html')}catch{filePath=path.join(DIST,'index.html')}
  const ext=path.extname(filePath).toLowerCase()
  res.writeHead(200,{
    ...SECURITY_HEADERS,
    'content-type':MIME[ext]||'application/octet-stream',
    'cache-control':ext==='.html'?'no-cache':'public, max-age=300',
  })
  createReadStream(filePath).pipe(res)
}

const server=http.createServer(async(req,res)=>{
  const url=new URL(req.url,`http://${req.headers.host||'localhost'}`)
  if(req.method==='GET'&&url.pathname==='/api/health'){
    const data=await loadAll(); return json(res,200,{status:'ok',generated_at:new Date().toISOString(),sources:{nfl_scores:Boolean(data.nflScores),mlb_scores:Boolean(data.mlbScores),nba_scores:Boolean(data.nbaScores),nhl_scores:Boolean(data.nhlScores),cfb_scores:Boolean(data.cfbScores),cbb_scores:Boolean(data.cbbScores),best_bets_v2:Boolean(data.bettingV2),props_v2:Boolean(data.propV2),parlays_v2:Boolean(data.parlayV2),survivor_v2:Boolean(data.survivorV2),fantasy_news:Boolean(data.fantasyNews),ask_context:Boolean(data.askContext),ask_retrieval:Boolean(data.askRetrieval)}})
  }
  if(req.method==='GET'&&url.pathname==='/api/boxscore'){
    try{
      const league=String(url.searchParams.get('league')||'').toUpperCase()
      const event=String(url.searchParams.get('event')||'')
      const result=await fetchEspnBoxscore(league,event)
      return json(res,200,result)
    }catch(err){
      return json(res,400,{status:'ERROR',error:err instanceof Error?err.message:String(err)})
    }
  }
  if(req.method==='GET'&&url.pathname==='/api/account/summary'){
    const user=await authenticatedUser(req)
    if(!user) return json(res,401,{status:'AUTH_REQUIRED',message:'Sign in to load your account.'})

    const client=scopedInsForgeClient(req)
    if(!client) return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Private account storage is temporarily unavailable.'})

    const linkedName=await linkedSurvivorEntry(req,user.id)
    const survivorState=await loadExternalJson(SURVIVOR_ENTRIES_PATH)
    const linkedEntry=linkedName ? (survivorState?.entries||{})[linkedName]||null : null

    let leagues=[]
    let fantasyStatus='READY'
    try{
      const {data,error}=await client.database
        .from('fantasy_leagues')
        .select('id,platform,league_name,sync_status')
        .order('created_at',{ascending:false})
        .limit(20)
      if(error) fantasyStatus='UNAVAILABLE'
      else leagues=Array.isArray(data)?data:[]
    }catch{
      fantasyStatus='UNAVAILABLE'
    }

    return json(res,200,{
      status:'READY',
      account:{
        email_verified:Boolean(user.emailVerified),
      },
      survivor:{
        linked:Boolean(linkedName),
        active_entry:linkedName||null,
        entry_status:linkedEntry?.status||null,
        used_team_count:Array.isArray(linkedEntry?.used_teams)?linkedEntry.used_teams.length:0,
        current_week:Number(survivorState?.pool_current_week||linkedEntry?.current_week||0)||null,
      },
      fantasy:{
        status:fantasyStatus,
        league_count:leagues.length,
        leagues:leagues.map(row=>({
          id:row.id,
          platform:row.platform||null,
          league_name:row.league_name||null,
          sync_status:row.sync_status||null,
        })),
      },
    })
  }
  if(req.method==='GET'&&url.pathname==='/api/fantasy/my-teams'){
    try{
      const user=await authenticatedUser(req)
      if(!user) return json(res,401,{status:'AUTH_REQUIRED',message:'Sign in to load your fantasy teams.'})

      const client=scopedInsForgeClient(req)
      if(!client) return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Private fantasy storage is temporarily unavailable.'})

      const {data:leagueRows,error:leagueError}=await client.database
        .from('fantasy_leagues')
        .select('id,platform,provider_league_id,league_name,season,scoring,roster_settings,sync_status,last_synced_at,provenance,created_at')
        .order('last_synced_at',{ascending:false})
        .limit(20)

      if(leagueError){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your saved fantasy teams could not be loaded.'})
      }

      const leagues=Array.isArray(leagueRows)?leagueRows:[]
      if(!leagues.length){
        return json(res,200,{status:'READY',team_count:0,teams:[]})
      }

      const leagueIds=leagues.map(row=>row.id).filter(Boolean)
      const {data:rosterRows,error:rosterError}=await client.database
        .from('fantasy_rosters')
        .select('id,league_id,provider_team_id,team_name,roster,starters,bench,updated_at')
        .in('league_id',leagueIds)
        .order('updated_at',{ascending:false})
        .limit(50)

      if(rosterError){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your saved fantasy rosters could not be loaded.'})
      }

      const rosterByLeague=new Map()
      for(const row of Array.isArray(rosterRows)?rosterRows:[]){
        if(!rosterByLeague.has(row.league_id)) rosterByLeague.set(row.league_id,row)
      }

      const teams=leagues.map(league=>{
        const roster=rosterByLeague.get(league.id)||null
        const latest=league?.provenance?.last_rate_my_team||null
        return {
          league_id:league.id,
          roster_id:roster?.id||null,
          platform:league.platform||null,
          league_name:league.league_name||null,
          season:league.season||null,
          sync_status:league.sync_status||null,
          last_synced_at:league.last_synced_at||roster?.updated_at||league.created_at||null,
          roster_updated_at:roster?.updated_at||null,
          settings_updated_at:league?.provenance?.league_settings_updated_at||null,
          team_name:roster?.team_name||league.league_name||null,
          roster:Array.isArray(roster?.roster)?roster.roster:[],
          starters:Array.isArray(roster?.starters)?roster.starters:[],
          bench:Array.isArray(roster?.bench)?roster.bench:[],
          scoring:league.scoring&&typeof league.scoring==='object'?league.scoring:{},
          roster_settings:league.roster_settings&&typeof league.roster_settings==='object'?league.roster_settings:{},
          last_analysis:latest&&typeof latest==='object'?{
            generated_at:latest.generated_at||null,
            roster_size:latest.roster_size??null,
            matched_count:latest.matched_count??null,
            coverage_pct:latest.coverage_pct??null,
            decision_coverage_pct:latest.decision_coverage_pct??null,
            roster_research_index:latest.roster_research_index??null,
            roster_research_band:latest.roster_research_band||null,
            score_is_probability:false,
          }:null,
        }
      })

      return json(res,200,{status:'READY',team_count:teams.length,teams})
    }catch(err){
      return json(res,400,{
        status:'ERROR',
        message:'Sports Zenith could not load your saved teams.',
        error:err instanceof Error?err.message:String(err),
      })
    }
  }
  if(req.method==='POST'&&url.pathname==='/api/fantasy/league-settings'){
    try{
      const user=await authenticatedUser(req)
      if(!user) return json(res,401,{status:'AUTH_REQUIRED',message:'Sign in before changing league settings.'})

      const client=scopedInsForgeClient(req)
      if(!client) return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Private fantasy storage is temporarily unavailable.'})

      const body=await readBody(req)
      const leagueId=String(body.league_id||'').trim()
      if(!leagueId) return json(res,400,{status:'MISSING_LEAGUE',message:'Choose a saved team before editing league settings.'})

      const preset=String(body.scoring_preset||'').trim().toLowerCase()
      const receptionPointsMap={ppr:1,half_ppr:0.5,standard:0}
      if(!Object.prototype.hasOwnProperty.call(receptionPointsMap,preset)){
        return json(res,400,{status:'INVALID_SCORING',message:'Scoring must be PPR, Half-PPR or Standard.'})
      }

      const clampInt=(value,min,max,fallback=0)=>{
        const parsed=Number(value)
        if(!Number.isFinite(parsed)) return fallback
        return Math.max(min,Math.min(max,Math.round(parsed)))
      }
      const starterSlots={
        qb:clampInt(body?.starter_slots?.qb,0,4,1),
        rb:clampInt(body?.starter_slots?.rb,0,8,2),
        wr:clampInt(body?.starter_slots?.wr,0,8,2),
        te:clampInt(body?.starter_slots?.te,0,4,1),
        flex:clampInt(body?.starter_slots?.flex,0,6,1),
        superflex:clampInt(body?.starter_slots?.superflex,0,4,0),
        dst:clampInt(body?.starter_slots?.dst,0,4,1),
        k:clampInt(body?.starter_slots?.k,0,4,1),
        dl:clampInt(body?.starter_slots?.dl,0,12,0),
        lb:clampInt(body?.starter_slots?.lb,0,12,0),
        db:clampInt(body?.starter_slots?.db,0,12,0),
        idp_flex:clampInt(body?.starter_slots?.idp_flex,0,12,0),
      }
      const benchSlots=clampInt(body.bench_slots,0,30,6)
      const irSlots=clampInt(body.ir_slots,0,20,1)

      const faabBudgetRaw=body.faab_budget
      const faabRemainingRaw=body.faab_remaining
      const faabBudget=faabBudgetRaw==null||faabBudgetRaw===''?null:Number(faabBudgetRaw)
      const faabRemaining=faabRemainingRaw==null||faabRemainingRaw===''?null:Number(faabRemainingRaw)
      if(faabBudget!=null&&(!Number.isFinite(faabBudget)||faabBudget<0||faabBudget>100000)){
        return json(res,400,{status:'INVALID_FAAB',message:'FAAB budget must be between 0 and 100,000.'})
      }
      if(faabRemaining!=null&&(!Number.isFinite(faabRemaining)||faabRemaining<0||faabRemaining>100000)){
        return json(res,400,{status:'INVALID_FAAB',message:'FAAB remaining must be between 0 and 100,000.'})
      }
      if(faabBudget!=null&&faabRemaining!=null&&faabRemaining>faabBudget){
        return json(res,400,{status:'INVALID_FAAB',message:'FAAB remaining cannot be greater than the total budget.'})
      }

      const {data:rows,error:readError}=await client.database
        .from('fantasy_leagues')
        .select('id,scoring,roster_settings,provenance')
        .eq('id',leagueId)
        .eq('owner_id',user.id)
        .limit(1)

      if(readError) return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your fantasy league could not be loaded.'})
      const league=Array.isArray(rows)?rows[0]:null
      if(!league) return json(res,404,{status:'LEAGUE_NOT_FOUND',message:'That saved fantasy team was not found in your account.'})

      const scoring={
        ...(league.scoring&&typeof league.scoring==='object'&&!Array.isArray(league.scoring)?league.scoring:{}),
        preset,
        reception_points:receptionPointsMap[preset],
      }
      if(faabBudget!=null) scoring.faab_budget=faabBudget
      else delete scoring.faab_budget
      if(faabRemaining!=null) scoring.faab_remaining=faabRemaining
      else delete scoring.faab_remaining

      const rosterSettings={
        ...(league.roster_settings&&typeof league.roster_settings==='object'&&!Array.isArray(league.roster_settings)?league.roster_settings:{}),
        starting_slots:starterSlots,
        bench_slots:benchSlots,
        ir_slots:irSlots,
      }
      if(faabBudget!=null) rosterSettings.faab_budget=faabBudget
      else delete rosterSettings.faab_budget
      if(faabRemaining!=null) rosterSettings.faab_remaining=faabRemaining
      else delete rosterSettings.faab_remaining

      const provenance={
        ...(league.provenance&&typeof league.provenance==='object'&&!Array.isArray(league.provenance)?league.provenance:{}),
        league_settings_updated_at:new Date().toISOString(),
      }

      const {error:updateError}=await client.database
        .from('fantasy_leagues')
        .update({
          scoring,
          roster_settings:rosterSettings,
          provenance,
          last_synced_at:new Date().toISOString(),
        })
        .eq('id',leagueId)
        .eq('owner_id',user.id)

      if(updateError) return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your league settings could not be saved.'})

      return json(res,200,{
        status:'SAVED',
        league_id:leagueId,
        scoring,
        roster_settings:rosterSettings,
        settings_ready:{
          scoring:true,
          starter_slots:true,
          faab_budget:faabBudget!=null,
          faab_remaining:faabRemaining!=null,
        },
      })
    }catch(err){
      return json(res,400,{
        status:'ERROR',
        message:'Sports Zenith could not save those league settings.',
        error:err instanceof Error?err.message:String(err),
      })
    }
  }
  if(req.method==='GET'&&url.pathname==='/api/fantasy/idp'){
    try{
      const user=await authenticatedUser(req)
      if(!user) return json(res,401,{status:'AUTH_REQUIRED',message:'Sign in to load roster-aware IDP research.'})

      const client=scopedInsForgeClient(req)
      if(!client) return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Private fantasy storage is temporarily unavailable.'})

      const requestedLeagueId=String(url.searchParams.get('league_id')||'').trim()
      let leagueQuery=client.database
        .from('fantasy_leagues')
        .select('id,league_name,season,roster_settings,last_synced_at')
        .eq('owner_id',user.id)

      if(requestedLeagueId){
        leagueQuery=leagueQuery.eq('id',requestedLeagueId)
      }else{
        leagueQuery=leagueQuery.order('last_synced_at',{ascending:false})
      }

      const {data:leagueRows,error:leagueError}=await leagueQuery.limit(1)
      if(leagueError){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your fantasy league could not be loaded.'})
      }

      const league=Array.isArray(leagueRows)?leagueRows[0]:null
      if(!league){
        return json(res,200,{
          status:'AUTHENTICATED_NO_TEAM',
          personalization_level:'NO_SAVED_ROSTER',
          message:'Save a team in My Teams / Rate My Team first.',
          matched_idp:[],
          starter_candidates:[],
          outside_targets_to_check:[],
        })
      }

      const {data:rosterRows,error:rosterError}=await client.database
        .from('fantasy_rosters')
        .select('id,team_name,roster,updated_at')
        .eq('league_id',league.id)
        .order('updated_at',{ascending:false})
        .limit(1)

      if(rosterError){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your saved roster could not be loaded.'})
      }

      const savedRoster=Array.isArray(rosterRows)?rosterRows[0]:null
      const roster=Array.isArray(savedRoster?.roster)?savedRoster.roster:[]
      if(!roster.length){
        return json(res,200,{
          status:'SAVED_TEAM_NO_ROSTER',
          personalization_level:'NO_SAVED_ROSTER',
          league:{id:league.id,league_name:league.league_name||null,team_name:savedRoster?.team_name||null},
          matched_idp:[],
          starter_candidates:[],
          outside_targets_to_check:[],
        })
      }

      const rosterSettings=league.roster_settings&&typeof league.roster_settings==='object'&&!Array.isArray(league.roster_settings)?league.roster_settings:{}
      const starterSlots=rosterSettings.starting_slots&&typeof rosterSettings.starting_slots==='object'&&!Array.isArray(rosterSettings.starting_slots)
        ? rosterSettings.starting_slots
        : {}
      const clampSlot=value=>Math.max(0,Math.min(12,Math.round(Number(value)||0)))
      const idpSlots={
        dl:clampSlot(starterSlots.dl),
        lb:clampSlot(starterSlots.lb),
        db:clampSlot(starterSlots.db),
        idp_flex:clampSlot(starterSlots.idp_flex),
      }
      const idpFit=await runIdpFit({
        roster,
        idp_slots:idpSlots,
      })
      const researchFreshness=await fantasyResearchFreshness('idp_opportunity',savedRoster?.updated_at)

      return json(res,200,{
        ...idpFit,
        status:'READY',
        research_freshness:researchFreshness,
        league:{
          id:league.id,
          league_name:league.league_name||null,
          team_name:savedRoster?.team_name||league.league_name||null,
          season:league.season||null,
          idp_slots:idpSlots,
          idp_slot_context_connected:Object.values(idpSlots).some(value=>value>0),
          last_synced_at:league.last_synced_at||savedRoster?.updated_at||null,
          roster_updated_at:savedRoster?.updated_at||null,
        },
        fantasy_points_projection_available:false,
        user_league_availability_verified:false,
      })
    }catch(err){
      return json(res,400,{
        status:'ERROR',
        message:'Sports Zenith could not build roster-aware IDP research.',
        error:err instanceof Error?err.message:String(err),
      })
    }
  }
  if(req.method==='GET'&&url.pathname==='/api/fantasy/defense-streaming'){
    try{
      const user=await authenticatedUser(req)
      if(!user) return json(res,401,{status:'AUTH_REQUIRED',message:'Sign in to load roster-aware defense streaming research.'})

      const client=scopedInsForgeClient(req)
      if(!client) return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Private fantasy storage is temporarily unavailable.'})

      const requestedLeagueId=String(url.searchParams.get('league_id')||'').trim()
      let leagueQuery=client.database
        .from('fantasy_leagues')
        .select('id,league_name,season,roster_settings,last_synced_at')
        .eq('owner_id',user.id)

      if(requestedLeagueId){
        leagueQuery=leagueQuery.eq('id',requestedLeagueId)
      }else{
        leagueQuery=leagueQuery.order('last_synced_at',{ascending:false})
      }

      const {data:leagueRows,error:leagueError}=await leagueQuery.limit(1)
      if(leagueError){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your fantasy league could not be loaded.'})
      }

      const league=Array.isArray(leagueRows)?leagueRows[0]:null
      if(!league){
        return json(res,200,{
          status:'AUTHENTICATED_NO_TEAM',
          personalization_level:'NO_SAVED_ROSTER',
          message:'Save a team in My Teams / Rate My Team first.',
          saved_defenses:[],
          alternatives_to_check:[],
        })
      }

      const {data:rosterRows,error:rosterError}=await client.database
        .from('fantasy_rosters')
        .select('id,team_name,roster,updated_at')
        .eq('league_id',league.id)
        .order('updated_at',{ascending:false})
        .limit(1)

      if(rosterError){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your saved roster could not be loaded.'})
      }

      const savedRoster=Array.isArray(rosterRows)?rosterRows[0]:null
      const roster=Array.isArray(savedRoster?.roster)?savedRoster.roster:[]
      if(!roster.length){
        return json(res,200,{
          status:'SAVED_TEAM_NO_ROSTER',
          personalization_level:'NO_SAVED_ROSTER',
          league:{id:league.id,league_name:league.league_name||null,team_name:savedRoster?.team_name||null},
          saved_defenses:[],
          alternatives_to_check:[],
        })
      }

      const rosterSettings=league.roster_settings&&typeof league.roster_settings==='object'&&!Array.isArray(league.roster_settings)?league.roster_settings:{}
      const starterSlots=rosterSettings.starting_slots&&typeof rosterSettings.starting_slots==='object'&&!Array.isArray(rosterSettings.starting_slots)
        ? rosterSettings.starting_slots
        : {}
      const dstSlots=Math.max(0,Math.min(4,Math.round(Number(starterSlots.dst)||0)))
      const analysis=await runRateMyTeam({roster})
      const defenseFit=await runDefenseStreamFit({roster_analysis:analysis})
      const researchFreshness=await fantasyResearchFreshness('defense_streaming',savedRoster?.updated_at)

      return json(res,200,{
        ...defenseFit,
        status:'READY',
        research_freshness:researchFreshness,
        league:{
          id:league.id,
          league_name:league.league_name||null,
          team_name:savedRoster?.team_name||league.league_name||null,
          season:league.season||null,
          dst_slots:dstSlots,
          last_synced_at:league.last_synced_at||savedRoster?.updated_at||null,
          roster_updated_at:savedRoster?.updated_at||null,
        },
        user_league_availability_verified:false,
      })
    }catch(err){
      return json(res,400,{
        status:'ERROR',
        message:'Sports Zenith could not build roster-aware defense streaming research.',
        error:err instanceof Error?err.message:String(err),
      })
    }
  }
  if(req.method==='GET'&&url.pathname==='/api/fantasy/ir-stash'){
    try{
      const user=await authenticatedUser(req)
      if(!user) return json(res,401,{status:'AUTH_REQUIRED',message:'Sign in to load roster-aware IR stash research.'})

      const client=scopedInsForgeClient(req)
      if(!client) return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Private fantasy storage is temporarily unavailable.'})

      const requestedLeagueId=String(url.searchParams.get('league_id')||'').trim()
      let leagueQuery=client.database
        .from('fantasy_leagues')
        .select('id,league_name,season,roster_settings,last_synced_at')
        .eq('owner_id',user.id)

      if(requestedLeagueId){
        leagueQuery=leagueQuery.eq('id',requestedLeagueId)
      }else{
        leagueQuery=leagueQuery.order('last_synced_at',{ascending:false})
      }

      const {data:leagueRows,error:leagueError}=await leagueQuery.limit(1)
      if(leagueError){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your fantasy league could not be loaded.'})
      }

      const league=Array.isArray(leagueRows)?leagueRows[0]:null
      if(!league){
        return json(res,200,{
          status:'AUTHENTICATED_NO_TEAM',
          personalization_level:'NO_SAVED_ROSTER',
          message:'Save a team in My Teams / Rate My Team first.',
          roster_injured:[],
          outside_targets_to_check:[],
        })
      }

      const {data:rosterRows,error:rosterError}=await client.database
        .from('fantasy_rosters')
        .select('id,team_name,roster,updated_at')
        .eq('league_id',league.id)
        .order('updated_at',{ascending:false})
        .limit(1)

      if(rosterError){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your saved roster could not be loaded.'})
      }

      const savedRoster=Array.isArray(rosterRows)?rosterRows[0]:null
      const roster=Array.isArray(savedRoster?.roster)?savedRoster.roster:[]
      if(!roster.length){
        return json(res,200,{
          status:'SAVED_TEAM_NO_ROSTER',
          personalization_level:'NO_SAVED_ROSTER',
          league:{id:league.id,league_name:league.league_name||null,team_name:savedRoster?.team_name||null},
          roster_injured:[],
          outside_targets_to_check:[],
        })
      }

      const rosterSettings=league.roster_settings&&typeof league.roster_settings==='object'&&!Array.isArray(league.roster_settings)?league.roster_settings:{}
      const irSlots=Math.max(0,Math.min(20,Math.round(Number(rosterSettings.ir_slots)||0)))
      const analysis=await runRateMyTeam({roster})
      const stashFit=await runIrStashFit({
        roster,
        roster_analysis:analysis,
        ir_slots:irSlots,
      })
      const researchFreshness=await fantasyResearchFreshness('ir_stash',savedRoster?.updated_at)

      return json(res,200,{
        ...stashFit,
        status:'READY',
        research_freshness:researchFreshness,
        league:{
          id:league.id,
          league_name:league.league_name||null,
          team_name:savedRoster?.team_name||league.league_name||null,
          season:league.season||null,
          ir_slots:irSlots,
          last_synced_at:league.last_synced_at||savedRoster?.updated_at||null,
          roster_updated_at:savedRoster?.updated_at||null,
        },
        platform_ir_eligibility_verified:false,
        league_availability_verified:false,
      })
    }catch(err){
      return json(res,400,{
        status:'ERROR',
        message:'Sports Zenith could not build roster-aware IR stash research.',
        error:err instanceof Error?err.message:String(err),
      })
    }
  }
  if(req.method==='GET'&&url.pathname==='/api/fantasy/waivers'){
    try{
      const user=await authenticatedUser(req)
      if(!user) return json(res,401,{status:'AUTH_REQUIRED',message:'Sign in to load roster-aware waiver research.'})

      const client=scopedInsForgeClient(req)
      if(!client) return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Private fantasy storage is temporarily unavailable.'})

      const requestedLeagueId=String(url.searchParams.get('league_id')||'').trim()
      let leagueQuery=client.database
        .from('fantasy_leagues')
        .select('id,league_name,season,scoring,roster_settings,sync_status,last_synced_at,provenance')
        .eq('owner_id',user.id)

      if(requestedLeagueId){
        leagueQuery=leagueQuery.eq('id',requestedLeagueId)
      }else{
        leagueQuery=leagueQuery.order('last_synced_at',{ascending:false})
      }

      const {data:leagueRows,error:leagueError}=await leagueQuery.limit(1)
      if(leagueError){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your fantasy league could not be loaded.'})
      }

      const league=Array.isArray(leagueRows)?leagueRows[0]:null
      if(!league){
        return json(res,200,{
          status:'AUTHENTICATED_NO_TEAM',
          personalization_level:'NO_SAVED_ROSTER',
          message:'Save a team in My Teams / Rate My Team first.',
          position_needs:[],
          targets:[],
        })
      }

      const {data:rosterRows,error:rosterError}=await client.database
        .from('fantasy_rosters')
        .select('id,team_name,roster,starters,bench,updated_at')
        .eq('league_id',league.id)
        .order('updated_at',{ascending:false})
        .limit(1)

      if(rosterError){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your saved roster could not be loaded.'})
      }

      const savedRoster=Array.isArray(rosterRows)?rosterRows[0]:null
      const roster=Array.isArray(savedRoster?.roster)?savedRoster.roster:[]
      if(!roster.length){
        return json(res,200,{
          status:'SAVED_TEAM_NO_ROSTER',
          personalization_level:'NO_SAVED_ROSTER',
          league:{id:league.id,league_name:league.league_name||null,team_name:savedRoster?.team_name||null},
          position_needs:[],
          targets:[],
        })
      }

      const analysis=await runRateMyTeam({roster})

      const scoring=league.scoring&&typeof league.scoring==='object'&&!Array.isArray(league.scoring)?league.scoring:{}
      const rosterSettings=league.roster_settings&&typeof league.roster_settings==='object'&&!Array.isArray(league.roster_settings)?league.roster_settings:{}
      const rawBudget=scoring.faab_budget ?? rosterSettings.faab_budget ?? null
      const rawRemaining=scoring.faab_remaining ?? rosterSettings.faab_remaining ?? null
      const faabBudget=Number(rawBudget)
      const faabRemaining=Number(rawRemaining)
      const budgetContextConnected=Number.isFinite(faabBudget)&&faabBudget>0&&Number.isFinite(faabRemaining)&&faabRemaining>=0&&faabRemaining<=faabBudget
      const waiverFit=await runWaiverFit({
        roster,
        roster_analysis:analysis,
        faab_budget:budgetContextConnected?faabBudget:null,
        faab_remaining:budgetContextConnected?faabRemaining:null,
      })
      const researchFreshness=await fantasyResearchFreshness('faab',savedRoster?.updated_at)

      return json(res,200,{
        ...waiverFit,
        status:'READY',
        research_freshness:researchFreshness,
        league:{
          id:league.id,
          league_name:league.league_name||null,
          team_name:savedRoster?.team_name||league.league_name||null,
          season:league.season||null,
          last_synced_at:league.last_synced_at||savedRoster?.updated_at||null,
          roster_updated_at:savedRoster?.updated_at||null,
          faab_budget:budgetContextConnected?faabBudget:null,
          faab_remaining:budgetContextConnected?faabRemaining:null,
        },
        budget_context_status:budgetContextConnected?'CONNECTED_TRANSLATION_ONLY':'WAITING',
        budget_context_connected:budgetContextConnected,
        league_availability_status:'NOT_VERIFIED',
        user_league_availability_verified:false,
      })
    }catch(err){
      return json(res,400,{
        status:'ERROR',
        message:'Sports Zenith could not build roster-aware waiver research.',
        error:err instanceof Error?err.message:String(err),
      })
    }
  }
  if(req.method==='GET'&&url.pathname==='/api/fantasy/start-sit'){
    try{
      const user=await authenticatedUser(req)
      if(!user) return json(res,401,{status:'AUTH_REQUIRED',message:'Sign in to load roster-aware Start/Sit research.'})

      const client=scopedInsForgeClient(req)
      if(!client) return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Private fantasy storage is temporarily unavailable.'})

      const requestedLeagueId=String(url.searchParams.get('league_id')||'').trim()
      let leagueQuery=client.database
        .from('fantasy_leagues')
        .select('id,league_name,season,scoring,roster_settings,sync_status,last_synced_at,provenance')
        .eq('owner_id',user.id)

      if(requestedLeagueId){
        leagueQuery=leagueQuery.eq('id',requestedLeagueId)
      }else{
        leagueQuery=leagueQuery.order('last_synced_at',{ascending:false})
      }

      const {data:leagueRows,error:leagueError}=await leagueQuery.limit(1)
      if(leagueError){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your fantasy league could not be loaded.'})
      }

      const league=Array.isArray(leagueRows)?leagueRows[0]:null
      if(!league){
        return json(res,200,{
          status:'AUTHENTICATED_NO_TEAM',
          personalization_level:'NO_SAVED_ROSTER',
          message:'Save a team in My Teams / Rate My Team first.',
          groups:[],
          players:[],
        })
      }

      const {data:rosterRows,error:rosterError}=await client.database
        .from('fantasy_rosters')
        .select('id,team_name,roster,starters,bench,updated_at')
        .eq('league_id',league.id)
        .order('updated_at',{ascending:false})
        .limit(1)

      if(rosterError){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your saved roster could not be loaded.'})
      }

      const savedRoster=Array.isArray(rosterRows)?rosterRows[0]:null
      const roster=Array.isArray(savedRoster?.roster)?savedRoster.roster:[]
      if(!roster.length){
        return json(res,200,{
          status:'SAVED_TEAM_NO_ROSTER',
          personalization_level:'NO_SAVED_ROSTER',
          league:{id:league.id,league_name:league.league_name||null,team_name:savedRoster?.team_name||null},
          groups:[],
          players:[],
        })
      }

      const analysis=await runRateMyTeam({roster})
      const scoredPlayers=(analysis.players||[])
        .filter(row=>['QB','RB','WR','TE','DST'].includes(String(row.position||'').toUpperCase()))
        .map(row=>({...row}))

      const positionOrder=['QB','RB','WR','TE','DST']
      const groups=[]
      for(const position of positionOrder){
        const rows=scoredPlayers
          .filter(row=>String(row.position||'').toUpperCase()===position)
          .sort((a,b)=>Number(b.weekly_research_score??-1)-Number(a.weekly_research_score??-1))

        if(!rows.length) continue
        rows.forEach((row,index)=>{
          row.roster_position_rank=index+1
          row.roster_position_count=rows.length
          row.roster_priority=index===0?'TOP_ROSTER_OPTION':'ROSTER_OPTION'
        })
        groups.push({position,count:rows.length,players:rows})
      }

      const scoring=league.scoring&&typeof league.scoring==='object'&&!Array.isArray(league.scoring)?league.scoring:{}
      const rosterSettings=league.roster_settings&&typeof league.roster_settings==='object'&&!Array.isArray(league.roster_settings)?league.roster_settings:{}
      const starters=Array.isArray(savedRoster?.starters)?savedRoster.starters:[]
      const bench=Array.isArray(savedRoster?.bench)?savedRoster.bench:[]
      const starterSlots=rosterSettings.starting_slots&&typeof rosterSettings.starting_slots==='object'&&!Array.isArray(rosterSettings.starting_slots)
        ? rosterSettings.starting_slots
        : {}
      const scoringConnected=['ppr','half_ppr','standard'].includes(String(scoring.preset||'').toLowerCase())
      const slotContextConnected=Object.keys(starterSlots).length>0
      const scoringFormat=String(scoring.preset||'').toLowerCase()
      let formatContext=null
      let formatContextError=null

      if(scoringConnected){
        try{
          formatContext=await runFormatContext({
            players:scoredPlayers.filter(row=>['QB','RB','WR','TE'].includes(String(row.position||'').toUpperCase())),
            scoring_format:scoringFormat,
          })
          const byIdentity=new Map()
          for(const row of formatContext?.players||[]){
            const key=String(row.player_key||row.player||'').toLowerCase()
            if(key) byIdentity.set(key,row)
          }
          for(const row of scoredPlayers){
            const key=String(row.player_key||row.player||'').toLowerCase()
            const enriched=byIdentity.get(key)
            if(enriched) Object.assign(row,enriched)
          }
        }catch(err){
          formatContextError=err instanceof Error?err.message:String(err)
        }
      }

      const closeCallWeeklyWindow=3.0
      const formatCoverage=Number(formatContext?.coverage?.context_available||0)
      const lineupResearch={
        status:slotContextConnected?'SLOT_AWARE_RESEARCH':'SLOT_CONTEXT_WAITING',
        scoring_format:scoringFormat||null,
        scoring_format_connected:scoringConnected,
        scoring_format_applied_to_score:false,
        scoring_format_context_is_projection:false,
        scoring_format_tiebreaker_status:scoringConnected
          ? (formatContextError?'FORMAT_CONTEXT_DEGRADED':formatCoverage>0?'READY':'NO_FORMAT_CONTEXT')
          : 'SCORING_FORMAT_WAITING',
        scoring_format_used_as_tiebreaker:false,
        close_call_weekly_window:closeCallWeeklyWindow,
        format_context_coverage:formatCoverage,
        format_context_error:formatContextError,
        tiebreakers:[],
        starter_slots:starterSlots,
        starter_candidates:[],
        bench_candidates:[],
        open_slots:[],
        unscored_slots:[],
        note:slotContextConnected
          ? 'Starter candidates are allocated primarily by Sports Zenith weekly research. Saved scoring format can only break close calls within a 3-point weekly-score window using historical season-average format context. It does not change the weekly score and is not a fantasy-point projection.'
          : 'Save starter-slot settings before Sports Zenith can build slot-aware lineup research.',
      }

      if(slotContextConnected){
        const used=new Set()
        const playerId=row=>String(row.player_key||row.player||'')
        const eligibleRows=(positions)=>scoredPlayers
          .filter(row=>positions.includes(String(row.position||'').toUpperCase())&&!used.has(playerId(row)))
          .sort((a,b)=>Number(b.weekly_research_score??-1)-Number(a.weekly_research_score??-1))

        const chooseCloseCallCandidate=(slot,positions,slotIndex)=>{
          const rows=eligibleRows(positions)
          const weeklyTop=rows[0]||null
          if(!weeklyTop) return {candidate:null,tiebreaker:null}

          const topWeekly=Number(weeklyTop.weekly_research_score??-1)
          const closeGroup=rows.filter(row=>
            topWeekly-Number(row.weekly_research_score??-1)<=closeCallWeeklyWindow
          )

          if(!scoringConnected||formatContextError||closeGroup.length<2||!weeklyTop.format_context_available){
            return {candidate:weeklyTop,tiebreaker:null}
          }

          const contextual=closeGroup.filter(row=>
            row.format_context_available&&
            Number.isFinite(Number(row.historical_format_points_per_game))&&
            Number.isFinite(Number(row.format_context_position_percentile))
          )
          if(contextual.length<2){
            return {candidate:weeklyTop,tiebreaker:null}
          }

          const crossPosition=new Set(positions).size>1
          const metric=crossPosition?'historical_format_points_per_game':'format_context_position_percentile'
          const ranked=[...contextual].sort((a,b)=>
            Number(b[metric]??-1)-Number(a[metric]??-1) ||
            Number(b.weekly_research_score??-1)-Number(a.weekly_research_score??-1)
          )
          const chosen=ranked[0]||weeklyTop
          const applied=playerId(chosen)!==playerId(weeklyTop)
          const tiebreaker={
            slot,
            slot_index:slotIndex,
            weekly_window:closeCallWeeklyWindow,
            eligible_positions:positions,
            scoring_format:scoringFormat,
            metric,
            weekly_top:{
              player:weeklyTop.player,
              weekly_research_score:weeklyTop.weekly_research_score,
              context_value:weeklyTop[metric]??null,
            },
            selected:{
              player:chosen.player,
              weekly_research_score:chosen.weekly_research_score,
              context_value:chosen[metric]??null,
            },
            close_group:contextual.map(row=>({
              player:row.player,
              position:row.position,
              weekly_research_score:row.weekly_research_score,
              context_value:row[metric]??null,
            })),
            applied,
            context_is_projection:false,
          }
          lineupResearch.tiebreakers.push(tiebreaker)
          if(applied) lineupResearch.scoring_format_used_as_tiebreaker=true
          return {candidate:chosen,tiebreaker}
        }

        const fillSlots=(slot,positions,count)=>{
          const total=Math.max(0,Math.min(30,Math.round(Number(count)||0)))
          for(let index=1;index<=total;index+=1){
            const decision=chooseCloseCallCandidate(slot,positions,index)
            const candidate=decision.candidate
            if(!candidate){
              lineupResearch.open_slots.push({slot,slot_index:index,eligible_positions:positions,reason:'NO_SCORED_ELIGIBLE_PLAYER'})
              continue
            }
            used.add(playerId(candidate))
            lineupResearch.starter_candidates.push({
              ...candidate,
              assigned_slot:slot,
              slot_index:index,
              lineup_research_status:'STARTER_CANDIDATE',
              close_call_tiebreaker_considered:Boolean(decision.tiebreaker),
              close_call_tiebreaker_applied:Boolean(decision.tiebreaker?.applied),
              close_call_tiebreaker_metric:decision.tiebreaker?.metric||null,
            })
          }
        }

        fillSlots('QB',['QB'],starterSlots.qb)
        fillSlots('RB',['RB'],starterSlots.rb)
        fillSlots('WR',['WR'],starterSlots.wr)
        fillSlots('TE',['TE'],starterSlots.te)
        fillSlots('DST',['DST'],starterSlots.dst)
        fillSlots('SUPERFLEX',['QB','RB','WR','TE'],starterSlots.superflex)
        fillSlots('FLEX',['RB','WR','TE'],starterSlots.flex)

        const kickerSlots=Math.max(0,Math.min(10,Math.round(Number(starterSlots.k)||0)))
        const kickers=(analysis.recognized_without_decision||[])
          .filter(row=>String(row.position||'').toUpperCase()==='K')
        for(let index=1;index<=kickerSlots;index+=1){
          const kicker=kickers[index-1]||null
          lineupResearch.unscored_slots.push({
            slot:'K',
            slot_index:index,
            player:kicker?.player||null,
            team:kicker?.team||null,
            reason:kicker?'NO_CURRENT_KICKER_DECISION_SCORE':'NO_KICKER_RECOGNIZED',
          })
        }

        lineupResearch.bench_candidates=scoredPlayers
          .filter(row=>!used.has(playerId(row)))
          .sort((a,b)=>Number(b.weekly_research_score??-1)-Number(a.weekly_research_score??-1))
          .map(row=>({...row,lineup_research_status:'BENCH_CANDIDATE'}))
      }

      const researchFreshness=await fantasyResearchFreshness('weekly',savedRoster?.updated_at)

      return json(res,200,{
        status:'READY',
        research_freshness:researchFreshness,
        personalization_level:slotContextConnected?'SLOT_AWARE_RESEARCH':'ROSTER_AWARE_RESEARCH',
        context_status:slotContextConnected
          ? (
              scoringConnected
                ? (
                    lineupResearch.scoring_format_used_as_tiebreaker
                      ? 'SLOT_CONTEXT_APPLIED_FORMAT_TIEBREAKER_USED'
                      : lineupResearch.scoring_format_tiebreaker_status==='READY'
                        ? 'SLOT_CONTEXT_APPLIED_FORMAT_TIEBREAKER_READY'
                        : 'SLOT_CONTEXT_APPLIED_FORMAT_CONTEXT_DEGRADED'
                  )
                : 'SLOT_CONTEXT_APPLIED_SCORING_WAITING'
            )
          : 'SCORING_AND_SLOT_CONTEXT_WAITING',
        is_official_lineup:false,
        score_is_probability:false,
        league:{
          id:league.id,
          league_name:league.league_name||null,
          team_name:savedRoster?.team_name||league.league_name||null,
          season:league.season||null,
          scoring_connected:scoringConnected,
          scoring_format:String(scoring.preset||'').toLowerCase()||null,
          slot_context_connected:slotContextConnected,
          starter_slots:starterSlots,
          last_synced_at:league.last_synced_at||savedRoster?.updated_at||null,
          roster_updated_at:savedRoster?.updated_at||null,
        },
        coverage:{
          roster_size:analysis.roster_size,
          matched_count:analysis.matched_count,
          recognized_without_decision_count:analysis.recognized_without_decision_count,
          unmatched_count:analysis.unmatched_count,
          coverage_pct:analysis.coverage_pct,
          decision_coverage_pct:analysis.decision_coverage_pct,
        },
        groups,
        lineup_research:lineupResearch,
        players:scoredPlayers,
        recognized_without_decision:analysis.recognized_without_decision||[],
        unmatched:analysis.unmatched||[],
        note:slotContextConnected
          ? 'This is slot-aware Sports Zenith lineup research built from your saved roster settings. It uses weekly research scores, not fantasy-point projections, so scoring format is context only and the lineup is not official.'
          : 'This is roster-aware Sports Zenith weekly research. Save starter-slot settings to build slot-aware lineup research.',
      })
    }catch(err){
      return json(res,400,{
        status:'ERROR',
        message:'Sports Zenith could not build roster-aware Start/Sit research.',
        error:err instanceof Error?err.message:String(err),
      })
    }
  }
  if(req.method==='POST'&&url.pathname==='/api/fantasy/rate-my-team'){
    try{
      const user=await authenticatedUser(req)
      if(!user) return json(res,401,{status:'AUTH_REQUIRED',message:'Sign in before saving a fantasy team.'})

      const rateLimit=consumeRateLimit(`rate-my-team:${user.id}:${clientIp(req)}`,30,15*60*1000)
      if(!rateLimit.ok){
        return json(
          res,
          429,
          {status:'RATE_LIMITED',message:'Too many team-analysis requests. Wait a few minutes and try again.'},
          {'retry-after':String(Math.ceil(rateLimit.retryAfterMs/1000))}
        )
      }

      const body=await readBody(req)
      const rawRoster=Array.isArray(body.roster)?body.roster:[]
      if(!rawRoster.length) return json(res,400,{status:'MISSING_ROSTER',message:'Add at least one player before rating the team.'})
      if(rawRoster.length>60) return json(res,400,{status:'ROSTER_TOO_LARGE',message:'A fantasy roster cannot exceed 60 entries.'})

      const sanitizeRosterItem=item=>{
        if(typeof item==='string') return item.trim().slice(0,160)
        if(item && typeof item==='object' && !Array.isArray(item)){
          return {
            name:String(item.name||item.player||'').trim().slice(0,160),
            team:String(item.team||'').trim().slice(0,24),
            position:String(item.position||'').trim().slice(0,16),
          }
        }
        return ''
      }
      const validRosterItem=item=>typeof item==='string'?Boolean(item):Boolean(item?.name)
      const roster=rawRoster.map(sanitizeRosterItem).filter(validRosterItem)
      if(!roster.length) return json(res,400,{status:'MISSING_ROSTER',message:'No valid roster entries were provided.'})

      const leagueName=String(body.league_name||'My Team').trim()||'My Team'
      const teamName=String(body.team_name||leagueName).trim()||leagueName
      if(leagueName.length>120 || teamName.length>120){
        return json(res,400,{status:'INVALID_FIELDS',message:'League and team names must be 120 characters or fewer.'})
      }

      const seasonRaw=Number(body.season)
      const season=Number.isInteger(seasonRaw) && seasonRaw>=2020 && seasonRaw<=2100
        ? seasonRaw
        : new Date().getUTCFullYear()

      const scoring=body.scoring && typeof body.scoring==='object' && !Array.isArray(body.scoring)
        ? body.scoring
        : null
      const rosterSettings=body.roster_settings && typeof body.roster_settings==='object' && !Array.isArray(body.roster_settings)
        ? body.roster_settings
        : null
      const starters=Array.isArray(body.starters)
        ? body.starters.slice(0,40).map(sanitizeRosterItem).filter(validRosterItem)
        : []
      const bench=Array.isArray(body.bench)
        ? body.bench.slice(0,40).map(sanitizeRosterItem).filter(validRosterItem)
        : []

      const analysis=await runRateMyTeam({roster})

      const client=scopedInsForgeClient(req)
      if(!client) return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Private fantasy storage is temporarily unavailable.'})

      const {data:leagueRows,error:leagueReadError}=await client.database
        .from('fantasy_leagues')
        .select('id,scoring,roster_settings,provenance')
        .eq('owner_id',user.id)
        .eq('platform','manual')
        .eq('league_name',leagueName)
        .eq('season',season)
        .limit(1)

      if(leagueReadError){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your fantasy account could not be loaded.'})
      }

      const existingLeague=Array.isArray(leagueRows)?leagueRows[0]:null
      const generatedAt=new Date().toISOString()
      const provenance={
        ...(existingLeague?.provenance && typeof existingLeague.provenance==='object' ? existingLeague.provenance : {}),
        setup_method:'quick_roster',
        last_rate_my_team:{
          generated_at:generatedAt,
          roster_size:analysis.roster_size,
          matched_count:analysis.matched_count,
          coverage_pct:analysis.coverage_pct,
          decision_coverage_pct:analysis.decision_coverage_pct,
          roster_research_index:analysis.roster_research_index,
          roster_research_band:analysis.roster_research_band,
          score_is_probability:false,
        },
      }

      const leaguePayload={
        owner_id:user.id,
        platform:'manual',
        provider_league_id:null,
        league_name:leagueName,
        season,
        scoring:scoring ?? existingLeague?.scoring ?? {},
        roster_settings:rosterSettings ?? existingLeague?.roster_settings ?? {},
        sync_status:'manual',
        last_synced_at:generatedAt,
        provenance,
      }

      let leagueId=existingLeague?.id||null
      let createdLeague=false
      if(existingLeague){
        const {error}=await client.database
          .from('fantasy_leagues')
          .update(leaguePayload)
          .eq('id',existingLeague.id)
        if(error) return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your fantasy league could not be updated.'})
      }else{
        const {data,error}=await client.database
          .from('fantasy_leagues')
          .insert(leaguePayload)
          .select('id')
        if(error || !Array.isArray(data) || !data[0]?.id){
          return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your fantasy league could not be saved.'})
        }
        leagueId=data[0].id
        createdLeague=true
      }

      const rollbackNewLeague=async()=>{
        if(!createdLeague || !leagueId) return
        try{ await client.database.from('fantasy_leagues').delete().eq('id',leagueId) }catch{}
      }

      const {data:rosterRows,error:rosterReadError}=await client.database
        .from('fantasy_rosters')
        .select('id')
        .eq('league_id',leagueId)
        .eq('provider_team_id','manual-primary')
        .limit(1)

      if(rosterReadError){
        await rollbackNewLeague()
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your saved roster could not be loaded.'})
      }

      const rosterPayload={
        league_id:leagueId,
        provider_team_id:'manual-primary',
        team_name:teamName,
        roster,
        starters,
        bench,
        available_players:[],
        updated_at:generatedAt,
      }

      const existingRoster=Array.isArray(rosterRows)?rosterRows[0]:null
      let rosterId=existingRoster?.id||null
      if(existingRoster){
        const {error}=await client.database
          .from('fantasy_rosters')
          .update(rosterPayload)
          .eq('id',existingRoster.id)
        if(error){
          await rollbackNewLeague()
          return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your roster could not be updated.'})
        }
      }else{
        const {data,error}=await client.database
          .from('fantasy_rosters')
          .insert(rosterPayload)
          .select('id')
        if(error || !Array.isArray(data) || !data[0]?.id){
          await rollbackNewLeague()
          return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Your roster could not be saved.'})
        }
        rosterId=data[0].id
      }

      return json(res,200,{
        status:'READY',
        saved:true,
        league:{
          id:leagueId,
          league_name:leagueName,
          team_name:teamName,
          platform:'manual',
          season,
        },
        roster_id:rosterId,
        analysis,
      })
    }catch(err){
      return json(res,400,{
        status:'ERROR',
        message:'Sports Zenith could not rate that roster.',
        error:err instanceof Error?err.message:String(err),
      })
    }
  }
  if(req.method==='POST'&&url.pathname==='/api/survivor/link-entry'){
    try{
      const user=await authenticatedUser(req)
      if(!user) return json(res,401,{status:'AUTH_REQUIRED',message:'Sign in before linking a Survivor entry.'})

      const claimLimit=consumeRateLimit(`survivor-claim:${user.id}:${clientIp(req)}`,8,15*60*1000)
      if(!claimLimit.ok){
        return json(
          res,
          429,
          {status:'RATE_LIMITED',message:'Too many claim attempts. Wait a few minutes and try again.'},
          {'retry-after':String(Math.ceil(claimLimit.retryAfterMs/1000))}
        )
      }

      const body=await readBody(req)
      const entryName=String(body.entry_name||'').trim()
      const claimCode=String(body.claim_code||'').trim().toUpperCase()
      if(!entryName || !claimCode) return json(res,400,{status:'MISSING_FIELDS',message:'Entry name and claim code are required.'})
      if(entryName.length>160 || claimCode.length>128) return json(res,400,{status:'INVALID_FIELDS',message:'Entry name or claim code is too long.'})

      const state=await loadExternalJson(SURVIVOR_ENTRIES_PATH)
      const entry=(state?.entries||{})[entryName]
      if(!entry) return json(res,404,{status:'ENTRY_NOT_FOUND',message:'That Survivor entry was not found.'})

      const links=await loadExternalJson(MEMBER_LINKS_PATH)
      links.survivor_entries ||= {}
      links.survivor_claims ||= {}

      const existingForUser=links.survivor_entries[user.id]
      if(existingForUser && existingForUser !== entryName){
        return json(res,409,{status:'ACCOUNT_ALREADY_LINKED',message:'This account is already linked to a different Survivor entry.'})
      }

      const existingOwner=Object.entries(links.survivor_entries).find(([userId,name])=>userId!==user.id && name===entryName)
      if(existingOwner){
        return json(res,409,{status:'ENTRY_ALREADY_CLAIMED',message:'That Survivor entry is already linked to another account.'})
      }

      if(!INSFORGE_ADMIN){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Private account storage is temporarily unavailable. Please try again.'})
      }

      let claim=null
      let claimFromDatabase=false
      try{
        const {data:claimRows,error:claimReadError}=await INSFORGE_ADMIN.database
          .from('survivor_claims')
          .select('entry_name,code_sha256,claimed_by,claimed_at,expires_at')
          .eq('entry_name',entryName)
          .limit(1)
        if(claimReadError){
          return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'The private claim store could not be verified. Please try again.'})
        }
        if(Array.isArray(claimRows) && claimRows[0]){
          claim=claimRows[0]
          claimFromDatabase=true
        }
      }catch{
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'The private claim store could not be verified. Please try again.'})
      }

      if(!claim){
        claim=links.survivor_claims[entryName]||null
      }
      if(!claim || claim.claimed_by){
        return json(res,403,{status:'CLAIM_UNAVAILABLE',message:'No unused claim code is available for that entry.'})
      }
      if(claim.expires_at && Date.parse(claim.expires_at) <= Date.now()){
        return json(res,403,{status:'CLAIM_EXPIRED',message:'That claim code has expired. Request a new claim code.'})
      }

      const submittedHash=sha256(claimCode)
      if(!secureHashEqual(submittedHash,claim.code_sha256)){
        return json(res,403,{status:'INVALID_CLAIM_CODE',message:'The claim code is not valid for that entry.'})
      }

      if(!claimFromDatabase){
        const {error:claimSyncError}=await INSFORGE_ADMIN.database
          .from('survivor_claims')
          .insert({
            entry_name:entryName,
            code_sha256:claim.code_sha256,
            claimed_by:null,
            claimed_at:null,
            expires_at:claim.expires_at||null,
          })
        if(claimSyncError){
          return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'The claim record could not be secured. Please try again.'})
        }
        claimFromDatabase=true
      }

      const { data: dbOwners, error: dbOwnersError } = await INSFORGE_ADMIN.database
        .from('survivor_entries')
        .select('owner_id,entry_name,is_active')
        .eq('entry_name', entryName)
        .limit(10)
      if(dbOwnersError){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Private account storage could not be verified. Please try again.'})
      }
      const dbOtherOwner=(dbOwners||[]).find(row=>row.owner_id && row.owner_id!==user.id && row.is_active!==false)
      if(dbOtherOwner){
        return json(res,409,{status:'ENTRY_ALREADY_CLAIMED',message:'That Survivor entry is already linked to another account.'})
      }

      const { data: dbUserEntries, error: dbUserEntriesError } = await INSFORGE_ADMIN.database
        .from('survivor_entries')
        .select('id,entry_name,is_active')
        .eq('owner_id', user.id)
        .limit(10)
      if(dbUserEntriesError){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'Private account storage could not be verified. Please try again.'})
      }

      const dbDifferentEntry=(dbUserEntries||[]).find(row=>row.entry_name!==entryName && row.is_active!==false)
      if(dbDifferentEntry){
        return json(res,409,{status:'ACCOUNT_ALREADY_LINKED',message:'This account is already linked to a different Survivor entry.'})
      }

      const dbExisting=(dbUserEntries||[]).find(row=>row.entry_name===entryName)
      const dbPayload={
        owner_id:user.id,
        entry_name:entryName,
        is_active:true,
        used_teams:Array.isArray(entry.used_teams)?entry.used_teams:[],
      }
      const dbWrite=dbExisting
        ? await INSFORGE_ADMIN.database.from('survivor_entries').update(dbPayload).eq('id',dbExisting.id).select('id')
        : await INSFORGE_ADMIN.database.from('survivor_entries').insert(dbPayload).select('id')
      if(dbWrite.error){
        return json(res,503,{status:'ACCOUNT_STORAGE_UNAVAILABLE',message:'The entry was verified but could not be attached to the account. Please try again.'})
      }

      const claimedAt=new Date().toISOString()
      const claimWrite=await INSFORGE_ADMIN.database
        .from('survivor_claims')
        .update({claimed_by:user.id,claimed_at:claimedAt})
        .eq('entry_name',entryName)
        .is('claimed_by',null)
        .select('entry_name,claimed_by')

      let claimCommitted=!claimWrite.error && Array.isArray(claimWrite.data) && claimWrite.data.some(row=>row.claimed_by===user.id)
      if(!claimCommitted){
        try{
          const {data:claimVerify}=await INSFORGE_ADMIN.database
            .from('survivor_claims')
            .select('claimed_by')
            .eq('entry_name',entryName)
            .limit(1)
          claimCommitted=Array.isArray(claimVerify) && claimVerify[0]?.claimed_by===user.id
        }catch{}
      }

      if(!claimCommitted){
        if(!dbExisting){
          try{
            await INSFORGE_ADMIN.database
              .from('survivor_entries')
              .delete()
              .eq('owner_id',user.id)
              .eq('entry_name',entryName)
          }catch{}
        }
        return json(res,409,{status:'CLAIM_UNAVAILABLE',message:'That Survivor entry was claimed before this request completed. Refresh your account and try again.'})
      }

      links.survivor_entries[user.id]=entryName
      const localClaim=links.survivor_claims[entryName]
      if(localClaim){
        localClaim.claimed_by=user.id
        localClaim.claimed_at=claimedAt
      }
      await saveMemberLinks(links)

      return json(res,200,{
        status:'LINKED',
        entry_linked:true,
        active_entry:entryName,
        entry_status:entry.status||null,
        pool_current_week:Number(state.pool_current_week||entry.current_week||0)||null,
      })
    }catch(err){
      return json(res,400,{status:'ERROR',message:'Could not link Survivor entry.',error:err instanceof Error?err.message:String(err)})
    }
  }
  if(req.method==='GET'&&url.pathname==='/api/survivor/state'){
    const user=await authenticatedUser(req)
    if(!user) return json(res,401,{
      status:'AUTH_REQUIRED',
      entry_linked:false,
      message:'Sign in to load private Survivor entries.'
    })

    const data=await loadAll()
    const state=data.survivorUser||{}
    const linkedName=await linkedSurvivorEntry(req,user.id)
    const entry=linkedName ? (state.entries||{})[linkedName]||null : null

    if(!entry) return json(res,200,{
      status:'AUTHENTICATED_NO_ENTRY',
      entry_linked:false,
      pool_current_week:Number(state.pool_current_week||0)||null,
      used_teams:[],
      current_picks:[],
      entry_status:null,
      updated_at:null,
      source:'PRIVATE_MEMBER_STATE'
    })

    const governed=await loadExternalJson(SURVIVOR_V2_PRIVATE_PATH)
    const governedEntry=governed?.active_entry===linkedName ? governed : null

    return json(res,200,{
      status:'READY',
      entry_linked:true,
      active_entry:linkedName,
      entry_status:entry?.status||null,
      pool_current_week:Number(state.pool_current_week||entry?.current_week||0)||null,
      active_entry_week:governedEntry?.active_entry_week||entry?.current_week||null,
      state_week_matches_pool:governedEntry?.state_week_matches_pool??null,
      used_teams:Array.isArray(entry?.used_teams)?entry.used_teams:[],
      current_picks:Array.isArray(entry?.current_picks)?entry.current_picks:[],
      required_picks:governedEntry?.required_picks??null,
      rule_status:governedEntry?.rule_status||null,
      rule_confirmed:Boolean(governedEntry?.rule_confirmed),
      ownership:governedEntry?.ownership||{status:'PERSONAL_CONTEXT_WAITING'},
      recommendation_status:governedEntry?.recommendation_status||'PERSONAL_CONTEXT_WAITING',
      shadow_recommendation:governedEntry?.shadow_recommendation||[],
      updated_at:state.manual_state_updated_at||state.last_result_refresh_at||null,
      source:'PRIVATE_MEMBER_STATE'
    })
  }
  if(req.method==='POST'&&url.pathname==='/api/ask'){
    try{
      const body=await readBody(req)
      const question=String(body.question||body.message||'').trim()
      const context=body.context&&typeof body.context==='object'?body.context:{}
      const data=await loadAll()
      const personalAnswer=await personalizedFantasyAsk(req,question,context)
      const answer=personalAnswer||routeAsk(question,data,context)
      return json(res,200,{question,context,...answer,generated_at:new Date().toISOString()})
    }
    catch(err){return json(res,400,{status:'ERROR',take:'The sports analyst could not process that request.',error:err instanceof Error?err.message:String(err)})}
  }
  if(req.method==='POST'&&url.pathname==='/api/dfs/optimize'){
    try{
      const body=await readBody(req)
      const result=await runDfsOptimizer(body)
      return json(res,200,result)
    } catch(err){
      return json(res,400,{status:'ERROR',error:err instanceof Error?err.message:String(err)})
    }
  }
  if(req.method==='GET'||req.method==='HEAD') return serveStatic(req,res,url.pathname)
  res.writeHead(405);res.end('Method Not Allowed')
})

server.listen(PORT,'0.0.0.0',()=>console.log(`Sports Zenith commercial server listening on ${PORT}`))
