import test from 'node:test'
import assert from 'node:assert/strict'
import { buildLinkedSurvivorSummaries } from './survivor_linked_entries.js'
test('last completed pick is shown separately from empty current week', () => {
 const state={pool_current_week:5,entries:{'ANNIE G 01':{status:'ALIVE',current_picks:[],used_teams:['Minnesota Vikings'],week_4:{picks:[{team:'Minnesota Vikings',result:'WIN'}],entry_result:'WIN'},week_5:{picks:[],entry_result:'OPEN'}}}}
 const [entry]=buildLinkedSurvivorSummaries(['ANNIE G 01'],state)
 assert.deepEqual(entry.current_picks,[])
 assert.equal(entry.last_completed_week,4)
 assert.equal(entry.last_completed_picks[0].team,'Minnesota Vikings')
 assert.equal(entry.last_completed_picks[0].result,'SURVIVED')
})

test('unsettled past-week selections are not described as a completed Survivor result',()=>{
 const state={pool_current_week:5,entries:{'SAMPLE 01':{
  status:'ALIVE',current_picks:[],used_teams:['Minnesota Vikings'],
  week_4:{picks:[{team:'Minnesota Vikings',result:'PENDING'}],entry_result:'OPEN'},
  week_3:{picks:[{team:'Kansas City Chiefs',result:'WIN'}],entry_result:'WIN'},
 }}}
 const [entry]=buildLinkedSurvivorSummaries(['SAMPLE 01'],state)
 assert.equal(entry.last_completed_week,3)
 assert.deepEqual(entry.last_completed_picks,[{team:'Kansas City Chiefs',result:'SURVIVED'}])
})

test('partially settled multi-pick weeks do not count as fully completed',()=>{
 const state={pool_current_week:6,entries:{'SAMPLE 01':{
  status:'ALIVE',current_picks:[],used_teams:[],
  week_5:{picks:[{team:'Detroit Lions',result:'WIN'},{team:'Miami Dolphins',result:'PENDING'}],entry_result:'OPEN'},
  week_4:{picks:[{team:'Minnesota Vikings',result:'WIN'}],entry_result:'WIN'},
 }}}
 const [entry]=buildLinkedSurvivorSummaries(['SAMPLE 01'],state)
 assert.equal(entry.last_completed_week,4)
 assert.equal(entry.last_completed_picks[0].team,'Minnesota Vikings')
})
