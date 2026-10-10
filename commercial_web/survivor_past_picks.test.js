import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {buildSurvivorPastPickHistory} from './survivor_past_picks.js'

const baseline={
 status:'ALIVE', current_week:5,current_picks:[],
 used_teams:['Los Angeles Chargers','San Francisco 49ers','Kansas City Chiefs','Buffalo Bills','Minnesota Vikings'],
 history:[
  {week:1,team:'Los Angeles Chargers',result:'SURVIVED',source:'WEEK #2 RESULTS A-Z.pdf'},
  {week:2,team:'San Francisco 49ers',result:'SURVIVED',source:'WEEK #2 RESULTS A-Z.pdf'},
  {week:3,team:'Kansas City Chiefs',result:'SURVIVED',source:'NFLVERSE_2026_SCHEDULE.csv'},
  {week:3,team:'Buffalo Bills',result:'SURVIVED',source:'NFLVERSE_2026_SCHEDULE.csv'},
  {week:4,team:'Minnesota Vikings',result:'SURVIVED',source:'NFLVERSE_2026_SCHEDULE.csv'},
 ],
 week_3:{required_picks:2,picks:[{team:'Kansas City Chiefs',result:'WIN',game_status:'FINAL: Kansas City Chiefs 24 - Miami Dolphins 10'},
  {team:'Buffalo Bills',result:'WIN',game_status:'FINAL: Los Angeles Chargers 16 - Buffalo Bills 24'}],
  entry_result:'WIN',submitted:true,official_pool_sheet_confirmed:true},
 week_4:{required_picks:1,picks:[{team:'Minnesota Vikings',result:'WIN',game_status:'FINAL: Miami Dolphins 10 - Minnesota Vikings 15'}],
  entry_result:'WIN',submitted:false,official_pool_sheet_confirmed:true},
 week_5:{picks:[],entry_result:'OPEN',submitted:false},
}
const build=(item=baseline)=>buildSurvivorPastPickHistory(item,5)

test('original private entry preserves all five recorded successful picks across four weeks',()=>{
 const before=JSON.stringify(baseline)
 const x=build()
 assert.equal(x.status,'RECORDED_HISTORY_COMPLETE')
 assert.equal(x.total_picks,5)
 assert.equal(x.total_weeks,4)
 assert.equal(x.used_team_count,5)
 assert.deepEqual(x.week_groups.map(g=>g.week),[1,2,3,4])
 assert.deepEqual(x.week_groups.map(g=>g.picks.map(r=>r.team)),[
  ['Los Angeles Chargers'],['San Francisco 49ers'],
  ['Kansas City Chiefs','Buffalo Bills'],['Minnesota Vikings'],
 ])
 assert.ok(x.week_groups.every(g=>g.picks.every(p=>p.result==='SURVIVED')))
 assert.equal(x.current_week,5)
 assert.equal(x.current_picks_saved,0)
 assert.equal(x.external_pool_submission_verified,false)
 assert.equal(x.week_groups[0].picks[0].game_score,null)
 assert.equal(x.week_groups[3].picks[0].game_score,'Miami Dolphins 10 - Minnesota Vikings 15')
 assert.equal(x.week_groups[2].submission_status,'SUBMISSION_RECORDED_IN_ZENITH')
 assert.equal(x.week_groups[3].submission_status,'SUBMISSION_NOT_RECORDED')
 assert.equal(JSON.stringify(baseline),before)
})

test('actual saved ANNIE G 01 records have five original pick histories and zero Week 5 choice',()=>{
 const source=JSON.parse(readFileSync(new URL('../nfl_live/derived/SURVIVOR_ENTRIES.json',import.meta.url),'utf8'))
 const e=source?.entries?.['ANNIE G 01']
 assert.ok(e)
 const x=buildSurvivorPastPickHistory(e,source.pool_current_week)
 assert.equal(x.status,'RECORDED_HISTORY_COMPLETE')
 assert.equal(x.total_picks,5)
 assert.equal(x.total_weeks,4)
 assert.equal(x.current_picks_saved,0)
 assert.deepEqual(x.week_groups[2].picks.map(r=>r.team),['Kansas City Chiefs','Buffalo Bills'])
 assert.equal(x.external_pool_submission_verified,false)
})

test('historical originals are not invented from burned team order, current scoreboard or missing source',()=>{
 const missing={status:'ALIVE',used_teams:[...baseline.used_teams],current_picks:[],history:[]}
 const x=build(missing)
 assert.equal(x.total_picks,0)
 assert.equal(x.status,'HISTORY_UNAVAILABLE')
 assert.equal(x.week_groups.length,0)
 assert.equal(x.used_team_count,5)
})

test('ambiguous previous win/loss or used-team conflict is flagged, never reported as survived',()=>{
 const conflict=structuredClone(baseline)
 conflict.history[0].result='SURVIVED'
 conflict.week_3.picks[0].result='LOSS'
 conflict.used_teams=conflict.used_teams.filter(team=>team!=='San Francisco 49ers')
 const x=build(conflict)
 assert.equal(x.status,'HISTORY_CONFLICT_NEEDS_REVIEW')
 assert.equal(x.week_groups[1].picks[0].result,'REVIEW_REQUIRED')
 assert.equal(x.week_groups[2].picks[0].result,'REVIEW_REQUIRED')
 assert.equal(x.week_groups[2].picks[1].result,'SURVIVED')
})

test('an OPEN Week 5 or future placeholders cannot appear as a recorded past result',()=>{
 const mutated=structuredClone(baseline)
 mutated.history.push({week:5,team:'Cincinnati Bengals',result:'PENDING',source:'TEST'})
 mutated.history.push({week:6,team:'Houston Texans',result:'WIN',source:'TEST'})
 const x=build(mutated)
 assert.equal(x.total_picks,5)
 assert.equal(x.current_picks_saved,0)
 assert.deepEqual(x.week_groups.map(g=>g.week),[1,2,3,4])
})

test('duplicate original history rows for the same week and team fail review, not double counts',()=>{
 const duplicate=structuredClone(baseline)
 duplicate.history.push({...duplicate.history[2]})
 const x=build(duplicate)
 assert.equal(x.total_picks,5)
 assert.equal(x.status,'HISTORY_CONFLICT_NEEDS_REVIEW')
})

test('past week with two distinct entries remains two results; result source never qualifies sportsbook odds',()=>{
 const x=build()
 const week3=x.week_groups.find(g=>g.week===3)
 assert.equal(week3.picks.length,2)
 assert.equal(week3.required_picks,2)
 assert.equal(week3.official_sheet_recorded,true)
 for (const p of week3.picks){
  assert.equal(p.source_kind,'RECORDED_PERSONAL_POOL_HISTORY')
  assert.equal(p.external_submitted_verified,false)
  assert.equal('market_prob_pct' in p,false)
 }
})

test('no linked entry or invalid pool week reveals no history',()=>{
 assert.equal(buildSurvivorPastPickHistory(null,5).status,'NO_LINKED_ENTRY')
 assert.equal(buildSurvivorPastPickHistory({},0).status,'NO_LINKED_ENTRY')
 assert.equal(buildSurvivorPastPickHistory({},5).total_picks,0)
})
