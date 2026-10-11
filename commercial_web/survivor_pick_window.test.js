import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {survivorVerifiedPickWindow} from './survivor_pick_window.js'
const schedule=readFileSync(new URL('../nfl_live/derived/NFLVERSE_2026_SCHEDULE.csv',import.meta.url),'utf8')
const originalScores=JSON.parse(readFileSync(new URL('./public/nfl_scores.json',import.meta.url),'utf8'))
const teams=['Los Angeles Chargers','San Francisco 49ers','Kansas City Chiefs','Buffalo Bills','Minnesota Vikings']
const before=Date.parse('2026-10-10T21:55:00Z')
const after=Date.parse('2026-10-10T22:21:00Z')
const scores={...originalScores,generated_at:'2026-10-10T21:55:00Z'}
const input={scheduleCsv:schedule,scoreboard:scores,poolWeek:5,entryStatus:'ALIVE',usedTeams:teams,currentPicks:[],nowMs:before,ruleConfirmed:true}
const run=(updates={})=>survivorVerifiedPickWindow({...input,...updates})

test('real NFLverse Week 5 2026 source opens only still-verifiable unused teams before Saturday cutoff',()=>{
 const v=run()
 assert.equal(v.status,'WINDOW_OPEN')
 assert.equal(v.pool_week,5)
 assert.equal(v.week_saturday_deadline,'2026-10-10T22:00:00.000Z')
 assert.equal(v.local_deadline_label,'Sat Oct 10, 6:00 PM EDT')
 assert.ok(v.editable_teams.includes('Jacksonville Jaguars'))
 assert.equal(v.editable_team_cutoffs['Jacksonville Jaguars'],'2026-10-10T22:00:00.000Z')
 assert.ok(v.editable_teams.includes('Houston Texans'))
 assert.ok(!v.editable_teams.includes('Dallas Cowboys'))
 for(const t of teams)assert.equal(v.editable_teams.includes(t),false)
 assert.equal(v.live_external_pool_submission_verified,false)
 assert.equal(v.saved_in_zenith_only,false)
 assert.equal(v.current_saved_pick_count,0)
 assert.equal(v.total_week_schedule_games,15)
 assert.ok(v.scoreboard_verified_games>=10)
 assert.match(v.schedule_source_sha256,/^[a-f0-9]{64}$/)
})

test('at exactly 6 PM Saturday, current editor closes before any Sunday game kickoffs',()=>{
 for(const time of ['2026-10-10T22:00:00Z','2026-10-10T22:21:00Z']){
  const v=run({nowMs:Date.parse(time),scoreboard:{...scores,generated_at:time}})
  assert.equal(v.status,'WINDOW_CLOSED')
  assert.equal(v.reason,'SATURDAY_POOL_DEADLINE_PASSED')
  assert.deepEqual(v.editable_teams,[])
  assert.equal(v.current_saved_pick_count,0)
  assert.equal(v.saved_in_zenith_only,false)
  assert.equal(v.external_pool_result_verified,false)
 }
})

test('the original Sunday rule never reopens on a later same-game kickoff day',()=>{
 const time='2026-10-11T15:00:00Z'
 const v=run({nowMs:Date.parse(time),scoreboard:{...scores,generated_at:time}})
 assert.equal(v.status,'WINDOW_CLOSED')
 assert.equal(v.editable_teams.length,0)
})

test('Thursday team cutoff uses two hours before first kickoff, not the upcoming Saturday',()=>{
 const old=JSON.parse(JSON.stringify(scores))
 old.next_games.push({event_id:'401872980',start_time:'2026-10-09T00:15:00Z',away:'Tampa Bay Buccaneers',home:'Dallas Cowboys',away_abbr:'TB',home_abbr:'DAL',state:'pre',final:false})
 const early=run({nowMs:Date.parse('2026-10-08T21:00:00Z'),scoreboard:{...old,generated_at:'2026-10-08T21:00:00Z'},usedTeams:[]})
 assert.equal(early.status,'WINDOW_OPEN')
 assert.ok(early.editable_teams.includes('Dallas Cowboys'))
 assert.equal(early.editable_team_cutoffs['Dallas Cowboys'],'2026-10-08T22:15:00.000Z')
 const late=run({nowMs:Date.parse('2026-10-08T22:16:00Z'),scoreboard:{...old,generated_at:'2026-10-08T22:16:00Z'},usedTeams:[]})
 assert.equal(late.status,'WINDOW_OPEN')
 assert.ok(!late.editable_teams.includes('Dallas Cowboys'))
 assert.ok(late.editable_teams.includes('Jacksonville Jaguars'))
})

test('Week 6 automatically shifts to Oct 17 Saturday at 6 ET and respects Thursday early cutoff',()=>{
 const starting={...scores,generated_at:'2026-10-15T21:00:00Z',next_games:[
  {event_id:'401872995',start_time:'2026-10-16T00:15:00Z',away:'Seattle Seahawks',home:'Denver Broncos',away_abbr:'SEA',home_abbr:'DEN',state:'pre',final:false},
 ],games:[]}
 const early=run({poolWeek:6,nowMs:Date.parse('2026-10-15T21:00:00Z'),scoreboard:starting,usedTeams:[]})
 assert.equal(early.week_saturday_deadline,'2026-10-17T22:00:00.000Z')
 assert.equal(early.status,'WINDOW_OPEN')
 assert.ok(early.editable_teams.includes('Seattle Seahawks'))
 const late=run({poolWeek:6,nowMs:Date.parse('2026-10-15T22:16:00Z'),scoreboard:{...starting,generated_at:'2026-10-15T22:16:00Z'},usedTeams:[]})
 assert.ok(!late.editable_teams.includes('Seattle Seahawks'))
 assert.equal(late.status,'WINDOW_SOURCE_INCOMPLETE')
})

test('winter DST weeks compute Saturday 6 PM EST rather than hard-coding EDT',()=>{
 const v=run({poolWeek:9,nowMs:Date.parse('2026-11-07T22:00:00Z'),scoreboard:{...scores,generated_at:'2026-11-07T22:00:00Z'},usedTeams:[]})
 assert.equal(v.week_saturday_deadline,'2026-11-07T23:00:00.000Z')
 assert.equal(v.local_deadline_label,'Sat Nov 7, 6:00 PM EST')
})

test('used teams and saved picks never become unknown external submissions after cutoff',()=>{
 const v=run({nowMs:after,scoreboard:{...scores,generated_at:new Date(after).toISOString()},currentPicks:['Jacksonville Jaguars']})
 assert.equal(v.status,'WINDOW_CLOSED')
 assert.equal(v.current_saved_pick_count,1)
 assert.equal(v.saved_in_zenith_only,true)
 assert.equal(v.live_external_pool_submission_verified,false)
 assert.deepEqual(v.editable_teams,[])
})

test('unverified official schedule, stale scoreboard and mismatch all fail closed',()=>{
 const scenarios=[
  {scheduleCsv:''},{scheduleCsv:schedule.replace('2026_05_PHI_JAX','2026_05_PHI_SEA')},
  {scoreboard:{...scores,generated_at:'2026-10-09T15:00:00Z'}},
  {ruleConfirmed:false},{poolWeek:0},
  {scoreboard:{...scores,games:scores.games.map(x=>x.event_id==='401872981'?{...x,start_time:'2026-10-14T13:30:00Z'}:x),next_games:scores.next_games.map(x=>x.event_id==='401872981'?{...x,start_time:'2026-10-14T13:30:00Z'}:x)}},
 ]
 for(const values of scenarios){
  const result=run(values)
  assert.equal(result.editable_teams.length,0)
  assert.equal(result.live_external_pool_submission_verified,false)
  assert.notEqual(result.status,'WINDOW_OPEN')
 }
})

test('no personal account or pool entries exposed in schedule-only response',()=>{
 const v=run({nowMs:after,scoreboard:{...scores,generated_at:new Date(after).toISOString()}})
 const raw=JSON.stringify(v)
 assert.equal(raw.includes('ANNIE G'),false)
 assert.equal(raw.includes('radr8124'),false)
 assert.equal('entry_name' in v,false)
 assert.equal('past_picks' in v,false)
 assert.equal('market_prob_pct' in v,false)
})
