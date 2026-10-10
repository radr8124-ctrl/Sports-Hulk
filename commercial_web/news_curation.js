// Sports Zenith newsroom curation, deterministic and replayable.
// Source articles are attributed links. Their claims DO NOT become verified
// player statuses, game facts, odds prices, or model recommendations.

export const NEWS_SPORTS = ['NFL','NHL','NBA','MLB','CFB','CBB']
export const NEWS_SPORT_NAMES = {
  NFL:'NFL',NHL:'NHL',NBA:'NBA',MLB:'MLB',CFB:'College Football',CBB:'College Basketball'
}
export const NEWS_CATEGORIES = [
  {id:'ALL',label:'All stories'},
  {id:'INJURY',label:'Injuries'},
  {id:'RECAP',label:'Recaps'},
  {id:'FANTASY',label:'Fantasy'},
  {id:'LINEUP',label:'Lineups'},
  {id:'TRANSACTION',label:'Roster moves'},
  {id:'MARKET',label:'Odds news'},
  {id:'NEWS',label:'Headlines'},
]
const weights={INJURY:72,LINEUP:70,TRANSACTION:62,MARKET:61,RECAP:58,NEWS:55,FANTASY:38}
const promotional=/promo codes?|bonus bets?|deposit bonus|free bets?|sportsbook signup|odds boost promo|betting promo/i
const videoOnly=/\b(game highlights?|full highlights?|top plays|highlight reel)\b/i

function sourceUrl(raw) {
  if(typeof raw!=='string'||!raw.trim())return null
  try{
    const result=new URL(raw)
    if(result.protocol!=='https:' && result.protocol!=='http:')return null
    if(!result.hostname || /^(localhost|127\.|0\.0\.0\.0)/i.test(result.hostname))return null
    if(result.username||result.password)return null
    return result.href
  }catch{return null}
}
function publishedTime(value,nowMs) {
  const time=Date.parse(typeof value==='string'?value:'')
  // A future article can never become "breaking news" prematurely.
  return Number.isFinite(time)&&time>=0&&time<=nowMs+5*60*1000?time:null
}
const normalizedTitle=text=>String(text||'').toLowerCase()
 .replace(/[^a-z0-9]+/g,' ').replace(/\s+/g,' ').trim()
const sourceFingerprint=link=>{
  try{
    const url=new URL(link)
    // ESPN keeps multiple distinct recap articles at /recap?gameId=N.
    // Do not silently collapse every game's recap to the first one.
    const identity=['gameId','id','articleId'].map(key=>url.searchParams.get(key)).find(Boolean)
    return url.host.toLowerCase()+url.pathname.replace(/\/$/,'').toLowerCase()+
      (identity?'?id='+encodeURIComponent(identity):'')
  }catch{return ''}
}

export function newsCategory(row={}) {
 const type=String(row.event_type||'').toUpperCase()
 const title=String(row.title||'')
 // This categorizes an ATTRIBUTED ARTICLE. It does not assert an actual
 // current player injury or a model-changing validated lineup state.
 const injuryTerms=/\b(injury|injured|concussion|questionable|x-rays?|helped off|carted off|exits? (?:game|early)|ruled out|torn acl|placed on ir|on ir|surgery|ankle injury|broken rib)\b/i
 if(injuryTerms.test(title)||(type==='INJURY'&&injuryTerms.test(String(row.detail||''))))
  return 'INJURY'
 if(type==='LINEUP_ROLE'||/\b(starting (?:lineup|pitcher|quarterback|goalie)|to start (?:game|first|against)|confirmed starter|rotation change|lineup confirmed)\b/i.test(title))
  return 'LINEUP'
 if(type==='TRANSACTION'||/\b(traded to|trade deal|signs with|placed on waivers|suspended \d+ games)\b/i.test(title))
  return 'TRANSACTION'
 if(type==='RECAP')return 'RECAP'
 if(type==='FANTASY'||type==='RANKINGS'||/\bfantasy (?:football|basketball|baseball|hockey|rankings|guide)\b/i.test(title))
  return 'FANTASY'
 if(/\b(odds (?:to win|for|shift)|line movement|betting line|sportsbook market)\b/i.test(title))
  return 'MARKET'
 return 'NEWS'
}

function urgencyScore(article,nowMs){
 const ageH=Math.max(0,(nowMs-article.publishedMs)/3_600_000)
 const freshness=ageH<=3?54:ageH<=12?42:ageH<=24?31:ageH<=48?19:
                 ageH<=96?8:ageH<=168?2:0
 let score=(weights[article.category]||45)+freshness
 const title=article.title
 if(/\brankings?\b|\bcheat sheet\b|\bdraft guide\b/i.test(title))score-=12
 if(/\ball.time\b|\bwhat is\b|\bwhere to watch\b|\bhistory of\b/i.test(title))score-=8
 return score
}

export function curateSportsNews(payload,nowMs=Date.now()) {
 if(!Number.isFinite(nowMs)||!payload||typeof payload!=='object'||Array.isArray(payload))
  return {status:'DATA_SOURCE_FAILURE',stories:[],reason:'MISSING_OR_INVALID_PAYLOAD',rawNewsRows:0}
 const collected=Date.parse(typeof payload.generated_at==='string'?payload.generated_at:'')
 if(!Number.isFinite(collected)||collected>nowMs+5*60*1000)
  return {status:'DATA_SOURCE_FAILURE',stories:[],reason:'INVALID_OR_FUTURE_COLLECTION_CLOCK',rawNewsRows:0}
 if(!Array.isArray(payload.news_events))
  return {status:'DATA_SOURCE_FAILURE',stories:[],reason:'COLLECTION_MISSING_NEWS_EVENTS',rawNewsRows:0}
 if(nowMs-collected>6*3600_000)
  return {status:'SOURCE_STALE',stories:[],reason:'ARTICLE_COLLECTION_OLDER_THAN_SIX_HOURS',
    generatedAt:payload.generated_at,rawNewsRows:0}
 const rows=payload.news_events.filter(row=>row?.event_source_type==='NEWS' && typeof row?.title==='string')
 const seenTitles=new Set(), seenUrls=new Set()
 const result=[]
 for(const raw of rows){
  const sport=String(raw.sport||'').toUpperCase()
  const title=String(raw.title||'').trim()
  const url=sourceUrl(raw.source_url)
  const when=publishedTime(raw.published_or_effective_at,nowMs)
  if(!NEWS_SPORTS.includes(sport)||title.length<12||!url||when===null
    ||promotional.test(title)||videoOnly.test(title))continue
  const norm=normalizedTitle(title),linkKey=sourceFingerprint(url)
  if(!norm||seenTitles.has(sport+'|'+norm)||seenUrls.has(linkKey))continue
  seenTitles.add(sport+'|'+norm)
  seenUrls.add(linkKey)
  const category=newsCategory(raw)
  const story={
    id:String(raw.event_node_id||sport+'|'+norm),sport,category,
    title,summary:String(raw.detail||'').trim().slice(0,420),
    source:String(raw.source||'Attributed reporting').slice(0,85),
    sourceTier:String(raw.source_tier||''),
    publishedAt:new Date(when).toISOString(),publishedMs:when,
    url,attributedNotVerifiedFact:true,
  }
  story.priority=urgencyScore(story,nowMs)
  result.push(story)
 }
 result.sort((a,b)=>b.priority-a.priority||b.publishedMs-a.publishedMs||a.id.localeCompare(b.id))
 return {
  status:result.length?'READY':'NO_QUALIFIED_ARTICLES',
  stories:result,
  generatedAt:payload.generated_at,
  rawNewsRows:rows.length,
  excludedRows:rows.length-result.length,
  sourceAttributionOnly:true,
  originalOddsOrBettingModelInputsCreated:false,
 }
}

export function selectHomeTopStories(stories,nowMs=Date.now(),limit=4){
 const eligible=(Array.isArray(stories)?stories:[])
  .filter(s=>s?.url && s?.publishedMs<=nowMs && nowMs-s.publishedMs<=48*3600_000)
  .sort((a,b)=>b.priority-a.priority||b.publishedMs-a.publishedMs)
 const featured=[],sports=new Set(),storyFamilies=new Set()
 const fingerprint=s=>s.title.toLowerCase()
   .replace(/\b(quarterback|running back|wide receiver|tight end|kicker|d\/st|idp)\b/g,'')
   .replace(/[^a-z0-9]+/g,' ').replace(/\s+/g,' ').trim()
 const add=story=>{
  if(!story||featured.length>=limit||featured.some(x=>x.id===story.id))return false
  if(storyFamilies.has(fingerprint(story)))return false
  featured.push(story);sports.add(story.sport);storyFamilies.add(fingerprint(story))
  return true
 }
 // Give the small home preview at least one honest injury report and one
 // different-sport newspaper recap when both exist. This preserves the user's
 // requested visible category signs without turning Home into a fantasy feed.
 for(const category of ['INJURY','RECAP']){
  const item=eligible.find(x=>x.category===category&&!sports.has(x.sport)&&
    !storyFamilies.has(fingerprint(x)))
  if(item)add(item)
 }
 for(const story of eligible){
  if(featured.length>=limit)break
  if(sports.has(story.sport)||storyFamilies.has(fingerprint(story)))continue
  add(story)
 }
 for(const story of eligible){
  if(featured.length>=limit)break
  add(story)
 }
 return featured
}

export function filterSportsNews(stories,{sport='ALL',category='ALL',search='',sort='TOP'}={}){
 const term=String(search||'').trim().toLowerCase()
 const rows=(Array.isArray(stories)?stories:[]).filter(story=>
  (sport==='ALL'||story.sport===sport)&&
  (category==='ALL'||story.category===category)&&
  (!term||(story.title+' '+story.summary+' '+story.sport).toLowerCase().includes(term)))
 return [...rows].sort((a,b)=>sort==='LATEST'
  ?b.publishedMs-a.publishedMs||b.priority-a.priority
  :b.priority-a.priority||b.publishedMs-a.publishedMs)
}

export function groupSportsNews(stories) {
 return NEWS_SPORTS.map(sport=>({
   sport,label:NEWS_SPORT_NAMES[sport],
   stories:stories.filter(story=>story.sport===sport)
 })).filter(group=>group.stories.length)
}
