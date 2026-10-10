import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {
 GAME_DAY_SPORTS,GAME_DAY_SOURCE_FILES,normalizeGameDayFeed,gameDayDeck,
} from './game_day_deck.js'

const NOW=Date.parse('2026-10-10T04:30:00Z')
const iso=ms=>new Date(ms).toISOString()
const mock=(rows,status='READY')=>({generated_at:iso(NOW-10*60000),status,games:rows})
const game=(date,league='NHL',overrides={})=>({
 event_id:'4010901',start_time:iso(NOW+date*3600000),
 away:'Road Tigers',home:'Home Falcons',away_abbr:'RTG',home_abbr:'HFL',
 away_score:0,home_score:0,final:false,live:false,status:'Scheduled',
 ...overrides,
})

test('all league score source files use explicit sport selectors',()=>{
 assert.deepEqual(GAME_DAY_SPORTS,['NFL','NHL','CFB','NBA','MLB'])
 assert.equal(Object.keys(GAME_DAY_SOURCE_FILES).length,5)
 for(const url of Object.values(GAME_DAY_SOURCE_FILES)){
  assert.match(url,/^\/[a-z]+_scores\.json$/)
 }
})

test('missing feed and failed provider are DATA SOURCE FAILURE, never NO BET',()=>{
 let n=normalizeGameDayFeed('NHL',null,NOW)
 assert.equal(n.status,'DATA_SOURCE_FAILURE')
 assert.deepEqual(n.games,[])
 n=normalizeGameDayFeed('NBA',{...mock([]),'status':'FAILED'},NOW)
 assert.equal(n.status,'DATA_SOURCE_FAILURE')
 n=normalizeGameDayFeed('MLB',{generated_at:iso(NOW-60_000)},NOW)
 assert.equal(n.status,'DATA_SOURCE_FAILURE')
 assert.equal(gameDayDeck({NHL:n},'NHL',NOW).state,'DATA_SOURCE_FAILURE')
})

test('valid empty schedule is NO SCHEDULED GAMES, not data failure or a forced PASS',()=>{
 const source=normalizeGameDayFeed('NHL',mock([]),NOW)
 assert.equal(source.status,'READY')
 const deck=gameDayDeck({NHL:source},'NHL',NOW)
 assert.equal(deck.state,'NO_SCHEDULED_GAMES')
 assert.deepEqual(deck.games,[])
 assert.equal(deck.explicitlyNotABettingRecommendation,true)
})

test('expired or future source timestamps cannot claim live games',()=>{
 const old=normalizeGameDayFeed('NHL',{
  generated_at:iso(NOW-4*3600000),games:[game(-.1,'NHL',{live:true})],
 },NOW)
 assert.equal(old.status,'SOURCE_STALE')
 assert.equal(old.games[0]?.state,'STATUS_NOT_VERIFIED')
 assert.equal(gameDayDeck({NHL:old},'NHL',NOW).state,'SOURCE_STALE')
 const future=normalizeGameDayFeed('NHL',{
  generated_at:iso(NOW+60*60000),games:[game(-.1)],
 },NOW)
 assert.equal(future.status,'DATA_SOURCE_FAILURE')
 assert.equal(future.games.length,0)
})

test('source must have real event IDs/teams/UTC date; future scores are not final',()=>{
 const rows=[game(1),game(2,'NHL',{event_id:'4010902',away_score:38,home_score:27}),
             game(2,'NHL',{event_id:'4010902'})]
 const source=normalizeGameDayFeed('NHL',mock(rows),NOW)
 assert.equal(source.games.length,2)
 assert.equal(source.games[0].awayScore,null)
 assert.equal(source.games[1].homeScore,null)
 assert.equal(source.games[0].state,'UPCOMING')
 assert.equal(source.games[1].state,'UPCOMING')
 assert.equal(source.games.every(x=>x.originalQuoteOrModelProbabilityProvided===false),true)
})

test('a legitimate final shows exact official scores and live status is not invented',()=>{
 const source=normalizeGameDayFeed('NBA',mock([
  game(-1,'NBA',{event_id:'101',away_score:101,home_score:104,final:true}),
  game(-.2,'NBA',{event_id:'102',away_score:62,home_score:63,live:true}),
 ]),NOW)
 assert.equal(source.games[0].state,'FINAL')
 assert.equal(source.games[0].awayScore,101)
 assert.equal(source.games[0].homeScore,104)
 assert.equal(source.games[1].state,'LIVE')
})

test('MLB schedule source contains today, next, recent; no scores for upcoming fixtures',()=>{
 const payload={
  generated_at:iso(NOW-10*60000),today_games:[{
   gamePk:849831,gameDate:iso(NOW+1*3600000),
   away:'Chicago White Sox',home:'Cleveland Guardians',
   away_score:null,home_score:null,final:false,
  }],
  next_games:[{
   gamePk:849809,gameDate:iso(NOW+36*3600000),
   away:'Los Angeles Dodgers',home:'Milwaukee Brewers',
   away_score:null,home_score:null,final:false,
  }],
 }
 const parsed=normalizeGameDayFeed('MLB',payload,NOW)
 assert.equal(parsed.games.length,2)
 assert.equal(parsed.games[0].sourceName,'MLB StatsAPI')
 assert.equal(parsed.games[0].state,'UPCOMING')
 assert.equal(parsed.games[1].awayScore,null)
})

test('All games chooses one matched game per league before repeating a single league',()=>{
 const source={}
 for(const [i,sport] of GAME_DAY_SPORTS.entries()){
  const rows=[
   game(i+1,sport,{event_id:'event'+sport}),
   game(i+1.1,sport,{event_id:'second'+sport}),
  ]
  source[sport]=normalizeGameDayFeed(sport,sport==='MLB'?{
    generated_at:iso(NOW-10*60000),
    today_games:rows.map((item,j)=>({
      gamePk:89000+j,gameDate:item.start_time,away:item.away,home:item.home,
      final:false,
    })),
  }:mock(rows),NOW)
 }
 const all=gameDayDeck(source,'ALL',NOW)
 assert.equal(all.games.length,5)
 assert.equal(new Set(all.games.map(x=>x.sport)).size,5)
 assert(all.games.every(x=>x.state==='UPCOMING'))
 assert.deepEqual(all.sources.map(x=>x.status),['READY','READY','READY','READY','READY'])
})

test('one failed league does not suppress honest data in healthy leagues',()=>{
 const healthy=normalizeGameDayFeed('CFB',mock([game(1,'CFB')]),NOW)
 const deck=gameDayDeck({CFB:healthy,NHL:normalizeGameDayFeed('NHL',null,NOW)},'ALL',NOW)
 assert.equal(deck.state,'GAMES_AVAILABLE')
 assert.equal(deck.games[0].sport,'CFB')
 assert.ok(deck.sourceFailureCount>=1)
 assert.equal(deck.explicitlyNotABettingRecommendation,true)
})

test('real first-party fixture files have source timestamp and nonfabricated game identity',()=>{
 for(const sport of GAME_DAY_SPORTS){
  const filename=GAME_DAY_SOURCE_FILES[sport].slice(1)
  const data=JSON.parse(readFileSync(new URL('./public/'+filename,import.meta.url),'utf8'))
  const referenceClock=Date.parse(data.generated_at)+5*60_000
  const parsed=normalizeGameDayFeed(sport,data,referenceClock)
  assert.equal(parsed.status,'READY',sport)
  for(const event of parsed.games){
   assert.equal(event.sport,sport)
   assert(event.officialEventId)
   assert(Number.isFinite(Date.parse(event.start)))
   if(event.state==='UPCOMING'){
    assert.equal(event.awayScore,null)
    assert.equal(event.homeScore,null)
   }
  }
 }
})
