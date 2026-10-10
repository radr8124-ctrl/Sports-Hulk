import test from 'node:test'
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {readFileSync} from 'node:fs'
import {buildSurvivorPreflightEvidence} from './survivor_preflight_evidence.js'

const asOf=Date.parse('2026-10-10T20:00:00Z')
const bookBytes=Buffer.from('original,paired,source\n')
const archive='nfl_live/game_fusion/history/NFL_GAME_SPORTWIZZARD_20261010T194410Z.csv'
const sha=createHash('sha256').update(bookBytes).digest('hex')
const fixture={game_key:'PHI@JAX',home:'JAX',away:'PHI',official_start:'2026-10-11T13:30:00+00:00',official_espn_event_id:'401872981',
 approved_play:false,markets:{MONEYLINE:{book:'fanduel',home_price:-400,away_price:315,quote_type:'TWO_SIDED_ARCHIVED_RESEARCH_SNAPSHOT',
 is_executable_current_offer:false,is_approved_bet:false,is_verified_main_line:false,source_captured_at:'2026-10-10T19:44:10+00:00',source_updated_at:'2026-10-10T19:42:49+00:00'}}}
const scoreboard={next_games:[{event_id:'401872981',start_time:'2026-10-11T13:30Z',home_abbr:'JAC',away_abbr:'PHI',home:'Jacksonville Jaguars',away:'Philadelphia Eagles',state:'pre'}],games:[]}
const books={status:'RESEARCH_ONLY',original_archive:{archive,sha256:sha},
 book_prices_live_or_executable_verified:false,model_advantage_proven:false,main_line_verified:false,fixtures:[fixture]}
const injuryCsv=[
 'player,team,position,status,injury_type,espn_team_id,espn_team_name,team_source_status,source_record_at,source_observed_at,source,espn_injury_id',
 'Saquon Barkley,PHI,RB,Out,Hamstring,21,Philadelphia Eagles,VERIFIED_ESPN_TEAM_ID_AND_NAME,2026-10-09T15:32Z,2026-10-10T19:44:19Z,ESPN_PUBLIC_GROUPED_NFL_INJURIES,641200',
 'Jalen Hurts,PHI,QB,Active,,21,Philadelphia Eagles,VERIFIED_ESPN_TEAM_ID_AND_NAME,2026-10-04T21:11Z,2026-10-10T19:44:19Z,ESPN_PUBLIC_GROUPED_NFL_INJURIES,641201',
 'Eric Murray,JAX,S,Doubtful,Concussion,30,Jacksonville Jaguars,VERIFIED_ESPN_TEAM_ID_AND_NAME,2026-10-10T00:02Z,2026-10-10T19:44:19Z,ESPN_PUBLIC_GROUPED_NFL_INJURIES,641202',
].join('\n')
const basics={team:'Jacksonville Jaguars',opponent:'Philadelphia Eagles',usedTeams:['Minnesota Vikings'],
 scoreboard,bookRef:books,archiveBytes:bookBytes,injuryCsv,nowMs:asOf}
const build=x=>buildSurvivorPreflightEvidence({...basics,...x})

test('real source identity gives paired dated price and two-sided player reports, never a qualified pick',()=>{
 const x=build()
 assert.equal(x.status,'SOURCE_EVIDENCE_ONLY')
 assert.equal(x.home,'Jacksonville Jaguars');assert.equal(x.away,'Philadelphia Eagles')
 assert.equal(x.event_id,'401872981')
 assert.equal(x.book.status,'RECENT_DATED_RESEARCH_NOT_EXECUTABLE')
 assert.equal(x.book.selected_team_american,-400)
 assert.equal(x.book.opponent_american,315)
 assert.equal(x.book.book,'fanduel')
 assert.equal(x.book.live_offer_verified,false)
 assert.equal(x.book.independent_model_edge_verified,false)
 assert.equal(x.qualified_survivor_pick,false)
 assert.equal(x.injuries.status,'RECENT_LIMITED_ESPN_REPORTS_NOT_STARTER_CONFIRMATION')
 assert.deepEqual(x.injuries.selected_team.players.map(y=>y.player),['Eric Murray'])
 assert.deepEqual(x.injuries.opponent.players.map(y=>y.player),['Saquon Barkley'])
 assert.equal(JSON.stringify(x).includes('Jalen Hurts'),false)
 assert.equal(JSON.stringify(x).includes('ANNIE G'),false)
})

test('wrong hashed archive, conflicting official ESPN event, or wrong pairing hides prices',()=>{
 for(const opts of [
  {archiveBytes:Buffer.from('tamper')},
  {scoreboard:{next_games:[{...scoreboard.next_games[0],event_id:'401000001'}]}},
  {bookRef:{...books,fixtures:[{...fixture,official_espn_event_id:'400000000'}]}},
  {bookRef:{...books,fixtures:[{...fixture,markets:{MONEYLINE:{...fixture.markets.MONEYLINE,home_price:0}}}]}},
 ]){
  const x=build(opts)
  assert.notEqual(x.book.status,'RECENT_DATED_RESEARCH_NOT_EXECUTABLE')
  assert.equal(x.book.selected_team_american,null)
  assert.equal(x.qualified_survivor_pick,false)
 }
})

test('expired price, inconsistent timestamps and started games cannot be labeled current',()=>{
 const aged=build({nowMs:Date.parse('2026-10-11T10:50:00Z')})
 assert.equal(aged.book.selected_team_american,null)
 assert.notEqual(aged.book.status,'RECENT_DATED_RESEARCH_NOT_EXECUTABLE')
 const started=build({nowMs:Date.parse('2026-10-11T14:00:00Z')})
 assert.equal(started.status,'GAME_STARTED_NO_PREGAME_RESEARCH')
 assert.equal(started.book.selected_team_american,null)
 const future=build({bookRef:{...books,fixtures:[{...fixture,markets:{MONEYLINE:{...fixture.markets.MONEYLINE,source_updated_at:'2026-10-11T19:42:49+00:00'}}}]}})
 assert.equal(future.book.selected_team_american,null)
})

test('source identity/date conflicts cannot claim players are Out or medically cleared',()=>{
 const mismatched=build({injuryCsv:injuryCsv.replace('21,Philadelphia Eagles','30,Philadelphia Eagles')})
 assert.equal(mismatched.injuries.opponent.players.length,0)
 const stale=build({nowMs:Date.parse('2026-10-11T10:50:00Z')})
 assert.equal(stale.injuries.opponent.players.length,0)
 assert.equal(stale.injuries.status,'INJURY_SOURCE_STALE_OR_UNVERIFIED')
 assert.equal(JSON.stringify(build().injuries).includes('clearance_verified":true'),false)
})

test('burned teams or not-official games fail closed with no data leaked',()=>{
 assert.equal(build({usedTeams:['Jacksonville Jaguars']}).status,'TEAM_PREVIOUSLY_USED')
 assert.equal(build({team:'Fake Team'}).status,'TEAM_NOT_RECOGNIZED')
 assert.equal(build({opponent:'Tennessee Titans'}).status,'OFFICIAL_FIXTURE_UNVERIFIED')
})

test('mutable production feeds cannot promote an unverified sportsbook snapshot or infer lineup clearance',()=>{
 // Files are live hourly source observations. This test deliberately does NOT
 // require a specific past player status/fixture or frozen capture time.
 const csv=readFileSync(new URL('../nfl_live/decision/NFL_ESPN_INJURIES.csv',import.meta.url),'utf8')
 const score=JSON.parse(readFileSync(new URL('./public/nfl_scores.json',import.meta.url),'utf8'))
 const research=JSON.parse(readFileSync(new URL('./public/nfl_research_book_refs.json',import.meta.url),'utf8'))
 const raw=readFileSync(new URL('../'+research.original_archive.archive,import.meta.url))
 const v=buildSurvivorPreflightEvidence({team:'Jacksonville Jaguars',opponent:'Philadelphia Eagles',usedTeams:[],
  scoreboard:score,bookRef:research,archiveBytes:raw,injuryCsv:csv,nowMs:Date.now()})
 assert.equal(v.qualified_survivor_pick,false)
 assert.equal(v.book.live_offer_verified===true,false)
 assert.equal(v.injuries.clearance_verified===true,false)
 assert.equal(v.injuries.starting_lineup_verified===true,false)
})
