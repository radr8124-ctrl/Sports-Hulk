import test from 'node:test'
import assert from 'node:assert/strict'
import { explainBetProof, organizeBetResearch } from './betting_proof_presentation.js'

test('low-history market explains exact proof gap without calling research a recommendation', () => {
  const proof=explainBetProof({sport:'NBA',market:'MONEYLINE',proof_lane_key:'NBA_MONEYLINE|PRESEASON',selection_rule_status:'INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY',lane_history_n:5,shadow_decision:'PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE'}, {'NBA_MONEYLINE|PRESEASON':{history_n:5,independent_blocks:5}})
  assert.equal(proof.kind,'HISTORY_BUILDING')
  assert.equal(proof.label,'Building history')
  assert.match(proof.description,/5 of 50 pregame outcomes/i)
  assert.match(proof.description,/5 of 25 separate games/i)
  assert.equal(proof.isPlay,false)
  assert.equal(proof.estimateLabel,'Market-based estimate')
})

test('ready CFB validation with no independent model edge gets a distinct plain language explanation', () => {
  const proof=explainBetProof({sport:'CFB',market:'MONEYLINE',selection_rule_status:'NO_INDEPENDENT_MODEL_EDGE',shadow_decision:'PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE'}, {})
  assert.equal(proof.kind,'NO_PROVEN_EDGE')
  assert.equal(proof.label,'No proven edge')
  assert.match(proof.description,/did not beat the market/i)
  assert.equal(proof.isPlay,false)
})

test('model lacks lane proof count: never invent missing independent-game evidence', () => {
  const proof=explainBetProof({selection_rule_status:'INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY',lane_history_n:40},{})
  assert.match(proof.description,/40 of 50/i)
  assert.doesNotMatch(proof.description,/of 25 separate games/i)
})

test('organizer never upgrades PASS to PLAY; separates filtered research from validated plays', () => {
  const candidates=[
    {sport:'NBA',market:'MONEYLINE',selection_rule_status:'INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY',shadow_decision:'PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE',game_key:'g1'},
    {sport:'CFB',market:'MONEYLINE',selection_rule_status:'NO_INDEPENDENT_MODEL_EDGE',shadow_decision:'PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE',game_key:'g2'},
    {sport:'CFB',market:'SPREAD',selection_rule_status:'FORWARD_VALIDATION_REQUIRED',shadow_decision:'SHADOW_PLAY',game_key:'g3'},
  ]
  const group=organizeBetResearch(candidates,'CFB','ALL')
  assert.equal(group.plays.length,1)
  assert.equal(group.research.length,1)
  assert.equal(group.plays[0].game_key,'g3')
  assert.equal(group.research[0].game_key,'g2')
  assert.equal(organizeBetResearch(candidates,'NBA','MONEYLINE').plays.length,0)
})
