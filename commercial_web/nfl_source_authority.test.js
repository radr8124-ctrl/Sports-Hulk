import test from 'node:test'
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {readFileSync} from 'node:fs'
import {auditNflBookSourceAuthority} from './nfl_source_authority.js'

const nowMs=Date.parse('2026-10-10T21:30:00Z')
const archive=Buffer.from('immutable_book_archive_fixture\n')
const sha=createHash('sha256').update(archive).digest('hex')
const book=(game,away,home,eventId)=>({
 approved_play:false,away,home,game_key:game,official_espn_event_id:eventId,
 official_start:'2026-10-11T13:30:00+00:00',
 markets:{MONEYLINE:{book:'fanduel',home_price:-400,away_price:315,
  quote_type:'TWO_SIDED_ARCHIVED_RESEARCH_SNAPSHOT',is_approved_bet:false,
  is_executable_current_offer:false,is_verified_main_line:false,
  source_updated_at:'2026-10-10T20:20:00+00:00',source_captured_at:'2026-10-10T20:44:21+00:00'}},
})
const scoreboard={generated_at:'2026-10-10T21:25:00Z',next_games:[{
 event_id:'401872981',start_time:'2026-10-11T13:30:00Z',
 away:'Philadelphia Eagles',home:'Jacksonville Jaguars',away_abbr:'PHI',home_abbr:'JAC',state:'pre',final:false,
}],games:[]}
const header=['event_id','start','away_team','home_team','away_moneyline','home_moneyline',
 'away_spread','home_spread','total','sportsbooks','books_list','collected_at','market_source',
 'market_status','source_event_last_update'].join(',')
const row=(update='2026-10-02T07:54:00Z',collected='2026-10-02T07:55:00Z')=>[
 '24886','2026-10-11 13:30:00+00:00','Philadelphia Eagles','Jacksonville Jaguars',
 315,-400,4.5,-4.5,47,2,'"fanduel, betmgm"',collected,'propline','LIVE',update,
].join(',')
const csv=header+'\n'+row()+'\n'
const research={status:'RESEARCH_ONLY',book_prices_live_or_executable_verified:false,
 model_advantage_proven:false,main_line_verified:false,betting_decision_created:false,
 original_archive:{archive:'nfl_live/game_fusion/history/NFL_GAME_SPORTWIZZARD_20261010T204421Z.csv',sha256:sha},
 fixtures:[book('PHI@JAX','PHI','JAX','401872981')]}
const fusion={generated_at:'2026-10-10T20:44:21Z',therundown_receipts:[{http:429,remaining:'0',date:'2026-10-10'}],therundown_games:0}
const base={primaryCsv:csv,scoreboard,research,archiveBytes:archive,fusion,nowMs}
const audit=options=>auditNflBookSourceAuthority({...base,...options})

test('LIVE source label with 8-day-old source time is stale; archived paired research remains non-executable',()=>{
 const a=audit()
 assert.equal(a.status,'PRIMARY_STALE_RESEARCH_ONLY')
 assert.equal(a.official_upcoming_games,1)
 assert.equal(a.original_primary_matching_games,1)
 assert.equal(a.primary_fresh_game_count,0)
 assert.equal(a.primary_stale_game_count,1)
 assert.equal(a.primary_live_label_but_stale_count,1)
 assert.equal(a.research_recent_paired_games,1)
 assert.equal(a.research_archive_verified,true)
 assert.equal(a.alternate_quota_status,'QUOTA_LIMITED_AT_LAST_CAPTURE')
 assert.equal(a.no_approved_bet_or_survivor_pick_created,true)
 assert.equal(a.executability_verified,false)
 assert.equal(a.independent_model_edge_verified,false)
 assert.ok(a.primary_latest_provider_at.startsWith('2026-10-02'))
 assert.equal(JSON.stringify(a).includes('Jalen'),false)
})

test('corrupt original archive bytes or changed original source hash suppresses research counts',()=>{
 for(const options of [
  {archiveBytes:Buffer.from('fake')},
  {research:{...research,original_archive:{...research.original_archive,sha256:'0'.repeat(64)}}},
  {research:{...research,book_prices_live_or_executable_verified:true}},
 ]){
  const a=audit(options)
  assert.equal(a.research_archive_verified,false)
  assert.equal(a.research_recent_paired_games,0)
  assert.equal(a.status,'SOURCES_STALE_OR_UNVERIFIED')
  assert.equal(a.no_approved_bet_or_survivor_pick_created,true)
 }
})

test('source time must be actual provider time; future or naive dates do not become fresh',()=>{
 for(const time of ['2026-10-11T20:00:00Z','2026-10-10T21:15:00','2026-10-02T07:54:00Z']){
  const a=audit({primaryCsv:header+'\n'+row(time,'2026-10-10T21:25:00Z')+'\n'})
  assert.equal(a.primary_fresh_game_count,0)
  assert.equal(a.no_approved_bet_or_survivor_pick_created,true)
 }
})

test('genuinely recent primary source still cannot prove bookmaker execution or an independent edge',()=>{
 const a=audit({primaryCsv:header+'\n'+row('2026-10-10T21:18:00Z','2026-10-10T21:20:00Z')+'\n'})
 assert.equal(a.status,'PRIMARY_TIME_FRESH_EXECUTION_UNVERIFIED')
 assert.equal(a.primary_fresh_game_count,1)
 assert.equal(a.executability_verified,false)
 assert.equal(a.independent_model_edge_verified,false)
 assert.equal(a.qualified_selection_count,0)
})

test('duplicate original primary game, wrong research ESPN game ID or ambiguous research matchup fail closed',()=>{
 const duplicate=audit({primaryCsv:csv+row()+'\n'})
 assert.equal(duplicate.primary_identity_conflicts,1)
 assert.equal(duplicate.primary_fresh_game_count,0)
 assert.equal(duplicate.primary_stale_game_count,0)
 const noOfficial=audit({research:{...research,fixtures:[{...research.fixtures[0],official_espn_event_id:'401000000'}]}})
 assert.equal(noOfficial.research_recent_paired_games,0)
 const duplicateBook=audit({research:{...research,fixtures:[...research.fixtures,...research.fixtures]}})
 assert.equal(duplicateBook.research_recent_paired_games,0)
})

test('recent research and primary started games cannot appear as pregame status',()=>{
 const a=audit({nowMs:Date.parse('2026-10-11T15:00:00Z'),scoreboard:{...scoreboard,generated_at:'2026-10-11T14:55:00Z'}})
 assert.equal(a.status,'SOURCE_SCOREBOARD_STALE_OR_UNVERIFIED')
 assert.equal(a.official_upcoming_games,null)
 assert.equal(a.research_recent_paired_games,0)
 assert.equal(a.primary_fresh_game_count,0)
 assert.equal(a.no_approved_bet_or_survivor_pick_created,true)
})

test('actual production source readback is aggregate only and explicitly never qualifies any selections',()=>{
 const read=x=>JSON.parse(readFileSync(new URL(x,import.meta.url),'utf8'))
 const origin=read('../nfl_live/game_fusion/NFL_GAME_BETTING_FUSION_RECEIPT.json')
 const reference=read('./public/nfl_research_book_refs.json')
 const bytes=readFileSync(new URL('../'+reference.original_archive.archive,import.meta.url))
 const a=auditNflBookSourceAuthority({
  primaryCsv:readFileSync(new URL('../nfl_live/derived/NFL_LIVE_MARKET.csv',import.meta.url),'utf8'),
  research:reference,archiveBytes:bytes,fusion:origin,
  scoreboard:read('./public/nfl_scores.json'),nowMs:Date.now(),
 })
 assert.equal(a.no_approved_bet_or_survivor_pick_created,true)
 assert.equal(a.qualified_selection_count,0)
 assert.equal(a.executability_verified,false)
 assert.equal(a.independent_model_edge_verified,false)
 assert.ok(a.official_upcoming_games===null||a.official_upcoming_games>=0)
})
