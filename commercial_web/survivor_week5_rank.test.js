import test from 'node:test'
import assert from 'node:assert/strict'
import { rankSurvivorCandidates, selectSurvivorAskChoice } from './survivor_week5_rank.js'
test('viable Week 5 candidates outrank AVOID irrespective of raw strategy score', () => {
 const rows=[{team:'Cincinnati Bengals',strategy_index:72.3,strategy_action:'AVOID'}, {team:'Dallas Cowboys',strategy_index:73.8,strategy_action:'VIABLE'}, {team:'Baltimore Ravens',strategy_index:67.2,strategy_action:'VIABLE'}, {team:'Seattle Seahawks',strategy_index:66.3,strategy_action:'WATCH'}]
 const result=rankSurvivorCandidates(rows,[])
 assert.deepEqual(result.map(r=>r.team),['Dallas Cowboys','Baltimore Ravens','Seattle Seahawks','Cincinnati Bengals'])
 assert.equal(rankSurvivorCandidates(rows,['Dallas Cowboys'])[0].team,'Baltimore Ravens')
})


test('Ask Week 5 selects array shadow choice, never a higher-score AVOID or already-used team', () => {
 const model={pool_current_week:5,rule_confirmed:true,recommendation_status:'SHADOW_RECOMMENDATION_READY',
  used_teams:['Minnesota Vikings'],
  candidates:[{team:'Cincinnati Bengals',strategy_action:'AVOID',decision_tier:'CAUTION',strategy_index:91},
    {team:'Dallas Cowboys',strategy_action:'VIABLE',decision_tier:'VIABLE',strategy_index:75},
    {team:'Minnesota Vikings',strategy_action:'VIABLE',strategy_index:99}],
  shadow_recommendation:[{team:'Dallas Cowboys',strategy_action:'VIABLE',strategy_index:75}]}
 const outcome=selectSurvivorAskChoice(model)
 assert.equal(outcome.modelReady,true)
 assert.equal(outcome.top.team,'Dallas Cowboys')
 assert.deepEqual(outcome.candidates.map(v=>v.team),['Dallas Cowboys'])
 const waiting=selectSurvivorAskChoice({...model,recommendation_status:'WAITING_FOR_PROOF',shadow_recommendation:[]})
 assert.equal(waiting.modelReady,false)
 assert.equal(waiting.top.team,'Dallas Cowboys')
})


test('Ask never suggests a market favorite when primary Survivor quote is stale', () => {
 const blocked=selectSurvivorAskChoice({
   rule_confirmed:true, recommendation_status:'WAIT_FOR_FRESH_VERIFIED_MARKET_QUOTES',
   candidates:[{team:'Cincinnati Bengals',market_prob_pct:null,spread:null,
      primary_market_source_status:'PRIMARY_PRICE_UNVERIFIED_OR_STALE',
      strategy_action:'WAIT_FOR_FRESH_PRICES',eligible_for_shadow:false}],
   shadow_recommendation:[],
 })
 assert.equal(blocked.modelReady,false)
 assert.equal(blocked.top,null)
 assert.deepEqual(blocked.candidates,[])
})
