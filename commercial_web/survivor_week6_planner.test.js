import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { buildSurvivorWeek6Plan, projectWeek6WhatIf } from './survivor_week6_planner.js'

const source=readFileSync(new URL('../nfl_live/derived/NFLVERSE_2026_SCHEDULE.csv',import.meta.url),'utf8')
const played=['Los Angeles Chargers','San Francisco 49ers','Kansas City Chiefs','Buffalo Bills','Minnesota Vikings']
const at='2026-10-10T19:00:00Z'
const defaults={poolWeek:5,entryStatus:'ALIVE',usedTeams:played,currentPicks:[],nowMs:Date.parse(at)}
const make=(x={})=>buildSurvivorWeek6Plan(source,{...defaults,...x})

test('the source-verifiable NFLverse Week 6 has 14 different matches, 28 unique teams, 4 correct byes',()=>{
 const plan=make()
 assert.equal(plan.status,'SCHEDULE_ONLY_UNRANKED')
 assert.equal(plan.pool_week,5)
 assert.equal(plan.target_week,6)
 assert.equal(plan.week5_required,1)
 assert.equal(plan.week6_required,2)
 assert.equal(plan.games.length,14)
 assert.deepEqual(plan.byes.sort(),['Cincinnati Bengals','Detroit Lions','Miami Dolphins','Minnesota Vikings'].sort())
 assert.match(plan.source_sha256,/^[a-f0-9]{64}$/)
 assert.equal(plan.schedule_source,'NFLVERSE_2026_SCHEDULE.csv')
 assert.equal(plan.qualification,'NOT_A_MODEL_RECOMMENDATION')
 assert.equal('estimated_win_probability' in plan,false)
 const playedTeams=plan.games.flatMap(r=>[r.home,r.away])
 assert.equal(new Set(playedTeams).size,28)
 assert.ok(plan.games.every(r=>/^2026_06_/.test(r.game_id)&&/2026-10-/.test(r.kickoff_et)))
})

test('unused Week 5 teams exclude burned teams and already-started Dallas game',()=>{
 const plan=make()
 assert.equal(plan.week5_what_if_teams.includes('Jacksonville Jaguars'),true)
 assert.equal(plan.week5_what_if_teams.includes('Cincinnati Bengals'),true)
 assert.equal(plan.week5_what_if_teams.includes('Dallas Cowboys'),false)
 assert.equal(plan.week5_what_if_teams.includes('Tampa Bay Buccaneers'),false)
 for(const team of played)assert.equal(plan.week5_what_if_teams.includes(team),false)
})

test('no team chosen stays undecided, and no model confidence or sportsbook odds are implied',()=>{
 const plan=make()
 const view=projectWeek6WhatIf(plan,'')
 assert.equal(view.status,'WHAT_IF_ONLY')
 assert.equal(view.hypothetical_week5_team,null)
 assert.equal(view.changed_saved_picks,false)
 assert.ok(view.eligible_week6_teams>0)
 assert.ok(view.distinct_game_pair_options>0)
 assert.ok(!JSON.stringify(view).includes('probability_pct'))
 assert.ok(!JSON.stringify(view).includes('RECOMMENDED'))
})

test('hypothetical Jacksonville removes one Week 6 option, Cincinnati on bye removes no extra Week 6 option',()=>{
 const plan=make()
 const base=projectWeek6WhatIf(plan,'')
 const jax=projectWeek6WhatIf(plan,'Jacksonville Jaguars')
 const cin=projectWeek6WhatIf(plan,'Cincinnati Bengals')
 assert.equal(jax.eligible_week6_teams,base.eligible_week6_teams-1)
 assert.equal(cin.eligible_week6_teams,base.eligible_week6_teams)
 assert.equal(jax.hypothetical_week5_team,'Jacksonville Jaguars')
 assert.equal(jax.changed_saved_picks,false)
 const one=jax.games.find(g=>g.game_id==='2026_06_HOU_JAX')
 assert.deepEqual(one.eligible_teams,['Houston Texans'])
 assert.equal(jax.distinct_game_pair_options<base.distinct_game_pair_options,true)
})

test('pairs from opposing sides of the same game are never counted as both winning picks',()=>{
 const plan=make()
 const result=projectWeek6WhatIf(plan,'Houston Texans')
 assert.ok(result.games.every(g=>g.eligible_teams.length<=2))
 let total=0
 for(let i=0;i<result.games.length;i++)for(let j=i+1;j<result.games.length;j++){
  total+=result.games[i].eligible_teams.length*result.games[j].eligible_teams.length
 }
 assert.equal(result.distinct_game_pair_options,total)
 assert.equal(result.games.find(g=>g.game_id==='2026_06_HOU_JAX').eligible_teams.includes('Houston Texans'),false)
})

test('a previously saved Week 5 pick locks what-if to actual saved team and blocks other what-ifs',()=>{
 const plan=make({currentPicks:['Jacksonville Jaguars']})
 assert.equal(plan.saved_week5_team,'Jacksonville Jaguars')
 assert.equal(projectWeek6WhatIf(plan,'').hypothetical_week5_team,'Jacksonville Jaguars')
 assert.equal(projectWeek6WhatIf(plan,'Jacksonville Jaguars').status,'SAVED_IN_ZENITH_ONLY')
 assert.equal(projectWeek6WhatIf(plan,'Houston Texans').status,'OTHER_SCENARIO_BLOCKED_SAVED_PICK')
 assert.equal(plan.week5_what_if_teams.length,0)
})

test('used teams and byes never appear as eligible Week 6 selections',()=>{
 const result=projectWeek6WhatIf(make(),'')
 for(const team of [...played,'Cincinnati Bengals','Miami Dolphins','Detroit Lions']){
  assert.equal(result.games.some(g=>g.eligible_teams.includes(team)),false,team)
 }
})

test('after Week 5 original Saturday deadline no unsaved what-if is presented as an eligible late choice',()=>{
 const plan=make({nowMs:Date.parse('2026-10-10T22:01:00Z')})
 assert.equal(plan.status,'SCHEDULE_ONLY_UNRANKED')
 assert.equal(plan.week5_deadline_passed,true)
 assert.equal(plan.week5_what_if_teams.length,0)
 assert.equal(projectWeek6WhatIf(plan,'Jacksonville Jaguars').status,'INVALID_WEEK5_WHAT_IF')
 assert.equal(plan.week5_pool_deadline_et,'2026-10-10T18:00:00-04:00')
})

test('Week 6 Thursday kickoff and conditional earlier deadline derive from source time',()=>{
 const plan=make()
 const first=plan.games[0]
 assert.equal(first.game_id,'2026_06_SEA_DEN')
 assert.equal(first.kickoff_et,'2026-10-15T20:15:00-04:00')
 assert.equal(plan.earliest_kickoff_et,'2026-10-15T20:15:00-04:00')
 assert.equal(plan.early_game_cutoff_et,'2026-10-15T18:15:00-04:00')
})

test('bad roster, unknown or reused Week 5 what-if, wrong pool week fail closed',()=>{
 assert.equal(make({poolWeek:6}).status,'POOL_WEEK_NOT_FIVE')
 assert.equal(make({entryStatus:'ELIMINATED'}).status,'ENTRY_NOT_ACTIVE')
 for(const team of ['Dallas Cowboys','Buffalo Bills','Not an NFL Team']){
  assert.equal(projectWeek6WhatIf(make(),team).status,'INVALID_WEEK5_WHAT_IF')
 }
 assert.equal(buildSurvivorWeek6Plan(source.replace('2026_06_HOU_JAX','2026_06_SEA_DEN'),defaults).status,'SCHEDULE_SOURCE_CONFLICT')
 assert.equal(buildSurvivorWeek6Plan('oops',defaults).status,'SCHEDULE_SOURCE_CONFLICT')
})
