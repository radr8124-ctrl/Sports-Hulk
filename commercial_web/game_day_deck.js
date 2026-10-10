// Sports Zenith Game Day — pure, timestamp-aware official score/fixture presenter.
// SOURCE_FAILURE != no scheduled games != NO EDGE. No sportsbook odds or bets here.

export const GAME_DAY_SPORTS = ['NFL','NHL','CFB','NBA','MLB']
export const GAME_DAY_SOURCE_FILES = {
  NFL:'/nfl_scores.json', NHL:'/nhl_scores.json', CFB:'/cfb_scores.json',
  NBA:'/nba_scores.json', MLB:'/mlb_scores.json',
}
export const GAME_DAY_STALE_AFTER_MS = 3*60*60*1000
const HOUR=60*60*1000
const DAY=24*HOUR

const parsedDate=value=>{
  const stamp=Date.parse(typeof value==='string'?value:'')
  return Number.isFinite(stamp)?stamp:null
}
const score=value=>{
  if (value===null||value===undefined||value==='')return null
  const n=Number(value)
  return Number.isInteger(n)&&n>=0&&n<999?n:null
}
const simple=value=>String(value||'').trim().slice(0,70)

function allEventRows(sport,feed){
  const names=sport==='MLB'?['today_games','next_games','recent_games']:['games','next_games']
  const originals=[]
  for(const name of names){
    if (Array.isArray(feed[name]))originals.push(...feed[name])
  }
  return originals
}

export function normalizeGameDayFeed(sport,feed,nowMs=Date.now()){
  if(!GAME_DAY_SPORTS.includes(sport)||!Number.isFinite(nowMs))
    return {sport,status:'DATA_SOURCE_FAILURE',games:[],reason:'UNSUPPORTED_SOURCE'}
  if(!feed||typeof feed!=='object'||Array.isArray(feed))
    return {sport,status:'DATA_SOURCE_FAILURE',games:[],reason:'MISSING_SOURCE_PAYLOAD'}
  const observed=parsedDate(feed.generated_at)
  if(observed===null||observed>nowMs+5*60*1000)
    return {sport,status:'DATA_SOURCE_FAILURE',games:[],reason:'MISSING_OR_FUTURE_SOURCE_TIME'}
  if(['FAILED','ERROR','UNAVAILABLE','SOURCE_FAILURE'].includes(String(feed.status||'').toUpperCase()))
    return {sport,status:'DATA_SOURCE_FAILURE',games:[],reason:'PROVIDER_MARKED_FAILED'}
  const hasArray=(sport==='MLB'?['today_games','next_games','recent_games']:['games','next_games'])
    .some(name=>Array.isArray(feed[name]))
  if(!hasArray && String(feed.status||'').toUpperCase()!=='NO_GAMES')
    return {sport,status:'DATA_SOURCE_FAILURE',games:[],reason:'SOURCE_HAS_NO_GAME_COLLECTIONS'}
  const age=nowMs-observed
  const stale=age>GAME_DAY_STALE_AFTER_MS
  const seen=new Set()
  const games=[]
  for(const raw of allEventRows(sport,feed)){
    if(!raw||typeof raw!=='object')continue
    const start=parsedDate(raw.start_time||raw.gameDate||raw.start)
    const away=simple(raw.away),home=simple(raw.home)
    const sourceId=String(raw.event_id||raw.gamePk||'').trim()
    if(!start||!away||!home||!sourceId||start>nowMs+7*DAY||start<nowMs-36*HOUR)continue
    const key=sport+'|'+sourceId
    if(seen.has(key))continue
    seen.add(key)
    const final=raw.final===true
    const live=raw.live===true&&!final&&!stale
    const awayScore=final||live?score(raw.away_score):null
    const homeScore=final||live?score(raw.home_score):null
    const completeScore=awayScore!==null&&homeScore!==null
    const state=final?(completeScore?'FINAL':'SCORE_UNVERIFIED'):
      live?'LIVE':start<=nowMs?'STATUS_NOT_VERIFIED':'UPCOMING'
    const logo=(value)=>typeof value==='string'&&/^https:\/\/a\.espncdn\.com\/i\/teamlogos\/[a-z0-9/_-]+\.png$/i.test(value)?value:null
    games.push({
      key,sport,officialEventId:sourceId,
      away,home,awayCode:simple(raw.away_abbr||away.slice(0,3)).slice(0,5).toUpperCase(),
      homeCode:simple(raw.home_abbr||home.slice(0,3)).slice(0,5).toUpperCase(),
      awayScore,homeScore,
      awayLogo:logo(raw.away_logo),homeLogo:logo(raw.home_logo),
      start:new Date(start).toISOString(),state,
      feedFresh:!stale,sourceAgeMinutes:Math.floor(age/60000),
      sourceName:sport==='MLB'?'MLB StatsAPI':'ESPN',
      originalQuoteOrModelProbabilityProvided:false,
    })
  }
  return {sport,status:stale?'SOURCE_STALE':'READY',
    generated_at:feed.generated_at,sourceAgeMinutes:Math.floor(age/60000),
    reason:stale?'SOURCE_OLDER_THAN_THREE_HOURS':null,games}
}

const gameSort=(a,b)=>{
  const rank=x=>x.state==='LIVE'?0:
    x.state==='UPCOMING'?1:x.state==='STATUS_NOT_VERIFIED'?2:
    x.state==='FINAL'?3:4
  const delta=rank(a)-rank(b)
  if(delta)return delta
  const ta=Date.parse(a.start),tb=Date.parse(b.start)
  return rank(a)===3?tb-ta:ta-tb
}

export function gameDayDeck(sourceResults={},sport='ALL',nowMs=Date.now()){
  const filtered=GAME_DAY_SPORTS.filter(s=>sport==='ALL'||s===sport)
  const sourceStatuses=filtered.map(s=>({
    sport:s,status:sourceResults[s]?.status||'DATA_SOURCE_FAILURE',
  }))
  const available=filtered.flatMap(s=>sourceResults[s]?.games||[])
    .filter(x=>x.feedFresh===true)
  available.sort(gameSort)
  let games=available
  if(sport==='ALL'){
    const heads=[]
    const IDs=new Set()
    for(const league of GAME_DAY_SPORTS){
      const first=available.find(x=>x.sport===league)
      if(first){heads.push(first);IDs.add(first.key)}
    }
    heads.sort(gameSort)
    games=[...heads,...available.filter(x=>!IDs.has(x.key))]
  }
  const anyReady=sourceStatuses.some(x=>x.status==='READY')
  const anyFailure=sourceStatuses.some(x=>x.status==='DATA_SOURCE_FAILURE')
  const anyStale=sourceStatuses.some(x=>x.status==='SOURCE_STALE')
  const state=!anyReady?(anyStale?'SOURCE_STALE':'DATA_SOURCE_FAILURE'):
    !games.length?'NO_SCHEDULED_GAMES':'GAMES_AVAILABLE'
  return {
    state,games:games.slice(0,sport==='ALL'?5:6),sources:sourceStatuses,
    sourceFailureCount:sourceStatuses.filter(x=>x.status==='DATA_SOURCE_FAILURE').length,
    sourceStaleCount:sourceStatuses.filter(x=>x.status==='SOURCE_STALE').length,
    visibleLeagues:[...new Set(games.map(x=>x.sport))],
    explicitlyNotABettingRecommendation:true,
  }
}
