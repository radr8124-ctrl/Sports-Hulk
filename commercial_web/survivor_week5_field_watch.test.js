import test from 'node:test'
import assert from 'node:assert/strict'
import{readFileSync}from'node:fs'
import{buildSurvivorWeek5FieldWatch}from'./survivor_week5_field_watch.js'
const csv=readFileSync(new URL('../nfl_live/survivor_pool/derived/SURVIVOR_POOL_LEDGER.csv',import.meta.url),'utf8')
const meta=JSON.parse(readFileSync(new URL('../nfl_live/survivor_pool/derived/LATEST_OFFICIAL_POOL.json',import.meta.url),'utf8'))
const scores=JSON.parse(readFileSync(new URL('./public/nfl_scores.json',import.meta.url),'utf8'))
const now=Date.parse('2026-10-11T12:00:00Z')
const run=(changes={})=>buildSurvivorWeek5FieldWatch({csvText:csv,meta,scoreboard:{...scores,generated_at:'2026-10-11T11:58:00Z'},linkedEntry:'ANNIE G 01',zenithPicks:[],at:now,...changes})

test('all 333 official tickets, 148 X-Cowboys, 185 pending Sunday, exact PDF team',()=>{
 const w=run()
 assert.equal(w.status,'VERIFIED_OFFICIAL_FIELD')
 assert.equal(w.week,5)
 assert.equal(w.total_entries,333)
 assert.equal(w.marked_eliminated_before_sunday,148)
 assert.equal(w.in_contention_before_sunday,185)
 assert.equal(w.teams.reduce((n,t)=>n+t.entries,0),185)
 assert.equal(w.teams.find(x=>x.team==='Houston Texans').entries,62)
 assert.equal(w.teams.find(x=>x.team==='Cincinnati Bengals').entries,60)
 assert.equal(w.owner.entry_name,'ANNIE G 01')
 assert.deepEqual(w.owner.official_teams,['Houston Texans'])
 assert.deepEqual(w.owner.zenith_saved_teams,[])
 assert.equal(w.owner.synchronization,'ORGANIZER_PDF_ONLY_NOT_ZENITH_SAVED')
 assert.equal(w.pool_result_certified,false)
 assert.equal(w.external_submission_verified_by_zenith,false)
 assert.equal(w.teams.find(x=>x.team==='Houston Texans').game.status,'UPCOMING')
 assert.equal(w.teams.find(x=>x.team==='Houston Texans').game.opponent,'Tennessee Titans')
})

test('never compare to next week Houston Jacksonville from scoreboard',()=>{
 const w=run()
 const hou=w.teams.find(x=>x.team==='Houston Texans')
 assert.equal(hou.game.opponent,'Tennessee Titans')
 assert.match(hou.game.kickoff_utc,/2026-10-11/)
})

test('fresh ESPN fixture with live lead shows LIVE_AHEAD but not certified surviving',()=>{
 const mock=structuredClone(scores)
 mock.generated_at='2026-10-11T17:42:00Z'
 const game=[...mock.games,...mock.next_games].find(g=>g.event_id==='401872984')
 game.state='in';game.live=true;game.home_score='10';game.away_score='17';game.status='Q2 6:05'
 const w=run({scoreboard:mock,at:Date.parse('2026-10-11T17:43:00Z')})
 assert.equal(w.teams.find(x=>x.team==='Houston Texans').game.status,'LIVE_AHEAD')
 assert.equal(w.teams.find(x=>x.team==='Houston Texans').game.score_line,'Houston Texans 17 – Tennessee Titans 10')
 assert.equal(w.pool_result_certified,false)
 assert.equal(w.live_exposure.currently_ahead,62)
 assert.equal(w.live_exposure.currently_behind,0)
 assert.equal(w.live_exposure.currently_ahead+w.live_exposure.currently_behind+w.live_exposure.currently_tied+w.live_exposure.final_games_pending_pool_grade+w.live_exposure.waiting_or_unverified,185)
})

test('Final Houston loss counts all 62 tickets as provisional losses, not organizer-certified eliminations',()=>{
 const mock=structuredClone(scores)
 mock.generated_at='2026-10-11T21:45:00Z'
 const game=[...mock.games,...mock.next_games].find(g=>g.event_id==='401872984')
 game.state='post';game.live=false;game.final=true;game.away_score='14';game.home_score='21';game.status='Final'
 const w=run({scoreboard:mock,at:Date.parse('2026-10-11T21:46:00Z')})
 assert.equal(w.teams.find(x=>x.team==='Houston Texans').game.status,'FINAL_LOSS_PENDING_ORGANIZER')
 assert.equal(w.live_exposure.final_loss_pending_organizer,62)
 assert.equal(w.live_exposure.final_win_pending_organizer,0)
 assert.equal(w.in_contention_before_sunday,185)
 assert.equal(w.pool_result_certified,false)
 assert.deepEqual(w.owner.official_teams,['Houston Texans'])
})

test('Final Houston win counts as pending verified game result but does not auto-advance pool',()=>{
 const mock=structuredClone(scores)
 mock.generated_at='2026-10-11T21:45:00Z'
 const game=[...mock.games,...mock.next_games].find(g=>g.event_id==='401872984')
 game.state='post';game.live=false;game.final=true;game.away_score='24';game.home_score='17';game.status='Final'
 const w=run({scoreboard:mock,at:Date.parse('2026-10-11T21:46:00Z')})
 assert.equal(w.teams.find(x=>x.team==='Houston Texans').game.status,'FINAL_WIN_PENDING_ORGANIZER')
 assert.equal(w.live_exposure.final_win_pending_organizer,62)
 assert.equal(w.pool_result_certified,false)
})

test('old scoreboard still displays original picks but not fake live scores',()=>{
 const old={...scores,generated_at:'2026-10-10T12:00:00Z'}
 const w=run({scoreboard:old})
 assert.equal(w.scoreboard_status,'STALE_SCOREBOARD')
 assert.equal(w.teams.find(x=>x.team==='Houston Texans').game.status,'SCORE_NOT_VERIFIED')
 assert.deepEqual(w.owner.official_teams,['Houston Texans'])
})

test('no personal owner leaks when not explicitly linked and missing official metadata fails closed',()=>{
 const anon=run({linkedEntry:null})
 assert.equal(anon.owner,null)
 assert.equal(JSON.stringify(anon).includes('ANNIE G 01'),false)
 const absent=run({meta:{max_week_in_file:4}})
 assert.equal(absent.status,'OFFICIAL_WEEK5_SOURCE_UNAVAILABLE')
 assert.equal(absent.teams.length,0)
})

test('incomplete or nonmatching team rows never produce an invented 185 score',()=>{
 const corrupted=csv.replaceAll('ANNIE G 01','ANNIE G 99')
 const w=run({csvText:corrupted})
 assert.equal(w.status,'VERIFIED_OFFICIAL_FIELD')
 assert.deepEqual(w.owner.official_teams,[])
 assert.equal(w.owner.synchronization,'ORGANIZER_TICKET_NOT_MATCHED')
 const truncated=csv.slice(0,900)
 assert.equal(run({csvText:truncated}).status,'FIELD_INTEGRITY_CONFLICT')
})
