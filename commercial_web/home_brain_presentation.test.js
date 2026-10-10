import test from 'node:test'
import assert from 'node:assert/strict'
import {homeBrainSnapshot} from './home_brain_presentation.js'

// Frozen synthetic fixture shaped like the Oct 10 official three-pick sample.
// Do not test against the mutable production feed: its results will settle.
const frozen={
 official:{published:3,settled:1,pending:2,wins:0,losses:1,pushes:0},
 official_recent:[{
  official:true,event_type:'SETTLED',grade:'LOSS',
  pick_id:'original-official-game-1',
  selection:'New Orleans Saints',game_key:'ATL@NO',
  american_odds:-141,result:'ATL 45 - 24 NO',
  settled_at:'2026-10-06T04:05:14Z',
 }]
}

test('a one-game official record explains sample size and sources the loss',()=>{
 const r=homeBrainSnapshot(frozen)
 assert.equal(r.status,'READY')
 assert.equal(r.headline,'1 pick graded')
 assert.equal(r.summary,'0 wins · 1 loss · 2 pending')
 assert.equal(r.graded,1)
 assert.equal(r.published,3)
 assert.equal(r.lastResult.pick,'New Orleans Saints to win (-141)')
 assert.equal(r.lastResult.outcome,'Lost')
 assert.equal(r.lastResult.score,'ATL 45 - 24 NO')
 assert.match(r.clarity,/not every Zenith model/i)
 assert.match(r.sampleWarning,/Too few/)
})

test('inconsistent official counts never silently default to a winning record',()=>{
 for(const damaged of [
   {},
   {official:{...frozen.official,wins:9}},
   {official:{...frozen.official,pending:-1}},
   {official:{...frozen.official,settled:3}},
 ]){
  const r=homeBrainSnapshot(damaged)
  assert.equal(r.status,'SOURCE_UNVERIFIED')
  assert.equal(r.lastResult,null)
 }
})

test('the home summary has no private Survivor ticket names',()=>{
 const result=homeBrainSnapshot(frozen)
 assert.equal(JSON.stringify(result).includes('ANNIE G'),false)
 assert.equal(result.lastResult.event,'ATL@NO')
})

test('official record remains valid without game detail and never invents a loss cause',()=>{
 const r=homeBrainSnapshot({...frozen,official_recent:[]})
 assert.equal(r.status,'READY')
 assert.equal(r.lastResult,null)
})

test('future settled results update headline and sample warning naturally',()=>{
 const multi=homeBrainSnapshot({official:{published:25,settled:20,pending:5,wins:12,losses:8,pushes:0},official_recent:[]})
 assert.equal(multi.headline,'20 picks graded')
 assert.equal(multi.summary,'12 wins · 8 losses · 5 pending')
 assert.equal(multi.lastResult,null)
 assert.doesNotMatch(multi.sampleWarning,/Too few/)
})
