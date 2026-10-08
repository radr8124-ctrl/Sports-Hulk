import test from 'node:test'
import assert from 'node:assert/strict'
import {compareFantasyTrade,normalizePlayerName} from './src/fantasyTradeResearch.js'

const now=Date.parse('2026-10-08T06:00:00Z')
const source='2026-10-08T05:40:00Z'
const rows=[
  {player:'Josh Allen',team:'BUF',position:'QB',ros_research_score:85.3,weekly_research_score:90,generated_at:source},
  {player:'Lamar Jackson',team:'BAL',position:'QB',ros_research_score:89.5,weekly_research_score:94,generated_at:source},
  {player:'James Cook',team:'BUF',position:'RB',ros_research_score:79.4,weekly_research_score:92,generated_at:source},
  {player:'Bijan Robinson',team:'ATL',position:'RB',ros_research_score:87.2,weekly_research_score:88,generated_at:source},
  {player:'CeeDee Lamb',team:'DAL',position:'WR',ros_research_score:88.3,weekly_research_score:95,generated_at:source},
]

function compare(give,receive, extra={}) {
  return compareFantasyTrade({give,receive,weeklyRows:rows,sourceGeneratedAt:source,nowMs:now,...extra})
}

test('an NFL RB-for-RB research delta is explicitly directional only',()=>{
  const r=compare(['James Cook'],['Bijan Robinson'],{savedRoster:['James Cook','Josh Allen']})
  assert.equal(r.status,'DIRECTIONAL_RESEARCH_ONLY')
  assert.equal(r.comparable,true)
  assert.equal(r.deltaRos,7.8)
  assert.deepEqual(r.givingNotOnSavedRoster,[])
  assert.equal(r.sourceFresh,true)
  assert.match(r.explanation,/not a fantasy-point forecast/)
  assert.equal(r.giving[0].weekly,92)
})

test('different NFL positions cannot be compared as if scores were fungible',()=>{
  const r=compare(['Josh Allen'],['CeeDee Lamb'])
  assert.equal(r.status,'DIFFERENT_POSITION_CONTEXT')
  assert.equal(r.comparable,false)
  assert.equal(r.deltaRos,null)
})

test('unequal player counts cannot produce a false winner for a two-for-one trade',()=>{
  const r=compare(['James Cook','Josh Allen'],['Bijan Robinson'])
  assert.equal(r.status,'DIFFERENT_PLAYER_COUNTS')
  assert.equal(r.deltaRos,null)
})

test('unrecognized player or missing research score forces insufficient coverage',()=>{
  const a=compare(['Not In Research'],['Bijan Robinson'])
  assert.equal(a.status,'INSUFFICIENT_PLAYER_COVERAGE')
  assert.equal(a.deltaRos,null)
  const b=compare(['James Cook'],['Bijan Robinson'],{weeklyRows:[{player:'James Cook',position:'RB',ros_research_score:''},rows[3]]})
  assert.equal(b.status,'INSUFFICIENT_PLAYER_COVERAGE')
})

test('stale, undated or future-dated snapshots cannot generate trade deltas',()=>{
  const stale=compare(['James Cook'],['Bijan Robinson'],{sourceGeneratedAt:'2026-09-05T05:00:00Z'})
  assert.equal(stale.status,'STALE_RESEARCH')
  assert.equal(stale.deltaRos,null)
  const missing=compare(['James Cook'],['Bijan Robinson'],{sourceGeneratedAt:null})
  assert.equal(missing.status,'STALE_RESEARCH')
  const future=compare(['James Cook'],['Bijan Robinson'],{sourceGeneratedAt:'2026-10-09T07:00:00Z'})
  assert.equal(future.status,'STALE_RESEARCH')
})

test('duplicate or same player on both sides blocks the comparison',()=>{
  const r=compare(['James Cook','James Cook'],['Bijan Robinson','Josh Allen'])
  assert.equal(r.status,'INVALID_COMPARISON')
  const same=compare(['James Cook'],['James Cook'])
  assert.equal(same.status,'INVALID_COMPARISON')
  assert.equal(same.deltaRos,null)
})

test('ambiguous player identity cannot be silently matched by the model',()=>{
  const duplicate={player:'James Cook',position:'QB',team:'OTHER',ros_research_score:72}
  const r=compare(['James Cook'],['Bijan Robinson'],{weeklyRows:[...rows,duplicate]})
  assert.equal(r.status,'INSUFFICIENT_PLAYER_COVERAGE')
  assert.equal(r.giving[0].ambiguous,true)
  assert.equal(r.giving[0].ros,null)
})

test('saved team mismatch is flagged but does not mutate or reveal another roster',()=>{
  const savedRoster=[{name:'Josh Allen'},{name:'James Cook'}]
  const original=JSON.stringify(savedRoster)
  const r=compare(['Bijan Robinson'],['James Cook'],{savedRoster})
  assert.deepEqual(r.givingNotOnSavedRoster,['Bijan Robinson'])
  assert.equal(JSON.stringify(savedRoster),original)
  assert.equal(r.status,'DIRECTIONAL_RESEARCH_ONLY')
})

test('no entries never fabricates an evaluation and normalization is predictable',()=>{
  assert.equal(compare([''],['']).status,'WAITING')
  assert.equal(normalizePlayerName('  J. Állen Jr. '),'j allen jr')
})
