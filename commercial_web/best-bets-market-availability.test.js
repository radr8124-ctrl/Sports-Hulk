import test from 'node:test'
import assert from 'node:assert/strict'
import {BET_SPORT_FILTERS,BET_MARKET_FILTERS,sourceMarketStatus,nflUpcomingSchedule} from './best_bets_market_availability.js'

const byProofLane={
  NFL_MONEYLINE:{history_n:16,independent_blocks:16,selection_rule_status:'INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY'},
  NFL_SPREAD:{history_n:16,independent_blocks:16,selection_rule_status:'INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY'},
  NFL_TOTAL:{history_n:13,independent_blocks:13,selection_rule_status:'INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY'},
  CFB_MONEYLINE:{history_n:92,independent_blocks:58,selection_rule_status:'NO_INDEPENDENT_MODEL_EDGE'},
}
const marketBoard=Array.from({length:13},(_,i)=>({sport:'NFL',game_key:`g${i}`,decision_current:'PASS_STALE_MARKET',selection:'Team'}))
const picks=Array.from({length:39},(_,i)=>({sport:'CFB',market:'MONEYLINE',game_key:`cfb-${i}`,shadow_decision:'PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE'}))
  .concat(Array.from({length:5},(_,i)=>({sport:'NHL',market:'MONEYLINE',game_key:`nhl-${i}`,shadow_decision:'PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE'})))

test('sports + Point Spreads + Totals filters always visible even with zero qualified rows',()=>{
 assert.deepEqual(BET_SPORT_FILTERS,['NFL','CFB','NBA','NHL','MLB','CBB'])
 assert.deepEqual(BET_MARKET_FILTERS.map(m=>m.id),['ALL','MONEYLINE','SPREAD','TOTAL'])
 assert.equal(BET_MARKET_FILTERS.find(m=>m.id==='SPREAD').label,'Point spreads')
})

test('NFL source data stale is separate from approved selections',()=>{
 const x=sourceMarketStatus({sport:'NFL',market:'SPREAD',picks,byProofLane,marketBoard})
 assert.equal(x.candidateCount,0)
 assert.equal(x.approvedPlayCount,0)
 assert.equal(x.nflStaleUpstreamMoneylineCount,13)
 assert.deepEqual(x.categories.map(y=>[y.sport,y.market,y.historyCount,y.independent,y.approvedPlayCount]),
   [['NFL','SPREAD',16,16,0]])
 assert.equal(x.researchNotApproved,true)
})

test('NFL totals absence and independent game record shown without inventing prices',()=>{
 const x=sourceMarketStatus({sport:'NFL',market:'TOTAL',picks,byProofLane,marketBoard})
 assert.equal(x.categories[0].historyCount,13)
 assert.equal(x.categories[0].independent,13)
 assert.equal(x.candidateCount,0)
 assert.equal(x.approvedPlayCount,0)
})

test('legacy or source-market picks do not turn into approved Best Bets',()=>{
 const b=sourceMarketStatus({picks,byProofLane,marketBoard})
 assert.equal(b.candidateCount,44)
 assert.equal(b.researchCount,44)
 assert.equal(b.approvedPlayCount,0)
 assert.equal(b.nflStaleUpstreamMoneylineCount,13)
})

test('sport market views retain data truth; filters no synthetic candidates',()=>{
 const c=sourceMarketStatus({sport:'CFB',market:'MONEYLINE',picks,byProofLane})
 assert.equal(c.candidateCount,39)
 assert.equal(c.categories[0].independent,58)
 assert.equal(c.categories[0].historyCount,92)
 assert.equal(c.categories[0].approvedPlayCount,0)
 const empty=sourceMarketStatus({sport:'CFB',market:'SPREAD',picks,byProofLane})
 assert.equal(empty.candidateCount,0)
 assert.equal(empty.approvedPlayCount,0)
})

test('a truly source qualified shadow play remains a paper qualifier, never a placed wager',()=>{
 const x=sourceMarketStatus({sport:'NFL',market:'SPREAD',picks:[{sport:'NFL',market:'SPREAD',shadow_decision:'SHADOW_PLAY'}],byProofLane})
 assert.equal(x.approvedPlayCount,1)
 assert.equal(x.categories[0].approvedPlayCount,1)
})

test('NFL official schedule deduplicated by event ID; final/past/unknown games rejected',()=>{
 const now=Date.parse('2026-10-09T18:00:00Z')
 const r={next_games:[
  {event_id:'1',away_abbr:'HOU',home_abbr:'TEN',start_time:'2026-10-11T17:00:00Z',state:'pre'},
  {event_id:'1',away_abbr:'HOU',home_abbr:'TEN',start_time:'2026-10-11T17:00:00Z',state:'pre'},
  {event_id:'2',away_abbr:'SF',home_abbr:'SEA',start_time:'2026-10-11T20:25:00Z',state:'pre'},
  {event_id:'3',away_abbr:'TB',home_abbr:'DAL',start_time:'2026-10-08T00:00:00Z',state:'post',final:true},
  {event_id:'4',away_abbr:'BAL',home_abbr:'ATL',start_time:'2026-10-12T00:20:00Z',state:'pre'},
  {event_id:'5',start_time:'bad-time',state:'pre'}
 ]}
 const a=nflUpcomingSchedule(r,now,15)
 assert.deepEqual(a.map(g=>g.event_id),['1','2','4'])
 assert.deepEqual(nflUpcomingSchedule(r,now,2).map(g=>g.event_id),['1','2'])
 assert.deepEqual(nflUpcomingSchedule(r,now,0),[])
})
